"""
Reference Implementation: Encrypted Persistent Memory for MCP (Synapse Layer)

A minimal MCP server that exposes two tools — store_memory and recall_memory —
backed by Synapse Layer's privacy-first memory SDK. Every memory goes through
automatic PII sanitization and differential-privacy noise injection before
storage, giving any MCP-compatible client (Claude Desktop, LangChain, CrewAI,
custom agents) a production-grade secure memory layer with zero configuration.

Author : Synapse Layer — https://github.com/SynapseLayer
License: Apache 2.0
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from synapse_memory import __version__ as SYNAPSE_VERSION
from synapse_memory.core import SynapseMemory

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENT_ID: str = os.getenv("SYNAPSE_AGENT_ID", "mcp-secure-memory")
PRIVACY_EPSILON: float = float(os.getenv("SYNAPSE_PRIVACY_EPSILON", "0.5"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("mcp-secure-memory")

# ---------------------------------------------------------------------------
# Synapse Layer memory instance (stateless — no DB required)
# ---------------------------------------------------------------------------
memory = SynapseMemory(
    agent_id=AGENT_ID,
    sanitize_enabled=True,
    privacy_enabled=True,
    privacy_epsilon=PRIVACY_EPSILON,
)

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Synapse Layer — Secure Memory",
    json_response=True,
)


@mcp.tool()
def store_memory(
    content: str,
    confidence: float = 0.9,
    metadata: Optional[str] = None,
) -> dict:
    """Store a memory with automatic PII sanitization and differential-privacy
    noise injection.  Returns an audit-ready payload including the memory ID,
    trust quotient, and privacy/sanitization details.

    Parameters
    ----------
    content : str
        The raw text to memorize (PII will be stripped automatically).
    confidence : float
        How confident the agent is about this memory (0.0–1.0).
    metadata : str | None
        Optional JSON string with extra key-value pairs to attach.
    """
    meta = json.loads(metadata) if metadata else None
    result = memory.store(content, confidence=confidence, metadata=meta)

    return {
        "memory_id": result.memory_id,
        "trust_quotient": round(result.trust_quotient, 4),
        "sanitized": result.sanitized,
        "privacy_applied": result.privacy_applied,
        "content_hash": result.content_hash,
        "timestamp": result.timestamp,
    }


@mcp.tool()
def recall_memory(query: str, top_k: int = 5) -> list[dict]:
    """Recall memories semantically similar to *query*.  Results include
    self-healing metadata — conflicting memories are automatically
    reclassified before being returned.

    Parameters
    ----------
    query : str
        Natural-language query describing what the agent wants to remember.
    top_k : int
        Maximum number of memories to return (default 5).
    """
    results = memory.recall(query, top_k=top_k)

    return [
        {
            "memory_id": r.memory_id,
            "content": r.content,
            "similarity": round(r.similarity, 4),
            "trust_quotient": round(r.trust_quotient, 4),
            "self_healed": r.self_healed,
            "timestamp": r.timestamp,
        }
        for r in results
    ]


@mcp.tool()
def health_check() -> dict:
    """Liveness/readiness probe for the secure-memory service.

    This is a PUBLIC, low-privilege status check. It is intentionally a
    pure status probe: it verifies that the memory engine is constructed
    and its storage backend is wired, equivalent to a ``SELECT 1`` liveness
    check. It performs NO data access.

    Security contract (enforced by tests):
      * MUST NOT call ``recall``, ``search``, ``store`` or any operation
        requiring the ``read:fulltext`` or ``admin:export`` token scopes.
      * MUST NOT read, decrypt or return any stored memory content.
      * Plaintext memory data is NEVER included in the response — only
        non-sensitive service metadata (status, version, engine, backend
        type name, timestamp).

    Returns
    -------
    dict
        A status envelope: ``status`` (healthy|unhealthy), ``version``,
        ``engine``, ``backend`` (backend class name only — never contents),
        ``timestamp`` (UTC ISO-8601), and static ``capabilities`` flags.
    """
    # Pure liveness check — inspect object wiring only, never query data.
    backend_ok = getattr(memory, "_backend", None) is not None
    status = "healthy" if backend_ok else "unhealthy"

    return {
        "status": status,
        "version": SYNAPSE_VERSION,
        "engine": "synapse-layer",
        # Class name only — reveals no stored memory content.
        "backend": type(memory._backend).__name__ if backend_ok else None,
        "capabilities": {
            "sanitize": bool(getattr(memory, "sanitize_enabled", False)),
            "privacy": bool(getattr(memory, "privacy_enabled", False)),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Entrypoint — stdio transport for Claude Desktop / MCP Inspector
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(
        "Starting Synapse Layer Secure Memory MCP server "
        "(agent_id=%s, epsilon=%.2f)",
        AGENT_ID,
        PRIVACY_EPSILON,
    )
    mcp.run(transport="stdio")
