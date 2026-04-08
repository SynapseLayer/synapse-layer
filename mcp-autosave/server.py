"""
Synapse Layer — Auto-Save MCP Bridge (Production)

A production-grade MCP server that persists AI agent memories to Supabase
with automatic PII redaction, async embedding generation, and deduplication.

Tools:
    1. save_to_synapse — Insert redacted memory (embedding=NULL, async backfill)
    2. process_text — Auto-detect milestones/decisions and save
    3. backfill_embeddings — Process pending embedding jobs
    4. health_check — Server + DB status

Security:
    - PII/secrets are redacted BEFORE storage and embedding.
    - Content is NEVER logged (only IDs + counters).
    - Supabase SERVICE_ROLE key is server-side only.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# Add parent dir to path so we can import synapse_memory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client as SupabaseClient

from redactor import redact
from synapse_memory.autosave import (
    AutoSaveEngine,
    AutoSaveEvent,
    SaveResult,
    PolicyEngine,
    TriggerDetector,
    EventFormatter,
)
from synapse_memory.autosave.types import ALL_PROJECTS, ALL_EVENT_TYPES

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

VERSION = "1.0.7"

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
REDACTION_LEVEL: str = os.getenv("REDACTION_LEVEL", "strict")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
SYNAPSE_MODE: str = os.getenv("SYNAPSE_MODE", "oss").lower()

_raw_projects = os.getenv("ALLOWED_PROJECTS", "")
ALLOWED_PROJECTS: frozenset[str] = frozenset(
    p.strip().upper() for p in _raw_projects.split(",") if p.strip()
) if _raw_projects else ALL_PROJECTS

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("synapse.autosave")

# ───────────────────────────────────────────────────────────────────────
# Supabase Adapter (bridges DatabaseProtocol)
# ───────────────────────────────────────────────────────────────────────

db: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)


class SupabaseAdapter:
    """Adapt Supabase client to DatabaseProtocol."""

    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def insert_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self._client.table("memories").insert(payload).execute()
        return result.data[0] if result.data else {}

    def enqueue_embedding(self, memory_id: str) -> None:
        self._client.table("embedding_jobs").insert({
            "memory_id": memory_id,
            "status": "pending",
        }).execute()

    def fetch_pending_jobs(self, limit: int) -> List[Dict[str, Any]]:
        result = (
            self._client.table("embedding_jobs")
            .select("id, memory_id")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def fetch_memory_content(self, memory_id: str) -> Optional[str]:
        result = (
            self._client.table("memories")
            .select("content")
            .eq("id", memory_id)
            .single()
            .execute()
        )
        return result.data["content"] if result.data else None

    def update_embedding(self, memory_id: str, embedding: List[float]) -> None:
        self._client.table("memories").update({
            "embedding": embedding,
        }).eq("id", memory_id).execute()

    def complete_job(self, job_id: str) -> None:
        self._client.table("embedding_jobs").update({
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

    def fail_job(self, job_id: str, error: str) -> None:
        self._client.table("embedding_jobs").update({
            "status": "failed",
            "error_message": error[:500],
        }).eq("id", job_id).execute()


# ───────────────────────────────────────────────────────────────────────
# Embedding Provider
# ───────────────────────────────────────────────────────────────────────

def _generate_embedding(text: str) -> List[float]:
    """Generate a 1536-dim embedding. SECURITY: Only redacted content."""
    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536,
        )
        return response.data[0].embedding
    elif EMBEDDING_PROVIDER == "local":
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("pip install sentence-transformers")
        model_name = os.getenv("LOCAL_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)
        emb = model.encode(text).tolist()
        if len(emb) < 1536:
            emb.extend([0.0] * (1536 - len(emb)))
        return emb[:1536]
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


# ───────────────────────────────────────────────────────────────────────
# Rate Limiter
# ───────────────────────────────────────────────────────────────────────

import time
_call_timestamps: List[float] = []

def _check_rate_limit() -> bool:
    now = time.time()
    while _call_timestamps and _call_timestamps[0] < now - 60.0:
        _call_timestamps.pop(0)
    if len(_call_timestamps) >= RATE_LIMIT_PER_MINUTE:
        return False
    _call_timestamps.append(now)
    return True


# ───────────────────────────────────────────────────────────────────────
# Bootstrap AutoSaveEngine
# ───────────────────────────────────────────────────────────────────────

engine = AutoSaveEngine(
    database=SupabaseAdapter(db),
    redactor=redact,
    policy=PolicyEngine(mode=SYNAPSE_MODE, allowed_projects=ALLOWED_PROJECTS),
    trigger_detector=TriggerDetector(),
    formatter=EventFormatter(),
)


# ───────────────────────────────────────────────────────────────────────
# MCP Server
# ───────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Synapse Layer — Auto-Save MCP Bridge",
    json_response=True,
)


def _result_to_dict(r: SaveResult) -> dict:
    return {
        "id": r.id,
        "status": r.status,
        "project": r.project,
        "type": r.type,
        "importance": r.importance,
        "created_at": r.created_at,
        "reason": r.reason,
    }


@mcp.tool()
def save_to_synapse(
    content: str,
    project: str,
    metadata: Optional[str] = None,
) -> dict:
    """Save a memory to Synapse Layer with automatic PII redaction.

    The memory is inserted immediately with embedding=NULL for near-zero
    latency. Embeddings are generated asynchronously via backfill_embeddings.

    Parameters
    ----------
    content : str
        Raw text to memorize. PII and secrets are redacted before storage.
    project : str
        Project identifier (e.g., 'OFFLY', 'SYNAPSE_LAYER', 'GOARQIA').
    metadata : str | None
        Optional JSON string with extra fields. Recommended structure:
        {"type": "[AUTO-STRAT]", "importance": 5, "tags": [...], "source": "chatllm_teams"}
    """
    if not _check_rate_limit():
        return {"id": None, "status": "rate_limited",
                "error": f"Exceeded {RATE_LIMIT_PER_MINUTE} calls/min."}

    meta: Dict[str, Any] = {}
    if metadata:
        try:
            meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        except json.JSONDecodeError as e:
            return {"id": None, "status": "error", "error": f"Invalid JSON: {e}"}

    event = AutoSaveEvent(
        content=content,
        project=project.strip().upper(),
        type=meta.get("type", "[AUTO-CONTEXT]"),
        importance=int(meta.get("importance", 3)),
        source=meta.get("source", "mcp_tool"),
        tags=meta.get("tags", []),
        source_ref=meta.get("source_ref", {}),
    )

    result = engine.save(event)
    return _result_to_dict(result)


@mcp.tool()
def process_text(
    text: str,
    project: Optional[str] = None,
    source: Optional[str] = None,
) -> list:
    """Auto-detect milestones, decisions, and alerts in text, then save.

    Scans the provided text for strategic triggers and persists each
    detected event as an autonomous memory.

    Parameters
    ----------
    text : str
        Free-form text to analyze for auto-save triggers.
    project : str | None
        Force a specific project (auto-detected if not provided).
    source : str | None
        Override source identifier.
    """
    if not _check_rate_limit():
        return [{"id": None, "status": "rate_limited",
                 "error": f"Exceeded {RATE_LIMIT_PER_MINUTE} calls/min."}]

    results = engine.process_text(
        text,
        project=project.strip().upper() if project else None,
        source=source,
    )
    return [_result_to_dict(r) for r in results]


@mcp.tool()
def backfill_embeddings(limit: int = 10) -> dict:
    """Process pending embedding jobs asynchronously.

    SECURITY: Only REDACTED content is sent to the embedding provider.

    Parameters
    ----------
    limit : int
        Maximum number of pending jobs to process (default 10, max 50).
    """
    return engine.backfill(limit=limit, embed_fn=_generate_embedding)


@mcp.tool()
def health_check() -> dict:
    """Check server health, database connectivity, and queue status."""
    try:
        db.table("memories").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    try:
        pending = (
            db.table("embedding_jobs")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        queue_pending = pending.count or 0
    except Exception:
        queue_pending = -1

    return {
        "ok": db_status == "connected",
        "version": VERSION,
        "autosave_engine_version": AutoSaveEngine.VERSION,
        "mode": SYNAPSE_MODE,
        "embedding_provider": EMBEDDING_PROVIDER,
        "db": db_status,
        "queue": {"pending_embeddings": queue_pending},
        "projects_allowlist": sorted(ALLOWED_PROJECTS),
        "redaction_level": REDACTION_LEVEL,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }


# ───────────────────────────────────────────────────────────────────────
# Entrypoint
# ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "Starting Synapse Layer Auto-Save MCP Bridge v%s "
        "(engine=%s, mode=%s, provider=%s, redaction=%s)",
        VERSION, AutoSaveEngine.VERSION, SYNAPSE_MODE,
        EMBEDDING_PROVIDER, REDACTION_LEVEL,
    )
    mcp.run(transport="stdio")
