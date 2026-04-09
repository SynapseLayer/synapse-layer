"""
Tests for Synapse Layer CrewAI Integration

Verifies that the SynapseCrewStorage adapter:
- Implements the CrewAI StorageBackend protocol
- Routes storage through the OSS security pipeline
- Returns CrewAI-compatible structures
- Works without PRO modules
- Maintains Sentinel Protocol compliance

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest

# Skip entire module if crewai is not installed
pytest.importorskip("crewai", reason="crewai not installed")

from crewai.memory.storage.backend import StorageBackend
from crewai.memory.types import MemoryRecord, ScopeInfo

from synapse_memory.core import SynapseMemory
from synapse_memory.integrations.crewai_memory import SynapseCrewStorage


# ══ Fixtures ════════════════════════════════════════════════════════════

@pytest.fixture
def storage() -> SynapseCrewStorage:
    """Fresh storage instance."""
    return SynapseCrewStorage(agent_id="test-crewai-agent")


@pytest.fixture
def custom_memory() -> SynapseMemory:
    """Pre-configured SynapseMemory."""
    return SynapseMemory(
        agent_id="custom-agent",
        sanitize_enabled=False,
        privacy_enabled=False,
    )


@pytest.fixture
def sample_records() -> list:
    """Sample CrewAI MemoryRecord list."""
    return [
        MemoryRecord(
            content="User prefers dark mode interfaces.",
            scope="/crew/design",
            categories=["preference", "ui"],
            importance=0.8,
            source="designer-agent",
        ),
        MemoryRecord(
            content="Project deadline is next Friday.",
            scope="/crew/design",
            categories=["deadline"],
            importance=0.9,
        ),
        MemoryRecord(
            content="Budget approved for Q2 campaign.",
            scope="/crew/marketing",
            categories=["budget", "decision"],
            importance=0.7,
        ),
    ]


# ══ Protocol Compliance ════════════════════════════════════════════════

class TestProtocolCompliance:
    """Verify SynapseCrewStorage satisfies the StorageBackend protocol."""

    def test_implements_storage_backend(self):
        assert isinstance(SynapseCrewStorage(agent_id="test"), StorageBackend)

    def test_has_save(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "save", None))

    def test_has_search(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "search", None))

    def test_has_delete(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "delete", None))

    def test_has_update(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "update", None))

    def test_has_get_record(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "get_record", None))

    def test_has_list_records(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "list_records", None))

    def test_has_count(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "count", None))

    def test_has_reset(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "reset", None))

    def test_has_async_variants(self, storage: SynapseCrewStorage):
        assert callable(getattr(storage, "asave", None))
        assert callable(getattr(storage, "asearch", None))
        assert callable(getattr(storage, "adelete", None))

    def test_repr(self, storage: SynapseCrewStorage):
        r = repr(storage)
        assert "SynapseCrewStorage" in r
        assert "test-crewai-agent" in r


# ══ Storage Tests ══════════════════════════════════════════════════════

class TestStorage:
    """Verify records are saved through the Synapse pipeline."""

    def test_save_single_record(self, storage: SynapseCrewStorage):
        record = MemoryRecord(
            content="Test fact for storage.",
            scope="/test",
            categories=["test"],
            importance=0.7,
        )
        storage.save([record])
        assert storage.count() == 1

    def test_save_multiple_records(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        assert storage.count() == 3

    def test_metadata_preserved(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        mem = storage._memory._memories[0]
        metadata = mem.get("metadata", {})
        assert metadata.get("integration") == "crewai"
        assert metadata.get("scope") == "/crew/design"
        assert "preference" in metadata.get("categories", [])

    def test_source_preserved(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        mem = storage._memory._memories[0]
        assert mem.get("metadata", {}).get("source") == "designer-agent"

    def test_sanitization_active(self, storage: SynapseCrewStorage):
        """Verify PII redaction is active (Sentinel Protocol)."""
        record = MemoryRecord(
            content="Contact me at john@example.com or 555-1234.",
            scope="/test",
        )
        storage.save([record])
        stored_content = storage._memory._memories[0]["content"]
        # Sanitizer should redact email/phone
        assert "john@example.com" not in stored_content


# ══ Retrieval Tests ════════════════════════════════════════════════════

class TestRetrieval:
    """Verify retrieval returns CrewAI-compatible structures."""

    def test_list_records(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        records = storage.list_records()
        assert len(records) == 3
        assert all(isinstance(r, MemoryRecord) for r in records)

    def test_list_records_with_scope(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        records = storage.list_records(scope_prefix="/crew/design")
        assert len(records) == 2

    def test_get_record(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        record_id = sample_records[0].id
        found = storage.get_record(record_id)
        assert found is not None
        assert isinstance(found, MemoryRecord)

    def test_get_record_not_found(self, storage: SynapseCrewStorage):
        assert storage.get_record("nonexistent") is None

    def test_count(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        assert storage.count() == 3
        assert storage.count(scope_prefix="/crew/marketing") == 1


# ══ Scope Tests ════════════════════════════════════════════════════════

class TestScopes:
    """Verify scope management works."""

    def test_get_scope_info(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        info = storage.get_scope_info("/crew/design")
        assert isinstance(info, ScopeInfo)
        assert info.record_count == 2
        assert info.path == "/crew/design"

    def test_list_scopes(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        scopes = storage.list_scopes("/crew")
        assert "/crew/design" in scopes
        assert "/crew/marketing" in scopes

    def test_list_categories(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        cats = storage.list_categories(scope_prefix="/crew/design")
        assert "preference" in cats or "ui" in cats or "deadline" in cats


# ══ Delete & Reset Tests ═══════════════════════════════════════════════

class TestDeleteReset:
    """Verify delete and reset operations."""

    def test_delete_by_scope(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        deleted = storage.delete(scope_prefix="/crew/marketing")
        assert deleted == 1
        assert storage.count() == 2

    def test_delete_by_category(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        deleted = storage.delete(categories=["deadline"])
        assert deleted >= 1

    def test_reset_all(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        storage.reset()
        assert storage.count() == 0

    def test_reset_scoped(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        storage.reset(scope_prefix="/crew/design")
        assert storage.count() == 1  # Only marketing remains


# ══ Update Tests ═══════════════════════════════════════════════════════

class TestUpdate:
    """Verify update operations."""

    def test_update_existing(
        self, storage: SynapseCrewStorage, sample_records: list
    ):
        storage.save(sample_records)
        original_id = sample_records[0].id
        updated = MemoryRecord(
            id=original_id,
            content="Updated: User now prefers light mode.",
            scope="/crew/design",
            categories=["preference"],
            importance=0.9,
        )
        storage.update(updated)
        found = storage.get_record(original_id)
        assert found is not None
        # Content may be sanitized, but should reflect update
        assert storage.count() == 3  # No duplicate added


# ══ Async Tests ════════════════════════════════════════════════════════

class TestAsync:
    """Verify async variants work."""

    @pytest.mark.asyncio
    async def test_async_save(self, storage: SynapseCrewStorage):
        records = [
            MemoryRecord(content="Async test memory.", scope="/async"),
        ]
        await storage.asave(records)
        assert storage.count() == 1

    @pytest.mark.asyncio
    async def test_async_search(self, storage: SynapseCrewStorage):
        records = [
            MemoryRecord(content="Searchable async memory.", scope="/async"),
        ]
        await storage.asave(records)
        results = await storage.asearch(query_embedding=[], limit=5)
        assert isinstance(results, list)


# ══ Custom Memory Injection ════════════════════════════════════════════

class TestCustomMemory:
    """Verify custom SynapseMemory injection."""

    def test_custom_memory_injection(self, custom_memory: SynapseMemory):
        storage = SynapseCrewStorage(
            agent_id="custom-agent",
            memory=custom_memory,
        )
        assert storage._memory is custom_memory

    def test_custom_memory_stores(self, custom_memory: SynapseMemory):
        storage = SynapseCrewStorage(
            agent_id="custom-agent",
            memory=custom_memory,
        )
        storage.save([
            MemoryRecord(content="Custom backend test.", scope="/custom"),
        ])
        assert len(custom_memory._memories) == 1


# ══ OSS Safety ═════════════════════════════════════════════════════════

class TestOSSSafety:
    """Verify no PRO modules or scoring internals exposed."""

    def test_no_pro_imports(self):
        import synapse_memory.integrations.crewai_memory as mod
        source = open(mod.__file__).read()
        assert "synapse_memory_pro" not in source
        assert "ProImportanceScorer" not in source
        assert "ProConflictResolver" not in source
        assert "ProDedupStrategy" not in source

    def test_no_scoring_internals(self):
        import synapse_memory.integrations.crewai_memory as mod
        source = open(mod.__file__).read()
        assert "Jaccard" not in source
        assert "SATURATION_HITS" not in source
        assert "0.65" not in source


# ══ Sentinel Protocol ══════════════════════════════════════════════════

class TestSentinelProtocol:
    """Verify Sentinel Protocol is not bypassed."""

    def test_pii_redaction_active(self, storage: SynapseCrewStorage):
        """Emails should be redacted by the security pipeline."""
        storage.save([
            MemoryRecord(
                content="Send report to admin@company.com immediately.",
                scope="/test",
            ),
        ])
        stored = storage._memory._memories[0]["content"]
        assert "admin@company.com" not in stored

    def test_pipeline_processes_content(self, storage: SynapseCrewStorage):
        """Content must go through SynapseMemory.store(), not bypass it."""
        storage.save([
            MemoryRecord(content="Important decision made.", scope="/test"),
        ])
        mem = storage._memory._memories[0]
        # Verify it went through the full pipeline
        assert "trust_quotient" in mem
        assert "intent" in mem
        assert mem.get("agent_id") == "test-crewai-agent"
