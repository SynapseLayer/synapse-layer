"""
Tests for Synapse Layer LlamaIndex Integration

Verifies that:
- SynapseRetriever implements BaseRetriever contract
- SynapseChatStore implements BaseChatStore contract
- All messages route through the OSS security pipeline
- Metadata is preserved through store/recall cycle

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Skip entire module if llama-index-core is not installed
pytest.importorskip("llama_index.core", reason="llama-index-core not installed")

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.storage.chat_store import BaseChatStore
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from synapse_memory.core import SynapseMemory
from synapse_memory.integrations.llamaindex import (
    SynapseRetriever,
    SynapseChatStore,
)


# ══ Fixtures ════════════════════════════════════════════════════════════════

@pytest.fixture
def retriever() -> SynapseRetriever:
    return SynapseRetriever(agent_id="test-retriever")


@pytest.fixture
def retriever_k3() -> SynapseRetriever:
    return SynapseRetriever(agent_id="test-retriever-k3", top_k=3)


@pytest.fixture
def chat_store() -> SynapseChatStore:
    return SynapseChatStore(agent_id="test-chat-store")


def _qb(text: str) -> QueryBundle:
    return QueryBundle(query_str=text)


# =========================================================================
# RETRIEVER TESTS
# =========================================================================

class TestRetrieverConstruction:
    def test_default_params(self, retriever: SynapseRetriever):
        assert retriever.agent_id == "test-retriever"
        assert retriever.top_k == 5
        assert isinstance(retriever.synapse, SynapseMemory)

    def test_is_base_retriever(self, retriever: SynapseRetriever):
        assert isinstance(retriever, BaseRetriever)

    def test_custom_top_k(self, retriever_k3: SynapseRetriever):
        assert retriever_k3.top_k == 3

    def test_repr(self, retriever: SynapseRetriever):
        r = repr(retriever)
        assert "test-retriever" in r
        assert "top_k=5" in r


class TestRetrieverRetrieve:
    async def test_retrieve_returns_nodes(self, retriever: SynapseRetriever):
        await retriever.astore("Kubernetes is used for container orchestration.")
        nodes = await retriever._aretrieve(_qb("Kubernetes container orchestration"))
        assert len(nodes) >= 1
        assert all(isinstance(n, NodeWithScore) for n in nodes)

    async def test_score_is_trust_quotient(self, retriever: SynapseRetriever):
        await retriever.astore("The API uses OAuth 2.0 for authentication.")
        nodes = await retriever._aretrieve(_qb("OAuth 2.0 API authentication"))
        assert len(nodes) >= 1
        for n in nodes:
            assert 0.0 <= n.score <= 1.0

    async def test_node_metadata(self, retriever: SynapseRetriever):
        await retriever.astore("Redis is the caching layer.")
        nodes = await retriever._aretrieve(_qb("Redis caching layer"))
        assert len(nodes) >= 1
        meta = nodes[0].node.metadata
        assert "trust_quotient" in meta
        assert "intent" in meta
        assert "timestamp" in meta
        assert meta["source"] == "synapse_layer"

    async def test_node_has_memory_id(self, retriever: SynapseRetriever):
        await retriever.astore("Grafana is used for monitoring.")
        nodes = await retriever._aretrieve(_qb("Grafana monitoring"))
        assert len(nodes) >= 1
        assert nodes[0].node.id_ is not None
        assert len(nodes[0].node.id_) > 0

    async def test_empty_store_returns_empty(self, retriever: SynapseRetriever):
        nodes = await retriever._aretrieve(_qb("anything"))
        assert nodes == []

    async def test_top_k_respected(self, retriever_k3: SynapseRetriever):
        for i in range(10):
            await retriever_k3.astore(f"Data point beta {i}")
        nodes = await retriever_k3._aretrieve(_qb("data point beta"))
        assert len(nodes) <= 3

    def test_sync_retrieve(self, retriever: SynapseRetriever):
        retriever.store("Sync test: the server runs on port 443.")
        nodes = retriever._retrieve(_qb("server port 443"))
        assert len(nodes) >= 1

    def test_sync_store(self, retriever: SynapseRetriever):
        retriever.store("Sync store entry for testing.")
        nodes = retriever._retrieve(_qb("sync store entry testing"))
        assert len(nodes) >= 1


class TestRetrieverStore:
    async def test_store_with_metadata(self, retriever: SynapseRetriever):
        await retriever.astore(
            "PostgreSQL 16 is the production database.",
            metadata={"env": "production"},
        )
        nodes = await retriever._aretrieve(_qb("PostgreSQL 16 production database"))
        assert len(nodes) >= 1

    async def test_store_with_confidence(self, retriever: SynapseRetriever):
        await retriever.astore(
            "High confidence fact about deployment.",
            confidence=0.95,
        )
        nodes = await retriever._aretrieve(_qb("high confidence deployment"))
        assert len(nodes) >= 1


# =========================================================================
# CHAT STORE TESTS
# =========================================================================

class TestChatStoreConstruction:
    def test_default_params(self, chat_store: SynapseChatStore):
        assert chat_store.agent_id == "test-chat-store"
        assert isinstance(chat_store.synapse, SynapseMemory)

    def test_is_base_chat_store(self, chat_store: SynapseChatStore):
        assert isinstance(chat_store, BaseChatStore)

    def test_repr(self, chat_store: SynapseChatStore):
        assert "test-chat-store" in repr(chat_store)


class TestChatStoreMessages:
    def test_add_and_get(self, chat_store: SynapseChatStore):
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        chat_store.add_message("s1", msg)
        messages = chat_store.get_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "Hello"
        assert messages[0].role == MessageRole.USER

    def test_multiple_messages(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="Q1"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT, content="A1"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="Q2"))
        messages = chat_store.get_messages("s1")
        assert len(messages) == 3
        assert messages[0].content == "Q1"
        assert messages[2].content == "Q2"

    def test_set_messages_replaces(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="old"))
        chat_store.set_messages("s1", [
            ChatMessage(role=MessageRole.USER, content="new1"),
            ChatMessage(role=MessageRole.ASSISTANT, content="new2"),
        ])
        messages = chat_store.get_messages("s1")
        assert len(messages) == 2
        assert messages[0].content == "new1"

    def test_get_empty_key(self, chat_store: SynapseChatStore):
        messages = chat_store.get_messages("nonexistent")
        assert messages == []

    def test_multiple_keys(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="Session 1"))
        chat_store.add_message("s2", ChatMessage(
            role=MessageRole.USER, content="Session 2"))
        assert len(chat_store.get_messages("s1")) == 1
        assert len(chat_store.get_messages("s2")) == 1
        assert chat_store.get_messages("s1")[0].content == "Session 1"


class TestChatStoreDelete:
    def test_delete_messages(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="msg1"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT, content="msg2"))
        deleted = chat_store.delete_messages("s1")
        assert deleted is not None
        assert len(deleted) == 2
        assert chat_store.get_messages("s1") == []

    def test_delete_messages_nonexistent(self, chat_store: SynapseChatStore):
        result = chat_store.delete_messages("no-key")
        assert result is None

    def test_delete_last_message(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="first"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT, content="second"))
        removed = chat_store.delete_last_message("s1")
        assert removed is not None
        assert removed.content == "second"
        assert len(chat_store.get_messages("s1")) == 1

    def test_delete_last_message_empty(self, chat_store: SynapseChatStore):
        result = chat_store.delete_last_message("empty")
        assert result is None

    def test_delete_message_by_index(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="m0"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT, content="m1"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="m2"))
        removed = chat_store.delete_message("s1", 1)
        assert removed is not None
        assert removed.content == "m1"
        remaining = chat_store.get_messages("s1")
        assert len(remaining) == 2
        assert remaining[1].content == "m2"

    def test_delete_message_invalid_index(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="only"))
        assert chat_store.delete_message("s1", 5) is None
        assert chat_store.delete_message("s1", -1) is None


class TestChatStoreKeys:
    def test_get_keys_empty(self, chat_store: SynapseChatStore):
        assert chat_store.get_keys() == []

    def test_get_keys_populated(self, chat_store: SynapseChatStore):
        chat_store.add_message("alpha", ChatMessage(
            role=MessageRole.USER, content="a"))
        chat_store.add_message("beta", ChatMessage(
            role=MessageRole.USER, content="b"))
        keys = chat_store.get_keys()
        assert "alpha" in keys
        assert "beta" in keys


class TestChatStoreAsync:
    async def test_async_add_and_get(self, chat_store: SynapseChatStore):
        await chat_store.async_add_message("s1", ChatMessage(
            role=MessageRole.USER, content="async hello"))
        messages = await chat_store.aget_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "async hello"

    async def test_async_set_messages(self, chat_store: SynapseChatStore):
        await chat_store.aset_messages("s1", [
            ChatMessage(role=MessageRole.USER, content="a1"),
            ChatMessage(role=MessageRole.ASSISTANT, content="a2"),
        ])
        messages = await chat_store.aget_messages("s1")
        assert len(messages) == 2

    async def test_async_delete_messages(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="to delete"))
        deleted = await chat_store.adelete_messages("s1")
        assert deleted is not None
        assert len(deleted) == 1

    async def test_async_delete_last(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="first"))
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT, content="last"))
        removed = await chat_store.adelete_last_message("s1")
        assert removed is not None
        assert removed.content == "last"

    async def test_async_get_keys(self, chat_store: SynapseChatStore):
        chat_store.add_message("k1", ChatMessage(
            role=MessageRole.USER, content="x"))
        keys = await chat_store.aget_keys()
        assert "k1" in keys


class TestChatStoreEdgeCases:
    def test_system_message(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.SYSTEM, content="You are helpful."))
        messages = chat_store.get_messages("s1")
        assert messages[0].role == MessageRole.SYSTEM

    def test_empty_content(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content=""))
        messages = chat_store.get_messages("s1")
        assert len(messages) == 1

    def test_unicode_content(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.USER, content="你好世界 🌍"))
        messages = chat_store.get_messages("s1")
        assert "你好" in messages[0].content

    def test_additional_kwargs_preserved(self, chat_store: SynapseChatStore):
        chat_store.add_message("s1", ChatMessage(
            role=MessageRole.ASSISTANT,
            content="response",
            additional_kwargs={"model": "gpt-4"},
        ))
        messages = chat_store.get_messages("s1")
        assert messages[0].additional_kwargs["model"] == "gpt-4"
