"""
Synapse Layer — ForgeBackend Unit Tests

Verifies encryption guarantees (server never sees plaintext):
  - TEST-ZK-1: store() encrypts client-side — NO plaintext in HTTP payload
  - TEST-2: recall() decrypts encrypted envelope before returning
  - TEST-3, TEST-4: Auth failures raised correctly
  - TEST-5: Key validation rejects wrong sizes
  - TEST-6: Decrypt failures skip items gracefully
  - TEST-7: count() returns correct integer
  - TEST-8: _build_search_index() sanitizes PII

Architecture (True ZK):
  SDK encrypt (AES-256-GCM) → HTTP POST (ciphertext only) → Server stores
  SDK recall → Server returns encrypted envelope → SDK decrypt locally
  Plaintext NEVER traverses the network in EITHER direction.

Uses respx to mock httpx requests — no network calls.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import base64
import json
import os

import httpx
import pytest
import respx

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from synapse_memory.backends.forge_backend import ForgeBackend
from synapse_memory.exceptions import (
    ForgeAuthError,
    ForgeBackendError,
    ForgeRateLimitError,
)

# ── Fixtures ──────────────────────────────────────────────────────────

TEST_KEY = b"\x42" * 32  # deterministic 32-byte key
TEST_API_KEY = "sk_connect_test_abc123"
BASE_URL = "https://forge.synapselayer.org"


@pytest.fixture
def backend() -> ForgeBackend:
    return ForgeBackend(
        api_key=TEST_API_KEY,
        encryption_key=TEST_KEY,
        base_url=BASE_URL,
    )


def _make_encrypted_payload(key: bytes, plaintext: str) -> dict:
    """Encrypt plaintext using AESGCM and return Forge API wire-format dict."""
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    ct_bytes = ct_with_tag[:-16]
    tag_bytes = ct_with_tag[-16:]
    return {
        "encryptedContent": base64.b64encode(ct_bytes).decode(),
        "iv": base64.b64encode(iv).decode(),
        "authTag": base64.b64encode(tag_bytes).decode(),
    }


# ── TEST-ZK-1: store() encrypts BEFORE sending (TRUE ZK GUARANTEE) ────

@respx.mock
@pytest.mark.asyncio
async def test_zk_store_no_plaintext_in_payload(backend: ForgeBackend) -> None:
    """⚡ CRITICAL: Plaintext must NEVER appear in the HTTP payload.
    SDK encrypts client-side BEFORE POST.  Server NEVER sees plaintext.
    This is THE definitive encryption test — server never sees plaintext.
    """
    secret_content = "My SSN is 123-45-6789 and my password is hunter2"
    captured_body: dict = {}

    def capture_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(
            201,
            json={"id": "mem_zk_001", "status": "stored", "zkMode": True},
        )

    respx.post(f"{BASE_URL}/api/v1/capture").mock(side_effect=capture_request)

    memory_id = await backend.store(secret_content)

    # ✔ Memory ID returned
    assert memory_id == "mem_zk_001"

    # ✔ "content" ABSENT from payload — ZK guarantee
    assert "content" not in captured_body, (
        "CRITICAL ZK VIOLATION: plaintext 'content' found in HTTP payload!"
    )

    # ✔ Full plaintext NEVER in serialized payload (excluding searchIndex)
    payload_str = json.dumps(captured_body)
    assert secret_content not in payload_str, (
        "ZK VIOLATION: full plaintext found in serialized HTTP payload"
    )

    # ✔ PII sanitized FROM searchIndex (SSN is redacted by _build_search_index)
    assert "123-45-6789" not in captured_body.get("searchIndex", ""), (
        "ZK VIOLATION: SSN found in searchIndex"
    )

    # ✔ encryptedContent is NOT the plaintext
    assert captured_body["encryptedContent"] != secret_content, (
        "ZK VIOLATION: encryptedContent is plaintext!"
    )

    # ✔ Encrypted fields PRESENT
    assert "encryptedContent" in captured_body
    assert "iv" in captured_body
    assert "authTag" in captured_body

    # ✔ zkMode flag set
    assert captured_body["zkMode"] is True

    # ✔ encrypted flag set
    assert captured_body["encrypted"] is True

    # ✔ searchIndex present (sanitized keywords)
    assert "searchIndex" in captured_body

    # ✔ Embedding present
    assert "embedding" in captured_body
    assert isinstance(captured_body["embedding"], list)

    # ✔ Verify ciphertext is actually decryptable with the same key
    plaintext_roundtrip = ForgeBackend._decrypt_aes_gcm(
        captured_body["encryptedContent"],
        captured_body["iv"],
        captured_body["authTag"],
        TEST_KEY,
    )
    assert plaintext_roundtrip == secret_content


# ── TEST-2: recall() decrypts BEFORE returning ───────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_recall_decrypts_before_returning(backend: ForgeBackend) -> None:
    """Caller receives plaintext; ciphertext fields are stripped."""
    original_text = "User prefers dark mode with purple accents"
    encrypted = _make_encrypted_payload(TEST_KEY, original_text)

    respx.post(f"{BASE_URL}/api/v1/recall").mock(
        return_value=httpx.Response(
            200,
            json={
                "memories": [
                    {
                        "id": "mem_recall_001",
                        **encrypted,
                        "trustQuotient": 0.95,
                        "intent": "preference",
                        "isCritical": False,
                        "memoryType": "semantic",
                        "timestamp": 1713139200,
                    }
                ]
            },
        )
    )

    results = await backend.recall("dark mode")

    assert len(results) == 1
    result = results[0]

    # ✔ Plaintext content decrypted and returned
    assert result["content"] == original_text

    # ✔ Ciphertext fields NEVER returned to caller
    assert "encryptedContent" not in result
    assert "iv" not in result
    assert "authTag" not in result

    # ✔ Metadata preserved
    assert result["trustQuotient"] == 0.95
    assert result["intent"] == "preference"
    assert result["id"] == "mem_recall_001"


# ── TEST-3: store() without api_key → ForgeAuthError ─────────────────

def test_store_without_api_key_raises_auth_error() -> None:
    """Empty api_key must raise ForgeAuthError at construction."""
    with pytest.raises(ForgeAuthError):
        ForgeBackend(api_key="", encryption_key=TEST_KEY)

    with pytest.raises(ForgeAuthError):
        ForgeBackend(api_key=None, encryption_key=TEST_KEY)  # type: ignore[arg-type]


# ── TEST-4: recall() with 401 → ForgeAuthError ──────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_recall_with_invalid_token_raises_auth_error(
    backend: ForgeBackend,
) -> None:
    """Mock 401 response must raise ForgeAuthError."""
    respx.post(f"{BASE_URL}/api/v1/recall").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )

    with pytest.raises(ForgeAuthError):
        await backend.recall("anything")


# ── TEST-4B: explicit no-auth/invalid-token/corrupted-data coverage ───

@respx.mock
@pytest.mark.asyncio
async def test_no_auth_returns_401() -> None:
    """No Authorization header must return 401 and raise ForgeAuthError."""
    backend = ForgeBackend(api_key=TEST_API_KEY, encryption_key=TEST_KEY)

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(401, json={"error": "__test_unauthorized_no_auth"})

    respx.post(f"{BASE_URL}/api/v1/recall").mock(side_effect=handle_request)

    backend._client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Content-Type": "application/json", "User-Agent": "synapse-memory-sdk/python"},
        timeout=30.0,
    )

    with pytest.raises(ForgeAuthError):
        await backend.recall("__test_no_auth_request")


@respx.mock
@pytest.mark.asyncio
async def test_invalid_token_returns_401() -> None:
    """Invalid Authorization token must return 401 and raise ForgeAuthError."""
    backend = ForgeBackend(api_key=TEST_API_KEY, encryption_key=TEST_KEY)

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer invalid_token_value"
        return httpx.Response(401, json={"error": "__test_unauthorized_invalid_token"})

    respx.post(f"{BASE_URL}/api/v1/recall").mock(side_effect=handle_request)

    backend._client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers={
            "Authorization": "Bearer invalid_token_value",
            "Content-Type": "application/json",
            "User-Agent": "synapse-memory-sdk/python",
        },
        timeout=30.0,
    )

    with pytest.raises(ForgeAuthError):
        await backend.recall("__test_invalid_token_request")


@respx.mock
@pytest.mark.asyncio
async def test_corrupted_memory_data_returns_error() -> None:
    """Corrupted memory payload must surface an error response (non-200)."""
    backend = ForgeBackend(api_key=TEST_API_KEY, encryption_key=TEST_KEY)

    respx.post(f"{BASE_URL}/api/v1/recall").mock(
        return_value=httpx.Response(500, json={"error": "__test_corrupted_memory_blob"})
    )

    with pytest.raises(ForgeBackendError):
        await backend.recall("__test_corrupted_memory_data")


# ── TEST-5: wrong encryption_key size → ValueError ───────────────────

def test_wrong_encryption_key_size_raises_value_error() -> None:
    """Key must be exactly 32 bytes. 31 bytes must fail."""
    with pytest.raises(ValueError, match="32 bytes"):
        ForgeBackend(api_key=TEST_API_KEY, encryption_key=b"x" * 31)

    with pytest.raises(ValueError, match="32 bytes"):
        ForgeBackend(api_key=TEST_API_KEY, encryption_key=b"x" * 33)


# ── TEST-6: recall() with decrypt failure → item skipped ──────────────

@respx.mock
@pytest.mark.asyncio
async def test_recall_skips_undecryptable_items(backend: ForgeBackend) -> None:
    """If one item fails to decrypt, it's skipped. Others are returned."""
    good_text = "User likes Python"
    good_encrypted = _make_encrypted_payload(TEST_KEY, good_text)

    # Bad item: encrypted with a DIFFERENT key → decrypt with TEST_KEY fails
    other_key = b"\xff" * 32
    bad_encrypted = _make_encrypted_payload(other_key, "wrong key data")

    respx.post(f"{BASE_URL}/api/v1/recall").mock(
        return_value=httpx.Response(
            200,
            json={
                "memories": [
                    {"id": "good_001", **good_encrypted, "trustQuotient": 0.9},
                    {"id": "bad_001", **bad_encrypted, "trustQuotient": 0.8},
                ]
            },
        )
    )

    results = await backend.recall("Python")

    # Only the good item is returned
    assert len(results) == 1
    assert results[0]["id"] == "good_001"
    assert results[0]["content"] == good_text


