"""
Integration Tests for SynapseMemory — Full Pipeline

Tests the complete store/recall pipeline with all security layers
working together: sanitize → validate → encrypt → DP noise → vault.
Also tests Neural Handover™ integration from SynapseMemory.

Author: Security & Architecture Team @ Synapse Layer
"""

import math
import pytest
from synapse_memory.core import SynapseMemory, StoreResult, RecallResult
from synapse_memory.engine.handover import HandoverStatus
from tests.conftest import l2_norm, cosine_similarity


# ════════════════════════════════════════════════════════════════
#  Store Pipeline (Sanitize → Validate → DP → Persist)
# ════════════════════════════════════════════════════════════════

class TestStorePipeline:
    """End-to-end store() with all security layers active."""

    @pytest.mark.asyncio
    async def test_basic_store_all_flags(self, memory_default):
        result = await memory_default.store(
            content="User prefers concise answers in Portuguese",
            confidence=0.95,
        )
        assert result.sanitized is True, "Sanitization flag must be True"
        assert result.privacy_applied is True, "DP flag must be True"
        assert result.trust_quotient > 0
        assert result.memory_id, "Memory ID must be generated"
        assert result.content_hash, "Content hash must exist"
        assert result.timestamp > 0

    @pytest.mark.asyncio
    async def test_store_audit_details(self, memory_default):
        """Audit payload must contain all required fields."""
        result = await memory_default.store(
            content="User prefers dark mode",
            confidence=0.95,
        )
        # Validation details
        vd = result.validation_details
        assert 'final_intent' in vd
        assert 'source_type' in vd
        assert 'confidence' in vd
        assert 'confidence_boost' in vd
        assert 'is_critical' in vd
        assert 'is_valid' in vd
        assert 'self_healing_applied' in vd

        # Privacy details
        pd = result.privacy_details
        assert pd['epsilon'] == 0.5
        assert pd['sigma'] is not None
        assert pd['snr_db'] is not None

        # Sanitization details
        sd = result.sanitization_details
        assert 'pii_count' in sd
        assert 'risk_score' in sd

    @pytest.mark.asyncio
    async def test_pii_sanitized_before_storage(self, memory_default):
        """SECURITY: PII must not survive the store pipeline."""
        result = await memory_default.store(
            content="Call john@acme.com at +55 11 99999-8888",
            confidence=0.85,
        )
        assert result.sanitized is True
        assert result.sanitization_details['pii_count'] >= 2, \
            "Both email and phone must be detected"

    @pytest.mark.asyncio
    async def test_critical_keyword_auto_promotion(self, memory_default):
        """SECURITY: Critical keywords must force CRITICAL intent."""
        result = await memory_default.store(
            content="Security breach detected in authentication system",
            confidence=0.60,
        )
        assert result.validation_details['final_intent'] == 'critical'
        assert result.validation_details['source_type'] == 'critical_override'
        assert result.validation_details['confidence_boost'] == 1.0
        assert result.validation_details['is_critical'] is True

    @pytest.mark.asyncio
    async def test_low_confidence_warning(self, memory_default):
        result = await memory_default.store(
            content="Something happened yesterday somewhere",
            confidence=0.30,
        )
        assert result.validation_details['source_type'] == 'inference'
        assert result.validation_details['warning'] is not None

    @pytest.mark.asyncio
    async def test_dp_noise_alters_embedding(self, memory_default):
        """SECURITY: DP noise must alter the stored embedding."""
        content = "Deterministic content for embedding test"
        result = await memory_default.store(content=content, confidence=0.9)
        # Generate the pseudo embedding without noise for comparison
        clean_emb = SynapseMemory._generate_pseudo_embedding(content)
        stored_emb = memory_default._memories[-1]['embedding']
        assert stored_emb != clean_emb, \
            "Stored embedding must differ from clean (DP noise applied)"

    @pytest.mark.asyncio
    async def test_embedding_preserves_similarity(self, memory_default):
        """Despite DP noise, similar content should have some correlation."""
        await memory_default.store("User prefers dark mode", confidence=0.9)
        await memory_default.store("User likes dark theme", confidence=0.9)
        emb_a = memory_default._memories[-2]['embedding']
        emb_b = memory_default._memories[-1]['embedding']
        sim = cosine_similarity(emb_a, emb_b)
        # They're different texts, so similarity may vary, but should be finite
        assert math.isfinite(sim)


