"""Synapse Layer — Simple Client (sync one-liner API).

Sync HTTP client for Forge API endpoints. Server-side AES-256-GCM
encryption; the server owns the master key. For client-side zero-knowledge,
use :class:`synapse_memory.backends.forge_backend.ForgeBackend` instead.

Usage::

    from synapse_layer import SynapseClient

    client = SynapseClient(token="sk_connect_...")
    client.remember("Ismael prefere TypeScript e dark mode")
    results = client.recall("preferências do Ismael")
    print(results)

Author : Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import (
    ForgeAuthError,
    ForgeBackendError,
    ForgeRateLimitError,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = os.environ.get(
    "SYNAPSE_FORGE_URL", "https://forge.synapselayer.org"
)
_DEFAULT_TIMEOUT = 15.0
_DEFAULT_AGENT = "sdk-client"


class Synapse:
    """Synchronous Synapse client — minimal one-liner API.

    Targets Forge REST + MCP endpoints with ``x-connect-token`` auth.
    Server performs sanitization, AES-256-GCM at rest, Trust Quotient scoring.

    Args:
        api_key: ``sk_connect_*`` token (positional or keyword).
        token:   Alias for ``api_key`` (keyword only).
        base_url: Forge base URL. Defaults to ``$SYNAPSE_FORGE_URL`` or
            ``https://forge.synapselayer.org``.
        agent_id: Agent identifier to tag memories with. Defaults to
            ``"sdk-client"``.
        timeout: HTTP timeout in seconds. Defaults to ``15``.
        verbose: Enable verbose logging. Defaults to ``False``.

    Raises:
        ValueError: If ``api_key``/``token`` is missing or empty.
    """

    __slots__ = ("_api_key", "_base_url", "_agent", "_timeout", "_client", "_verbose")

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        token: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        agent_id: str = _DEFAULT_AGENT,
        timeout: float = _DEFAULT_TIMEOUT,
        verbose: bool = False,
    ) -> None:
        resolved_key = api_key or token or os.environ.get("SYNAPSE_TOKEN", "")
        if not resolved_key or not isinstance(resolved_key, str):
            raise ValueError("api_key/token must be a non-empty string")
        if not resolved_key.startswith("sk_connect_"):
            raise ValueError(
                "token must start with 'sk_connect_' — get one at /dashboard/connect"
            )

        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._agent = agent_id
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._verbose = verbose

    def _log(self, *args: Any) -> None:
        if self._verbose:
            print("[Synapse]", *args)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "x-connect-token": self._api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "synapse-layer-python-sdk",
                },
            )
        return self._client

    # ── Store / Remember ────────────────────────────────────────────

    def store(
        self,
        content: str,
        *,
        memory_type: str = "long_term",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist a memory on the Forge and return the response payload.

        Args:
            content: Plaintext memory content. Required, non-empty.
            memory_type: ``short_term`` | ``long_term`` | ``episodic``.
            metadata: Optional dict of arbitrary metadata.

        Returns:
            dict with keys: ``memoryId``, ``contentHash``, ``trustQuotient``,
            ``requestId`` (when available).
        """
        if not content or not isinstance(content, str):
            raise ValueError("content must be a non-empty string")

        self._log(f'Saving memory: "{content[:60]}"...')

        payload: Dict[str, Any] = {
            "agent": self._agent,
            "content": content,
            "memoryType": memory_type,
        }
        if metadata:
            payload["metadata"] = metadata

        client = self._get_client()
        try:
            resp = client.post("/api/v1/memory/commit", json=payload)
        except httpx.HTTPError as exc:
            raise ForgeBackendError(f"network error: {exc}") from exc

        if resp.status_code in (200, 201):
            data = resp.json()
            self._log(f"Memory saved: id={data.get('memoryId')} tq={data.get('trustQuotient')}")
            return data
        if resp.status_code == 401:
            raise ForgeAuthError(f"authentication failed (401): {resp.text[:200]}")
        if resp.status_code == 429:
            raise ForgeRateLimitError(f"rate limit exceeded (429): {resp.text[:200]}")
        raise ForgeBackendError(
            f"unexpected response {resp.status_code}: {resp.text[:200]}"
        )

    def remember(
        self,
        content: str,
        *,
        memory_type: str = "long_term",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Alias for :meth:`store`. Save a memory to Forge."""
        return self.store(content, memory_type=memory_type, metadata=metadata)

    # ── Recall ──────────────────────────────────────────────────────

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Recall relevant memories via MCP recall_memory tool.

        Uses server-side decryption — returns plaintext content.

        Args:
            query: Natural language query for memory retrieval.
            top_k: Maximum number of memories to return (default 5).
            mode: Recall mode — ``semantic``, ``temporal``, ``priority``,
                ``hybrid``, or ``auto``. Defaults to server auto-detect.

        Returns:
            List of memory dicts with keys: ``content``, ``trust_quotient``,
            ``intent``, ``agent``, ``timestamp``, ``memory_type``.
        """
        start = time.time()
        self._log(f'Recalling memories for: "{query}"...')

        payload: Dict[str, Any] = {"query": query, "limit": top_k}
        if mode:
            payload["mode"] = mode

        client = self._get_client()
        try:
            resp = client.post("/api/v1/sdk/recall", json=payload)
        except httpx.HTTPError as exc:
            raise ForgeBackendError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            raise ForgeBackendError(f"recall failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        memories = data.get("memories", [])
        elapsed_ms = int((time.time() - start) * 1000)
        self._log(f"{len(memories)} memories found ({elapsed_ms}ms, server={data.get('latency_ms', '?')}ms)")
        return memories

    # ── List ────────────────────────────────────────────────────────

    def list_memories(self, *, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent memories.

        Args:
            limit: Maximum number of memories to return (default 10).

        Returns:
            List of memory dicts.
        """
        client = self._get_client()
        try:
            resp = client.post("/mcp", json={
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": "tools/call",
                "params": {"name": "list_memories", "arguments": {"limit": limit}},
            })
        except httpx.HTTPError as exc:
            raise ForgeBackendError(f"network error: {exc}") from exc

        if resp.status_code != 200:
            raise ForgeBackendError(f"list failed ({resp.status_code})")

        rpc = resp.json()
        text = None
        try:
            text = rpc["result"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return []

        import json
        parsed = json.loads(text)
        return parsed.get("memories", [])

    # ── Lifecycle ───────────────────────────────────────────────────

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "Synapse":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Synapse(base_url={self._base_url!r}, agent_id={self._agent!r})"


# Convenience alias
SynapseClient = Synapse
