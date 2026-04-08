"""
Synapse Layer — Auto-Save MCP Bridge (Production)

A production-grade MCP server that persists AI agent memories to Supabase
with automatic PII redaction, async embedding generation, and deduplication.

Tools:
    1. save_to_synapse — Insert redacted memory (embedding=NULL, async backfill)
    2. backfill_embeddings — Process pending embedding jobs
    3. health_check — Server + DB status

Security:
    - PII/secrets are redacted BEFORE storage and embedding.
    - Content is NEVER logged (only IDs + counters).
    - Supabase SERVICE_ROLE key is server-side only.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import os
import re
import time
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client as SupabaseClient

from redactor import redact, RedactionResult

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

# Project allowlist
_raw_projects = os.getenv("ALLOWED_PROJECTS", "")
ALLOWED_PROJECTS: set = {
    p.strip().upper() for p in _raw_projects.split(",") if p.strip()
} if _raw_projects else set()  # Empty = allow all

# Valid metadata types (policy helper)
VALID_METADATA_TYPES = {
    "[AUTO-STRAT]", "[AUTO-OP]", "[AUTO-INSIGHT]",
    "[AUTO-DECISION]", "[AUTO-CONTEXT]", "[MANUAL]",
}

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("synapse.autosave")

# ───────────────────────────────────────────────────────────────────────
# Supabase Client (SERVICE_ROLE — server-side only)
# ───────────────────────────────────────────────────────────────────────

db: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

# ───────────────────────────────────────────────────────────────────────
# Rate Limiter (in-memory, per-process)
# ───────────────────────────────────────────────────────────────────────

_call_timestamps: List[float] = []


def _check_rate_limit() -> bool:
    """Returns True if within rate limit, False if exceeded."""
    now = time.time()
    window_start = now - 60.0
    # Prune old entries
    while _call_timestamps and _call_timestamps[0] < window_start:
        _call_timestamps.pop(0)
    if len(_call_timestamps) >= RATE_LIMIT_PER_MINUTE:
        return False
    _call_timestamps.append(now)
    return True


# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────


def _normalize_content(content: str) -> str:
    """Normalize content for hashing: lowercase, collapse whitespace."""
    return re.sub(r'\s+', ' ', content.strip().lower())


def _compute_source_hash(
    project: str, content_redacted: str, metadata: Dict[str, Any]
) -> str:
    """SHA-256 hash for deduplication.

    Uses project + normalized redacted content + stable metadata subset
    (type, tags, source) to produce a deterministic hash.
    """
    stable_meta = {
        k: metadata.get(k)
        for k in sorted(["type", "tags", "source"])
        if metadata.get(k) is not None
    }
    payload = json.dumps(
        {"project": project, "content": _normalize_content(content_redacted),
         "meta": stable_meta},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _validate_project(project: str) -> Optional[str]:
    """Validate project against allowlist. Returns error message or None."""
    project_upper = project.strip().upper()
    if ALLOWED_PROJECTS and project_upper not in ALLOWED_PROJECTS:
        return (
            f"Project '{project}' not in allowlist. "
            f"Allowed: {sorted(ALLOWED_PROJECTS)}"
        )
    return None


def _validate_metadata_type(metadata: Dict[str, Any]) -> Optional[str]:
    """Policy helper: validate metadata.type if present."""
    meta_type = metadata.get("type")
    if meta_type and meta_type not in VALID_METADATA_TYPES:
        return (
            f"Invalid metadata.type '{meta_type}'. "
            f"Allowed: {sorted(VALID_METADATA_TYPES)}"
        )
    return None


# ───────────────────────────────────────────────────────────────────────
# Embedding Provider
# ───────────────────────────────────────────────────────────────────────


def _generate_embedding(text: str) -> List[float]:
    """Generate a 1536-dim embedding from REDACTED text.

    SECURITY: Only redacted content reaches this function.
    The raw content NEVER passes through here.
    """
    if EMBEDDING_PROVIDER == "openai":
        return _embed_openai(text)
    elif EMBEDDING_PROVIDER == "local":
        return _embed_local(text)
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


def _embed_openai(text: str) -> List[float]:
    """OpenAI text-embedding-3-small (1536 dimensions)."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        dimensions=1536,
    )
    return response.data[0].embedding


