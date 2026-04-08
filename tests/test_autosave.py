"""
Synapse Layer — Auto-Save Engine Test Suite

Covers: PolicyEngine, TriggerDetector, EventFormatter, AutoSaveEngine.
Target: 90%+ coverage on synapse_memory/autosave/.
"""

from __future__ import annotations

import time
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from synapse_memory.autosave import (
    AutoSaveEngine,
    AutoSaveEvent,
    SaveResult,
    PolicyDecision,
    PolicyEngine,
    TriggerDetector,
    EventFormatter,
)
from synapse_memory.autosave.types import ALL_PROJECTS, ALL_EVENT_TYPES


# ── Fixtures ────────────────────────────────────────────────────────

class FakeRedactionResult:
    def __init__(self, content: str):
        self.content = content
        self.pii_redacted = False
        self.secrets_filtered = False
        self.redaction_level = "strict"


def fake_redact(content: str, level: str = "strict") -> FakeRedactionResult:
    return FakeRedactionResult(content)


class FakeDatabase:
    """In-memory database mock implementing DatabaseProtocol."""

    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._counter = 0
        self.should_raise = False
        self.raise_duplicate = False

    def insert_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.should_raise:
            raise RuntimeError("DB error")
        if self.raise_duplicate:
            raise RuntimeError("duplicate key violates unique constraint")
        self._counter += 1
        mid = f"mem-{self._counter:04d}"
        self.memories[mid] = {**payload, "id": mid}
        return {"id": mid}

    def enqueue_embedding(self, memory_id: str) -> None:
        self._counter += 1
        jid = f"job-{self._counter:04d}"
        self.jobs[jid] = {"id": jid, "memory_id": memory_id, "status": "pending"}

    def fetch_pending_jobs(self, limit: int) -> List[Dict[str, Any]]:
        pending = [j for j in self.jobs.values() if j["status"] == "pending"]
        return pending[:limit]

    def fetch_memory_content(self, memory_id: str) -> Optional[str]:
        mem = self.memories.get(memory_id)
        return mem["content"] if mem else None

    def update_embedding(self, memory_id: str, embedding: List[float]) -> None:
        if memory_id in self.memories:
            self.memories[memory_id]["embedding"] = embedding

    def complete_job(self, job_id: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "completed"

    def fail_job(self, job_id: str, error: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["error"] = error


@pytest.fixture
def policy():
    return PolicyEngine(mode="oss")


@pytest.fixture
def policy_pro():
    return PolicyEngine(mode="pro")


@pytest.fixture
def detector():
    return TriggerDetector()


@pytest.fixture
def formatter():
    return EventFormatter()


@pytest.fixture
def fake_db():
    return FakeDatabase()


@pytest.fixture
def engine(fake_db):
    return AutoSaveEngine(
        database=fake_db,
        redactor=fake_redact,
        policy=PolicyEngine(mode="oss"),
    )


@pytest.fixture
def engine_pro(fake_db):
    return AutoSaveEngine(
        database=fake_db,
        redactor=fake_redact,
        policy=PolicyEngine(mode="pro"),
    )


def _make_event(**kwargs) -> AutoSaveEvent:
    defaults = {
        "content": "We deployed OFFLY v2.0 to production",
        "project": "OFFLY",
        "type": "[MILESTONE]",
        "importance": 4,
        "source": "test",
        "tags": ["deploy"],
    }
    defaults.update(kwargs)
    return AutoSaveEvent(**defaults)


# ════════════════════════════════════════════════════════════════
# PolicyEngine Tests
# ════════════════════════════════════════════════════════════════

class TestPolicyEngine:

    def test_approve_valid_event(self, policy):
        event = _make_event(importance=4)
        d = policy.evaluate(event)
        assert d.should_save is True
        assert d.reason == "approved"

    def test_block_api_key(self, policy):
        event = _make_event(content="My api_key=sk-abcdef1234567890abcdef1234567890")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "security_blocked"

    def test_block_bearer_token(self, policy):
        event = _make_event(content="Token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCIXXX")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "security_blocked"

    def test_block_aws_key(self, policy):
        event = _make_event(content="key is AKIAIOSFODNN7EXAMPLE")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_github_token(self, policy):
        event = _make_event(content="token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_password(self, policy):
        event = _make_event(content="password: MySuper$ecret123")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_connection_string(self, policy):
        event = _make_event(content="db at postgres://user:pass@host:5432/db")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_private_key(self, policy):
        event = _make_event(content="-----BEGIN RSA PRIVATE KEY-----\nMIIE")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_email(self, policy):
        event = _make_event(content="Contact john@acme.com for details")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "security_blocked"

    def test_block_phone_br(self, policy):
        event = _make_event(content="Ligar para +55 11 99999-8888")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_phone_intl(self, policy):
        event = _make_event(content="Call +1 5551234567890")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_cpf(self, policy):
        event = _make_event(content="CPF do cliente: 123.456.789-00")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_cnpj(self, policy):
        event = _make_event(content="CNPJ: 12.345.678/0001-00")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_ssn(self, policy):
        event = _make_event(content="SSN is 123-45-6789")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_private_endpoint(self, policy):
        event = _make_event(content="API at http://localhost:3000/api/secret")
        d = policy.evaluate(event)
        assert d.should_save is False

    def test_block_zero_importance(self, policy):
        event = _make_event(importance=0, type="[AUTO-OP]")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "zero_importance"

    def test_block_invalid_project(self, policy):
        event = _make_event(project="INVALID_PROJECT")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "project_not_allowed"

    def test_block_invalid_type(self, policy):
        event = _make_event(type="[INVALID]")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert d.reason == "type_not_allowed"

    def test_oss_blocks_low_importance(self, policy):
        event = _make_event(importance=2, type="[AUTO-OP]")
        d = policy.evaluate(event)
        assert d.should_save is False
        assert "below_oss_threshold" in d.reason

    def test_pro_allows_low_importance(self, policy_pro):
        event = _make_event(importance=1, type="[AUTO-OP]")
        d = policy_pro.evaluate(event)
        assert d.should_save is True

    def test_milestone_elevates_importance(self, policy):
        event = _make_event(importance=2, type="[MILESTONE]")
        d = policy.evaluate(event)
        assert d.should_save is True
        assert d.adjusted_importance >= 4

    def test_alert_elevates_to_5(self, policy):
        event = _make_event(importance=1, type="[ALERT]")
        d = policy.evaluate(event)
        assert d.adjusted_importance == 5

    def test_decision_elevates_importance(self, policy):
        event = _make_event(importance=1, type="[DECISION]")
        d = policy.evaluate(event)
        assert d.adjusted_importance >= 3

    def test_auto_decision_elevates(self, policy):
        event = _make_event(importance=1, type="[AUTO-DECISION]")
        d = policy.evaluate(event)
        assert d.adjusted_importance >= 3

    def test_tag_elevation(self, policy):
        event = _make_event(importance=3, tags=["launch", "monetization"])
        d = policy.evaluate(event)
        assert d.adjusted_importance >= 4

    def test_tag_elevation_caps_at_5(self, policy):
        event = _make_event(importance=5, type="[ALERT]", tags=["security"])
        d = policy.evaluate(event)
        assert d.adjusted_importance == 5

    def test_semantic_dedup(self, policy):
        event = _make_event(content="Unique content for dedup test")
        d1 = policy.evaluate(event)
        assert d1.should_save is True
        # Same event again within window
        d2 = policy.evaluate(event)
        assert d2.should_save is False
        assert d2.reason == "semantic_duplicate"

    def test_dedup_window_expires(self, policy):
        policy._dedup_window = 0.05  # 50ms
        event = _make_event(content="Window test content ABC")
        d1 = policy.evaluate(event)
        assert d1.should_save is True
        time.sleep(0.1)
        d2 = policy.evaluate(event)
        assert d2.should_save is True  # Window expired


# ════════════════════════════════════════════════════════════════
# TriggerDetector Tests
# ════════════════════════════════════════════════════════════════

class TestTriggerDetector:

    def test_empty_text_returns_empty(self, detector):
        assert detector.detect("") == []
        assert detector.detect(None) == []

    def test_detect_milestone_deployed(self, detector):
        events = detector.detect("We deployed OFFLY v2.0 to production")
        assert len(events) >= 1
        types = [e.type for e in events]
        assert "[MILESTONE]" in types

    def test_detect_milestone_launched(self, detector):
        events = detector.detect("Successfully launched the new platform")
        assert any(e.type == "[MILESTONE]" for e in events)

    def test_detect_milestone_first_customer(self, detector):
        events = detector.detect("We got our first paying customer today!")
        assert any(e.type == "[MILESTONE]" for e in events)

    def test_detect_milestone_version(self, detector):
        events = detector.detect("Released v1.0.7 to PyPI")
        assert any(e.type == "[MILESTONE]" for e in events)

    def test_detect_decision(self, detector):
        events = detector.detect("We decided to pivot GOARQIA to B2B")
        assert any(e.type == "[DECISION]" for e in events)

    def test_detect_decision_strategy(self, detector):
        events = detector.detect("The strategy is to focus on enterprise")
        assert any(e.type == "[DECISION]" for e in events)

    def test_detect_alert(self, detector):
        events = detector.detect("There's a critical bug in authentication")
        assert any(e.type == "[ALERT]" for e in events)
        alert = next(e for e in events if e.type == "[ALERT]")
        assert alert.importance == 5

    def test_detect_alert_breach(self, detector):
        events = detector.detect("Security breach detected in NEXUMI")
        assert any(e.type == "[ALERT]" for e in events)

    def test_detect_project_offly(self, detector):
        events = detector.detect("OFFLY launched the new dashboard")
        assert events[0].project == "OFFLY"

    def test_detect_project_safezap(self, detector):
        events = detector.detect("SafeZap launched new features")
        assert events[0].project == "SAFEZAP_BRASIL"

    def test_detect_project_default(self, detector):
        events = detector.detect("We shipped the update today")
        assert events[0].project == "SYNAPSE_LAYER"  # default

    def test_detect_json_classification(self, detector):
        text = 'Analysis: {"classification": "[AUTO-STRAT]", "content": "pivot to B2B", "importance": 5}'
        events = detector.detect(text)
        json_events = [e for e in events if e.type == "[AUTO-STRAT]"]
        assert len(json_events) >= 1
        assert json_events[0].importance == 5

    def test_no_triggers_returns_empty(self, detector):
        events = detector.detect("The weather is nice today")
        assert len(events) == 0

    def test_tags_extracted(self, detector):
        events = detector.detect("We deployed the production infrastructure")
        assert len(events) > 0
        assert len(events[0].tags) > 0

    def test_source_override(self, detector):
        events = detector.detect("Deployed v1.0", source="custom_source")
        assert events[0].source == "custom_source"

    def test_project_override(self, detector):
        events = detector.detect("Deployed v1.0", project_override="NEXUMI")
        assert events[0].project == "NEXUMI"

    def test_alert_priority_over_milestone(self, detector):
        """Alert triggers should be detected even if milestone also matches."""
        events = detector.detect("Urgent: we launched but there's a critical bug")
        types = [e.type for e in events]
        # Alert is detected (it has higher priority in the detection chain)
        assert "[ALERT]" in types


# ════════════════════════════════════════════════════════════════
# EventFormatter Tests
# ════════════════════════════════════════════════════════════════

class TestEventFormatter:

    def test_format_canonical(self, formatter):
        event = _make_event()
        payload = formatter.format(event)
        assert payload["content"] == event.content
        assert payload["project"] == "OFFLY"
        assert payload["metadata"]["type"] == "[MILESTONE]"
        assert payload["metadata"]["importance"] == 4
        assert payload["metadata"]["synapse_version"] == "1.0.7"
        assert payload["metadata"]["autosave_engine"] == "1.0.0"

    def test_format_with_content_override(self, formatter):
        event = _make_event(content="raw content")
        payload = formatter.format(event, content_override="redacted content")
        assert payload["content"] == "redacted content"

    def test_format_preserves_tags(self, formatter):
        event = _make_event(tags=["deploy", "production"])
        payload = formatter.format(event)
        assert payload["metadata"]["tags"] == ["deploy", "production"]

    def test_format_preserves_source_ref(self, formatter):
        event = _make_event(source_ref={"conversation_id": "abc123"})
        payload = formatter.format(event)
        assert payload["metadata"]["source_ref"] == {"conversation_id": "abc123"}

    def test_project_uppercased(self, formatter):
        event = _make_event(project="offly")
        payload = formatter.format(event)
        assert payload["project"] == "OFFLY"


# ════════════════════════════════════════════════════════════════
# AutoSaveEngine Tests
# ════════════════════════════════════════════════════════════════

class TestAutoSaveEngine:

    def test_save_approved(self, engine, fake_db):
        event = _make_event(content="Unique content for engine test 001")
        result = engine.save(event)
        assert result.status == "saved"
        assert result.id is not None
        assert result.project == "OFFLY"
        assert len(fake_db.memories) == 1
        assert len(fake_db.jobs) == 1

    def test_save_blocked_by_policy(self, engine):
        event = _make_event(content="password: SuperSecret123!")
        result = engine.save(event)
        assert result.status == "blocked"
        assert result.id is None

    def test_save_blocked_low_importance_oss(self, engine):
        event = _make_event(
            content="Minor note 002",
            importance=1,
            type="[AUTO-OP]",
        )
        result = engine.save(event)
        assert result.status == "blocked"

    def test_save_allowed_low_importance_pro(self, engine_pro, fake_db):
        event = _make_event(
            content="Minor note for pro 003",
            importance=1,
            type="[AUTO-OP]",
        )
        result = engine_pro.save(event)
        assert result.status == "saved"

    def test_save_dedup_cache(self, fake_db):
        # Use a policy with no dedup window so only engine cache catches it
        policy_nodedup = PolicyEngine(mode="oss", dedup_window_seconds=0.0)
        eng = AutoSaveEngine(
            database=fake_db,
            redactor=fake_redact,
            policy=policy_nodedup,
        )
        event = _make_event(content="Dedup test content 004")
        r1 = eng.save(event)
        assert r1.status == "saved"
        r2 = eng.save(event)
        assert r2.status == "deduplicated"
        assert r2.reason == "LRU cache hit"

    def test_save_db_error(self, engine, fake_db):
        fake_db.should_raise = True
        event = _make_event(content="DB error test 005")
        result = engine.save(event)
        assert result.status == "error"

    def test_save_db_duplicate_constraint(self, engine, fake_db):
        fake_db.raise_duplicate = True
        event = _make_event(content="DB duplicate test 006")
        result = engine.save(event)
        assert result.status == "deduplicated"
        assert "unique" in result.reason.lower() or "db" in result.reason.lower()

    def test_save_attaches_redaction_meta(self, engine, fake_db):
        event = _make_event(content="Redaction meta test 007")
        result = engine.save(event)
        assert result.status == "saved"
        mem = list(fake_db.memories.values())[0]
        assert "redaction" in mem["metadata"]

    def test_process_text_detects_and_saves(self, engine, fake_db):
        text = "We deployed OFFLY v3.0 to production today"
        results = engine.process_text(text)
        assert len(results) >= 1
        assert any(r.status == "saved" for r in results)

    def test_process_text_no_triggers(self, engine):
        results = engine.process_text("The weather is sunny")
        assert len(results) == 0

    def test_process_text_with_project_override(self, engine, fake_db):
        results = engine.process_text(
            "Deployed the update",
            project="NEXUMI",
        )
        assert len(results) >= 1
        assert results[0].project == "NEXUMI"

    def test_process_text_with_source(self, engine):
        results = engine.process_text(
            "Milestone reached: first flight",
            source="deepagent",
        )
        assert len(results) >= 1

    def test_backfill_no_embed_fn(self, engine):
        result = engine.backfill(limit=10, embed_fn=None)
        assert result["processed"] == 0

    def test_backfill_processes_jobs(self, engine, fake_db):
        # First save to create a pending job
        event = _make_event(content="Backfill test content 008")
        engine.save(event)
        assert len(fake_db.jobs) == 1

        def fake_embed(text: str) -> List[float]:
            return [0.1] * 1536

        result = engine.backfill(limit=10, embed_fn=fake_embed)
        assert result["processed"] == 1

    def test_backfill_handles_failure(self, engine, fake_db):
        event = _make_event(content="Backfill fail test 009")
        engine.save(event)

        def bad_embed(text: str) -> List[float]:
            raise RuntimeError("Embedding API error")

        result = engine.backfill(limit=10, embed_fn=bad_embed)
        assert result["failed"] == 1

    def test_importance_clamped(self):
        event = AutoSaveEvent(
            content="test", project="OFFLY", type="[ALERT]",
            importance=10,
        )
        assert event.importance == 5
        event2 = AutoSaveEvent(
            content="test", project="OFFLY", type="[ALERT]",
            importance=-5,
        )
        assert event2.importance == 0


# ════════════════════════════════════════════════════════════════
# Types Tests
# ════════════════════════════════════════════════════════════════

class TestTypes:

    def test_all_projects_frozen(self):
        assert isinstance(ALL_PROJECTS, frozenset)
        assert "OFFLY" in ALL_PROJECTS
        assert len(ALL_PROJECTS) == 5

    def test_all_event_types(self):
        assert isinstance(ALL_EVENT_TYPES, frozenset)
        assert "[AUTO-STRAT]" in ALL_EVENT_TYPES
        assert "[MILESTONE]" in ALL_EVENT_TYPES

    def test_save_result_defaults(self):
        r = SaveResult(id=None, status="blocked")
        assert r.project == ""
        assert r.reason == ""

    def test_policy_decision_frozen(self):
        d = PolicyDecision(should_save=True, reason="ok", adjusted_importance=3)
        assert d.blocked_reason is None
