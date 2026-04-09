"""
Tests for Synapse Layer AutoGen Integration

Verifies that the SynapseAutoGenMemory adapter:
- Implements the AutoGen Memory contract
- Stores memories through the OSS security pipeline
- Queries memories with semantic relevance
- Injects context via update_context
- Works without PRO modules

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Skip entire module if autogen-core is not installed
pytest.importorskip("autogen_core", reason="autogen-core not installed")

from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.models import SystemMessage

from synapse_memory.core import SynapseMemory, RecallResult
from synapse_memory.integrations.autogen_memory import SynapseAutoGenMemory


# ══ Fixtures ════════════════════════════════════════════════════════════════

@pytest.fixture
def memory() -> SynapseAutoGenMemory:
    """Fresh memory instance with default SynapseMemory."""
    return SynapseAutoGenMemory(agent_id="test-autogen-agent")


@pytest.fixture
def memory_custom() -> SynapseAutoGenMemory:
    """Memory with custom top_k and name."""
    return SynapseAutoGenMemory(
        agent_id="custom-agent",
        top_k=3,
        name="custom_memory",
    )


def _make_recall_result(
    content: str,
    memory_id: str = "mem-1",
    tq: float = 0.85,
    intent: str = "factual",
    ts: float = 1700000000.0,
) -> RecallResult:
    """Helper to build a RecallResult without triggering the full pipeline."""
    return RecallResult(
        content=content,
        trust_quotient=tq,
        memory_id=memory_id,
        timestamp=ts,
        intent=intent,
        is_critical=False,
        self_healing=None,
    )


def _mock_context(messages=None):
    """Create a mock ChatCompletionContext."""
    ctx = AsyncMock()
    ctx.get_messages = AsyncMock(return_value=messages or [])
    ctx.add_message = AsyncMock()
    return ctx


# ══ Basic Construction ═════════════════════════════════════════════════════

class TestConstruction:
    def test_default_params(self, memory: SynapseAutoGenMemory):
        assert memory.agent_id == "test-autogen-agent"
        assert memory.name == "synapse_memory"
        assert memory._top_k == 5
        assert isinstance(memory.synapse, SynapseMemory)

    def test_custom_params(self, memory_custom: SynapseAutoGenMemory):
        assert memory_custom.agent_id == "custom-agent"
        assert memory_custom.name == "custom_memory"
        assert memory_custom._top_k == 3

    def test_is_memory_subclass(self, memory: SynapseAutoGenMemory):
        assert isinstance(memory, Memory)

    def test_component_type(self):
        assert SynapseAutoGenMemory.component_type == "memory"

    def test_repr(self, memory: SynapseAutoGenMemory):
        r = repr(memory)
        assert "test-autogen-agent" in r
        assert "top_k=5" in r


# ══ add() ═════════════════════════════════════════════════════════════════

class TestAdd:
    async def test_add_text_memory(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content="The deadline is Friday.",
            mime_type=MemoryMimeType.TEXT,
        )
        await memory.add(content)
        results = await memory.synapse.recall("deadline", top_k=5)
        assert len(results) >= 1
        assert any("deadline" in r.content.lower() for r in results)

    async def test_add_with_metadata(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content="Use PostgreSQL for the production database.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"source": "config", "confidence": 0.95},
        )
        await memory.add(content)
        results = await memory.synapse.recall("PostgreSQL database", top_k=5)
        assert len(results) >= 1

    async def test_add_json_content(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content='{"key": "value"}',
            mime_type=MemoryMimeType.JSON,
        )
        await memory.add(content)
        results = await memory.synapse.recall("key value", top_k=5)
        assert len(results) >= 1

    async def test_add_preserves_mime_type(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content="markdown content",
            mime_type=MemoryMimeType.MARKDOWN,
        )
        await memory.add(content)
        results = await memory.synapse.recall("markdown", top_k=5)
        assert len(results) >= 1

    async def test_add_multiple(self, memory: SynapseAutoGenMemory):
        for i in range(5):
            await memory.add(MemoryContent(
                content=f"Memory entry number {i}",
                mime_type=MemoryMimeType.TEXT,
            ))
        results = await memory.synapse.recall("memory entry", top_k=10)
        assert len(results) == 5


# ══ query() ═══════════════════════════════════════════════════════════════

class TestQuery:
    async def test_query_string(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Python 3.12 is the target runtime.",
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("What Python version?")
        assert isinstance(result, MemoryQueryResult)
        assert len(result.results) >= 1
        assert any("3.12" in r.content for r in result.results)

    async def test_query_memory_content(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="The server runs on port 8080.",
            mime_type=MemoryMimeType.TEXT,
        ))
        q = MemoryContent(content="server port", mime_type=MemoryMimeType.TEXT)
        result = await memory.query(q)
        assert len(result.results) >= 1

    async def test_query_returns_metadata(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Deployment target is AWS.",
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("deployment")
        assert result.results[0].metadata is not None
        meta = result.results[0].metadata
        assert "memory_id" in meta
        assert "trust_quotient" in meta
        assert "intent" in meta
        assert "timestamp" in meta

    async def test_query_empty_store(self, memory: SynapseAutoGenMemory):
        result = await memory.query("anything")
        assert isinstance(result, MemoryQueryResult)
        assert len(result.results) == 0

    async def test_query_custom_top_k(self, memory: SynapseAutoGenMemory):
        for i in range(10):
            await memory.add(MemoryContent(
                content=f"Data point alpha {i}",
                mime_type=MemoryMimeType.TEXT,
            ))
        result = await memory.query("data point alpha", top_k=3)
        assert len(result.results) <= 3

    async def test_query_result_type(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Test content",
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("test")
        for r in result.results:
            assert isinstance(r, MemoryContent)
            assert r.mime_type == MemoryMimeType.TEXT


# ══ update_context() ══════════════════════════════════════════════════════

class TestUpdateContext:
    async def test_injects_system_message(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Important: always use HTTPS.",
            mime_type=MemoryMimeType.TEXT,
        ))

        from autogen_core.models import UserMessage
        ctx = _mock_context([
            UserMessage(content="How should I configure the server?", source="user"),
        ])

        result = await memory.update_context(ctx)
        assert isinstance(result, UpdateContextResult)

        # Should have called add_message with a SystemMessage
        ctx.add_message.assert_called_once()
        injected = ctx.add_message.call_args[0][0]
        assert isinstance(injected, SystemMessage)
        assert "HTTPS" in injected.content

    async def test_returns_memory_contents(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Rate limit is 1000 req/min.",
            mime_type=MemoryMimeType.TEXT,
        ))

        from autogen_core.models import UserMessage
        ctx = _mock_context([
            UserMessage(content="What is the rate limit?", source="user"),
        ])

        result = await memory.update_context(ctx)
        assert len(result.memories.results) >= 1
        assert any("1000" in r.content for r in result.memories.results)

    async def test_empty_context(self, memory: SynapseAutoGenMemory):
        ctx = _mock_context([])
        result = await memory.update_context(ctx)
        assert len(result.memories.results) == 0
        ctx.add_message.assert_not_called()

    async def test_no_relevant_memories(self, memory: SynapseAutoGenMemory):
        from autogen_core.models import UserMessage
        ctx = _mock_context([
            UserMessage(content="random query", source="user"),
        ])
        result = await memory.update_context(ctx)
        assert len(result.memories.results) == 0
        ctx.add_message.assert_not_called()

    async def test_context_header_present(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Use TLS 1.3 for all secure connections and encryption.",
            mime_type=MemoryMimeType.TEXT,
        ))

        from autogen_core.models import UserMessage
        ctx = _mock_context([
            UserMessage(content="Tell me about TLS connections and encryption.", source="user"),
        ])

        await memory.update_context(ctx)
        if ctx.add_message.called:
            injected = ctx.add_message.call_args[0][0]
            assert "Relevant memories from Synapse Layer" in injected.content

    async def test_multiple_memories_in_context(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Database host is db.example.com.",
            mime_type=MemoryMimeType.TEXT,
        ))
        await memory.add(MemoryContent(
            content="Database port is 5432.",
            mime_type=MemoryMimeType.TEXT,
        ))

        from autogen_core.models import UserMessage
        ctx = _mock_context([
            UserMessage(content="database connection details", source="user"),
        ])

        result = await memory.update_context(ctx)
        assert len(result.memories.results) >= 2
        injected = ctx.add_message.call_args[0][0]
        assert "1." in injected.content
        assert "2." in injected.content


# ══ clear() & close() ════════════════════════════════════════════════════

class TestClearClose:
    async def test_clear_removes_all(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Temporary data",
            mime_type=MemoryMimeType.TEXT,
        ))
        results_before = await memory.synapse.recall("temporary", top_k=5)
        assert len(results_before) >= 1

        await memory.clear()
        results_after = await memory.synapse.recall("temporary", top_k=5)
        assert len(results_after) == 0

    async def test_clear_idempotent(self, memory: SynapseAutoGenMemory):
        await memory.clear()
        await memory.clear()  # should not raise

    async def test_close_is_noop(self, memory: SynapseAutoGenMemory):
        await memory.close()  # should not raise

    async def test_add_after_clear(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="First entry",
            mime_type=MemoryMimeType.TEXT,
        ))
        await memory.clear()
        await memory.add(MemoryContent(
            content="Second entry after clear",
            mime_type=MemoryMimeType.TEXT,
        ))
        results = await memory.synapse.recall("second entry", top_k=5)
        assert len(results) == 1


# ══ Edge Cases ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    async def test_special_characters(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="Path is /usr/local/bin && echo $HOME",
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("path")
        assert len(result.results) >= 1

    async def test_unicode_content(self, memory: SynapseAutoGenMemory):
        await memory.add(MemoryContent(
            content="数据库配置：主机=db.example.com",
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("数据库")
        assert len(result.results) >= 1

    async def test_long_content(self, memory: SynapseAutoGenMemory):
        long_text = "word " * 500
        await memory.add(MemoryContent(
            content=long_text,
            mime_type=MemoryMimeType.TEXT,
        ))
        result = await memory.query("word")
        assert len(result.results) >= 1

    async def test_empty_string_content(self, memory: SynapseAutoGenMemory):
        # Should handle gracefully
        await memory.add(MemoryContent(
            content="",
            mime_type=MemoryMimeType.TEXT,
        ))

    async def test_none_metadata(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content="No metadata here.",
            mime_type=MemoryMimeType.TEXT,
            metadata=None,
        )
        await memory.add(content)
        result = await memory.query("no metadata")
        assert len(result.results) >= 1

    async def test_cancellation_token_ignored(self, memory: SynapseAutoGenMemory):
        content = MemoryContent(
            content="With token.",
            mime_type=MemoryMimeType.TEXT,
        )
        # Should not fail even with a cancellation_token
        await memory.add(content, cancellation_token="fake-token")
        result = await memory.query("token", cancellation_token="fake-token")
        assert isinstance(result, MemoryQueryResult)
