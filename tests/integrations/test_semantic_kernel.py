"""
Tests for Synapse Layer Semantic Kernel Integration

Verifies that:
- SynapseChatHistory extends ChatHistory with Synapse persistence
- SynapseMemoryStore implements MemoryStoreBase contract
- All messages route through the OSS security pipeline
- Collection management works correctly

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch

# Skip entire module if semantic-kernel is not installed
pytest.importorskip("semantic_kernel", reason="semantic-kernel not installed")

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.memory.memory_store_base import MemoryStoreBase
from semantic_kernel.memory.memory_record import MemoryRecord

from synapse_memory.core import SynapseMemory
from synapse_memory.integrations.semantic_kernel import (
    SynapseChatHistory,
    SynapseMemoryStore,
)


# ══ Fixtures ════════════════════════════════════════════════════════════════

@pytest.fixture
def history() -> SynapseChatHistory:
    return SynapseChatHistory(agent_id="test-sk-history")


@pytest.fixture
def store() -> SynapseMemoryStore:
    return SynapseMemoryStore(agent_id="test-sk-store")


def _make_record(
    id: str = "rec-1",
    text: str = "test content",
    description: str = "test desc",
) -> MemoryRecord:
    return MemoryRecord.local_record(
        id=id,
        text=text,
        description=description,
        additional_metadata="{}",
        embedding=np.random.rand(3),
    )


# =========================================================================
# CHAT HISTORY TESTS
# =========================================================================

class TestChatHistoryConstruction:
    def test_default_params(self, history: SynapseChatHistory):
        assert history.agent_id == "test-sk-history"
        assert isinstance(history.synapse, SynapseMemory)
        assert len(history) == 0

    def test_is_chat_history(self, history: SynapseChatHistory):
        assert isinstance(history, ChatHistory)

    def test_repr(self, history: SynapseChatHistory):
        r = repr(history)
        assert "test-sk-history" in r
        assert "messages=0" in r


class TestChatHistoryMessages:
    def test_add_user_message(self, history: SynapseChatHistory):
        history.add_user_message("Hello")
        assert len(history) == 1
        assert history[0].role == AuthorRole.USER
        assert history[0].content == "Hello"

    def test_add_assistant_message(self, history: SynapseChatHistory):
        history.add_assistant_message("Hi there")
        assert len(history) == 1
        assert history[0].role == AuthorRole.ASSISTANT

    def test_add_system_message(self, history: SynapseChatHistory):
        history.add_system_message("You are helpful.")
        assert len(history) == 1
        assert history[0].role == AuthorRole.SYSTEM

    def test_add_message_dict(self, history: SynapseChatHistory):
        history.add_message({"role": AuthorRole.USER, "content": "dict msg"})
        assert len(history) == 1

    def test_multiple_messages(self, history: SynapseChatHistory):
        history.add_system_message("System prompt.")
        history.add_user_message("Question?")
        history.add_assistant_message("Answer.")
        assert len(history) == 3
        assert history[0].role == AuthorRole.SYSTEM
        assert history[1].role == AuthorRole.USER
        assert history[2].role == AuthorRole.ASSISTANT

    def test_persists_to_synapse(self, history: SynapseChatHistory):
        history.add_user_message("Persist this message to Synapse.")
        # Verify Synapse has the memory
        assert len(history.synapse._memories) >= 1

    def test_clear(self, history: SynapseChatHistory):
        history.add_user_message("msg1")
        history.add_assistant_message("msg2")
        assert len(history) == 2
        history.clear()
        assert len(history) == 0
        assert len(history.synapse._memories) == 0

    def test_empty_content_not_stored(self, history: SynapseChatHistory):
        initial = len(history.synapse._memories)
        history.add_user_message("")
        # Empty content should not be stored in Synapse
        assert len(history.synapse._memories) == initial


class TestChatHistoryEdgeCases:
    def test_unicode(self, history: SynapseChatHistory):
        history.add_user_message("你好世界 🌍")
        assert "你好" in history[0].content

    def test_long_message(self, history: SynapseChatHistory):
        long_text = "word " * 500
        history.add_user_message(long_text)
        assert len(history) == 1

    def test_special_chars(self, history: SynapseChatHistory):
        history.add_user_message("Path: /usr/bin && echo $HOME")
        assert len(history) == 1


# =========================================================================
# MEMORY STORE TESTS
# =========================================================================

class TestMemoryStoreConstruction:
    def test_default_params(self, store: SynapseMemoryStore):
        assert store.agent_id == "test-sk-store"

    def test_is_memory_store_base(self, store: SynapseMemoryStore):
        assert isinstance(store, MemoryStoreBase)

    def test_repr(self, store: SynapseMemoryStore):
        r = repr(store)
        assert "test-sk-store" in r
        assert "collections=0" in r


class TestMemoryStoreCollections:
    async def test_create_collection(self, store: SynapseMemoryStore):
        await store.create_collection("test-coll")
        assert await store.does_collection_exist("test-coll")

    async def test_get_collections(self, store: SynapseMemoryStore):
        await store.create_collection("alpha")
        await store.create_collection("beta")
        colls = await store.get_collections()
        assert "alpha" in colls
        assert "beta" in colls

    async def test_delete_collection(self, store: SynapseMemoryStore):
        await store.create_collection("temp")
        assert await store.does_collection_exist("temp")
        await store.delete_collection("temp")
        assert not await store.does_collection_exist("temp")

    async def test_nonexistent_collection(self, store: SynapseMemoryStore):
        assert not await store.does_collection_exist("nope")

    async def test_create_idempotent(self, store: SynapseMemoryStore):
        await store.create_collection("x")
        await store.create_collection("x")  # Should not raise
        assert len(await store.get_collections()) == 1


class TestMemoryStoreUpsert:
    async def test_upsert_single(self, store: SynapseMemoryStore):
        record = _make_record()
        rid = await store.upsert("coll", record)
        assert rid == "rec-1"

    async def test_upsert_creates_collection(self, store: SynapseMemoryStore):
        record = _make_record()
        await store.upsert("auto-coll", record)
        assert await store.does_collection_exist("auto-coll")

    async def test_upsert_batch(self, store: SynapseMemoryStore):
        records = [_make_record(f"r-{i}", f"text {i}") for i in range(5)]
        ids = await store.upsert_batch("coll", records)
        assert len(ids) == 5
        assert ids[0] == "r-0"

    async def test_upsert_overwrites(self, store: SynapseMemoryStore):
        r1 = _make_record("r-1", "original")
        r2 = _make_record("r-1", "updated")
        await store.upsert("coll", r1)
        await store.upsert("coll", r2)
        rec = await store.get("coll", "r-1", with_embedding=True)
        assert rec.text == "updated"


class TestMemoryStoreGet:
    async def test_get_with_embedding(self, store: SynapseMemoryStore):
        record = _make_record()
        await store.upsert("coll", record)
        rec = await store.get("coll", "rec-1", with_embedding=True)
        assert rec.text == "test content"
        assert rec.embedding is not None

    async def test_get_without_embedding(self, store: SynapseMemoryStore):
        record = _make_record()
        await store.upsert("coll", record)
        rec = await store.get("coll", "rec-1", with_embedding=False)
        assert rec.text == "test content"
        assert rec.embedding is None

    async def test_get_nonexistent_raises(self, store: SynapseMemoryStore):
        await store.create_collection("coll")
        with pytest.raises(KeyError):
            await store.get("coll", "nope", with_embedding=False)

    async def test_get_batch(self, store: SynapseMemoryStore):
        for i in range(3):
            await store.upsert("coll", _make_record(f"r-{i}", f"text {i}"))
        results = await store.get_batch("coll", ["r-0", "r-2", "r-99"], with_embeddings=True)
        assert len(results) == 2  # r-99 doesn't exist


class TestMemoryStoreRemove:
    async def test_remove(self, store: SynapseMemoryStore):
        await store.upsert("coll", _make_record())
        await store.remove("coll", "rec-1")
        with pytest.raises(KeyError):
            await store.get("coll", "rec-1", with_embedding=False)

    async def test_remove_nonexistent(self, store: SynapseMemoryStore):
        await store.create_collection("coll")
        await store.remove("coll", "nope")  # Should not raise

    async def test_remove_batch(self, store: SynapseMemoryStore):
        for i in range(3):
            await store.upsert("coll", _make_record(f"r-{i}"))
        await store.remove_batch("coll", ["r-0", "r-1"])
        results = await store.get_batch("coll", ["r-0", "r-1", "r-2"], with_embeddings=False)
        assert len(results) == 1
        assert results[0].id == "r-2"


class TestMemoryStoreClose:
    async def test_close(self, store: SynapseMemoryStore):
        await store.close()  # Should not raise


class TestMemoryStoreEdgeCases:
    async def test_unicode_text(self, store: SynapseMemoryStore):
        record = _make_record("u1", "数据库配置：主机=db.example.com")
        await store.upsert("coll", record)
        rec = await store.get("coll", "u1", with_embedding=True)
        assert "数据库" in rec.text

    async def test_empty_text(self, store: SynapseMemoryStore):
        record = _make_record("e1", "")
        await store.upsert("coll", record)
        rec = await store.get("coll", "e1", with_embedding=True)
        assert rec.text == ""

    async def test_multiple_collections_isolated(self, store: SynapseMemoryStore):
        await store.upsert("coll-a", _make_record("r-1", "alpha"))
        await store.upsert("coll-b", _make_record("r-1", "beta"))
        a = await store.get("coll-a", "r-1", with_embedding=True)
        b = await store.get("coll-b", "r-1", with_embedding=True)
        assert a.text == "alpha"
        assert b.text == "beta"
