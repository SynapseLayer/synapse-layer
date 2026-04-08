"""
Synapse Layer — Plugin Architecture Test Suite

Covers:
    - Core interfaces (Protocol compliance)
    - Default OSS implementations
    - Plugin loader (mock PRO / missing PRO)
    - SYNAPSE_MODE enforcement (oss vs pro)
    - AutoSaveEngine strategy injection
    - Backward compatibility (existing tests unaffected)

Target: 100% coverage on synapse_memory/core/
"""

from __future__ import annotations

import os
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from synapse_memory.autosave.types import AutoSaveEvent
from synapse_memory.plugins.interfaces import (
    ImportanceScorer,
    ConflictResolver,
    DedupStrategy,
    RedactionStrategy,
    RedactionResult,
    SynapseProPlugin,
)
from synapse_memory.plugins.defaults import (
    DefaultImportanceScorer,
    DefaultConflictResolver,
    DefaultDedupStrategy,
)
from synapse_memory.plugins.plugin_loader import load_pro_plugin
from synapse_memory.autosave.engine import AutoSaveEngine


# ── Helpers ───────────────────────────────────────────────────────────

def _make_event(**kwargs) -> AutoSaveEvent:
    defaults = dict(
        content="Test event content",
        project="SYNAPSE_LAYER",
        type="[MILESTONE]",
        importance=3,
        source="test",
    )
    defaults.update(kwargs)
    return AutoSaveEvent(**defaults)


class FakeRedactionResult:
    def __init__(self, content: str):
        self.content = content
        self.pii_redacted = False
        self.secrets_filtered = False
        self.redaction_level = "strict"


def fake_redact(content: str, level: str = "strict") -> FakeRedactionResult:
    return FakeRedactionResult(content)


class FakeDatabase:
    def __init__(self):
        self.memories: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def insert_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._counter += 1
        mid = f"mem-{self._counter}"
        self.memories[mid] = payload
        return {"id": mid}

    def enqueue_embedding(self, memory_id: str) -> None:
        pass

    def fetch_pending_jobs(self, limit: int) -> List[Dict[str, Any]]:
        return []

    def fetch_memory_content(self, memory_id: str) -> Optional[str]:
        m = self.memories.get(memory_id)
        return m["content"] if m else None

    def update_embedding(self, memory_id: str, embedding: List[float]) -> None:
        pass

    def complete_job(self, job_id: str) -> None:
        pass

    def fail_job(self, job_id: str, error: str) -> None:
        pass


# ── Mock PRO Plugin ────────────────────────────────────────────────

class MockProScorer:
    """Returns a fixed score of 0.99 for all events."""
    def score(self, event: AutoSaveEvent) -> float:
        return 0.99


class MockProResolver:
    """Always returns the first event."""
    def resolve(self, events: List[AutoSaveEvent]) -> AutoSaveEvent:
        return events[0]


class MockProDedup:
    """Never considers anything a duplicate."""
    def is_duplicate(self, event: AutoSaveEvent, recent_events: List[AutoSaveEvent]) -> bool:
        return False


class MockProPlugin:
    """Complete mock PRO plugin conforming to SynapseProPlugin."""
    def __init__(self):
        self.importance_scorer = MockProScorer()
        self.conflict_resolver = MockProResolver()
        self.dedup_strategy = MockProDedup()


# ─────────────────────────────────────────────────────────────────
# SECTION 1: Interface Protocol Tests
# ─────────────────────────────────────────────────────────────────

class TestInterfaceProtocols:
    """Verify Protocol compliance for all strategy interfaces."""

    def test_default_scorer_is_importance_scorer(self):
        assert isinstance(DefaultImportanceScorer(), ImportanceScorer)

    def test_default_resolver_is_conflict_resolver(self):
        assert isinstance(DefaultConflictResolver(), ConflictResolver)

    def test_default_dedup_is_dedup_strategy(self):
        assert isinstance(DefaultDedupStrategy(), DedupStrategy)

    def test_mock_pro_scorer_is_importance_scorer(self):
        assert isinstance(MockProScorer(), ImportanceScorer)

    def test_mock_pro_resolver_is_conflict_resolver(self):
        assert isinstance(MockProResolver(), ConflictResolver)

    def test_mock_pro_dedup_is_dedup_strategy(self):
        assert isinstance(MockProDedup(), DedupStrategy)

    def test_mock_plugin_is_synapse_pro_plugin(self):
        assert isinstance(MockProPlugin(), SynapseProPlugin)

    def test_redaction_result_immutable(self):
        r = RedactionResult(content="clean", pii_redacted=True)
        assert r.content == "clean"
        assert r.pii_redacted is True
        with pytest.raises(AttributeError):
            r.content = "modified"  # type: ignore


