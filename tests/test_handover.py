"""
Tests for NeuralHandover™ — Persistence-First Handover Engine

Covers Status Ledger, JWT signing/verification, Emergency Checkpoint,
grace period, PII sanitization in handover, and security edge cases.

Author: Security & Architecture Team @ Synapse Layer
"""

import time
import pytest
from synapse_memory.engine.handover import (
    NeuralHandover,
    HandoverStatus,
    HandoverResult,
    HandoverPackage,
    HandoverToken,
)

SIGNING_KEY = "test-key-for-unit-tests-256-bit-min!"


class TestCreateHandover:
    """Verify handover creation with full pipeline."""

    def test_basic_creation(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="user-123",
            memories=sample_memories,
        )
        assert r.status == HandoverStatus.PENDING
        assert r.memory_count == 3
        assert r.sanitized is True
        assert r.validation_applied is True
        assert r.token_encoded, "JWT token must be non-empty"
        assert r.handover_id.startswith("ho_")

    def test_sanitization_in_handover(self, handover_engine):
        """SECURITY: PII in handover memories must be sanitized."""
        r = handover_engine.create_handover(
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="user-pii",
            memories=[{"content": "Contact john@acme.com about it", "confidence": 0.9}],
        )
        pkg = handover_engine.accept_handover(r.handover_id)
        assert "john@acme.com" not in pkg.context_data[0]['content'], \
            "PII must not survive the handover pipeline"
        assert pkg.context_data[0].get('pii_removed', 0) >= 1

    def test_intent_validation_in_handover(self, handover_engine):
        r = handover_engine.create_handover(
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="user-val",
            memories=[{"content": "Security breach in auth system", "confidence": 0.99}],
        )
        pkg = handover_engine.accept_handover(r.handover_id)
        assert pkg.context_data[0].get('intent') == 'critical'
        assert pkg.context_data[0].get('is_critical') is True


class TestAcceptHandover:
    """Verify accept flow and state transitions."""

    def test_accept_transitions_to_completed(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u1", memories=sample_memories,
        )
        pkg = handover_engine.accept_handover(r.handover_id, accepting_agent="claude-3.5")
        assert pkg.status == HandoverStatus.COMPLETED
        assert pkg.completed_at is not None
        assert len(pkg.context_data) == 3

    def test_wrong_agent_rejected(self, handover_engine, sample_memories):
        """SECURITY: Only the target agent can accept a handover."""
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u2", memories=sample_memories,
        )
        with pytest.raises(PermissionError):
            handover_engine.accept_handover(r.handover_id, accepting_agent="gemini-1.5")

    def test_nonexistent_handover_raises(self, handover_engine):
        with pytest.raises(KeyError):
            handover_engine.accept_handover("ho_nonexistent")


class TestFailHandover:
    """Verify fallback with Emergency Checkpoint."""

    def test_fail_creates_emergency_checkpoint(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="llama-3",
            user_id="u3", memories=sample_memories,
        )
        pkg = handover_engine.fail_handover(r.handover_id, reason="Agent crashed")
        assert pkg.status == HandoverStatus.FAILED
        assert pkg.emergency_checkpoint is not None, \
            "Emergency checkpoint must be created on failure"
        assert pkg.emergency_checkpoint['failure_reason'] == "Agent crashed"
        assert len(pkg.emergency_checkpoint['context_snapshot']) == 3
        assert pkg.error_reason == "Agent crashed"

    def test_checkpoint_preserves_all_metadata(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u4", memories=sample_memories,
        )
        pkg = handover_engine.fail_handover(r.handover_id, "network timeout")
        cp = pkg.emergency_checkpoint
        assert cp['origin_agent'] == 'gpt-4'
        assert cp['target_agent'] == 'claude-3.5'
        assert cp['user_id'] == 'u4'
        assert cp['memory_count'] == 3
        assert 'content_hash' in cp