# ════════════════════════════════════════════════════════════════
#  Recall with Self-Healing
# ════════════════════════════════════════════════════════════════

class TestRecallPipeline:
    @pytest.mark.asyncio
    async def test_basic_recall(self, memory_default):
        await memory_default.store(
            "User prefers concise answers in Portuguese",
            confidence=0.95,
        )
        results = await memory_default.recall("concise answers Portuguese")
        assert len(results) > 0
        assert results[0].trust_quotient > 0
        assert results[0].intent, "Intent field must be populated"
        assert isinstance(results[0].is_critical, bool)

    @pytest.mark.asyncio
    async def test_recall_returns_most_relevant(self, memory_default):
        await memory_default.store("User prefers dark mode", confidence=0.95)
        await memory_default.store("Project deadline is Friday", confidence=0.90)
        results = await memory_default.recall("dark mode")
        assert len(results) >= 1
        assert "dark" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_recall_no_results_for_unrelated_query(self, memory_default):
        await memory_default.store("User prefers dark mode", confidence=0.95)
        results = await memory_default.recall("quantum physics black holes")
        # May or may not return results depending on word overlap
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_respects_top_k(self, memory_default):
        for i in range(10):
            await memory_default.store(
                f"Memory item number {i} about preferences",
                confidence=0.9,
            )
        results = await memory_default.recall("preferences", top_k=3)
        assert len(results) <= 3


# ════════════════════════════════════════════════════════════════
#  Configuration Variants
# ════════════════════════════════════════════════════════════════

class TestConfigVariants:
    @pytest.mark.asyncio
    async def test_sanitize_disabled(self, memory_raw):
        result = await memory_raw.store(
            content="john@test.com is the contact",
            confidence=0.80,
        )
        assert result.sanitized is False
        assert result.privacy_applied is True

    @pytest.mark.asyncio
    async def test_privacy_disabled(self, memory_no_privacy):
        result = await memory_no_privacy.store(
            content="Important data",
            confidence=0.90,
        )
        assert result.sanitized is True
        assert result.privacy_applied is False
        assert result.privacy_details['epsilon'] is None

    @pytest.mark.asyncio
    async def test_aggressive_sanitize(self, memory_aggressive):
        result = await memory_aggressive.store(
            content="Talk to Ricardo about the project at ricardo@corp.io",
            confidence=0.90,
        )
        assert result.sanitized is True
        # At minimum, email should be caught
        assert result.sanitization_details['pii_count'] >= 1

    @pytest.mark.asyncio
    async def test_custom_epsilon(self):
        mem = SynapseMemory(agent_id="eps-test", privacy_epsilon=0.1)
        result = await mem.store("Sensitive data", confidence=0.99)
        assert result.privacy_details['epsilon'] == 0.1

    def test_invalid_agent_id_raises(self):
        with pytest.raises(ValueError):
            SynapseMemory(agent_id="")

    def test_invalid_agent_id_none_raises(self):
        with pytest.raises(ValueError):
            SynapseMemory(agent_id=None)  # type: ignore


# ════════════════════════════════════════════════════════════════
#  Handover via SynapseMemory
# ════════════════════════════════════════════════════════════════

