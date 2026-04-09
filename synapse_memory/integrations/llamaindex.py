"""
Synapse Layer — LlamaIndex Integration

Two production-ready adapters for the LlamaIndex ecosystem:

* **SynapseRetriever** — implements ``BaseRetriever`` so that any
  LlamaIndex query engine or chat engine can retrieve knowledge
  from Synapse Layer’s encrypted, trust-scored memory store.

* **SynapseChatStore** — implements ``BaseChatStore`` so that chat
  history is persisted through the Cognitive Security pipeline
  (PII redaction + AES-256 encryption).

Compatible with ``llama-index-core >=0.11``.

Usage (Retriever)::

    from synapse_memory.integrations.llamaindex import SynapseRetriever

    retriever = SynapseRetriever(agent_id="researcher-01", top_k=5)
    nodes = retriever.retrieve("What is our deployment strategy?")

Usage (Chat Store)::

    from synapse_memory.integrations.llamaindex import SynapseChatStore
    from llama_index.core.memory import ChatMemoryBuffer

    store = SynapseChatStore(agent_id="assistant-01")
    memory = ChatMemoryBuffer.from_defaults(chat_store=store, chat_store_key="session-1")

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
from typing import Any, Dict, List, Optional

try:
    from llama_index.core.retrievers import BaseRetriever
    from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
    from llama_index.core.storage.chat_store import BaseChatStore
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
except ImportError as exc:
    raise ImportError(
        "llama-index-core is required for the LlamaIndex integration. "
        "Install it with: pip install llama-index-core"
    ) from exc

from synapse_memory.core import SynapseMemory

logger = logging.getLogger(__name__)

__all__ = ["SynapseRetriever", "SynapseChatStore"]


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
# SynapseRetriever — BaseRetriever implementation
# =========================================================================

class SynapseRetriever(BaseRetriever):
    """LlamaIndex retriever backed by Synapse Layer.

    Translates ``QueryBundle`` into a Synapse ``recall()`` call and
    returns results as ``NodeWithScore`` objects where
    ``score = RecallResult.trust_quotient``.

    Parameters
    ----------
    agent_id:
        Unique identifier for the memory namespace.
    encryption_key:
        Optional Fernet key for at-rest encryption.
    top_k:
        Number of memories to retrieve per query.
    """

    def __init__(self, agent_id: str = "llamaindex-agent",
                 encryption_key: Optional[str] = None,
                 top_k: int = 5, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.agent_id = agent_id
        self.encryption_key = encryption_key
        self.top_k = top_k

        kw: Dict[str, Any] = {"agent_id": agent_id}
        if encryption_key:
            kw["encryption_key"] = encryption_key
        self._synapse = SynapseMemory(**kw)

    @property
    def synapse(self) -> SynapseMemory:
        """Access the underlying :class:`SynapseMemory` instance."""
        return self._synapse

    # -- Sync retrieval -----------------------------------------------------

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Synchronous retrieval."""
        return _run_async(self._aretrieve(query_bundle))

    # -- Async retrieval ----------------------------------------------------

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Asynchronous retrieval — the primary code path."""
        query_text = query_bundle.query_str
        results = await self._synapse.recall(query_text, top_k=self.top_k)

        nodes: List[NodeWithScore] = []
        for r in results:
            node = TextNode(
                text=r.content,
                id_=r.memory_id,
                metadata={
                    "trust_quotient": r.trust_quotient,
                    "intent": r.intent,
                    "timestamp": r.timestamp,
                    "is_critical": r.is_critical,
                    "source": "synapse_layer",
                },
            )
            nodes.append(NodeWithScore(node=node, score=r.trust_quotient))

        logger.debug(
            "SynapseRetriever returned %d nodes for '%s'",
            len(nodes),
            query_text[:60],
        )
        return nodes

    # -- Store helper (populate the memory) ---------------------------------

    async def astore(self, content: str, confidence: float = 0.9,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a memory entry for later retrieval."""
        await self._synapse.store(content=content, confidence=confidence,
                                  metadata=metadata)

    def store(self, content: str, confidence: float = 0.9,
              metadata: Optional[Dict[str, Any]] = None) -> None:
        """Synchronous wrapper for :meth:`astore`."""
        _run_async(self.astore(content, confidence, metadata))

    def __repr__(self) -> str:
        return (
            f"SynapseRetriever(agent_id={self.agent_id!r}, "
            f"top_k={self.top_k})"
        )


# =========================================================================
# SynapseChatStore — BaseChatStore implementation
# =========================================================================

_ROLE_MAP = {
    "user": MessageRole.USER,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "function": MessageRole.FUNCTION,
    "tool": MessageRole.TOOL,
}


