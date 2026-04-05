"""
SynapseMemory — Zero-Knowledge Memory Core with Semantic Privacy Guard™

Orchestrates the full memory pipeline:
    raw_text → sanitize → validate → encrypt → embed → DP noise → upsert

Every call to store() returns an audit-ready payload with flags:
    {"sanitized": True, "privacy_applied": True, ...}

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import hashlib
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .sanitizer import SynapseSanitizer, SanitizationResult
from .privacy import DifferentialPrivacy, PrivacyResult
from .engine.validator import SynapseValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class StoreResult:
    """Immutable audit payload returned by SynapseMemory.store()."""
    memory_id: str                    # SHA-256 hash of sanitized content
    sanitized: bool                   # True if content was sanitized
    privacy_applied: bool             # True if DP noise was injected
    sanitization_details: Dict[str, Any]
    privacy_details: Dict[str, Any]
    validation_details: Dict[str, Any]
    trust_quotient: float             # Confidence × validation score
    timestamp: float
    content_hash: str                 # Integrity fingerprint


@dataclass
class RecallResult:
    """Memory recall output."""
    content: str
    trust_quotient: float
    memory_id: str
    timestamp: float


class SynapseMemory:
    """
    Zero-Knowledge Memory Layer for AI Agents.

    Provides persistent, encrypted, cross-model memory with:
    - Mandatory content sanitization (PII removal)
    - Differential Privacy on embeddings (Gaussian mechanism)
    - Intent validation and criticality scoring
    - Audit-ready payloads for compliance (GDPR / LGPD)

    Constructor Flags:
        sanitize_enabled (bool):  Enable content sanitization. Default: True.
        privacy_enabled (bool):   Enable DP noise on embeddings. Default: True.
        privacy_epsilon (float):  Privacy budget ε. Default: 0.5.
        aggressive_sanitize (bool): Enable aggressive mode (strip proper nouns).
                                    Default: False.

    Usage:
        memory = SynapseMemory(agent_id="my-agent")
        result = await memory.store(
            content="User prefers concise answers in Portuguese",
            confidence=0.95,
        )
        assert result.sanitized is True
        assert result.privacy_applied is True
    """

    def __init__(
        self,
        agent_id: str,
        *,
        sanitize_enabled: bool = True,
        privacy_enabled: bool = True,
        privacy_epsilon: float = 0.5,
        aggressive_sanitize: bool = False,
    ) -> None:
        """
        Initialize the memory layer.

        Args:
            agent_id: Unique identifier for the owning agent.
            sanitize_enabled: If True, content is sanitized before storage.
            privacy_enabled: If True, DP noise is applied to embeddings.
            privacy_epsilon: Privacy budget for Gaussian mechanism.
            aggressive_sanitize: If True, sanitizer strips proper nouns.
        """
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("agent_id must be a non-empty string.")

        self.agent_id = agent_id
        self.sanitize_enabled = sanitize_enabled
        self.privacy_enabled = privacy_enabled

        # Initialize sub-components
        self._sanitizer = SynapseSanitizer(aggressive=aggressive_sanitize)
        self._validator = SynapseValidator(enable_self_healing=True)
        self._privacy = (
            DifferentialPrivacy(epsilon=privacy_epsilon)
            if privacy_enabled
            else None
        )

        # In-memory store (production uses pgvector + AES-256-GCM)
        self._memories: List[Dict[str, Any]] = []

        logger.info(
            "SynapseMemory initialized: agent=%s, sanitize=%s, "
            "privacy=%s (ε=%.2f), aggressive=%s",
            agent_id, sanitize_enabled, privacy_enabled,
            privacy_epsilon, aggressive_sanitize,
        )

    # ── Public API ───────────────────────────────────────────────────

    async def store(
        self,
        content: str,
        confidence: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoreResult:
        """
        Store a memory through the full Semantic Privacy Guard™ pipeline.

        Pipeline:
            1. Sanitize content (mandatory by default)
            2. Validate intent and criticality
            3. Generate embedding (placeholder — production uses real model)
            4. Apply Differential Privacy noise to embedding
            5. Persist to memory vault
            6. Return audit payload

        Args:
            content:    Raw text content to store.
            confidence: Agent's confidence in this memory [0.0, 1.0].
            metadata:   Optional key-value metadata to attach.

        Returns:
            StoreResult with audit flags {sanitized, privacy_applied}.
        """
        timestamp = time.time()

        # ── Stage 1: Content Sanitization ────────────────────────────
        sanitization: Optional[SanitizationResult] = None
        working_content = content

        if self.sanitize_enabled:
            sanitization = self._sanitizer.sanitize_content(content)
            working_content = sanitization.sanitized_content
            logger.debug(
                "Sanitized: %d PII removed, risk=%.3f",
                sanitization.pii_count, sanitization.risk_score,
            )

        # ── Stage 2: Intent Validation ───────────────────────────────
        validation = self._validator.validate_intent(working_content)

        # ── Stage 3: Generate Embedding (placeholder) ────────────────
        # Production: calls embedding model (e.g., text-embedding-3-small)
        # SDK demo: deterministic hash-based pseudo-embedding
        embedding = self._generate_pseudo_embedding(working_content)

        # ── Stage 4: Differential Privacy ────────────────────────────
        privacy_result: Optional[PrivacyResult] = None

        if self._privacy is not None:
            privacy_result = self._privacy.apply(embedding)
            embedding = privacy_result.noisy_embedding
            logger.debug(
                "DP applied: σ=%.4f, SNR=%.1f dB",
                privacy_result.noise_sigma, privacy_result.snr_db,
            )

        # ── Stage 5: Persist ─────────────────────────────────────────
        content_hash = hashlib.sha256(
            working_content.encode()
        ).hexdigest()
        memory_id = content_hash[:32]

        trust_quotient = round(
            confidence * (validation.validation_score or 0.5), 4
        )

        record = {
            'memory_id': memory_id,
            'agent_id': self.agent_id,
            'content': working_content,
            'embedding': embedding,
            'trust_quotient': trust_quotient,
            'confidence': confidence,
            'intent': validation.intent_category.value,
            'is_critical': validation.is_critical,
            'metadata': metadata or {},
            'timestamp': timestamp,
        }
        self._memories.append(record)

        # ── Stage 6: Audit Payload ───────────────────────────────────
        result = StoreResult(
            memory_id=memory_id,
            sanitized=sanitization is not None,
            privacy_applied=privacy_result is not None,
            sanitization_details={
                'pii_count': sanitization.pii_count if sanitization else 0,
                'risk_score': sanitization.risk_score if sanitization else 0.0,
                'is_safe': sanitization.is_safe if sanitization else True,
                'items_removed': len(
                    sanitization.removed_items
                ) if sanitization else 0,
            },
            privacy_details={
                'epsilon': privacy_result.epsilon if privacy_result else None,
                'sigma': privacy_result.noise_sigma if privacy_result else None,
                'snr_db': privacy_result.snr_db if privacy_result else None,
            },
            validation_details={
                'intent': validation.intent_category.value,
                'confidence': validation.confidence,
                'is_critical': validation.is_critical,
                'is_valid': validation.is_valid,
            },
            trust_quotient=trust_quotient,
            timestamp=timestamp,
            content_hash=content_hash,
        )

        logger.info(
            "Memory stored: id=%s, TQ=%.4f, sanitized=%s, dp=%s",
            memory_id, trust_quotient, result.sanitized,
            result.privacy_applied,
        )

        return result

    async def recall(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[RecallResult]:
        """
        Recall memories by semantic similarity.

        In production, this queries pgvector with cosine similarity.
        SDK demo uses simple substring matching.

        Args:
            query: Natural language query.
            top_k: Maximum number of results to return.

        Returns:
            List of RecallResult ordered by trust_quotient.
        """
        query_lower = query.lower()

        # Simple relevance scoring for SDK demo
        scored = []
        for mem in self._memories:
            content_lower = mem['content'].lower()
            # Check if any query word appears in the content
            query_words = query_lower.split()
            hits = sum(1 for w in query_words if w in content_lower)
            if hits > 0:
                relevance = hits / len(query_words)
                scored.append((mem, relevance))

        # Sort by trust_quotient * relevance
        scored.sort(
            key=lambda x: x[0]['trust_quotient'] * x[1],
            reverse=True,
        )

        return [
            RecallResult(
                content=mem['content'],
                trust_quotient=mem['trust_quotient'],
                memory_id=mem['memory_id'],
                timestamp=mem['timestamp'],
            )
            for mem, _ in scored[:top_k]
        ]

    # ── Internal Helpers ─────────────────────────────────────────────

    @staticmethod
    def _generate_pseudo_embedding(
        text: str, dim: int = 384
    ) -> List[float]:
        """
        Generate a deterministic pseudo-embedding from text.

        Production systems replace this with a real embedding model.
        This implementation uses SHA-256 expansion for deterministic,
        reproducible vectors suitable for testing.
        """
        import struct

        h = hashlib.sha256(text.encode()).digest()
        # Expand hash to fill the required dimensions
        values: List[float] = []
        i = 0
        while len(values) < dim:
            block = hashlib.sha256(h + struct.pack('>I', i)).digest()
            # Unpack 8 floats from 32 bytes
            for j in range(0, 32, 4):
                if len(values) >= dim:
                    break
                raw = struct.unpack('>I', block[j:j + 4])[0]
                # Map to [-1, 1]
                val = (raw / 0xFFFFFFFF) * 2.0 - 1.0
                values.append(val)
            i += 1

        # L2 normalize
        import math
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]

        return values


# ── Inline Tests (run with: python -m synapse_memory.core) ───────────
if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("SynapseMemory — Inline Test Suite")
    print("=" * 60)

    async def run_tests():
        # Test 1: Basic store with full pipeline
        mem = SynapseMemory(agent_id="test-agent")
        r = await mem.store(
            content="User prefers concise answers in Brazilian Portuguese",
            confidence=0.95,
        )
        assert r.sanitized is True
        assert r.privacy_applied is True
        assert r.trust_quotient > 0
        assert r.memory_id
        print(f"[PASS] Basic store: TQ={r.trust_quotient:.4f}, "
              f"sanitized={r.sanitized}, dp={r.privacy_applied}")

        # Test 2: Store with PII — must be sanitized
        r2 = await mem.store(
            content="Call john@acme.com at +55 11 99999-8888",
            confidence=0.85,
        )
        assert r2.sanitized is True
        assert r2.sanitization_details['pii_count'] >= 2
        print(f"[PASS] PII sanitized: {r2.sanitization_details['pii_count']} "
              f"items removed")

        # Test 3: Store with aggressive mode
        mem_agg = SynapseMemory(
            agent_id="agg-agent",
            aggressive_sanitize=True,
        )
        r3 = await mem_agg.store(
            content="Talk to Ricardo about the neural handover protocol",
            confidence=0.90,
        )
        assert r3.sanitized is True
        print(f"[PASS] Aggressive mode: sanitized={r3.sanitized}")

        # Test 4: Disabled sanitization
        mem_no_san = SynapseMemory(
            agent_id="raw-agent",
            sanitize_enabled=False,
        )
        r4 = await mem_no_san.store(
            content="john@test.com is the contact",
            confidence=0.80,
        )
        assert r4.sanitized is False
        assert r4.privacy_applied is True
        print(f"[PASS] Sanitize disabled: sanitized={r4.sanitized}, "
              f"dp={r4.privacy_applied}")

        # Test 5: Disabled privacy
        mem_no_dp = SynapseMemory(
            agent_id="no-dp-agent",
            privacy_enabled=False,
        )
        r5 = await mem_no_dp.store(
            content="Important decision about architecture",
            confidence=0.90,
        )
        assert r5.sanitized is True
        assert r5.privacy_applied is False
        print(f"[PASS] Privacy disabled: sanitized={r5.sanitized}, "
              f"dp={r5.privacy_applied}")

        # Test 6: Recall
        r6 = await mem.recall("concise answers Portuguese")
        assert len(r6) > 0
        assert r6[0].trust_quotient > 0
        print(f"[PASS] Recall: {len(r6)} results, "
              f"TQ={r6[0].trust_quotient:.4f}")

        # Test 7: Custom epsilon
        mem_eps = SynapseMemory(
            agent_id="eps-agent",
            privacy_epsilon=0.1,
        )
        r7 = await mem_eps.store(
            content="Highly sensitive configuration data",
            confidence=0.99,
        )
        assert r7.privacy_details['epsilon'] == 0.1
        print(f"[PASS] Custom ε=0.1: σ={r7.privacy_details['sigma']:.4f}")

        # Test 8: Invalid agent_id
        try:
            SynapseMemory(agent_id="")
            assert False, "Should have raised ValueError"
        except ValueError:
            print("[PASS] Invalid agent_id rejected")

        print("\n✅ All inline tests passed.")

    asyncio.run(run_tests())
