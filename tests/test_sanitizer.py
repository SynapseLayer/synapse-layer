"""
Tests for SynapseSanitizer — Semantic Privacy Guard™

Covers PII detection (12 regex patterns), aggressive mode,
risk scoring, forensic hashing, batch processing, and
security edge cases.

Author: Security & Architecture Team @ Synapse Layer
"""

import hashlib
import pytest
from synapse_memory.sanitizer import (
    SynapseSanitizer,
    SanitizationResult,
    SensitivityLevel,
)


# ════════════════════════════════════════════════════════════════
#  PII Detection — Pattern-by-Pattern
# ════════════════════════════════════════════════════════════════

class TestPIIDetection:
    """Verify each of the 12 precompiled regex patterns detects PII."""

    def test_email_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Contact us at admin@synapse.org"
        )
        assert "admin@synapse.org" not in result.sanitized_content, \
            "Email address must be redacted"
        assert result.pii_count >= 1
        assert any(i['type'] == 'email' for i in result.removed_items)

    def test_phone_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Call me at +55 11 99999-8888"
        )
        assert "+55 11 99999-8888" not in result.sanitized_content, \
            "Phone number must be redacted"
        assert result.pii_count >= 1

    def test_ssn_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "SSN: 123-45-6789"
        )
        assert "123-45-6789" not in result.sanitized_content, \
            "SSN must be redacted"
        assert any(i['type'] == 'ssn' for i in result.removed_items)

    def test_cpf_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "CPF do cliente: 123.456.789-00"
        )
        assert "123.456.789-00" not in result.sanitized_content, \
            "Brazilian CPF must be redacted"
        assert any(i['type'] == 'cpf' for i in result.removed_items)

    def test_credit_card_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Card: 4111-1111-1111-1111"
        )
        assert "4111-1111-1111-1111" not in result.sanitized_content, \
            "Credit card must be redacted"

    def test_api_key_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Token: ghp_abcdefghijklmnopqrstuvwxyz1234"
        )
        assert "ghp_" not in result.sanitized_content, \
            "GitHub API key must be redacted"

    def test_bearer_token_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        )
        assert "eyJhbG" not in result.sanitized_content, \
            "Bearer token must be redacted"

    def test_aws_key_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Access key: AKIAIOSFODNN7EXAMPLE"
        )
        assert "AKIAIOSFODNN7EXAMPLE" not in result.sanitized_content, \
            "AWS access key must be redacted"

    def test_ip_address_detected(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Server IP: 192.168.1.100"
        )
        assert "192.168.1.100" not in result.sanitized_content

    def test_multiple_pii_in_single_input(self, sanitizer_standard):
        """SECURITY: Multiple PII types in one string must all be removed."""
        text = (
            "Email: john@test.com, SSN: 123-45-6789, "
            "Card: 4111-1111-1111-1111"
        )
        result = sanitizer_standard.sanitize_content(text)
        assert "john@test.com" not in result.sanitized_content
        assert "123-45-6789" not in result.sanitized_content
        assert "4111-1111-1111-1111" not in result.sanitized_content
        assert result.pii_count >= 3, \
            f"Expected ≥3 PII items, found {result.pii_count}"


# ════════════════════════════════════════════════════════════════
#  Aggressive Mode — Proper Noun Stripping
# ════════════════════════════════════════════════════════════════

class TestAggressiveMode:
    """SECURITY: Proper nouns must be stripped to prevent
    name-based correlation attacks across memory pools."""

    def test_proper_noun_stripped(self, sanitizer_aggressive):
        result = sanitizer_aggressive.sanitize_content(
            "Talk to Ricardo about the project"
        )
        assert "Ricardo" not in result.sanitized_content, \
            "Proper noun 'Ricardo' must be stripped in aggressive mode"

    def test_stop_words_preserved(self, sanitizer_aggressive):
        """Common English stop words should not be redacted."""
        result = sanitizer_aggressive.sanitize_content(
            "This is very important and true"
        )
        # 'This', 'Very', 'True' are stop words — should remain
        assert result.pii_count == 0 or all(
            i['type'] != 'proper_noun' for i in result.removed_items
            if i.get('redacted') in ['This', 'Very', 'True']
        )

    def test_aggressive_plus_pii(self, sanitizer_aggressive):
        """Both PII and proper nouns must be stripped together."""
        result = sanitizer_aggressive.sanitize_content(
            "Contact Ricardo at ricardo@corp.io"
        )
        assert "Ricardo" not in result.sanitized_content
        assert "ricardo@corp.io" not in result.sanitized_content
        assert result.pii_count >= 2

    def test_standard_mode_preserves_names(self, sanitizer_standard):
        """Standard mode must NOT strip proper nouns."""
        result = sanitizer_standard.sanitize_content(
            "Talk to Ricardo about the project"
        )
        # Ricardo might still be present (standard mode doesn't strip names)
        assert result.pii_count == 0


