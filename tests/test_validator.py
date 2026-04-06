"""
Tests for SynapseValidator — Intelligent Intent Validation™

Covers intent classification, confidence gate, critical keyword
auto-promotion, self-healing, batch validation, and security cases.

Author: Security & Architecture Team @ Synapse Layer
"""

import pytest
from synapse_memory.engine.validator import (
    SynapseValidator,
    ValidationResult,
    SelfHealingResult,
    IntentCategory,
)


class TestIntentClassification:
    """Each of the 6 canonical categories must be correctly identified."""

    @pytest.mark.parametrize("content,expected", [
        ("User prefers dark mode and concise answers", IntentCategory.PREFERENCE),
        ("I enjoy minimal UI and love clean design", IntentCategory.PREFERENCE),
    ])
    def test_preference(self, validator, content, expected):
        r = validator.validate_intent(content, agent_confidence=0.95)
        assert r.final_intent == expected, \
            f"Expected {expected.value}, got {r.final_intent.value}"

    @pytest.mark.parametrize("content,expected", [
        ("Scientific research confirmed the theory is true", IntentCategory.FACT),
        ("The data shows evidence of a proven principle", IntentCategory.FACT),
    ])
    def test_fact(self, validator, content, expected):
        r = validator.validate_intent(content, agent_confidence=0.95)
        assert r.final_intent == expected

    def test_procedural(self, validator):
        r = validator.validate_intent(
            "Follow these steps: first install, then configure the pipeline",
            agent_confidence=0.92,
        )
        assert r.final_intent == IntentCategory.PROCEDURAL

    def test_bio(self, validator):
        r = validator.validate_intent(
            "My name is Ismael, born in Brazil, working in AI",
            agent_confidence=0.93,
        )
        assert r.final_intent == IntentCategory.BIO

    def test_ephemeral(self, validator):
        r = validator.validate_intent(
            "I have a meeting today at 3pm, remind me now",
            agent_confidence=0.88,
        )
        assert r.final_intent == IntentCategory.EPHEMERAL

    def test_critical_via_category_keywords(self, validator):
        r = validator.validate_intent(
            "Password reset for the encryption key and security token",
            agent_confidence=0.92,
        )
        assert r.final_intent == IntentCategory.CRITICAL


class TestConfidenceGate:
    """The confidence gate at 0.85 determines source_type."""

    def test_high_confidence_validated(self, validator):
        r = validator.validate_intent(
            "User prefers dark mode style",
            agent_confidence=0.95,
        )
        assert r.source_type == "validated"
        assert r.warning is None

    def test_low_confidence_inference(self, validator):
        r = validator.validate_intent(
            "something vague happened",
            agent_confidence=0.3,
        )
        assert r.source_type == "inference"
        assert r.warning is not None, \
            "Low confidence must include a warning string"

    def test_confidence_merge_formula(self, validator):
        """Merged = 0.4*heuristic + 0.6*agent. High agent conf + keywords = validated."""
        r = validator.validate_intent(
            "User prefers dark mode and concise answers",
            agent_confidence=1.0,
        )
        assert r.confidence >= 0.85
        assert r.source_type == "validated"


class TestCriticalKeywords:
    """SECURITY: Critical keywords must force CRITICAL regardless of confidence."""

    @pytest.mark.parametrize("keyword", [
        "emergency", "breach", "attack", "ransomware",
        "warrant", "exploit", "vulnerability", "fraud",
        "urgent", "critical", "danger", "alert",
        "hack", "abuse", "subpoena", "immediate",
        "severe", "fatal", "lethal",
    ])
    def test_critical_keyword_forces_critical(self, validator, keyword):
        """Each of the 19 critical keywords must auto-promote."""
        r = validator.validate_intent(
            f"There is a {keyword} situation happening",
            agent_confidence=0.1,  # Even low confidence
        )
        assert r.final_intent == IntentCategory.CRITICAL, \
            f"Keyword '{keyword}' must force CRITICAL, got {r.final_intent.value}"
        assert r.source_type == "critical_override"
        assert r.confidence_boost == 1.0
        assert r.is_critical is True
        assert keyword in r.critical_keywords

    def test_critical_override_with_zero_confidence(self, validator):
        """SECURITY: Even confidence=0.0 must not prevent critical override."""
        r = validator.validate_intent(
            "Security breach detected",
            agent_confidence=0.0,
        )
        assert r.final_intent == IntentCategory.CRITICAL
        assert r.confidence == 1.0


class TestSelfHealing:
    """Self-healing resolves category conflicts between proximate memories."""

    def test_healing_on_conflicting_categories(self, validator):
        result = validator.heal_conflicts(
            memory_a={'content': 'User prefers concise answers', 'intent': 'preference'},
            memory_b={'content': 'User likes short responses in English', 'intent': 'fact'},
            similarity=0.92,
        )
        assert result is not None, "Should heal when similarity >= 0.85"
        assert result.reclassified is True
        assert isinstance(result.new_category, IntentCategory)

    def test_no_healing_below_threshold(self, validator):
        result = validator.heal_conflicts(
            memory_a={'content': 'Payment info', 'intent': 'critical'},
            memory_b={'content': 'Favorite color', 'intent': 'preference'},
            similarity=0.30,
        )
        assert result is None, "No healing when similarity < 0.85"

    def test_no_healing_same_category(self, validator):
        result = validator.heal_conflicts(
            memory_a={'content': 'Prefers dark mode', 'intent': 'preference'},
            memory_b={'content': 'Likes minimalism', 'intent': 'preference'},
            similarity=0.95,
        )
        assert result is None, "No healing needed when categories match"

    def test_healing_disabled(self, validator_no_healing):
        result = validator_no_healing.heal_conflicts(
            memory_a={'content': 'test', 'intent': 'preference'},
            memory_b={'content': 'test', 'intent': 'fact'},
            similarity=0.95,
        )
        assert result is None, "Healing disabled should return None"

    def test_healing_result_has_evidence(self, validator):
        result = validator.heal_conflicts(
            memory_a={'content': 'User prefers concise answers', 'intent': 'preference'},
            memory_b={'content': 'User enjoys short responses', 'intent': 'bio'},
            similarity=0.90,
        )
        assert result is not None
        assert 'memory_a_scores' in result.evidence_scores
        assert 'memory_b_scores' in result.evidence_scores


class TestValidatorEdgeCases:
    def test_empty_input(self, validator):
        r = validator.validate_intent("")
        assert r.final_intent == IntentCategory.INVALID
        assert r.is_valid is False

    def test_none_input(self, validator):
        r = validator.validate_intent(None)  # type: ignore
        assert r.final_intent == IntentCategory.INVALID

    def test_backward_compat_alias(self, validator):
        """intent_category property must alias final_intent."""
        r = validator.validate_intent(
            "User prefers dark mode", agent_confidence=0.95
        )
        assert r.intent_category == r.final_intent

    def test_batch_validate(self, validator):
        results = validator.batch_validate([
            "User prefers dark mode",
            "There was a security breach",
            "Follow these steps to deploy",
        ], agent_confidence=0.90)
        assert len(results) == 3
        assert results[0].final_intent == IntentCategory.PREFERENCE
        assert results[1].final_intent == IntentCategory.CRITICAL
        assert results[2].final_intent == IntentCategory.PROCEDURAL

    def test_validation_result_is_frozen(self, validator):
        r = validator.validate_intent("test content", agent_confidence=0.9)
        with pytest.raises(AttributeError):
            r.final_intent = IntentCategory.BIO  # type: ignore