def _embed_local(text: str) -> List[float]:
    """Local sentence-transformers fallback.

    NOTE: Output dimension may differ from 1536. If using a model with
    different dimensions, you must adjust the vector(1536) column or
    pad/truncate the output.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )
    model_name = os.getenv("LOCAL_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    embedding = model.encode(text).tolist()
    # Pad to 1536 if needed
    if len(embedding) < 1536:
        embedding.extend([0.0] * (1536 - len(embedding)))
    return embedding[:1536]


# ───────────────────────────────────────────────────────────────────────
# MCP Server
# ───────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Synapse Layer — Auto-Save MCP Bridge",
    json_response=True,
)


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

    Returns
    -------
    dict
        {"id": "uuid", "status": "saved", "redaction": {...}, "deduplicated": bool}
    """
    # ── Rate limit check
    if not _check_rate_limit():
        return {
            "id": None,
            "status": "rate_limited",
            "error": f"Exceeded {RATE_LIMIT_PER_MINUTE} calls/min. Try again shortly.",
        }

    # ── Validate project
    project_err = _validate_project(project)
    if project_err:
        return {"id": None, "status": "error", "error": project_err}

    # ── Parse metadata
    meta: Dict[str, Any] = {}
    if metadata:
        try:
            meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        except json.JSONDecodeError as e:
            return {"id": None, "status": "error", "error": f"Invalid metadata JSON: {e}"}

    # ── Validate metadata.type (policy helper)
    type_err = _validate_metadata_type(meta)
    if type_err:
        return {"id": None, "status": "error", "error": type_err}

    # ── Stage 1: PII + Secrets Redaction
    redaction: RedactionResult = redact(content, level=REDACTION_LEVEL)
    redacted_content = redaction.content

    # ── Compute source_hash for deduplication
    source_hash = _compute_source_hash(project, redacted_content, meta)

    # ── Attach redaction audit to metadata
    meta["redaction"] = {
        "pii_redacted": redaction.pii_redacted,
        "secrets_filtered": redaction.secrets_filtered,
        "redaction_level": redaction.redaction_level,
        "pii_count": redaction.pii_count,
        "secret_count": redaction.secret_count,
    }
    meta["source_hash"] = source_hash
    meta["synapse_version"] = VERSION
    meta["synapse_mode"] = SYNAPSE_MODE

    # ── Stage 2: Insert (embedding=NULL for low latency)
    try:
        result = db.table("memories").insert({
            "content": redacted_content,
            "metadata": meta,
            "project": project.strip().upper(),
            "source_hash": source_hash,
            # embedding is NULL — backfill will process it
        }).execute()

        memory_id = result.data[0]["id"]
        logger.info(
            "Memory saved: id=%s, project=%s, hash=%s",
            memory_id, project, source_hash[:12],
        )

        # ── Stage 3: Enqueue embedding job
        db.table("embedding_jobs").insert({
            "memory_id": memory_id,
            "status": "pending",
        }).execute()

        return {
            "id": memory_id,
            "status": "saved",
            "deduplicated": False,
            "redaction": {
                "pii_redacted": redaction.pii_redacted,
                "secrets_filtered": redaction.secrets_filtered,
                "redaction_level": redaction.redaction_level,
            },
        }

    except Exception as e:
        error_str = str(e)
        # Check for duplicate key violation (source_hash unique index)
        if "idx_memories_source_hash_unique" in error_str or "duplicate" in error_str.lower():
            logger.info(
                "Deduplicated: project=%s, hash=%s",
                project, source_hash[:12],
            )
            return {
                "id": None,
                "status": "deduplicated",
                "deduplicated": True,
                "message": "Identical memory already exists for this project.",
            }
        logger.error("Insert failed: %s", error_str)
        return {"id": None, "status": "error", "error": error_str}