# ── TEST-7: count() returns correct integer ────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_count_returns_integer(backend: ForgeBackend) -> None:
    """count() must return int from Forge API."""
    respx.get(f"{BASE_URL}/api/v1/memories/count").mock(
        return_value=httpx.Response(200, json={"count": 66})
    )

    count = await backend.count()
    assert count == 66
    assert isinstance(count, int)


# ── TEST-8: _build_search_index() sanitizes PII ──────────────────────

def test_build_search_index_sanitizes_pii() -> None:
    """PII (SSN, phone, email) must be redacted in search index."""
    content = "Call me at 555-123-4567 or email john@example.com, SSN 123-45-6789"
    idx = ForgeBackend._build_search_index(content, "test")

    # PII must NOT appear in index
    assert "555-123-4567" not in idx
    assert "john@example.com" not in idx
    assert "123-45-6789" not in idx

    # But keywords must be present
    assert "call" in idx
    assert "test" in idx

    # PII placeholders in lowercase form
    assert "phone" in idx
    assert "email" in idx
    assert "ssn" in idx


# ── TEST-EMB-1: store() includes embedding in payload (1536 dims) ──────

@respx.mock
@pytest.mark.asyncio
async def test_store_includes_embedding_in_payload(backend: ForgeBackend) -> None:
    """store() must include 'embedding' field with 1536-dim vector in payload."""
    captured_body: dict = {}

    def capture_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(
            201,
            json={"id": "mem_emb_001", "status": "stored", "zkMode": True},
        )

    respx.post(f"{BASE_URL}/api/v1/capture").mock(side_effect=capture_request)

    await backend.store("User loves semantic search")

    # ✔ embedding present and correct dimensions
    assert "embedding" in captured_body, "embedding field missing from payload"
    emb = captured_body["embedding"]
    assert isinstance(emb, list), "embedding must be a list"
    assert len(emb) == 1536, f"embedding must be 1536-dim, got {len(emb)}"
    assert all(isinstance(v, float) for v in emb), "all embedding values must be float"

    # ✔ ZK invariant maintained — "content" still absent
    assert "content" not in captured_body


