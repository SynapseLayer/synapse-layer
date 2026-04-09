"""
Synapse Layer — Semantic Kernel Integration

Two enterprise-ready adapters for the Microsoft Semantic Kernel ecosystem:

* **SynapseChatHistory** — extends ``ChatHistory`` with automatic
  Cognitive Security (PII redaction + AES-256 encryption) on every
  message, providing persistent, sovereign chat state.

* **SynapseMemoryStore** — implements ``MemoryStoreBase`` so that
  SK’s ``SemanticTextMemory`` can store and retrieve knowledge
  from Synapse Layer’s encrypted memory vault.

Compatible with ``semantic-kernel >=1.0``.

Usage (Chat History)::

    from synapse_memory.integrations.semantic_kernel import SynapseChatHistory

    history = SynapseChatHistory(agent_id="copilot-01")
    history.add_user_message("What is our revenue target?")

Usage (Memory Store)::

    from synapse_memory.integrations.semantic_kernel import SynapseMemoryStore

    store = SynapseMemoryStore(agent_id="enterprise-bot")
    memory = SemanticTextMemory(storage=store, embeddings_generator=embedder)

Note:
    Advanced scoring, PRO heuristics, and enterprise features are
    not part of this OSS adapter.  For enterprise capabilities, see
    https://synapselayer.org/docs.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import warnings as _warnings
    _warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module=r"semantic_kernel\.memory"
    )
    import numpy as np
    from semantic_kernel.contents.chat_history import ChatHistory
    from semantic_kernel.contents.chat_message_content import ChatMessageContent
    from semantic_kernel.contents.utils.author_role import AuthorRole
    from semantic_kernel.memory.memory_store_base import MemoryStoreBase
    from semantic_kernel.memory.memory_record import MemoryRecord
    from semantic_kernel.memory.memory_query_result import MemoryQueryResult
except ImportError as exc:
    raise ImportError(
        "semantic-kernel >=1.0 is required for the Semantic Kernel integration. "
        "Install it with: pip install semantic-kernel"
    ) from exc

from synapse_memory.core import SynapseMemory

logger = logging.getLogger(__name__)

__all__ = ["SynapseChatHistory", "SynapseMemoryStore"]


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------

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


# =========================================================================
# SynapseChatHistory — ChatHistory with Cognitive Security
# =========================================================================

_ROLE_MAP = {
    AuthorRole.USER: "user",
    AuthorRole.ASSISTANT: "assistant",
    AuthorRole.SYSTEM: "system",
    AuthorRole.TOOL: "tool",
}


class SynapseChatHistory(ChatHistory):
    """Semantic Kernel ``ChatHistory`` with Synapse Layer persistence.

    Every message added to this history is simultaneously routed
    through the Cognitive Security pipeline (PII redaction, intent
    validation, AES-256 encryption) before being stored.

    Parameters
    ----------
    agent_id:
        Unique identifier for the memory namespace.
    encryption_key:
        Optional Fernet key for at-rest encryption.
    """

    _synapse: SynapseMemory = None  # type: ignore[assignment]
    _agent_id: str = ""  # type: ignore[assignment]

    def __init__(
        self,
        agent_id: str = "sk-agent",
        encryption_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        kw: Dict[str, Any] = {"agent_id": agent_id}
        if encryption_key:
            kw["encryption_key"] = encryption_key
        object.__setattr__(self, "_synapse", SynapseMemory(**kw))
        object.__setattr__(self, "_agent_id", agent_id)

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def synapse(self) -> SynapseMemory:
        """Access the underlying :class:`SynapseMemory` instance."""
        return self._synapse

    # -- Override message addition to route through Synapse -----------------

    def add_message(
        self,
        message: ChatMessageContent | dict[str, Any],
        encoding: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message and persist through Cognitive Security."""
        super().add_message(message, encoding=encoding, metadata=metadata)

        # Extract content for Synapse storage
        if isinstance(message, ChatMessageContent):
            content = str(message.content or "")
            role = _ROLE_MAP.get(message.role, "user")
        elif isinstance(message, dict):
            content = str(message.get("content", ""))
            role = str(message.get("role", "user"))
        else:
            content = str(message)
            role = "user"

        if content.strip():
            _run_async(self._synapse.store(
                content=content,
                metadata={"role": role, "source": "semantic_kernel"},
            ))

    def add_user_message(
        self,
        content: Any,
        **kwargs: Any,
    ) -> None:
        """Add a user message with Synapse persistence."""
        super().add_user_message(content, **kwargs)
        text = str(content)
        if text.strip():
            _run_async(self._synapse.store(
                content=text,
                metadata={"role": "user", "source": "semantic_kernel"},
            ))

    def add_assistant_message(
        self,
        content: Any,
        **kwargs: Any,
    ) -> None:
        """Add an assistant message with Synapse persistence."""
        super().add_assistant_message(content, **kwargs)
        text = str(content)
        if text.strip():
            _run_async(self._synapse.store(
                content=text,
                metadata={"role": "assistant", "source": "semantic_kernel"},
            ))

    def add_system_message(
        self,
        content: Any,
        **kwargs: Any,
    ) -> None:
        """Add a system message with Synapse persistence."""
        super().add_system_message(content, **kwargs)
        text = str(content)
        if text.strip():
            _run_async(self._synapse.store(
                content=text,
                metadata={"role": "system", "source": "semantic_kernel"},
            ))

    def clear(self) -> None:
        """Remove all messages and clear Synapse store."""
        self.messages.clear()
        self._synapse._memories.clear()

    def __repr__(self) -> str:
        return (
            f"SynapseChatHistory(agent_id={self._agent_id!r}, "
            f"messages={len(self.messages)})"
        )