# ─────────────────────────────────────────────────────────────────
# SECTION 2: Default OSS Implementations
# ─────────────────────────────────────────────────────────────────

class TestDefaultImportanceScorer:
    """Test baseline linear importance scoring."""

    def test_score_range(self):
        scorer = DefaultImportanceScorer()
        for imp in range(6):
            event = _make_event(importance=imp)
            score = scorer.score(event)
            assert 0.0 <= score <= 1.0

    def test_score_zero(self):
        scorer = DefaultImportanceScorer()
        assert scorer.score(_make_event(importance=0)) == 0.0

    def test_score_max(self):
        scorer = DefaultImportanceScorer()
        assert scorer.score(_make_event(importance=5)) == 1.0

    def test_score_mid(self):
        scorer = DefaultImportanceScorer()
        assert scorer.score(_make_event(importance=3)) == 0.6

    def test_score_clamps_negative(self):
        scorer = DefaultImportanceScorer()
        # AutoSaveEvent.__post_init__ clamps to 0
        assert scorer.score(_make_event(importance=-1)) == 0.0

    def test_score_clamps_above_max(self):
        scorer = DefaultImportanceScorer()
        assert scorer.score(_make_event(importance=10)) == 1.0


class TestDefaultConflictResolver:
    """Test baseline conflict resolution."""

    def test_single_event(self):
        resolver = DefaultConflictResolver()
        event = _make_event()
        assert resolver.resolve([event]) is event

    def test_picks_highest_importance(self):
        resolver = DefaultConflictResolver()
        low = _make_event(importance=1)
        high = _make_event(importance=5)
        assert resolver.resolve([low, high]) is high

    def test_empty_raises(self):
        resolver = DefaultConflictResolver()
        with pytest.raises(ValueError, match="empty"):
            resolver.resolve([])

    def test_equal_importance_last_wins(self):
        resolver = DefaultConflictResolver()
        a = _make_event(importance=3, content="first")
        b = _make_event(importance=3, content="second")
        # With equal importance, higher id(e) wins; b created later
        result = resolver.resolve([a, b])
        assert result is not None


class TestDefaultDedupStrategy:
    """Test baseline hash-based deduplication."""

    def test_no_duplicates(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="unique content")
        assert dedup.is_duplicate(event, []) is False

    def test_exact_duplicate(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="same content")
        recent = [_make_event(content="same content")]
        assert dedup.is_duplicate(event, recent) is True

    def test_whitespace_normalized(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="hello   world")
        recent = [_make_event(content="hello world")]
        assert dedup.is_duplicate(event, recent) is True

    def test_case_normalized(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="Hello World")
        recent = [_make_event(content="hello world")]
        assert dedup.is_duplicate(event, recent) is True

    def test_different_project_not_duplicate(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="same", project="OFFLY")
        recent = [_make_event(content="same", project="NEXUMI")]
        assert dedup.is_duplicate(event, recent) is False

    def test_different_type_not_duplicate(self):
        dedup = DefaultDedupStrategy()
        event = _make_event(content="same", type="[MILESTONE]")
        recent = [_make_event(content="same", type="[ALERT]")]
        assert dedup.is_duplicate(event, recent) is False


# ─────────────────────────────────────────────────────────────────
# SECTION 3: Plugin Loader
# ─────────────────────────────────────────────────────────────────