# ── TEST-EMB-2: recall() sends vector in body ───────────────────────────

@respx.mock
@pytest.mark.asyncio
async def test_recall_sends_vector_in_body(backend: ForgeBackend) -> None:
    """recall() must send 'vector' field with embedding of the query."""
    captured_body: dict = {}

    def capture_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(200, json={"memories": []})

    respx.post(f"{BASE_URL}/api/v1/recall").mock(side_effect=capture_request)

    await backend.recall("semantic search test")

    # ✔ vector present with correct dimensions
    assert "vector" in captured_body, "vector field missing from recall body"
    vec = captured_body["vector"]
    assert isinstance(vec, list), "vector must be a list"
    assert len(vec) == 1536, f"vector must be 1536-dim, got {len(vec)}"
    assert all(isinstance(v, float) for v in vec), "all vector values must be float"

    # ✔ query text also present
    assert "query" in captured_body


# ── TEST-EMB-3: recall() returns plaintext, not encryptedContent ────────

@respx.mock
@pytest.mark.asyncio
async def test_recall_returns_plaintext_not_ciphertext(backend: ForgeBackend) -> None:
    """recall() must return decrypted content, never raw ciphertext fields."""
    original = "User prefers dark mode with semantic search"
    encrypted = _make_encrypted_payload(TEST_KEY, original)

    respx.post(f"{BASE_URL}/api/v1/recall").mock(
        return_value=httpx.Response(
            200,
            json={
                "memories": [
                    {
                        "id": "mem_emb_003",
                        **encrypted,
                        "trustQuotient": 0.85,
                        "intent": "preference",
                    }
                ]
            },
        )
    )

    results = await backend.recall("dark mode")

    assert len(results) == 1
    r = results[0]

    # ✔ Plaintext returned
    assert r["content"] == original

    # ✔ Ciphertext fields stripped
    assert "encryptedContent" not in r
    assert "iv" not in r
    assert "authTag" not in r


