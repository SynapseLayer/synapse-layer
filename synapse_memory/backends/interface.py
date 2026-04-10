"""
Synapse Layer — StorageBackend Protocol

Immutable contract for all persistence backends.
Any class implementing this protocol can be passed to SynapseMemory.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Universal storage interface for SynapseMemory.

    All methods are synchronous. For async backends, wrap with
    ``asyncio.to_thread``.
    """

    def save(self, record: Dict[str, Any]) -> str:
        """Persist a memory record.

        Args:
            record: Dict with keys: memory_id, agent_id, content,
                    embedding, trust_quotient, confidence, intent,
                    is_critical, source_type, metadata, timestamp.

        Returns:
            The memory_id of the persisted record.
        """
        ...

    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories matching query.

        Args:
            query: Natural language query (substring or semantic).
            agent_id: Optional scope filter.
            limit: Maximum results.

        Returns:
            List of memory record dicts, ordered by relevance.
        """
        ...

    def delete(self, memory_id: str) -> bool:
        """Delete a single memory by ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    def clear(self, agent_id: Optional[str] = None) -> int:
        """Delete all memories, optionally scoped to agent_id.

        Returns:
            Number of records deleted.
        """
        ...

    def count(self, agent_id: Optional[str] = None) -> int:
        """Count stored memories."""
        ...