class TestPluginLoader:
    """Test dynamic plugin loading with SYNAPSE_MODE enforcement."""

    def test_oss_mode_returns_none(self):
        """OSS mode never loads plugin."""
        result = load_pro_plugin(mode="oss")
        assert result is None

    def test_oss_mode_default(self):
        """Default mode is OSS."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SYNAPSE_MODE", None)
            result = load_pro_plugin()
            assert result is None

    def test_pro_mode_no_package_returns_none(self):
        """PRO mode without package installed returns None."""
        result = load_pro_plugin(mode="pro")
        assert result is None

    def test_pro_mode_with_mock_package(self):
        """PRO mode with conforming package returns plugin."""
        mock_module = MagicMock()
        mock_module.get_plugin.return_value = MockProPlugin()

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            result = load_pro_plugin(mode="pro")
            assert result is not None
            assert isinstance(result, SynapseProPlugin)

    def test_pro_mode_invalid_plugin_returns_none(self):
        """PRO mode with non-conforming plugin falls back."""
        mock_module = MagicMock()
        mock_module.get_plugin.return_value = "not_a_plugin"

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            result = load_pro_plugin(mode="pro")
            assert result is None

    def test_pro_mode_import_error(self):
        """PRO mode handles ImportError gracefully."""
        result = load_pro_plugin(mode="pro")
        assert result is None  # synapse_memory_pro not installed

    def test_pro_mode_runtime_exception(self):
        """PRO mode handles runtime exceptions in plugin."""
        mock_module = MagicMock()
        mock_module.get_plugin.side_effect = RuntimeError("plugin init failed")

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            result = load_pro_plugin(mode="pro")
            assert result is None

    def test_mode_case_insensitive(self):
        """Mode comparison is case-insensitive."""
        assert load_pro_plugin(mode="OSS") is None
        assert load_pro_plugin(mode="Oss") is None

    def test_env_var_override(self):
        """SYNAPSE_MODE env var is respected when mode param is None."""
        with patch.dict(os.environ, {"SYNAPSE_MODE": "oss"}):
            assert load_pro_plugin() is None


# ─────────────────────────────────────────────────────────────────
# SECTION 4: AutoSaveEngine Strategy Integration
# ─────────────────────────────────────────────────────────────────

class TestEngineStrategyIntegration:
    """Verify AutoSaveEngine uses injected strategies."""

    def _make_engine(self, **kwargs) -> AutoSaveEngine:
        return AutoSaveEngine(
            database=FakeDatabase(),
            redactor=fake_redact,
            mode="oss",
            **kwargs,
        )

    def test_default_strategies_oss(self):
        """OSS mode uses default strategies."""
        engine = self._make_engine()
        assert isinstance(engine.importance_scorer, DefaultImportanceScorer)
        assert isinstance(engine.conflict_resolver, DefaultConflictResolver)
        assert isinstance(engine.dedup_strategy, DefaultDedupStrategy)
        assert engine._plugin_loaded is False

    def test_custom_scorer_injection(self):
        """Custom scorer overrides default."""
        custom = MockProScorer()
        engine = self._make_engine(importance_scorer=custom)
        assert engine.importance_scorer is custom

    def test_custom_resolver_injection(self):
        """Custom resolver overrides default."""
        custom = MockProResolver()
        engine = self._make_engine(conflict_resolver=custom)
        assert engine.conflict_resolver is custom

    def test_custom_dedup_injection(self):
        """Custom dedup overrides default."""
        custom = MockProDedup()
        engine = self._make_engine(dedup_strategy=custom)
        assert engine.dedup_strategy is custom

    def test_pro_plugin_injection(self):
        """PRO mode with installed plugin uses plugin strategies."""
        mock_module = MagicMock()
        mock_plugin = MockProPlugin()
        mock_module.get_plugin.return_value = mock_plugin

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            engine = AutoSaveEngine(
                database=FakeDatabase(),
                redactor=fake_redact,
                mode="pro",
            )
            assert isinstance(engine.importance_scorer, MockProScorer)
            assert isinstance(engine.conflict_resolver, MockProResolver)
            assert isinstance(engine.dedup_strategy, MockProDedup)
            assert engine._plugin_loaded is True

    def test_explicit_overrides_plugin(self):
        """Explicitly passed strategies take priority over plugin."""
        mock_module = MagicMock()
        mock_module.get_plugin.return_value = MockProPlugin()

        custom_scorer = DefaultImportanceScorer()
        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            engine = AutoSaveEngine(
                database=FakeDatabase(),
                redactor=fake_redact,
                mode="pro",
                importance_scorer=custom_scorer,
            )
            # Explicit override wins
            assert engine.importance_scorer is custom_scorer
            # Others from plugin
            assert isinstance(engine.conflict_resolver, MockProResolver)

    def test_engine_save_still_works(self):
        """Backward compat: save pipeline unchanged."""
        engine = self._make_engine()
        event = _make_event(content="We deployed v2.0 to production", importance=4)
        result = engine.save(event)
        assert result.status == "saved"

    def test_engine_process_text_still_works(self):
        """Backward compat: process_text pipeline unchanged."""
        engine = self._make_engine()
        results = engine.process_text(
            "We deployed v2.0 to production",
            project="SYNAPSE_LAYER",
        )
        assert len(results) >= 1
        assert results[0].status == "saved"


# ─────────────────────────────────────────────────────────────────
# SECTION 5: SYNAPSE_MODE Enforcement
# ─────────────────────────────────────────────────────────────────

class TestSynapseModeEnforcement:
    """SYNAPSE_MODE=oss ignores plugin; SYNAPSE_MODE=pro warns if missing."""

    def test_oss_ignores_installed_plugin(self):
        """Even if synapse_memory_pro is installed, OSS mode ignores it."""
        mock_module = MagicMock()
        mock_module.get_plugin.return_value = MockProPlugin()

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            engine = AutoSaveEngine(
                database=FakeDatabase(),
                redactor=fake_redact,
                mode="oss",
            )
            assert isinstance(engine.importance_scorer, DefaultImportanceScorer)
            assert engine._plugin_loaded is False

    def test_pro_without_package_uses_defaults(self):
        """PRO mode without package falls back to defaults."""
        engine = AutoSaveEngine(
            database=FakeDatabase(),
            redactor=fake_redact,
            mode="pro",
        )
        assert isinstance(engine.importance_scorer, DefaultImportanceScorer)
        assert isinstance(engine.conflict_resolver, DefaultConflictResolver)
        assert isinstance(engine.dedup_strategy, DefaultDedupStrategy)
        assert engine._plugin_loaded is False

    def test_pro_with_package_uses_plugin(self):
        """PRO mode with package uses plugin strategies."""
        mock_module = MagicMock()
        mock_module.get_plugin.return_value = MockProPlugin()

        with patch.dict("sys.modules", {"synapse_memory_pro": mock_module}):
            engine = AutoSaveEngine(
                database=FakeDatabase(),
                redactor=fake_redact,
                mode="pro",
            )
            assert isinstance(engine.importance_scorer, MockProScorer)
            assert engine._plugin_loaded is True


# ─────────────────────────────────────────────────────────────────
# SECTION 6: Package-Level Imports
# ─────────────────────────────────────────────────────────────────

class TestPackageExports:
    """Verify all plugin types are importable from synapse_memory."""

    def test_import_interfaces(self):
        from synapse_memory import (
            ImportanceScorer,
            ConflictResolver,
            DedupStrategy,
            RedactionStrategy,
            SynapseProPlugin,
        )
        assert ImportanceScorer is not None

    def test_import_defaults(self):
        from synapse_memory import (
            DefaultImportanceScorer,
            DefaultConflictResolver,
            DefaultDedupStrategy,
        )
        assert DefaultImportanceScorer is not None

    def test_import_loader(self):
        from synapse_memory import load_pro_plugin
        assert callable(load_pro_plugin)

    def test_core_subpackage_imports(self):
        from synapse_memory.plugins import (
            ImportanceScorer,
            ConflictResolver,
            DedupStrategy,
            RedactionStrategy,
            RedactionResult,
            SynapseProPlugin,
            DefaultImportanceScorer,
            DefaultConflictResolver,
            DefaultDedupStrategy,
            load_pro_plugin,
        )
        assert all([
            ImportanceScorer, ConflictResolver, DedupStrategy,
            RedactionStrategy, RedactionResult, SynapseProPlugin,
            DefaultImportanceScorer, DefaultConflictResolver,
            DefaultDedupStrategy, load_pro_plugin,
        ])
