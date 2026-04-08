"""
Synapse Layer — Auto-Save Engine (Core)

Orchestrates the full auto-save pipeline:
    text → trigger_detect → policy_evaluate → redact → dedup → persist

Designed for:
    - Near-zero perceived latency (embedding=NULL on insert)
    - Security-first (PII redacted before any I/O)
    - Testability (all dependencies injected)

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol

from .types import AutoSaveEvent, PolicyDecision, SaveResult
from .policy import PolicyEngine
from .triggers import TriggerDetector
from .formatter import EventFormatter

logger = logging.getLogger("synapse.autosave.engine")


# ── Protocols for Dependency Injection ───────────────────────────────

class RedactorProtocol(Protocol):
    """Minimal interface for the redaction layer."""
    def __call__(self, content: str, level: str = "strict") -> Any: ...


class DatabaseProtocol(Protocol):
    """Minimal interface for database operations."""
    def insert_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...
    def enqueue_embedding(self, memory_id: str) -> None: ...
    def fetch_pending_jobs(self, limit: int) -> List[Dict[str, Any]]: ...
    def fetch_memory_content(self, memory_id: str) -> Optional[str]: ...
    def update_embedding(self, memory_id: str, embedding: List[float]) -> None: ...
    def complete_job(self, job_id: str) -> None: ...
    def fail_job(self, job_id: str, error: str) -> None: ...


# ── LRU Dedup Cache ─────────────────────────────────────────────────

class _LRUCache:
    """Simple LRU cache with TTL for dedup hashes."""

    def __init__(self, maxsize: int = 100, ttl: float = 60.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: OrderedDict[str, float] = OrderedDict()

    def contains(self, key: str) -> bool:
        if key in self._store:
            ts = self._store[key]
            if time.time() - ts < self._ttl:
                self._store.move_to_end(key)
                return True
            else:
                del self._store[key]
        return False

    def add(self, key: str) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = time.time()
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)


# ── Auto-Save Engine ────────────────────────────────────────────────

class AutoSaveEngine:
    """Autonomous memory persistence engine.

    Orchestrates trigger detection, policy evaluation, PII redaction,
    deduplication, and database persistence in a single pipeline.

    All dependencies are injected for testability.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        database: DatabaseProtocol,
        redactor: RedactorProtocol,
        policy: Optional[PolicyEngine] = None,
        trigger_detector: Optional[TriggerDetector] = None,
        formatter: Optional[EventFormatter] = None,
        cache_maxsize: int = 100,
        cache_ttl: float = 60.0,
    ) -> None:
        self._db = database
        self._redactor = redactor
        self._policy = policy or PolicyEngine()
        self._triggers = trigger_detector or TriggerDetector()
        self._formatter = formatter or EventFormatter()
        self._cache = _LRUCache(maxsize=cache_maxsize, ttl=cache_ttl)

    # ── Public API ─────────────────────────────────────────────────────

    def save(self, event: AutoSaveEvent) -> SaveResult:
        """Save a single event through the full pipeline.

        Pipeline:
            1. Policy evaluation (block/allow)
            2. PII/secrets redaction
            3. Source hash computation
            4. LRU cache dedup check
            5. Database insert (embedding=NULL)
            6. Enqueue embedding job

        Returns
        -------
        SaveResult
            Outcome with status: saved, deduplicated, blocked, or error.
        """
        # 1. Policy gate
        decision: PolicyDecision = self._policy.evaluate(event)
        if not decision.should_save:
            logger.info(
                "Event blocked: reason=%s, project=%s",
                decision.reason, event.project,
            )
            return SaveResult(
                id=None,
                status="blocked",
                project=event.project,
                type=event.type,
                importance=decision.adjusted_importance,
                reason=decision.blocked_reason or decision.reason,
            )

        # Update importance from policy decision
        event.importance = decision.adjusted_importance

        # 2. Redact PII/secrets
        redaction_result = self._redactor(event.content)
        redacted_content = (
            redaction_result.content
            if hasattr(redaction_result, 'content')
            else str(redaction_result)
        )
        event.redaction = {
            "pii_redacted": getattr(redaction_result, 'pii_redacted', False),
            "secrets_filtered": getattr(redaction_result, 'secrets_filtered', False),
            "redaction_level": getattr(redaction_result, 'redaction_level', 'strict'),
        }

        # 3. Compute source hash
        source_hash = self._compute_hash(
            event.project, redacted_content, event.type,
        )

        # 4. LRU cache dedup
        if self._cache.contains(source_hash):
            logger.info(
                "Deduplicated via cache: hash=%s, project=%s",
                source_hash[:12], event.project,
            )
            return SaveResult(
                id=None,
                status="deduplicated",
                project=event.project,
                type=event.type,
                importance=event.importance,
                reason="LRU cache hit",
            )

        # 5. Format and persist
        payload = self._formatter.format(event, content_override=redacted_content)
        payload["source_hash"] = source_hash

        try:
            result = self._db.insert_memory(payload)
            memory_id = result.get("id", "")

            # 6. Enqueue embedding job
            self._db.enqueue_embedding(memory_id)

            # 7. Update cache
            self._cache.add(source_hash)

            now = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Memory saved: id=%s, project=%s, type=%s, importance=%d",
                memory_id, event.project, event.type, event.importance,
            )

            return SaveResult(
                id=memory_id,
                status="saved",
                project=event.project,
                type=event.type,
                importance=event.importance,
                created_at=now,
                reason="approved",
            )

        except Exception as e:
            error_str = str(e)
            # Check for DB-level dedup (unique index)
            if "duplicate" in error_str.lower() or "unique" in error_str.lower():
                self._cache.add(source_hash)
                return SaveResult(
                    id=None,
                    status="deduplicated",
                    project=event.project,
                    type=event.type,
                    importance=event.importance,
                    reason="DB unique constraint",
                )
            logger.error("Save failed: %s", error_str)
            return SaveResult(
                id=None,
                status="error",
                project=event.project,
                type=event.type,
                importance=event.importance,
                reason=error_str[:200],
            )

    def process_text(
        self,
        text: str,
        project: Optional[str] = None,
        source: Optional[str] = None,
        source_ref: Optional[Dict[str, Any]] = None,
    ) -> List[SaveResult]:
        """Detect triggers in text and save all resulting events.

        Parameters
        ----------
        text : str
            Free-form text to scan for auto-save triggers.
        project : str | None
            Force a specific project (skip auto-detection).
        source : str | None
            Override source identifier.
        source_ref : dict | None
            Tracing metadata (conversation_id, message_id, url).

        Returns
        -------
        list[SaveResult]
            One result per detected event.
        """
        events = self._triggers.detect(
            text, source=source, project_override=project,
        )
        if source_ref:
            for event in events:
                event.source_ref = source_ref
        return [self.save(event) for event in events]

    def backfill(
        self,
        limit: int = 10,
        embed_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> Dict[str, int]:
        """Process pending embedding jobs.

        Parameters
        ----------
        limit : int
            Maximum jobs to process.
        embed_fn : callable | None
            Function that takes text and returns embedding vector.
            If None, jobs are skipped.

        Returns
        -------
        dict
            {"processed": int, "failed": int, "remaining": int}
        """
        if embed_fn is None:
            return {"processed": 0, "failed": 0, "remaining": 0}

        limit = min(max(limit, 1), 50)
        jobs = self._db.fetch_pending_jobs(limit)

        processed = 0
        failed = 0

        for job in jobs:
            job_id = job.get("id", "")
            memory_id = job.get("memory_id", "")
            try:
                content = self._db.fetch_memory_content(memory_id)
                if not content:
                    raise ValueError(f"Memory {memory_id} not found")

                # SECURITY: content is already redacted in DB
                embedding = embed_fn(content)
                self._db.update_embedding(memory_id, embedding)
                self._db.complete_job(job_id)
                processed += 1
                logger.info("Embedding generated: memory_id=%s", memory_id)

            except Exception as e:
                failed += 1
                logger.error(
                    "Embedding failed: job=%s, error=%s", job_id, str(e),
                )
                self._db.fail_job(job_id, str(e)[:500])

        remaining = max(len(self._db.fetch_pending_jobs(1)) if jobs else 0, 0)
        return {
            "processed": processed,
            "failed": failed,
            "remaining": remaining,
        }

    # ── Internal ───────────────────────────────────────────────────────

    @staticmethod
    def _compute_hash(project: str, content: str, event_type: str) -> str:
        """SHA-256 dedup hash from project + normalized content + type."""
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        payload = json.dumps(
            {"project": project.upper(), "content": normalized, "type": event_type},
            sort_keys=True, ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
