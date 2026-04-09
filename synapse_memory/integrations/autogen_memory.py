"""
Synapse Layer — AutoGen Integration

A memory backend that plugs Synapse Layer into AutoGen's native
``Memory`` interface, giving agents persistent, encrypted memory
across conversations.

Compatible with ``autogen-core >=0.7``.

Usage:
    from synapse_memory.integrations import SynapseAutoGenMemory
    from autogen_agentchat.agents import AssistantAgent

    memory = SynapseAutoGenMemory(agent_id="my-agent")
    agent  = AssistantAgent(
        name="assistant",
        model_client=client,
        memory=[memory],
    )

Note:
    Advanced scoring, PRO heuristics, and enterprise features are
    not part of this OSS adapter.  For enterprise capabilities, see
    https://synapselayer.org/docs.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from autogen_core.memory import (
        Memory,
        MemoryContent,
        MemoryMimeType,
        MemoryQueryResult,
        UpdateContextResult,
    )
    from autogen_core.model_context import ChatCompletionContext
    from autogen_core.models import SystemMessage
except ImportError as exc:
    raise ImportError(
        "autogen-core >=0.7 is required for the AutoGen integration. "
        "Install it with: pip install 'autogen-core>=0.7'"
    ) from exc

from synapse_memory.core import SynapseMemory

logger = logging.getLogger(__name__)

__all__ = ["SynapseAutoGenMemory"]

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
_DEFAULT_TOP_K = 5
_CONTEXT_HEADER = "Relevant memories from Synapse Layer:"


class SynapseAutoGenMemory(Memory):
    """AutoGen ``Memory`` implementation backed by Synapse Layer.

    Each instance wraps a :class:`SynapseMemory` core and exposes it
    through the standard AutoGen memory protocol so that
    ``AssistantAgent`` (and any future agent) can query, store, and
    inject memories transparently.

    Parameters
    ----------
    agent_id:
        Unique identifier for the memory namespace.
    encryption_key:
        Optional Fernet key for at-rest encryption.
    top_k:
        Number of memories to recall during ``update_context``.
    name:
        Human-readable name shown in AutoGen logging.
    """

    component_type = "memory"

    def __init__(
        self,
        agent_id: str = "autogen-agent",
        encryption_key: Optional[str] = None,
        top_k: int = _DEFAULT_TOP_K,
        name: str = "synapse_memory",
    ) -> None:
        self._agent_id = agent_id
        self._top_k = top_k
        self._name = name

        kw: Dict[str, Any] = {"agent_id": agent_id}
        if encryption_key:
            kw["encryption_key"] = encryption_key
        self._synapse = SynapseMemory(**kw)

    # -- Properties ---------------------------------------------------------

    @property
    def name(self) -> str:  # type: ignore[override]
        """Human-readable label."""
        return self._name

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def synapse(self) -> SynapseMemory:
        """Access the underlying :class:`SynapseMemory` instance."""
        return self._synapse

    # -- Memory interface ---------------------------------------------------

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """Inject relevant memories into the agent's context.

        Called by the agent before each LLM invocation.  We pull the
        last user message from the context, recall relevant memories,
        and append them as a single ``SystemMessage``.
        """
        messages = await model_context.get_messages()

        # Build a query from the most recent user-like message
        query_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                query_text = msg.content
                break

        if not query_text:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        results = await self._synapse.recall(query_text, top_k=self._top_k)

        if not results:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        # Convert to MemoryContent list
        memory_contents: List[MemoryContent] = []
        lines: List[str] = []
        for idx, r in enumerate(results, 1):
            mc = MemoryContent(
                content=r.content,
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "memory_id": r.memory_id,
                    "trust_quotient": r.trust_quotient,
                    "intent": r.intent,
                    "timestamp": r.timestamp,
                },
            )
            memory_contents.append(mc)
            lines.append(f"  {idx}. {r.content}")

        # Inject as a system message
        block = f"{_CONTEXT_HEADER}\n" + "\n".join(lines)
        await model_context.add_message(SystemMessage(content=block))

        logger.debug(
            "Synapse injected %d memories for agent '%s'",
            len(memory_contents),
            self._agent_id,
        )
        return UpdateContextResult(
            memories=MemoryQueryResult(results=memory_contents)
        )

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: Any = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Semantic search over stored memories."""
        query_text = query if isinstance(query, str) else str(query.content)
        top_k = kwargs.get("top_k", self._top_k)

        results = await self._synapse.recall(query_text, top_k=top_k)

        contents: List[MemoryContent] = []
        for r in results:
            contents.append(
                MemoryContent(
                    content=r.content,
                    mime_type=MemoryMimeType.TEXT,
                    metadata={
                        "memory_id": r.memory_id,
                        "trust_quotient": r.trust_quotient,
                        "intent": r.intent,
                        "timestamp": r.timestamp,
                    },
                )
            )
        return MemoryQueryResult(results=contents)

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: Any = None,
    ) -> None:
        """Store a new memory entry."""
        text = str(content.content)
        meta = dict(content.metadata) if content.metadata else {}
        meta["mime_type"] = (
            content.mime_type.value
            if content.mime_type
            else MemoryMimeType.TEXT.value
        )
        confidence = meta.pop("confidence", 0.9)
        await self._synapse.store(
            content=text,
            confidence=float(confidence),
            metadata=meta,
        )
        logger.debug("Stored memory for agent '%s': %s…", self._agent_id, text[:60])

    async def clear(self) -> None:
        """Remove all memories for this agent."""
        self._synapse._memories.clear()
        logger.debug("Cleared all memories for agent '%s'", self._agent_id)

    async def close(self) -> None:
        """Cleanup (no-op for local Synapse)."""
        pass

    # -- Helpers ------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SynapseAutoGenMemory(agent_id={self._agent_id!r}, "
            f"top_k={self._top_k})"
        )