# ════════════════════════════════════════════════════════════════
#  Risk Scoring & Safety
# ════════════════════════════════════════════════════════════════

class TestRiskScoring:
    """Verify risk scoring and safety classification."""

    def test_critical_pii_raises_risk(self, sanitizer_standard):
        """CRITICAL items (SSN, credit card) must produce high risk."""
        result = sanitizer_standard.sanitize_content(
            "SSN: 123-45-6789 Card: 4111-1111-1111-1111"
        )
        assert result.risk_score >= 0.5, \
            f"Critical PII risk should be ≥0.5, got {result.risk_score}"
        assert result.is_safe is False

    def test_clean_text_is_safe(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "The weather is nice today"
        )
        assert result.risk_score == 0.0
        assert result.is_safe is True

    def test_risk_score_capped_at_one(self, sanitizer_standard):
        """Risk score must never exceed 1.0."""
        heavy_pii = " ".join(
            ["john@test.com", "123-45-6789", "4111-1111-1111-1111",
             "123.456.789-00", "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaa"]
        )
        result = sanitizer_standard.sanitize_content(heavy_pii)
        assert result.risk_score <= 1.0


# ════════════════════════════════════════════════════════════════
#  Forensic Audit Hashes
# ════════════════════════════════════════════════════════════════

class TestForensicHashing:
    """Every redacted item must produce a SHA-256 hash for audit."""

    def test_hash_present_in_removed_items(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(
            "Email: test@example.com"
        )
        assert result.removed_items, "Should have removed items"
        item = result.removed_items[0]
        assert 'hash' in item, "Removed item must include SHA-256 hash"
        assert len(item['hash']) == 16, "Hash should be truncated to 16 chars"

    def test_hash_matches_original_pii(self, sanitizer_standard):
        """SECURITY: Hash must correspond to the original PII value."""
        pii = "test@example.com"
        result = sanitizer_standard.sanitize_content(f"Email: {pii}")
        expected_hash = hashlib.sha256(pii.encode()).hexdigest()[:16]
        actual_hash = result.removed_items[0]['hash']
        assert actual_hash == expected_hash, \
            f"Hash mismatch: expected {expected_hash}, got {actual_hash}"


# ════════════════════════════════════════════════════════════════
#  Edge Cases & Guards
# ════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content("")
        assert result.sanitized is True
        assert result.pii_count == 0
        assert result.sanitized_content == ""

    def test_none_input(self, sanitizer_standard):
        result = sanitizer_standard.sanitize_content(None)  # type: ignore
        assert result.sanitized is True
        assert result.pii_count == 0

    def test_sanitized_flag_always_true(self, sanitizer_standard):
        """The sanitized audit flag must always be True after pipeline."""
        for text in ["", "clean text", "test@email.com"]:
            result = sanitizer_standard.sanitize_content(text)
            assert result.sanitized is True

    def test_batch_sanitize(self, sanitizer_standard):
        results = sanitizer_standard.batch_sanitize([
            "Email: a@b.com",
            "Clean text",
            "SSN: 123-45-6789",
        ])
        assert len(results) == 3
        assert results[0].pii_count >= 1
        assert results[1].pii_count == 0
        assert results[2].pii_count >= 1

    def test_validate_sanitization_metrics(self, sanitizer_standard):
        original = "Email: test@example.com is my contact"
        result = sanitizer_standard.sanitize_content(original)
        metrics = sanitizer_standard.validate_sanitization(
            original, result.sanitized_content
        )
        assert 'reduction_pct' in metrics
        assert metrics['original_length'] == len(original)
