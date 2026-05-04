"""
Synapse Layer — LangChain Integration

A lightweight adapter that makes Synapse Layer available as a
chat message history backend for LangChain applications.

Uses the modern ``BaseChatMessageHistory`` interface (langchain-core >=0.3).

Usage:
    from synapse_memory.integrations import SynapseChatMessageHistory

    history = SynapseChatMessageHistory(agent_id="my-agent")

Note:
    Advanced scoring, PRO heuristics, and enterprise features are
    not part of this OSS adapter.  For enterprise capabilities, see
    https://synapselayer.org/docs.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        AIMessage,
        messages_from_dict,
        message_to_dict,
    )
except ImportError as exc:
    raise ImportError(
        "langchain-core is required for the LangChain integration. "
        "Install it with: pip install langchain-core"
    ) from exc

from synapse_memory.core import SynapseMemory

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run a coroutine from synchronous code.

    Handles the case where an event loop is already running
    (e.g., Jupyter notebooks) by creating a new thread.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class SynapseChatMessageHistory(BaseChatMessageHistory):
    """LangChain chat message history backed by Synapse Layer.

    Stores conversation messages through the Synapse Layer Cognitive
    Security pipeline (sanitization, PII redaction, encryption) and
    retrieves them for context-aware agent responses.

    This adapter uses only the public OSS API:
    - ``SynapseMemory.store()`` for persistence
    - ``SynapseMemory.recall()`` for retrieval

    Parameters
    ----------
    agent_id : str
        Unique identifier for the agent. Scopes memory isolation.
    session_id : str | None
        Optional session identifier. Stored as metadata for filtering.
    memory : SynapseMemory | None
        Pre-configured SynapseMemory instance. If None, one is created
        with default settings using ``agent_id``.
    recall_top_k : int
        Maximum number of memories to retrieve (default: 20).

    Example
    -------
    >>> from synapse_memory.integrations import SynapseChatMessageHistory
    >>> history = SynapseChatMessageHistory(agent_id="assistant-1")
    >>> history.add_user_message("I prefer dark mode.")
    >>> history.add_ai_message("Got it! I'll remember that.")
    >>> print(history.messages)
    [HumanMessage(content='I prefer dark mode.'), ...]
    """

    def __init__(
        self,
        agent_id: str,
        *,
        session_id: Optional[str] = None,
        memory: Optional[SynapseMemory] = None,
        recall_top_k: int = 20,
    ) -> None:
        self._agent_id = agent_id
        self._session_id = session_id
        self._memory = memory or SynapseMemory(agent_id=agent_id)
        self._recall_top_k = recall_top_k

        logger.info(
            "SynapseChatMessageHistory initialized: agent=%s, session=%s",
            agent_id,
            session_id,
        )

    # ── Core Properties ──────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        """The agent ID scoping this history."""
        return self._agent_id

    @property
    def session_id(self) -> Optional[str]:
        """The optional session ID for this history."""
        return self._session_id

    # ── BaseChatMessageHistory Contract ──────────────────────────────

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore[override]
        """Retrieve stored messages from Synapse Layer.

        Uses ``SynapseMemory.recall()`` with a broad query to fetch
        recent conversation history.
        """
        results = _run_async(
            self._memory.recall(
                query="conversation history messages",
                top_k=self._recall_top_k,
            )
        )

        messages: List[BaseMessage] = []
        for result in results:
            content = result.content
            role = self._resolve_role(result.memory_id)

            if role == "ai":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        return messages

    def _resolve_role(self, memory_id: str) -> str:
        """Look up the original role from internal memory metadata."""
        for mem in self._memory._memories:
            if mem.get("memory_id") == memory_id:
                return (mem.get("metadata") or {}).get("role", "human")
        return "human"

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Store messages through the Synapse Layer security pipeline.

        Each message is persisted individually with role metadata
        for accurate reconstruction on recall.
        """
        for message in messages:
            role = "ai" if isinstance(message, AIMessage) else "human"
            metadata = {
                "role": role,
                "type": "chat_message",
                "integration": "langchain",
            }
            if self._session_id:
                metadata["session_id"] = self._session_id

            _run_async(
                self._memory.store(
                    content=message.content,
                    metadata=metadata,
                )
            )

        logger.debug("Stored %d messages via Synapse Layer", len(messages))

    def clear(self) -> None:
        """Clear is a no-op in the OSS adapter.

        Synapse Layer's encrypted architecture does not support
        bulk deletion from the SDK. In production deployments,
        memory lifecycle is managed via retention policies.
        """
        logger.info(
            "clear() called — Synapse Layer manages memory lifecycle "
            "via retention policies. No-op in OSS adapter."
        )

    # ── Async Variants ───────────────────────────────────────────────

    async def aget_messages(self) -> List[BaseMessage]:  # type: ignore[override]
        """Async variant of messages retrieval."""
        results = await self._memory.recall(
            query="conversation history messages",
            top_k=self._recall_top_k,
        )

        messages: List[BaseMessage] = []
        for result in results:
            content = result.content
            role = self._resolve_role(result.memory_id)

            if role == "ai":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        return messages

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Async variant of message storage."""
        for message in messages:
            role = "ai" if isinstance(message, AIMessage) else "human"
            metadata = {
                "role": role,
                "type": "chat_message",
                "integration": "langchain",
            }
            if self._session_id:
                metadata["session_id"] = self._session_id

            await self._memory.store(
                content=message.content,
                metadata=metadata,
            )

        logger.debug("Async stored %d messages via Synapse Layer", len(messages))

    async def aclear(self) -> None:
        """Async clear — same no-op behavior as sync variant."""
        self.clear()

    # ── String Representation ────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SynapseChatMessageHistory("
            f"agent_id={self._agent_id!r}, "
            f"session_id={self._session_id!r})"
        )