class SynapseChatStore(BaseChatStore):
    """LlamaIndex chat store backed by Synapse Layer.

    Every message passes through the Cognitive Security pipeline
    (PII redaction, intent validation, AES-256 encryption) before
    being stored.  Messages are keyed by a string identifier
    (typically a session or conversation id).

    Parameters
    ----------
    agent_id:
        Unique identifier for the memory namespace.
    encryption_key:
        Optional Fernet key for at-rest encryption.
    """

    agent_id: str = "llamaindex-chat"
    encryption_key: Optional[str] = None

    # Internal storage: key -> ordered list of serialised messages
    _synapse: SynapseMemory = None  # type: ignore[assignment]
    _store: Dict[str, List[Dict[str, Any]]] = {}  # type: ignore[assignment]

    def __init__(self, agent_id: str = "llamaindex-chat",
                 encryption_key: Optional[str] = None,
                 **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            encryption_key=encryption_key,
            **kwargs,
        )
        kw: Dict[str, Any] = {"agent_id": agent_id}
        if encryption_key:
            kw["encryption_key"] = encryption_key
        object.__setattr__(self, "_synapse", SynapseMemory(**kw))
        object.__setattr__(self, "_store", {})

    @property
    def synapse(self) -> SynapseMemory:
        """Access the underlying :class:`SynapseMemory` instance."""
        return self._synapse

    # -- Serialization helpers ----------------------------------------------

    @staticmethod
    def _serialize_message(message: ChatMessage) -> Dict[str, Any]:
        """Convert a ChatMessage to a JSON-safe dict."""
        return {
            "role": message.role.value if message.role else "user",
            "content": str(message.content or ""),
            "additional_kwargs": dict(message.additional_kwargs)
            if message.additional_kwargs
            else {},
        }

    @staticmethod
    def _deserialize_message(data: Dict[str, Any]) -> ChatMessage:
        """Reconstruct a ChatMessage from a dict."""
        role = _ROLE_MAP.get(data.get("role", "user"), MessageRole.USER)
        return ChatMessage(
            role=role,
            content=data.get("content", ""),
            additional_kwargs=data.get("additional_kwargs", {}),
        )

    # -- BaseChatStore abstract methods (sync) ------------------------------

    def set_messages(self, key: str, messages: List[ChatMessage]) -> None:
        """Replace all messages for *key*."""
        serialized = [self._serialize_message(m) for m in messages]
        self._store[key] = serialized

        # Persist through Synapse pipeline
        for msg in messages:
            content = str(msg.content or "")
            if content.strip():
                _run_async(self._synapse.store(
                    content=content,
                    metadata={
                        "chat_store_key": key,
                        "role": msg.role.value if msg.role else "user",
                    },
                ))

    def get_messages(self, key: str) -> List[ChatMessage]:
        """Return all messages for *key* in order."""
        entries = self._store.get(key, [])
        return [self._deserialize_message(e) for e in entries]

    def add_message(self, key: str, message: ChatMessage) -> None:
        """Append a single message."""
        serialized = self._serialize_message(message)
        self._store.setdefault(key, []).append(serialized)

        content = str(message.content or "")
        if content.strip():
            _run_async(self._synapse.store(
                content=content,
                metadata={
                    "chat_store_key": key,
                    "role": message.role.value if message.role else "user",
                },
            ))

    def delete_messages(self, key: str) -> Optional[List[ChatMessage]]:
        """Delete all messages for *key*."""
        entries = self._store.pop(key, None)
        if entries is None:
            return None
        return [self._deserialize_message(e) for e in entries]

    def delete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Remove and return the last message for *key*."""
        entries = self._store.get(key)
        if not entries:
            return None
        removed = entries.pop()
        return self._deserialize_message(removed)

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Remove and return message at *idx* for *key*."""
        entries = self._store.get(key)
        if not entries or idx < 0 or idx >= len(entries):
            return None
        removed = entries.pop(idx)
        return self._deserialize_message(removed)

    def get_keys(self) -> List[str]:
        """Return all conversation keys."""
        return list(self._store.keys())

    # -- Async variants (delegate to sync) ----------------------------------

    async def aset_messages(
        self, key: str, messages: List[ChatMessage]
    ) -> None:
        self.set_messages(key, messages)

    async def aget_messages(self, key: str) -> List[ChatMessage]:
        return self.get_messages(key)

    async def async_add_message(
        self, key: str, message: ChatMessage
    ) -> None:
        self.add_message(key, message)

    async def adelete_messages(
        self, key: str,
    ) -> Optional[List[ChatMessage]]:
        return self.delete_messages(key)

    async def adelete_last_message(
        self, key: str,
    ) -> Optional[ChatMessage]:
        return self.delete_last_message(key)

    async def adelete_message(
        self, key: str, idx: int,
    ) -> Optional[ChatMessage]:
        return self.delete_message(key, idx)

    async def aget_keys(self) -> List[str]:
        return self.get_keys()

    def __repr__(self) -> str:
        return f"SynapseChatStore(agent_id={self.agent_id!r})"
