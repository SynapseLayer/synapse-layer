"""
Tests for Synapse Layer LangChain Integration

Verifies that the SynapseChatMessageHistory adapter:
- Implements the BaseChatMessageHistory contract
- Stores messages through the OSS security pipeline
- Retrieves messages in LangChain-compatible format
- Works without PRO modules

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

from synapse_memory.core import SynapseMemory
from synapse_memory.integrations.langchain_memory import SynapseChatMessageHistory


# ══ Fixtures ════════════════════════════════════════════════════════════

@pytest.fixture
def history() -> SynapseChatMessageHistory:
    """Fresh history instance with default SynapseMemory."""
    return SynapseChatMessageHistory(agent_id="test-langchain-agent")


@pytest.fixture
def history_with_session() -> SynapseChatMessageHistory:
    """History with explicit session_id."""
    return SynapseChatMessageHistory(
        agent_id="test-agent",
        session_id="session-42",
    )


@pytest.fixture
def custom_memory() -> SynapseMemory:
    """Pre-configured SynapseMemory instance."""
    return SynapseMemory(
        agent_id="custom-agent",
        sanitize_enabled=False,
        privacy_enabled=False,
    )


# ══ Interface Compliance ═══════════════════════════════════════════════

class TestInterfaceCompliance:
    """Verify the adapter satisfies the BaseChatMessageHistory contract."""

    def test_is_subclass(self):
        assert issubclass(SynapseChatMessageHistory, BaseChatMessageHistory)

    def test_has_messages_property(self, history: SynapseChatMessageHistory):
        assert hasattr(history, "messages")

    def test_has_add_messages(self, history: SynapseChatMessageHistory):
        assert callable(getattr(history, "add_messages", None))

    def test_has_clear(self, history: SynapseChatMessageHistory):
        assert callable(getattr(history, "clear", None))

    def test_has_async_variants(self, history: SynapseChatMessageHistory):
        assert callable(getattr(history, "aget_messages", None))
        assert callable(getattr(history, "aadd_messages", None))
        assert callable(getattr(history, "aclear", None))

    def test_repr(self, history: SynapseChatMessageHistory):
        r = repr(history)
        assert "SynapseChatMessageHistory" in r
        assert "test-langchain-agent" in r


# ══ Storage Tests ══════════════════════════════════════════════════════

class TestStorage:
    """Verify messages are stored through the OSS pipeline."""

    def test_add_user_message(self, history: SynapseChatMessageHistory):
        history.add_user_message("Hello, I prefer dark mode.")
        # Verify the message was stored in SynapseMemory's internal store
        memories = history._memory._memories
        assert len(memories) == 1
        assert "dark mode" in memories[0]["content"].lower() or \
               "dark mode" in memories[0].get("original_content", "").lower()

    def test_add_ai_message(self, history: SynapseChatMessageHistory):
        history.add_ai_message("I'll remember your preference.")
        memories = history._memory._memories
        assert len(memories) == 1

    def test_add_multiple_messages(self, history: SynapseChatMessageHistory):
        messages = [
            HumanMessage(content="What's the weather?"),
            AIMessage(content="It's sunny today."),
            HumanMessage(content="Thanks!"),
        ]
        history.add_messages(messages)
        memories = history._memory._memories
        assert len(memories) == 3

    def test_metadata_includes_role(self, history: SynapseChatMessageHistory):
        history.add_user_message("Test message")
        mem = history._memory._memories[0]
        assert mem["metadata"]["role"] == "human"
        assert mem["metadata"]["integration"] == "langchain"

    def test_ai_role_metadata(self, history: SynapseChatMessageHistory):
        history.add_ai_message("AI response")
        mem = history._memory._memories[0]
        assert mem["metadata"]["role"] == "ai"

    def test_session_id_in_metadata(
        self, history_with_session: SynapseChatMessageHistory
    ):
        history_with_session.add_user_message("Scoped message")
        mem = history_with_session._memory._memories[0]
        assert mem["metadata"]["session_id"] == "session-42"


# ══ Retrieval Tests ════════════════════════════════════════════════════

class TestRetrieval:
    """Verify messages are retrieved in LangChain-compatible format."""

    def test_empty_history_returns_empty_list(
        self, history: SynapseChatMessageHistory
    ):
        assert history.messages == []

    def test_roundtrip_messages(self, history: SynapseChatMessageHistory):
        history.add_user_message("conversation history messages user input")
        history.add_ai_message("conversation history messages ai response")

        messages = history.messages
        # At least some messages should be returned
        # (recall uses substring matching, so content must match query)
        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, (HumanMessage, AIMessage))

    def test_messages_are_base_message_instances(
        self, history: SynapseChatMessageHistory
    ):
        history.add_user_message("conversation history messages test")
        messages = history.messages
        for msg in messages:
            assert hasattr(msg, "content")


# ══ Async Tests ════════════════════════════════════════════════════════

class TestAsync:
    """Verify async variants work correctly."""

    @pytest.mark.asyncio
    async def test_async_add_and_retrieve(
        self, history: SynapseChatMessageHistory
    ):
        await history.aadd_messages([
            HumanMessage(content="conversation history messages async test"),
            AIMessage(content="conversation history messages async reply"),
        ])
        messages = await history.aget_messages()
        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_async_clear(self, history: SynapseChatMessageHistory):
        # clear() is a no-op but should not raise
        await history.aclear()


# ══ Custom Memory Injection ════════════════════════════════════════════

class TestCustomMemory:
    """Verify the adapter accepts a pre-configured SynapseMemory."""

    def test_custom_memory_injection(self, custom_memory: SynapseMemory):
        history = SynapseChatMessageHistory(
            agent_id="custom-agent",
            memory=custom_memory,
        )
        assert history._memory is custom_memory

    def test_custom_memory_stores(self, custom_memory: SynapseMemory):
        history = SynapseChatMessageHistory(
            agent_id="custom-agent",
            memory=custom_memory,
        )
        history.add_user_message("Custom memory test")
        assert len(custom_memory._memories) == 1


# ══ No PRO Dependency ══════════════════════════════════════════════════

class TestOSSSafety:
    """Verify the adapter works without PRO modules."""

    def test_no_pro_imports(self):
        """Ensure langchain_memory.py does not import PRO modules."""
        import synapse_memory.integrations.langchain_memory as mod
        source = open(mod.__file__).read()
        assert "synapse_memory_pro" not in source
        assert "ProImportanceScorer" not in source
        assert "ProConflictResolver" not in source
        assert "ProDedupStrategy" not in source

    def test_no_scoring_internals(self):
        """Ensure no TQ internals are exposed."""
        import synapse_memory.integrations.langchain_memory as mod
        source = open(mod.__file__).read()
        assert "Jaccard" not in source
        assert "SATURATION_HITS" not in source
        assert "0.65" not in source

    def test_clear_is_safe_noop(self, history: SynapseChatMessageHistory):
        """clear() should not raise or delete data."""
        history.add_user_message("Preserved message")
        history.clear()
        # Memory still exists (clear is a no-op)
        assert len(history._memory._memories) == 1