@mcp.tool()
def backfill_embeddings(limit: int = 10) -> dict:
    """Process pending embedding jobs asynchronously.

    Fetches memories with pending embedding jobs, generates embeddings
    via the configured provider, and updates the memories table.

    SECURITY: Only REDACTED content is sent to the embedding provider.

    Parameters
    ----------
    limit : int
        Maximum number of pending jobs to process (default 10, max 50).

    Returns
    -------
    dict
        {"processed": int, "failed": int, "remaining": int}
    """
    limit = min(max(limit, 1), 50)

    # Fetch pending jobs
    jobs_result = (
        db.table("embedding_jobs")
        .select("id, memory_id")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    jobs = jobs_result.data or []
    if not jobs:
        # Count total remaining
        remaining_result = (
            db.table("embedding_jobs")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        return {
            "processed": 0,
            "failed": 0,
            "remaining": remaining_result.count or 0,
        }

    processed = 0
    failed = 0

    for job in jobs:
        job_id = job["id"]
        memory_id = job["memory_id"]

        try:
            # Mark as processing (increment attempts via RPC or fetch+update)
            job_data = (
                db.table("embedding_jobs")
                .select("attempts")
                .eq("id", job_id)
                .single()
                .execute()
            )
            current_attempts = (job_data.data or {}).get("attempts", 0)
            db.table("embedding_jobs").update({
                "status": "processing",
                "attempts": current_attempts + 1,
            }).eq("id", job_id).execute()

            # Fetch redacted content
            mem_result = (
                db.table("memories")
                .select("content")
                .eq("id", memory_id)
                .single()
                .execute()
            )

            if not mem_result.data:
                raise ValueError(f"Memory {memory_id} not found")

            # SECURITY: content is already redacted (stored redacted)
            redacted_content = mem_result.data["content"]

            # Generate embedding from REDACTED content
            embedding = _generate_embedding(redacted_content)

            # Update memory with embedding
            db.table("memories").update({
                "embedding": embedding,
            }).eq("id", memory_id).execute()

            # Mark job completed
            db.table("embedding_jobs").update({
                "status": "completed",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()

            processed += 1
            logger.info("Embedding generated: memory_id=%s", memory_id)

        except Exception as e:
            failed += 1
            error_msg = str(e)
            logger.error(
                "Embedding failed: job_id=%s, memory_id=%s, error=%s",
                job_id, memory_id, error_msg,
            )
            # Mark as failed (will retry if attempts < max_attempts)
            try:
                db.table("embedding_jobs").update({
                    "status": "failed",
                    "error_message": error_msg[:500],
                }).eq("id", job_id).execute()
            except Exception:
                pass

    # Count remaining
    remaining_result = (
        db.table("embedding_jobs")
        .select("id", count="exact")
        .eq("status", "pending")
        .execute()
    )

    return {
        "processed": processed,
        "failed": failed,
        "remaining": remaining_result.count or 0,
    }


@mcp.tool()
def health_check() -> dict:
    """Check server health, database connectivity, and queue status.

    Returns
    -------
    dict
        {"ok": bool, "version": str, "db": str, "queue": {...}, "mode": str}
    """
    try:
        # Test DB connectivity
        test = db.table("memories").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    # Queue stats
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
        "mode": SYNAPSE_MODE,
        "embedding_provider": EMBEDDING_PROVIDER,
        "db": db_status,
        "queue": {
            "pending_embeddings": queue_pending,
        },
        "projects_allowlist": sorted(ALLOWED_PROJECTS) if ALLOWED_PROJECTS else "*",
        "redaction_level": REDACTION_LEVEL,
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }


# ───────────────────────────────────────────────────────────────────────
# Entrypoint
# ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "Starting Synapse Layer Auto-Save MCP Bridge v%s "
        "(mode=%s, provider=%s, redaction=%s)",
        VERSION, SYNAPSE_MODE, EMBEDDING_PROVIDER, REDACTION_LEVEL,
    )
    mcp.run(transport="stdio")