# ── TEST-EMB-4: embedding_provider configures embedding_fn ──────────────

def test_embedding_provider_openai_configures_fn() -> None:
    """When embedding_provider='openai' + api_key, _embedding_fn must NOT be None."""
    backend = ForgeBackend(
        api_key=TEST_API_KEY,
        encryption_key=TEST_KEY,
        embedding_provider="openai",
        embedding_api_key="sk-test-fake-key-12345",
    )
    assert backend._embedding_fn is not None, (
        "embedding_provider='openai' + api_key should auto-configure _embedding_fn"
    )


def test_embedding_provider_none_uses_pseudo() -> None:
    """With embedding_provider='none' (default), _embedding_fn should be None (pseudo fallback)."""
    backend = ForgeBackend(
        api_key=TEST_API_KEY,
        encryption_key=TEST_KEY,
    )
    assert backend._embedding_fn is None, (
        "embedding_provider='none' should use pseudo fallback"
    )
    assert backend._embedding_provider == "none"


def test_embedding_provider_openai_without_key_uses_pseudo() -> None:
    """embedding_provider='openai' WITHOUT api_key should fall back to pseudo."""
    backend = ForgeBackend(
        api_key=TEST_API_KEY,
        encryption_key=TEST_KEY,
        embedding_provider="openai",
        # no embedding_api_key
    )
    assert backend._embedding_fn is None, (
        "embedding_provider='openai' without api_key should fall back to pseudo"
    )


# ── TEST-EMB-5: embeddings.py pseudo-embedding ──────────────────────────

def test_pseudo_embedding_dimensions() -> None:
    """_pseudo_embedding must return 1536-dim L2-normalized vector."""
    from synapse_memory.embeddings import _pseudo_embedding

    vec = _pseudo_embedding("test text")
    assert len(vec) == 1536
    assert all(isinstance(v, float) for v in vec)

    # L2 norm should be ~1.0
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-6, f"L2 norm should be 1.0, got {norm}"

    # Deterministic: same input → same output
    vec2 = _pseudo_embedding("test text")
    assert vec == vec2