"""
Synapse Layer — In-Memory Backend

Non-persistent backend for testing and SDK demos.
This is the original behavior of SynapseMemory.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryBackend:
    """In-memory storage (non-persistent).

    Data is lost when the process exits. Suitable for testing,
    demos, and CI pipelines.
    """

    def __init__(self) -> None:
        self._store: List[Dict[str, Any]] = []

    def save(self, record: Dict[str, Any]) -> str:
        memory_id = record.get("memory_id", "")
        self._store.append(record)
        return memory_id

    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        pool = self._store
        if agent_id:
            pool = [m for m in pool if m.get("agent_id") == agent_id]

        words = [w for w in query.lower().split() if w]

        if not words:
            # No query — return most recent by trust_quotient
            pool = sorted(
                pool,
                key=lambda m: (m.get("trust_quotient", 0), m.get("timestamp", 0)),
                reverse=True,
            )
            return pool[:limit]

        results = []
        for mem in pool:
            content_lower = mem.get("content", "").lower()
            hits = sum(1 for w in words if w in content_lower)
            if hits > 0:
                relevance = hits / len(words)
                score = mem.get("trust_quotient", 0.5) * relevance
                results.append((mem, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]

    def delete(self, memory_id: str) -> bool:
        for i, mem in enumerate(self._store):
            if mem.get("memory_id") == memory_id:
                self._store.pop(i)
                return True
        return False

    def clear(self, agent_id: Optional[str] = None) -> int:
        if agent_id is None:
            count = len(self._store)
            self._store.clear()
            return count
        original = len(self._store)
        self._store = [
            m for m in self._store if m.get("agent_id") != agent_id
        ]
        return original - len(self._store)

    def count(self, agent_id: Optional[str] = None) -> int:
        if agent_id is None:
            return len(self._store)
        return sum(
            1 for m in self._store if m.get("agent_id") == agent_id
        )