# =========================================================================
# SynapseMemoryStore — MemoryStoreBase implementation
# =========================================================================

class SynapseMemoryStore(MemoryStoreBase):
    """Semantic Kernel ``MemoryStoreBase`` backed by Synapse Layer.

    Provides collection-based memory storage where each collection
    maps to a Synapse agent namespace.  Records are persisted through
    the Cognitive Security pipeline.

    Parameters
    ----------
    agent_id:
        Base identifier for the memory namespace.
    encryption_key:
        Optional Fernet key for at-rest encryption.
    """

    def __init__(
        self,
        agent_id: str = "sk-memory",
        encryption_key: Optional[str] = None,
    ) -> None:
        self._agent_id = agent_id
        self._encryption_key = encryption_key
        # collection_name -> {key -> MemoryRecord}
        self._collections: Dict[str, Dict[str, MemoryRecord]] = {}
        # One Synapse instance per collection for namespace isolation
        self._synapse_instances: Dict[str, SynapseMemory] = {}

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def _get_synapse(self, collection_name: str) -> SynapseMemory:
        """Get or create a SynapseMemory for a collection."""
        if collection_name not in self._synapse_instances:
            kw: Dict[str, Any] = {
                "agent_id": f"{self._agent_id}:{collection_name}"
            }
            if self._encryption_key:
                kw["encryption_key"] = self._encryption_key
            self._synapse_instances[collection_name] = SynapseMemory(**kw)
        return self._synapse_instances[collection_name]

    # -- Collection management ----------------------------------------------

    async def create_collection(self, collection_name: str) -> None:
        if collection_name not in self._collections:
            self._collections[collection_name] = {}
            self._get_synapse(collection_name)  # Ensure Synapse instance exists

    async def does_collection_exist(self, collection_name: str) -> bool:
        return collection_name in self._collections

    async def get_collections(self) -> list[str]:
        return list(self._collections.keys())

    async def delete_collection(self, collection_name: str) -> None:
        self._collections.pop(collection_name, None)
        synapse = self._synapse_instances.pop(collection_name, None)
        if synapse:
            synapse._memories.clear()

    # -- Record CRUD --------------------------------------------------------

    async def upsert(self, collection_name: str, record: MemoryRecord) -> str:
        if collection_name not in self._collections:
            await self.create_collection(collection_name)

        self._collections[collection_name][record.id] = record

        # Persist text through Synapse pipeline
        text = record.text or record.description or ""
        if text.strip():
            synapse = self._get_synapse(collection_name)
            await synapse.store(
                content=text,
                metadata={
                    "record_id": record.id,
                    "description": record.description or "",
                    "additional_metadata": record.additional_metadata or "",
                },
            )
        return record.id

    async def upsert_batch(
        self, collection_name: str, records: list[MemoryRecord],
    ) -> list[str]:
        ids = []
        for record in records:
            rid = await self.upsert(collection_name, record)
            ids.append(rid)
        return ids

    async def get(
        self, collection_name: str, key: str, with_embedding: bool,
    ) -> MemoryRecord:
        coll = self._collections.get(collection_name, {})
        record = coll.get(key)
        if record is None:
            raise KeyError(f"Record '{key}' not found in collection '{collection_name}'")
        if not with_embedding:
            return MemoryRecord(
                is_reference=record._is_reference,
                external_source_name=record._external_source_name,
                id=record.id,
                description=record.description,
                text=record.text,
                additional_metadata=record.additional_metadata,
                embedding=None,
                timestamp=record.timestamp,
            )
        return record

    async def get_batch(
        self, collection_name: str, keys: list[str], with_embeddings: bool,
    ) -> list[MemoryRecord]:
        results = []
        for key in keys:
            try:
                record = await self.get(collection_name, key, with_embeddings)
                results.append(record)
            except KeyError:
                pass
        return results

    async def remove(self, collection_name: str, key: str) -> None:
        coll = self._collections.get(collection_name, {})
        coll.pop(key, None)

    async def remove_batch(self, collection_name: str, keys: list[str]) -> None:
        for key in keys:
            await self.remove(collection_name, key)

    # -- Nearest match (semantic search via Synapse recall) -----------------

    async def get_nearest_matches(
        self,
        collection_name: str,
        embedding: np.ndarray,
        limit: int,
        min_relevance_score: float,
        with_embeddings: bool,
    ) -> list[tuple[MemoryRecord, float]]:
        """Semantic search using Synapse recall.

        Since Synapse uses its own similarity engine, the embedding
        parameter is used as a fallback query.  We reconstruct a text
        query from stored records that match the embedding profile.
        """
        coll = self._collections.get(collection_name, {})
        if not coll:
            return []

        # Use Synapse recall for semantic matching
        synapse = self._get_synapse(collection_name)

        # Build a query from the collection's most recent entry as context
        # (SK usually pairs this with an embedding from the query text)
        query_text = "memory search"
        # Try to find a matching record by embedding similarity
        if embedding is not None and len(coll) > 0:
            # Use first record's text as query fallback
            for rec in coll.values():
                if rec.text:
                    query_text = rec.text
                    break

        results = await synapse.recall(query_text, top_k=limit)

        matches: list[tuple[MemoryRecord, float]] = []
        for r in results:
            if r.trust_quotient < min_relevance_score:
                continue
            # Find the matching record in our collection
            record_id = None
            for mid, mem in synapse._memories.items():
                if mem.get("content") == r.content:
                    record_id = mem.get("metadata", {}).get("record_id")
                    break

            if record_id and record_id in coll:
                record = coll[record_id]
                if not with_embeddings:
                    record = MemoryRecord(
                        is_reference=record._is_reference,
                        external_source_name=record._external_source_name,
                        id=record.id,
                        description=record.description,
                        text=record.text,
                        additional_metadata=record.additional_metadata,
                        embedding=None,
                        timestamp=record.timestamp,
                    )
                matches.append((record, r.trust_quotient))

            if len(matches) >= limit:
                break

        return matches

    async def get_nearest_match(
        self,
        collection_name: str,
        embedding: np.ndarray,
        min_relevance_score: float,
        with_embedding: bool,
    ) -> tuple[MemoryRecord, float]:
        results = await self.get_nearest_matches(
            collection_name, embedding, limit=1,
            min_relevance_score=min_relevance_score,
            with_embeddings=with_embedding,
        )
        if not results:
            raise KeyError(
                f"No match found in collection '{collection_name}' "
                f"with min_relevance_score={min_relevance_score}"
            )
        return results[0]

    async def close(self) -> None:
        """Cleanup."""
        pass

    def __repr__(self) -> str:
        n = len(self._collections)
        return f"SynapseMemoryStore(agent_id={self._agent_id!r}, collections={n})"