class TestGracePeriod:
    """Verify TTL expiry and grace period behavior."""

    def test_grace_period_returns_summary(self, handover_engine, sample_memories):
        """When TTL expired but within grace, summary is returned."""
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-grace", memories=sample_memories,
        )
        # Manually expire the token (TTL expired 10s ago, within 15min grace)
        pkg = handover_engine._ledger[r.handover_id]
        expired_token = HandoverToken(
            token_id=r.handover_id,
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="u-grace",
            scope="full",
            issued_at=time.time() - 100,
            expires_at=time.time() - 10,
            signature=pkg.token.signature,
            encoded_token=pkg.token.encoded_token,
        )
        pkg.token = expired_token

        result = handover_engine.accept_handover(r.handover_id)
        assert result.status == HandoverStatus.EXPIRED
        assert result.grace_summary is not None, \
            "Grace period must generate summary"
        assert result.context_data == [], \
            "Raw data must be cleared during grace period"

    def test_fully_expired_raises_timeout(self, handover_engine, sample_memories):
        """Beyond grace period, TimeoutError is raised."""
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-expired", memories=sample_memories,
        )
        pkg = handover_engine._ledger[r.handover_id]
        # Expire beyond grace (2000s ago = well past 900s grace)
        expired_token = HandoverToken(
            token_id=r.handover_id,
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="u-expired",
            scope="full",
            issued_at=time.time() - 5000,
            expires_at=time.time() - 2000,
            signature=pkg.token.signature,
            encoded_token=pkg.token.encoded_token,
        )
        pkg.token = expired_token

        with pytest.raises(TimeoutError):
            handover_engine.accept_handover(r.handover_id)


class TestJWTTokens:
    """SECURITY: Verify JWT signing and verification."""

    def test_token_verification(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-jwt", memories=sample_memories,
        )
        decoded = handover_engine.verify_token_string(r.token_encoded)
        assert decoded['org'] == 'gpt-4'
        assert decoded['tgt'] == 'claude-3.5'
        assert decoded['uid'] == 'u-jwt'
        assert decoded['scp'] == 'full'

    def test_tampered_token_rejected(self, handover_engine, sample_memories):
        """SECURITY: Tampered tokens must be rejected."""
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-tamper", memories=sample_memories,
        )
        # Tamper with the token
        tampered = r.token_encoded[:-5] + "XXXXX"
        with pytest.raises((PermissionError, ValueError)):
            handover_engine.verify_token_string(tampered)

    def test_invalid_token_format(self, handover_engine):
        with pytest.raises(ValueError, match="3 parts"):
            handover_engine.verify_token_string("not.a.valid.jwt.token")


class TestGetLatestHandover:
    def test_get_latest(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-latest", memories=sample_memories,
        )
        latest = handover_engine.get_latest_handover(user_id="u-latest")
        assert latest is not None
        assert latest.handover_id == r.handover_id

    def test_nonexistent_user_returns_none(self, handover_engine):
        assert handover_engine.get_latest_handover(user_id="ghost") is None

    def test_status_filter(self, handover_engine, sample_memories):
        r = handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude-3.5",
            user_id="u-filter", memories=sample_memories,
        )
        handover_engine.accept_handover(r.handover_id)
        # Filter for PENDING should return None (it's COMPLETED now)
        assert handover_engine.get_latest_handover(
            user_id="u-filter", status_filter=HandoverStatus.PENDING
        ) is None
        # Filter for COMPLETED should return the handover
        result = handover_engine.get_latest_handover(
            user_id="u-filter", status_filter=HandoverStatus.COMPLETED
        )
        assert result is not None


class TestHandoverInputValidation:
    def test_same_agent_rejected(self, handover_engine):
        with pytest.raises(ValueError, match="must differ"):
            handover_engine.create_handover(
                origin_agent="gpt-4", target_agent="gpt-4",
                user_id="u", memories=[{"content": "test"}],
            )

    def test_empty_memories_rejected(self, handover_engine):
        with pytest.raises(ValueError, match="At least one"):
            handover_engine.create_handover(
                origin_agent="gpt-4", target_agent="claude",
                user_id="u", memories=[],
            )

    def test_missing_agent_ids(self, handover_engine):
        with pytest.raises(ValueError):
            handover_engine.create_handover(
                origin_agent="", target_agent="claude",
                user_id="u", memories=[{"content": "test"}],
            )

    def test_ledger_stats(self, handover_engine, sample_memories):
        handover_engine.create_handover(
            origin_agent="gpt-4", target_agent="claude",
            user_id="u-stats", memories=sample_memories,
        )
        stats = handover_engine.get_ledger_stats()
        assert stats['total_handovers'] >= 1
        assert stats['total_users'] >= 1
        assert 'pending' in stats['status_counts']
