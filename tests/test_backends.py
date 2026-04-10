"""Tests for StorageBackend implementations.

Covers:
  - MemoryBackend (in-memory)
  - SqliteBackend (persistent)
  - SynapseMemory integration with both backends
"""

import os
import tempfile
import pytest

from synapse_memory.backends import MemoryBackend, SqliteBackend, StorageBackend
from synapse_memory import SynapseMemory


# ═══ Fixtures ═════════════════════════════════════════════════════════════

def _make_record(memory_id: str = "abc123", agent_id: str = "test-agent",
                 content: str = "User prefers dark mode",
                 tq: float = 0.85) -> dict:
    return {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "content": content,
        "trust_quotient": tq,
        "confidence": 0.9,
        "intent": "preference",
        "is_critical": False,
        "source_type": "validated",
        "metadata": {"source": "test"},
        "timestamp": 1700000000.0,
    }


@pytest.fixture
def mem_backend():
    return MemoryBackend()


@pytest.fixture
def sqlite_backend(tmp_path):
    db_path = str(tmp_path / "test_memories.db")
    backend = SqliteBackend(path=db_path)
    yield backend
    backend.close()


# ═══ Protocol conformance ═════════════════════════════════════════════════

def test_memory_backend_is_storage_backend():
    assert isinstance(MemoryBackend(), StorageBackend)


def test_sqlite_backend_is_storage_backend(sqlite_backend):
    assert isinstance(sqlite_backend, StorageBackend)


# ═══ MemoryBackend ════════════════════════════════════════════════════════

class TestMemoryBackend:
    def test_save_and_recall(self, mem_backend):
        rec = _make_record()
        mem_backend.save(rec)
        results = mem_backend.recall("dark mode")
        assert len(results) == 1
        assert results[0]["content"] == "User prefers dark mode"

    def test_count(self, mem_backend):
        assert mem_backend.count() == 0
        mem_backend.save(_make_record())
        assert mem_backend.count() == 1

    def test_delete(self, mem_backend):
        mem_backend.save(_make_record(memory_id="x1"))
        assert mem_backend.delete("x1")
        assert mem_backend.count() == 0
        assert not mem_backend.delete("nonexistent")

    def test_clear(self, mem_backend):
        mem_backend.save(_make_record(memory_id="a"))
        mem_backend.save(_make_record(memory_id="b"))
        cleared = mem_backend.clear()
        assert cleared == 2
        assert mem_backend.count() == 0

    def test_recall_empty_query(self, mem_backend):
        mem_backend.save(_make_record())
        results = mem_backend.recall("")
        assert len(results) == 1  # returns all

    def test_count_by_agent(self, mem_backend):
        mem_backend.save(_make_record(agent_id="a1"))
        mem_backend.save(_make_record(memory_id="m2", agent_id="a2"))
        assert mem_backend.count(agent_id="a1") == 1
        assert mem_backend.count(agent_id="a2") == 1


# ═══ SqliteBackend ════════════════════════════════════════════════════════

class TestSqliteBackend:
    def test_save_and_recall(self, sqlite_backend):
        rec = _make_record()
        sqlite_backend.save(rec)
        results = sqlite_backend.recall("dark mode")
        assert len(results) == 1
        assert results[0]["content"] == "User prefers dark mode"

    def test_persistence(self, tmp_path):
        db_path = str(tmp_path / "persist.db")
        b1 = SqliteBackend(path=db_path)
        b1.save(_make_record())
        b1.close()

        b2 = SqliteBackend(path=db_path)
        assert b2.count() == 1
        results = b2.recall("dark")
        assert len(results) == 1
        b2.close()

    def test_upsert(self, sqlite_backend):
        sqlite_backend.save(_make_record(memory_id="x", content="v1"))
        sqlite_backend.save(_make_record(memory_id="x", content="v2"))
        assert sqlite_backend.count() == 1
        results = sqlite_backend.recall("v2")
        assert results[0]["content"] == "v2"

    def test_count(self, sqlite_backend):
        assert sqlite_backend.count() == 0
        sqlite_backend.save(_make_record())
        assert sqlite_backend.count() == 1

    def test_delete(self, sqlite_backend):
        sqlite_backend.save(_make_record(memory_id="d1"))
        assert sqlite_backend.delete("d1")
        assert sqlite_backend.count() == 0
        assert not sqlite_backend.delete("nope")

    def test_clear(self, sqlite_backend):
        sqlite_backend.save(_make_record(memory_id="c1"))
        sqlite_backend.save(_make_record(memory_id="c2"))
        cleared = sqlite_backend.clear()
        assert cleared == 2

    def test_clear_by_agent(self, sqlite_backend):
        sqlite_backend.save(_make_record(memory_id="m1", agent_id="a1"))
        sqlite_backend.save(_make_record(memory_id="m2", agent_id="a2"))
        cleared = sqlite_backend.clear(agent_id="a1")
        assert cleared == 1
        assert sqlite_backend.count() == 1

    def test_recall_with_agent_filter(self, sqlite_backend):
        sqlite_backend.save(_make_record(memory_id="m1", agent_id="a1",
                                          content="dark mode pref"))
        sqlite_backend.save(_make_record(memory_id="m2", agent_id="a2",
                                          content="dark theme choice"))
        results = sqlite_backend.recall("dark", agent_id="a1")
        assert len(results) == 1
        assert results[0]["agent_id"] == "a1"

    def test_metadata_roundtrip(self, sqlite_backend):
        rec = _make_record()
        rec["metadata"] = {"lang": "pt-BR", "tags": ["pref", "ui"]}
        sqlite_backend.save(rec)
        results = sqlite_backend.recall("dark")
        assert results[0]["metadata"]["lang"] == "pt-BR"
        assert "tags" in results[0]["metadata"]


# ═══ Integration: SynapseMemory + SqliteBackend ═══════════════════════════

class TestIntegrationSqlite:
    @pytest.mark.asyncio
    async def test_store_and_recall_with_sqlite(self, tmp_path):
        db_path = str(tmp_path / "integration.db")
        backend = SqliteBackend(path=db_path)
        mem = SynapseMemory(agent_id="int-agent", backend=backend)

        result = await mem.store("User prefers concise answers")
        assert result.sanitized is True
        assert result.memory_id

        recalls = await mem.recall("concise answers")
        assert len(recalls) >= 1
        assert "concise" in recalls[0].content.lower() or "answers" in recalls[0].content.lower()

        backend.close()

    @pytest.mark.asyncio
    async def test_default_backend_is_memory(self):
        mem = SynapseMemory(agent_id="default-test")
        assert isinstance(mem._backend, MemoryBackend)

    @pytest.mark.asyncio
    async def test_recall_uses_backend_not_legacy(self, tmp_path):
        """When SqliteBackend is used, recall queries the DB, not _memories."""
        db_path = str(tmp_path / "backend_prio.db")
        backend = SqliteBackend(path=db_path)
        mem = SynapseMemory(agent_id="bp-agent", backend=backend)

        await mem.store("The sky is blue")

        # Clear legacy list to prove recall uses backend
        mem._memories.clear()

        recalls = await mem.recall("sky")
        assert len(recalls) >= 1
        backend.close()
