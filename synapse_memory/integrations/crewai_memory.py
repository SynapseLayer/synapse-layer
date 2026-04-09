"""
Synapse Layer — CrewAI Integration

A storage backend that plugs Synapse Layer into CrewAI's unified
memory system as a persistent, encrypted memory provider.

Implements the ``StorageBackend`` protocol from CrewAI v1.14+.

Usage:
    from synapse_memory.integrations.crewai_memory import SynapseCrewStorage
    from crewai.memory.unified_memory import Memory
    from crewai import Crew

    crew = Crew(
        agents=[...],
        tasks=[...],
        memory=Memory(storage=SynapseCrewStorage(agent_id="my-crew")),
    )

Note:
    Advanced scoring, PRO heuristics, and enterprise features are
    not part of this OSS adapter.  For enterprise capabilities, see
    https://synapselayer.org/docs.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from crewai.memory.storage.backend import StorageBackend
    from crewai.memory.types import MemoryRecord, ScopeInfo
except ImportError as exc:
    raise ImportError(
        "crewai is required for the CrewAI integration. "
        "Install it with: pip install crewai"
    ) from exc

from synapse_memory.core import SynapseMemory

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run a coroutine from synchronous code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class SynapseCrewStorage:
    """CrewAI StorageBackend backed by Synapse Layer.

    Routes all memory operations through the Synapse Layer Cognitive
    Security pipeline (sanitization, PII redaction, encryption) while
    exposing the ``StorageBackend`` protocol expected by CrewAI v1.14+.

    Parameters
    ----------
    agent_id : str
        Unique identifier for memory isolation.
    memory : SynapseMemory | None
        Pre-configured SynapseMemory instance. If None, one is created
        with default settings using ``agent_id``.

    Example
    -------
    >>> from synapse_memory.integrations.crewai_memory import SynapseCrewStorage
    >>> storage = SynapseCrewStorage(agent_id="research-crew")
    >>> # Pass to CrewAI Memory:
    >>> # Memory(storage=storage)
    """

    def __init__(
        self,
        agent_id: str,
        *,
        memory: Optional[SynapseMemory] = None,
    ) -> None:
        self._agent_id = agent_id
        self._memory = memory or SynapseMemory(agent_id=agent_id)

        logger.info(
            "SynapseCrewStorage initialized: agent=%s",
            agent_id,
        )

    # ── Core Properties ──────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        """The agent ID scoping this storage."""
        return self._agent_id

    # ── StorageBackend Protocol: save ────────────────────────────────

    def save(self, records: List[MemoryRecord]) -> None:
        """Save CrewAI memory records through the Synapse Layer pipeline.

        Each record's content is stored via ``SynapseMemory.store()``
        with CrewAI metadata preserved.
        """
        for record in records:
            metadata = {
                "crewai_record_id": record.id,
                "scope": record.scope,
                "categories": record.categories,
                "importance": record.importance,
                "integration": "crewai",
                **(record.metadata or {}),
            }
            if record.source:
                metadata["source"] = record.source

            _run_async(
                self._memory.store(
                    content=record.content,
                    confidence=record.importance,
                    metadata=metadata,
                )
            )

        logger.debug("Saved %d records via Synapse Layer", len(records))

    # ── StorageBackend Protocol: search ──────────────────────────────

    def search(
        self,
        query_embedding: List[float],
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[tuple]:
        """Search memories by vector similarity.

        Uses Synapse Layer's cosine similarity matching against
        stored embeddings. Returns (MemoryRecord, score) tuples.
        """
        # Use the internal memory store for similarity search
        scored: List[tuple] = []

        for mem in self._memory._memories:
            mem_metadata = mem.get("metadata", {})

            # Scope filter
            if scope_prefix:
                mem_scope = mem_metadata.get("scope", "/")
                if not mem_scope.startswith(scope_prefix):
                    continue

            # Category filter
            if categories:
                mem_cats = mem_metadata.get("categories", [])
                if not any(c in mem_cats for c in categories):
                    continue

            # Metadata filter
            if metadata_filter:
                if not all(
                    mem_metadata.get(k) == v
                    for k, v in metadata_filter.items()
                ):
                    continue

            # Compute cosine similarity with query embedding
            mem_embedding = mem.get("embedding", [])
            if mem_embedding and query_embedding:
                score = SynapseMemory._cosine_similarity(
                    query_embedding, mem_embedding
                )
            else:
                score = 0.0

            if score >= min_score:
                record = self._mem_to_record(mem)
                scored.append((record, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    # ── StorageBackend Protocol: delete ──────────────────────────────

    def delete(
        self,
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        record_ids: Optional[List[str]] = None,
        older_than: Optional[datetime] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Delete memories matching criteria. Returns count deleted."""
        initial_count = len(self._memory._memories)
        to_keep = []

        for mem in self._memory._memories:
            mem_metadata = mem.get("metadata", {})
            should_delete = False

            if record_ids and mem.get("memory_id") in record_ids:
                should_delete = True
            if scope_prefix:
                mem_scope = mem_metadata.get("scope", "/")
                if mem_scope.startswith(scope_prefix):
                    should_delete = True
            if categories:
                mem_cats = mem_metadata.get("categories", [])
                if any(c in mem_cats for c in categories):
                    should_delete = True
            if older_than:
                mem_time = datetime.fromtimestamp(mem.get("timestamp", 0))
                if mem_time < older_than:
                    should_delete = True

            if not should_delete:
                to_keep.append(mem)

        self._memory._memories = to_keep
        deleted = initial_count - len(to_keep)
        logger.debug("Deleted %d records", deleted)
        return deleted

    # ── StorageBackend Protocol: update ──────────────────────────────

    def update(self, record: MemoryRecord) -> None:
        """Update an existing record by ID."""
        for i, mem in enumerate(self._memory._memories):
            if mem.get("memory_id") == record.id or \
               mem.get("metadata", {}).get("crewai_record_id") == record.id:
                self._memory._memories[i]["content"] = record.content
                self._memory._memories[i]["metadata"].update(record.metadata or {})
                self._memory._memories[i]["confidence"] = record.importance
                logger.debug("Updated record %s", record.id)
                return
        # If not found, save as new
        self.save([record])

    # ── StorageBackend Protocol: get_record ──────────────────────────

    def get_record(self, record_id: str) -> Optional[MemoryRecord]:
        """Return a single record by ID, or None."""
        for mem in self._memory._memories:
            if mem.get("memory_id") == record_id or \
               mem.get("metadata", {}).get("crewai_record_id") == record_id:
                return self._mem_to_record(mem)
        return None

    # ── StorageBackend Protocol: list_records ────────────────────────

    def list_records(
        self,
        scope_prefix: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[MemoryRecord]:
        """List records, newest first."""
        filtered = self._memory._memories
        if scope_prefix:
            filtered = [
                m for m in filtered
                if m.get("metadata", {}).get("scope", "/").startswith(scope_prefix)
            ]

        # Sort by timestamp descending
        filtered.sort(key=lambda m: m.get("timestamp", 0), reverse=True)
        return [
            self._mem_to_record(m)
            for m in filtered[offset:offset + limit]
        ]

    # ── StorageBackend Protocol: get_scope_info ──────────────────────

    def get_scope_info(self, scope: str) -> ScopeInfo:
        """Get information about a scope."""
        matching = [
            m for m in self._memory._memories
            if m.get("metadata", {}).get("scope", "/").startswith(scope)
        ]
        categories = set()
        timestamps = []
        child_scopes = set()

        for m in matching:
            for c in m.get("metadata", {}).get("categories", []):
                categories.add(c)
            timestamps.append(m.get("timestamp", 0))
            mem_scope = m.get("metadata", {}).get("scope", "/")
            if mem_scope != scope and mem_scope.startswith(scope):
                # Get immediate child
                remainder = mem_scope[len(scope):].strip("/")
                if remainder:
                    child = scope.rstrip("/") + "/" + remainder.split("/")[0]
                    child_scopes.add(child)

        return ScopeInfo(
            path=scope,
            record_count=len(matching),
            categories=sorted(categories),
            oldest_record=datetime.fromtimestamp(min(timestamps)) if timestamps else None,
            newest_record=datetime.fromtimestamp(max(timestamps)) if timestamps else None,
            child_scopes=sorted(child_scopes),
        )

    # ── StorageBackend Protocol: list_scopes ────────────────────────

    def list_scopes(self, parent: str = "/") -> List[str]:
        """List immediate child scopes under a parent path."""
        children = set()
        for m in self._memory._memories:
            mem_scope = m.get("metadata", {}).get("scope", "/")
            if mem_scope.startswith(parent) and mem_scope != parent:
                remainder = mem_scope[len(parent):].strip("/")
                if remainder:
                    child = parent.rstrip("/") + "/" + remainder.split("/")[0]
                    children.add(child)
        return sorted(children)

    # ── StorageBackend Protocol: list_categories ────────────────────

    def list_categories(self, scope_prefix: Optional[str] = None) -> Dict[str, int]:
        """List categories and their counts."""
        counts: Dict[str, int] = {}
        for m in self._memory._memories:
            if scope_prefix:
                mem_scope = m.get("metadata", {}).get("scope", "/")
                if not mem_scope.startswith(scope_prefix):
                    continue
            for c in m.get("metadata", {}).get("categories", []):
                counts[c] = counts.get(c, 0) + 1
        return counts

    # ── StorageBackend Protocol: count ───────────────────────────────

    def count(self, scope_prefix: Optional[str] = None) -> int:
        """Count records in scope."""
        if not scope_prefix:
            return len(self._memory._memories)
        return sum(
            1 for m in self._memory._memories
            if m.get("metadata", {}).get("scope", "/").startswith(scope_prefix)
        )

    # ── StorageBackend Protocol: reset ───────────────────────────────

    def reset(self, scope_prefix: Optional[str] = None) -> None:
        """Reset (delete all) memories in scope."""
        if not scope_prefix:
            self._memory._memories.clear()
        else:
            self._memory._memories = [
                m for m in self._memory._memories
                if not m.get("metadata", {}).get("scope", "/").startswith(scope_prefix)
            ]
        logger.info("Reset memories (scope=%s)", scope_prefix or "all")

    # ── StorageBackend Protocol: async variants ─────────────────────

    async def asave(self, records: List[MemoryRecord]) -> None:
        """Async save records."""
        for record in records:
            metadata = {
                "crewai_record_id": record.id,
                "scope": record.scope,
                "categories": record.categories,
                "importance": record.importance,
                "integration": "crewai",
                **(record.metadata or {}),
            }
            if record.source:
                metadata["source"] = record.source

            await self._memory.store(
                content=record.content,
                confidence=record.importance,
                metadata=metadata,
            )

    async def asearch(
        self,
        query_embedding: List[float],
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[tuple]:
        """Async search — delegates to sync implementation."""
        return self.search(
            query_embedding=query_embedding,
            scope_prefix=scope_prefix,
            categories=categories,
            metadata_filter=metadata_filter,
            limit=limit,
            min_score=min_score,
        )

    async def adelete(
        self,
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        record_ids: Optional[List[str]] = None,
        older_than: Optional[datetime] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Async delete — delegates to sync implementation."""
        return self.delete(
            scope_prefix=scope_prefix,
            categories=categories,
            record_ids=record_ids,
            older_than=older_than,
            metadata_filter=metadata_filter,
        )

    # ── Internal Helpers ────────────────────────────────────────────

    def _mem_to_record(self, mem: Dict[str, Any]) -> MemoryRecord:
        """Convert internal Synapse memory dict to CrewAI MemoryRecord."""
        metadata = mem.get("metadata", {})
        return MemoryRecord(
            id=metadata.get("crewai_record_id", mem.get("memory_id", "")),
            content=mem.get("content", ""),
            scope=metadata.get("scope", "/"),
            categories=metadata.get("categories", []),
            metadata={
                k: v for k, v in metadata.items()
                if k not in ("crewai_record_id", "scope", "categories",
                             "importance", "integration")
            },
            importance=metadata.get("importance", 0.5),
            created_at=datetime.fromtimestamp(mem.get("timestamp", time.time())),
            last_accessed=datetime.fromtimestamp(mem.get("timestamp", time.time())),
            embedding=mem.get("embedding"),
            source=metadata.get("source"),
        )

    # ── String Representation ────────────────────────────────────────

    def __repr__(self) -> str:
        return f"SynapseCrewStorage(agent_id={self._agent_id!r})"
