"""Synapse Layer — Embedding Generation Module (Provider-Abstracted).

Provides ``get_embedding()`` with pluggable providers:
    - ``"none"``   → deterministic pseudo-embedding (SHA-256, always works)
    - ``"openai"`` → OpenAI ``text-embedding-3-small`` (1536 dims, requires key)

The system works fully without any external API key.
When an embedding provider is configured, semantic recall quality improves.

Security:
    - NEVER logs the input text (may contain PII).
    - Only logs vector dimensions and latency.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
from typing import List, Literal, Optional

import httpx

logger = logging.getLogger("synapse.embeddings")

# ── Constants ──────────────────────────────────────────────────────

EmbeddingProvider = Literal["none", "openai"]

_OPENAI_MODEL = "text-embedding-3-small"
_EMBEDDING_DIM = 1536
_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_TIMEOUT = 15.0  # seconds


# ── Public API ─────────────────────────────────────────────────────

async def get_embedding(
    text: str,
    provider: EmbeddingProvider = "none",
    api_key: Optional[str] = None,
    dimensions: int = _EMBEDDING_DIM,
) -> List[float]:
    """Generate a semantic embedding vector for the given text.

    Args:
        text: Input text to embed.  Not logged (may contain PII).
        provider: ``"none"`` for pseudo-embedding, ``"openai"`` for real.
        api_key: API key for the provider.  Required for ``"openai"``.
        dimensions: Output vector dimensionality.

    Returns:
        List of floats with ``dimensions`` elements, L2-normalized.
    """
    if provider == "openai" and api_key:
        return await _openai_embedding(text, api_key, dimensions)

    # Default: pseudo-embedding (always works, no external deps)
    if provider == "openai" and not api_key:
        logger.warning("[Synapse] provider=openai but no api_key — falling back to pseudo")
    return _pseudo_embedding(text, dimensions)


async def _openai_embedding(
    text: str,
    api_key: str,
    dimensions: int = _EMBEDDING_DIM,
) -> List[float]:
    """Call OpenAI text-embedding-3-small. Falls back to pseudo on error."""
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": _OPENAI_MODEL,
                    "dimensions": dimensions,
                },
            )

        if resp.status_code != 200:
            error_body = resp.text[:200]
            logger.error(
                "[Synapse] OpenAI embedding failed: %d — %s",
                resp.status_code,
                error_body,
            )
            raise RuntimeError(
                f"OpenAI embedding API returned {resp.status_code}: {error_body}"
            )

        data = resp.json()
        vector = data["data"][0]["embedding"]
        elapsed = (time.monotonic() - t0) * 1000

        logger.info(
            "[Synapse] OpenAI embedding OK — %dd, %.0fms",
            len(vector),
            elapsed,
        )
        return vector

    except httpx.TimeoutException:
        logger.warning("[Synapse] OpenAI embedding timeout — falling back to pseudo")
        return _pseudo_embedding(text, dimensions)
    except Exception as exc:
        logger.warning(
            "[Synapse] OpenAI embedding error (%s) — falling back to pseudo",
            type(exc).__name__,
        )
        return _pseudo_embedding(text, dimensions)


# ── Pseudo-embedding (offline fallback) ────────────────────────────

def _pseudo_embedding(text: str, dim: int = _EMBEDDING_DIM) -> List[float]:
    """Deterministic pseudo-embedding via SHA-256 expansion.

    NOT semantically meaningful — only useful for tests and offline mode.
    Production callers should use provider="openai" for real semantics.
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
