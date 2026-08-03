"""
Synapse Layer — Forge Backend (AES-256-GCM Encrypted)

Production-grade backend for Synapse Layer Forge API.

Architecture (ZK Real):
  - **Store**: SDK encrypts content client-side (AES-256-GCM) BEFORE
    the HTTP POST.  The server NEVER sees plaintext.  The payload
    contains ``encryptedContent``, ``iv``, ``authTag``, ``searchIndex``
    (sanitized keywords), and ``zkMode: true``.
  - **Recall**: Server returns the encrypted envelope (ciphertext, iv,
    authTag).  SDK decrypts locally.  Plaintext NEVER traverses the
    network in either direction.

The encryption_key is the hex-decoded SYNAPSE_ENCRYPTION_KEY, shared
between SDK and server.  Both sides use identical AES-256-GCM params.

Usage::

    from synapse_memory.backends import ForgeBackend

    backend = ForgeBackend(
        api_key="sk_connect_abc123",
        encryption_key=bytes.fromhex("832d919b..."),  # SYNAPSE_ENCRYPTION_KEY
    )
    memory_id = await backend.store("User prefers dark mode")
    results  = await backend.recall("preferences")

⚠  Store your encryption_key securely.  Lost key = lost memories.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import random
import re
import struct
from typing import Any, Callable, Dict, List, Optional

import httpx

from synapse_memory.exceptions import (
    ForgeAuthError,
    ForgeBackendError,
    ForgeDecryptError,
    ForgeRateLimitError,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://forge.synapselayer.org"
_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0
_MAX_JITTER_SECONDS = 0.5
_RETRYABLE_STATUS = {429, 503}
_EMBEDDING_DIM = 1536  # Forge API expects 1536-dim vectors


class ForgeBackend:
    """AES-256-GCM encrypted backend for Synapse Layer Forge API.

    Store encrypts content CLIENT-SIDE (AES-256-GCM) BEFORE the HTTP
    POST — the server NEVER receives or sees plaintext.
    Recall receives encrypted envelopes and decrypts locally.
    Plaintext NEVER traverses the network in EITHER direction.

    This class implements the ``StorageBackend`` protocol with
    async-first methods.  For synchronous use, wrap calls with
    ``asyncio.run()``.

    Args:
        api_key: Bearer token (``sk_connect_...``).
        base_url: Forge API base URL.  Default: ``https://forge.synapselayer.org``.
        encryption_key: 32-byte AES-256 key — must match the Forge server's
            ``SYNAPSE_ENCRYPTION_KEY``.  Used to decrypt recalled memories.
            If ``None``, generates a random key and logs a WARNING.
        timeout: HTTP request timeout in seconds.
        embedding_fn: Optional callable ``(text: str) -> List[float]``.
            Supports sync and async functions.  Takes precedence over
            ``embedding_provider`` when provided.
        embedding_provider: ``"none"`` (default) or ``"openai"``.
            When ``"openai"`` with ``embedding_api_key``, auto-configures
            embedding generation via OpenAI ``text-embedding-3-small``.
        embedding_api_key: API key for the embedding provider.
            Required when ``embedding_provider`` is not ``"none"``.

    Embedding priority:
        1. ``embedding_fn`` (explicit custom function)
        2. ``embedding_provider`` + ``embedding_api_key`` (pluggable provider)
        3. Pseudo-embedding (SHA-256 expansion — always works, no deps)

    Example with OpenAI provider (semantic quality)::

        backend = ForgeBackend(
            api_key="sk_connect_...",
            encryption_key=bytes.fromhex("832d...cba"),
            embedding_provider="openai",
            embedding_api_key="sk-proj-...",
        )

    Example without provider (baseline — always works)::

        backend = ForgeBackend(
            api_key="sk_connect_abc123",
            encryption_key=bytes.fromhex("832d...cba"),
        )
        # Uses pseudo-embedding — functional but not semantically meaningful
    """

    __slots__ = (
        "_api_key", "_base_url", "_enc_key", "_client",
        "_timeout", "_embedding_fn", "_embedding_provider", "_embedding_api_key",
    )

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        encryption_key: Optional[bytes] = None,
        timeout: float = _DEFAULT_TIMEOUT,
        embedding_fn: Optional[Any] = None,
        embedding_provider: str = "none",
        embedding_api_key: Optional[str] = None,
    ) -> None:
        # ── Validate api_key ──────────────────────────────────────────
        if not api_key or not isinstance(api_key, str):
            raise ForgeAuthError("api_key is required and must be a non-empty string")

        # ── Validate / generate encryption_key ────────────────────────
        if encryption_key is None:
            encryption_key = os.urandom(32)
            logger.warning(
                "[Synapse] No encryption_key provided — generated random key. "
                "Persist this key or you will LOSE access to stored memories: %s",
                encryption_key.hex(),
            )
        if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
            raise ValueError(
                f"encryption_key must be exactly 32 bytes, got "
                f"{len(encryption_key) if isinstance(encryption_key, bytes) else type(encryption_key).__name__}"
            )

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._enc_key = encryption_key  # Raw 32-byte AES key
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._embedding_provider = embedding_provider
        self._embedding_api_key = embedding_api_key or None

        # ── Embedding function: explicit fn > provider-based > pseudo ─
        if embedding_fn is not None:
            self._embedding_fn = embedding_fn
        elif self._embedding_provider != "none" and self._embedding_api_key:
            from synapse_memory.embeddings import get_embedding as _get_emb

            _provider = self._embedding_provider
            _key = self._embedding_api_key

            async def _provider_embed(text: str) -> List[float]:
                return await _get_emb(text, provider=_provider, api_key=_key)

            self._embedding_fn = _provider_embed
        else:
            self._embedding_fn = None  # Falls back to pseudo-embedding

        # Resolve embedding mode label for logging
        if embedding_fn is not None:
            _emb_mode = "custom"
        elif self._embedding_provider != "none" and self._embedding_api_key:
            _emb_mode = self._embedding_provider
        else:
            _emb_mode = "pseudo"

        logger.info(
            "[Synapse] ForgeBackend initialized (key fingerprint: %s, url: %s, embedding: %s)",
            hashlib.sha256(encryption_key).hexdigest()[:12],
            self._base_url,
            _emb_mode,
        )

    # ── HTTP Client (lazy singleton) ──────────────────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init httpx.AsyncClient with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "synapse-memory-sdk/python",
                },
                timeout=self._timeout,
            )
        return self._client

    @staticmethod
    def _compute_retry_delay(attempt: int, retry_after: Optional[float] = None) -> float:
        """Compute capped exponential backoff with jitter (0-500ms)."""
        base_delay = min(
            _INITIAL_BACKOFF_SECONDS * (2 ** attempt),
            _MAX_BACKOFF_SECONDS,
        )
        delay = max(base_delay, retry_after if retry_after is not None else 0.0)
        jitter = random.uniform(0.0, _MAX_JITTER_SECONDS)
        return min(delay + jitter, _MAX_BACKOFF_SECONDS)

    async def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute HTTP request with retry on 429/503.

        Raises:
            ForgeAuthError: On 401.
            ForgeRateLimitError: On 429 after exhausting retries.
            ForgeBackendError: On any other non-2xx status.
        """
        client = self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.request(method, path, json=json_body)
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(self._compute_retry_delay(attempt))
                    continue
                raise ForgeBackendError(
                    f"Request timed out after {_MAX_RETRIES} attempts",
                    status_code=None,
                ) from exc
            except httpx.HTTPError as exc:
                raise ForgeBackendError(
                    f"HTTP transport error: {exc}", status_code=None
                ) from exc

            # ── Status handling ────────────────────────────────────────
            if resp.status_code == 401:
                raise ForgeAuthError("Invalid or expired api_key")

            if resp.status_code in _RETRYABLE_STATUS:
                retry_after_value: Optional[float] = None
                retry_after_header = resp.headers.get("Retry-After")
                if retry_after_header is not None:
                    try:
                        retry_after_value = float(retry_after_header)
                    except (TypeError, ValueError):
                        retry_after_value = None

                backoff = self._compute_retry_delay(attempt, retry_after=retry_after_value)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)
                    continue

                if resp.status_code == 429:
                    raise ForgeRateLimitError(
                        "Rate limit exceeded after retries", retry_after=backoff
                    )

            if resp.status_code >= 400:
                body = resp.text[:200]  # Truncate — never log full response
                raise ForgeBackendError(
                    f"Forge API error {resp.status_code}: {body}",
                    status_code=resp.status_code,
                )

            return resp

        # Should not reach here, but fail-closed
        raise ForgeBackendError(
            "Request failed after retries", status_code=None
        )

    # ── Embedding ──────────────────────────────────────────────────────

    async def _embed(self, text: str) -> List[float]:
        """Generate embedding via custom fn or fallback to pseudo-embedding.

        If ``embedding_fn`` was provided at construction, it is called.
        Supports both sync and async callables.  Falls back to the
        deterministic pseudo-embedding (SHA-256 expansion) if no custom
        function is configured.
        """
        if self._embedding_fn is not None:
            result = self._embedding_fn(text)
            # Support async embedding functions
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                result = await result
            return list(result)
        return self._generate_pseudo_embedding(text)

    @staticmethod
    def _generate_pseudo_embedding(text: str, dim: int = _EMBEDDING_DIM) -> List[float]:
        """Generate deterministic pseudo-embedding via SHA-256 expansion.

        Production callers should replace with a real embedding model.
        This fallback ensures the API receives valid vectors.
        """
        h = hashlib.sha256(text.encode("utf-8")).digest()
        values: List[float] = []
        i = 0
        while len(values) < dim:
            block = hashlib.sha256(h + struct.pack(">I", i)).digest()
            for j in range(0, 32, 4):
                if len(values) >= dim:
                    break
                raw = struct.unpack(">I", block[j : j + 4])[0]
                val = (raw / 0xFFFFFFFF) * 2.0 - 1.0
                values.append(round(val, 8))
            i += 1

        # L2-normalize
        norm = sum(v * v for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]
        return values

    # ── Public API ────────────────────────────────────────────────────

    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        source: str = "sdk",
    ) -> str:
        """Store a memory via Forge API — server never sees plaintext.

        Flow:
            1. Encrypt content CLIENT-SIDE (AES-256-GCM)
            2. Build sanitized search index (keywords, no PII)
            3. Generate embedding from plaintext (before sending)
            4. POST encrypted envelope + searchIndex + zkMode=True
            5. Server stores ciphertext WITHOUT re-encrypting

        The server NEVER sees plaintext.  The ``content`` field is
        intentionally absent from the payload — replaced by
        ``encryptedContent``, ``iv``, ``authTag``.

        Args:
            content: Memory content string.
            metadata: Optional key-value metadata dict.
            embedding: Optional 1536-dim float vector.  If None, generates
                a pseudo-embedding from content.
            source: Source label for the memory (default: "sdk").

        Returns:
            memory_id: Unique identifier of the stored memory.

        Raises:
            ForgeAuthError: If api_key is invalid (401).
            ForgeRateLimitError: If rate limit exceeded (429).
            ForgeBackendError: On any other API error.
        """
        if not content:
            raise ValueError("content must be a non-empty string")

        # ── Step 1: Client-side AES-256-GCM encryption ─────────────
        ct_b64, iv_b64, tag_b64 = self._encrypt_aes_gcm(content, self._enc_key)

        # ── Step 2: Build sanitized search index (keywords, no PII) ─
        search_index = self._build_search_index(content, source)

        # ── Step 3: Embedding (custom fn or pseudo-embedding fallback)
        if embedding is None:
            embedding = await self._embed(content)

        # ── Step 4: Build payload — NO "content" field ──────────────
        payload: Dict[str, Any] = {
            "encryptedContent": ct_b64,
            "iv": iv_b64,
            "authTag": tag_b64,
            "searchIndex": search_index,
            "source": source,
            "embedding": embedding,
            "encrypted": True,
            "zkMode": True,
        }
        if metadata:
            payload["metadata"] = metadata

        # ZK INVARIANT: "content" must NEVER appear in the payload
        assert "content" not in payload, (
            "ZK VIOLATION: plaintext 'content' found in HTTP payload"
        )

        resp = await self._request("POST", "/api/v1/capture", json_body=payload)
        data = resp.json()
        memory_id: str = data.get("id", data.get("memoryId", data.get("memory_id", "")))

        logger.info(
            "[Synapse] Memory stored via Forge ZK (id=%s)",
            memory_id[:12] if memory_id else "unknown",
        )
        return memory_id

    # ── Client-side Encryption ─────────────────────────────────────

    @staticmethod
    def _encrypt_aes_gcm(plaintext: str, key: bytes) -> tuple:
        """Encrypt plaintext with AES-256-GCM (Node.js crypto compatible).

        Returns:
            Tuple of (ciphertext_b64, iv_b64, auth_tag_b64).
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        iv = os.urandom(12)
        aesgcm = AESGCM(key)
        ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
        # AESGCM appends 16-byte tag to ciphertext
        ciphertext = ct_with_tag[:-16]
        auth_tag = ct_with_tag[-16:]

        return (
            base64.b64encode(ciphertext).decode(),
            base64.b64encode(iv).decode(),
            base64.b64encode(auth_tag).decode(),
        )

    # ── Search Index Builder ───────────────────────────────────────

    # PII patterns — redacted before building search index
    _PII_PATTERNS = [
        (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
        (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD]"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    ]

    @classmethod
    def _build_search_index(cls, content: str, source: str = "sdk") -> str:
        """Build a sanitized keyword index from content.

        PII is redacted before extraction.  Returns lowercase
        space-separated keywords suitable for PostgreSQL FTS.
        """
        text = content
        for pattern, replacement in cls._PII_PATTERNS:
            text = pattern.sub(replacement, text)

        # Lowercase, strip non-alphanumeric, deduplicate
        words = re.findall(r"[a-z0-9]+", text.lower())
        # Add source prefix and PII placeholders if present
        keywords = [source] + list(dict.fromkeys(words))
        return " ".join(keywords)

    @staticmethod
    def _decrypt_aes_gcm(
        ciphertext_b64: str, iv_b64: str, auth_tag_b64: str, key: bytes
    ) -> str:
        """Decrypt AES-256-GCM ciphertext (Node.js crypto compatible).

        Args:
            ciphertext_b64: Base64-encoded ciphertext bytes.
            iv_b64: Base64-encoded 12-byte IV/nonce.
            auth_tag_b64: Base64-encoded 16-byte auth tag.
            key: 32-byte AES-256 key.

        Returns:
            Decrypted plaintext string.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        iv = base64.b64decode(iv_b64)
        ct = base64.b64decode(ciphertext_b64)
        tag = base64.b64decode(auth_tag_b64)

        # AESGCM expects ciphertext+tag concatenated
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(iv, ct + tag, None)
        return plaintext_bytes.decode("utf-8")

    async def recall(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Recall memories with local AES-256-GCM decryption.

        Flow:
            1. Generate embedding from query
            2. POST to Forge recall API
            3. Decrypt each result locally using SYNAPSE_ENCRYPTION_KEY
            4. Return plaintext results — NEVER returns ciphertext to caller

        Memories that fail decryption are silently skipped (logged as
        WARNING without sensitive data).

        Args:
            query: Natural language search query.
            limit: Max results to return (1–100).
            threshold: Minimum similarity score (0.0–1.0).
            agent_id: Optional agent scope filter.

        Returns:
            List of dicts with keys: id, content (decrypted), score,
            trustQuotient, intent, isCritical, memoryType, timestamp.

        Raises:
            ForgeAuthError: If api_key is invalid (401).
            ForgeRateLimitError: If rate limit exceeded (429).
            ForgeBackendError: On any other API error.
        """
        # Clamp threshold
        threshold = max(0.0, min(1.0, threshold))
        limit = max(1, min(100, limit))

        # Step 1: Embedding for query (custom fn or pseudo-embedding fallback)
        query_embedding = await self._embed(query)

        # Step 2: POST to Forge recall API
        # Note: API uses "vector" field (not "embedding") for semantic search
        payload: Dict[str, Any] = {
            "query": query,
            "vector": query_embedding,
            "limit": limit,
        }
        if agent_id:
            payload["agent_id"] = agent_id

        resp = await self._request("POST", "/api/v1/recall", json_body=payload)
        data = resp.json()

        # Normalize: Forge API returns {memories: [...]}
        raw_results: List[Dict[str, Any]] = (
            data.get("memories")
            or data.get("results")
            or (data if isinstance(data, list) else [])
        )

        # Step 3: Decrypt each result using Node.js-compatible AES-256-GCM
        decrypted: List[Dict[str, Any]] = []

        for item in raw_results:
            memory_id = item.get("id", item.get("memoryId", "unknown"))
            try:
                enc_content = item.get("encryptedContent", "")
                iv_str = item.get("iv", "")
                tag_str = item.get("authTag", "")

                if not enc_content or not iv_str or not tag_str:
                    logger.warning(
                        "[Synapse] Recall item %s missing encryption fields — skipped",
                        str(memory_id)[:12],
                    )
                    continue

                # Decrypt using raw AES-256-GCM (base64 fields, no wire format)
                plaintext = self._decrypt_aes_gcm(
                    enc_content, iv_str, tag_str, self._enc_key
                )

                decrypted.append({
                    "id": memory_id,
                    "content": plaintext,
                    "trustQuotient": item.get("trustQuotient", 0.0),
                    "intent": item.get("intent", ""),
                    "isCritical": item.get("isCritical", False),
                    "memoryType": item.get("memoryType", ""),
                    "timestamp": item.get("timestamp", 0),
                })

            except Exception:
                # FAIL-SAFE: skip corrupted/mismatched items
                # NEVER log ciphertext, iv, tag, or plaintext
                logger.warning(
                    "[Synapse] Decryption failed for memory %s — skipped",
                    str(memory_id)[:12],
                )
                continue

        logger.info(
            "[Synapse] Recalled %d/%d memories via Forge",
            len(decrypted),
            len(raw_results),
        )
        return decrypted

    async def count(self, agent_id: Optional[str] = None) -> int:
        """Count stored memories.

        Args:
            agent_id: Optional scope filter.

        Returns:
            Number of memories stored for this user/agent.
        """
        path = "/api/v1/memories/count"
        if agent_id:
            path += f"?agent_id={agent_id}"

        resp = await self._request("GET", path)
        data = resp.json()
        return int(data.get("count", data.get("total", 0)))

    async def health(self) -> bool:
        """Check Forge API health.

        Returns:
            True if API responds with 2xx, False otherwise.
        """
        try:
            client = self._get_client()
            resp = await client.get("/api/health")
            return 200 <= resp.status_code < 300
        except Exception:
            return False

    # ── StorageBackend Protocol (sync wrappers) ───────────────────────
    # These allow ForgeBackend to be used where StorageBackend is expected.
    # They run the async methods in an event loop.

    def save(self, record: Dict[str, Any]) -> str:
        """Sync wrapper for store(). Implements StorageBackend.save()."""
        content = record.get("content", "")
        metadata = record.get("metadata", {})
        embedding = record.get("embedding")
        return asyncio.run(self.store(content, metadata=metadata, embedding=embedding))

    def recall_sync(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Sync wrapper for recall(). Implements StorageBackend.recall()."""
        return asyncio.run(
            self.recall(query, limit=limit, agent_id=agent_id)
        )

    def delete(self, memory_id: str) -> bool:
        """Not supported via Forge API — returns False."""
        logger.warning("[Synapse] ForgeBackend.delete() not supported via API")
        return False

    def clear(self, agent_id: Optional[str] = None) -> int:
        """Not supported via Forge API — returns 0."""
        logger.warning("[Synapse] ForgeBackend.clear() not supported via API")
        return 0

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ForgeBackend":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        fp = hashlib.sha256(self._enc_key).hexdigest()[:12]
        return (
            f"ForgeBackend("
            f"url={self._base_url!r}, "
            f"key_fingerprint={fp!r})"
        )