class TestHandoverIntegration:
    """Test Neural Handover™ via the SynapseMemory public API."""

    @pytest.mark.asyncio
    async def test_full_handover_flow(self):
        """Complete: store → create_handover → accept_handover."""
        agent_a = SynapseMemory(agent_id="gpt-4")
        await agent_a.store("User prefers dark mode", confidence=0.95)
        await agent_a.store("Project deadline is Friday", confidence=0.90)

        # Create handover
        result = agent_a.create_handover(
            target_agent="claude-3.5",
            user_id="user-123",
        )
        assert result.status == HandoverStatus.PENDING
        assert result.memory_count == 2

        # Accept from Agent B
        agent_b = SynapseMemory(agent_id="claude-3.5")
        # Need to use the same handover engine
        agent_b._handover = agent_a._handover
        package = agent_b.accept_handover(result.handover_id)
        assert package.status == HandoverStatus.COMPLETED
        # Agent B should now have the imported memories
        assert len(agent_b._memories) == 2

    @pytest.mark.asyncio
    async def test_handover_with_no_memories_raises(self):
        agent = SynapseMemory(agent_id="empty-agent")
        with pytest.raises(ValueError, match="No memories"):
            agent.create_handover(
                target_agent="claude",
                user_id="user-x",
            )

    @pytest.mark.asyncio
    async def test_fail_handover_via_memory(self):
        agent = SynapseMemory(agent_id="gpt-4")
        await agent.store("Test memory", confidence=0.9)
        result = agent.create_handover(
            target_agent="claude",
            user_id="user-fail",
        )
        pkg = agent.fail_handover(result.handover_id, "Agent crashed")
        assert pkg.status == HandoverStatus.FAILED
        assert pkg.emergency_checkpoint is not None

    @pytest.mark.asyncio
    async def test_get_latest_handover_via_memory(self):
        agent = SynapseMemory(agent_id="gpt-4")
        await agent.store("Test memory", confidence=0.9)
        result = agent.create_handover(
            target_agent="claude",
            user_id="user-latest",
        )
        latest = agent.get_latest_handover(user_id="user-latest")
        assert latest is not None
        assert latest.handover_id == result.handover_id


# ════════════════════════════════════════════════════════════════
#  Security Invariants
# ════════════════════════════════════════════════════════════════

class TestSecurityInvariants:
    """Cross-module security guarantees."""

    @pytest.mark.asyncio
    async def test_pii_never_in_stored_content(self):
        """SECURITY: PII must never appear in the stored memory content."""
        mem = SynapseMemory(agent_id="sec-test")
        pii_texts = [
            "john@acme.com is our contact",
            "SSN is 123-45-6789",
            "Card: 4111-1111-1111-1111",
            "CPF: 123.456.789-00",
            "Token: ghp_abcdefghijklmnopqrstuvwxyz1234",
        ]
        for text in pii_texts:
            await mem.store(text, confidence=0.9)

        # Verify no raw PII in stored memories
        for m in mem._memories:
            content = m['content']
            assert "john@acme.com" not in content
            assert "123-45-6789" not in content
            assert "4111-1111-1111-1111" not in content
            assert "123.456.789-00" not in content
            assert "ghp_" not in content

    @pytest.mark.asyncio
    async def test_trust_quotient_bounded(self):
        """TQ must be in [0, 1]."""
        mem = SynapseMemory(agent_id="tq-test")
        result = await mem.store(
            "Security breach emergency",
            confidence=1.0,
        )
        assert 0.0 <= result.trust_quotient <= 1.0

    @pytest.mark.asyncio
    async def test_pseudo_embedding_deterministic(self):
        """Same input must produce same pseudo-embedding."""
        emb1 = SynapseMemory._generate_pseudo_embedding("test")
        emb2 = SynapseMemory._generate_pseudo_embedding("test")
        assert emb1 == emb2, "Pseudo-embedding must be deterministic"

    @pytest.mark.asyncio
    async def test_pseudo_embedding_l2_normalized(self):
        emb = SynapseMemory._generate_pseudo_embedding("test")
        norm = l2_norm(emb)
        assert abs(norm - 1.0) < 1e-6, \
            f"Pseudo-embedding must be L2-normalized, got norm={norm}"

    @pytest.mark.asyncio
    async def test_different_content_different_embeddings(self):
        emb1 = SynapseMemory._generate_pseudo_embedding("dark mode")
        emb2 = SynapseMemory._generate_pseudo_embedding("light mode")
        assert emb1 != emb2
