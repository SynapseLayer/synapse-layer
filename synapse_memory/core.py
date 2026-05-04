"""
SynapseMemory — Persistent Memory Core with AES-256-GCM Encryption

Orchestrates the secure memory pipeline with built-in sanitization,
intent validation, differential privacy, and self-healing recall.

Every call to store() returns an audit-ready payload.
Enterprise tier extends with pluggable pipeline stages.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import hashlib
import math
import time
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from .sanitizer import SynapseSanitizer, SanitizationResult
from .privacy import DifferentialPrivacy, PrivacyResult
from .engine.validator import (
    SynapseValidator,
    ValidationResult,
    SelfHealingResult,
    IntentCategory,
)
from .engine.handover import (
    NeuralHandover,
    HandoverResult,
    HandoverPackage,
    HandoverStatus,
    HandoverToken,
)
from .backends.interface import StorageBackend

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
    """Memory recall output with optional self-healing metadata."""
    content: str
    trust_quotient: float
    memory_id: str
    timestamp: float
    intent: str                                          # Category value string
    is_critical: bool                                    # Criticality flag
    self_healing: Optional[SelfHealingResult] = None     # Set if reclassified


class SynapseMemory:
    """Persistent Memory Layer for AI Agents.

    Provides persistent, encrypted, cross-model memory with:
    - Mandatory content sanitization (PII removal)
    - Intelligent Intent Validation™ (two-step + self-healing)
    - Differential Privacy on embeddings (Gaussian mechanism)
    - Audit-ready payloads for compliance (GDPR / LGPD)

    Constructor Flags:
        sanitize_enabled (bool):  Enable content sanitization. Default: True.
        privacy_enabled (bool):   Enable DP noise on embeddings. Default: True.
        privacy_epsilon (float):  Privacy budget ε. Default: 0.5.
        aggressive_sanitize (bool): Enable aggressive mode (strip proper nouns).
                                    Default: False.

    Usage::

        memory = SynapseMemory(agent_id="my-agent")
        result = await memory.store(
            content="User prefers concise answers in Portuguese",
            confidence=0.95,
        )
        assert result.sanitized is True
        assert result.privacy_applied is True
        assert result.validation_details['source_type'] == 'validated'
    """

    def __init__(
        self,
        agent_id: str,
        *,
        sanitize_enabled: bool = True,
        privacy_enabled: bool = True,
        privacy_epsilon: float = 0.5,
        aggressive_sanitize: bool = False,
        backend: Optional[StorageBackend] = None,
    ) -> None:
        """Initialize the memory layer.

        Args:
            agent_id: Unique identifier for the owning agent.
            sanitize_enabled: If True, content is sanitized before storage.
            privacy_enabled: If True, DP noise is applied to embeddings.
            privacy_epsilon: Privacy budget for Gaussian mechanism.
            aggressive_sanitize: If True, sanitizer strips proper nouns.
            backend: Pluggable storage backend. If None, uses in-memory
                     (MemoryBackend). Pass SqliteBackend() for persistence.
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

        # Neural Handover™ engine
        self._handover = NeuralHandover(
            sanitize=sanitize_enabled,
            validate=True,
        )

        # Storage backend — pluggable persistence layer.
        # Default: MemoryBackend (in-memory, non-persistent).
        # Use SqliteBackend() for zero-config local persistence.
        if backend is not None:
            self._backend = backend
        else:
            from .backends.memory_backend import MemoryBackend
            self._backend = MemoryBackend()

        # Legacy in-memory list for backward compatibility with
        # integration adapters that access _memories directly.
        self._memories: List[Dict[str, Any]] = []

        logger.info(
            "SynapseMemory initialized: agent=%s, sanitize=%s, "
            "privacy=%s (ε=%.2f), aggressive=%s, backend=%s",
            agent_id, sanitize_enabled, privacy_enabled,
            privacy_epsilon, aggressive_sanitize,
            type(self._backend).__name__,
        )

    # ══ Public API ═══════════════════════════════════════════════════════

    async def store(
        self,
        content: str,
        confidence: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoreResult:
        """Store a memory through the full Cognitive Security™ pipeline.

        Pipeline:
            1. Sanitize content (mandatory by default)
            2. Validate intent (two-step: agent suggestion → Synapse validation)
            3. Generate embedding (placeholder — production uses real model)
            4. Apply Differential Privacy noise to embedding
            5. Persist to memory vault
            6. Return audit payload

        Args:
            content:    Raw text content to store.
            confidence: Agent's confidence in this memory [0.0, 1.0].
            metadata:   Optional key-value metadata to attach.

        Returns:
            StoreResult with audit flags {sanitized, privacy_applied, validation_details}.
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

        # ── Stage 2: Intelligent Intent Validation™ ─────────────────
        validation = self._validator.validate_intent(
            working_content,
            agent_confidence=confidence,
        )

        # ── Stage 3: Generate Embedding (placeholder) ───────────────
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

        # Trust Quotient — proprietary ranking signal (Enterprise extends
        # with multi-factor TQ including recency decay and agent reputation).
        trust_quotient = self._compute_tq(validation)

        record: Dict[str, Any] = {
            'memory_id': memory_id,
            'agent_id': self.agent_id,
            'content': working_content,
            'embedding': embedding,
            'trust_quotient': trust_quotient,
            'confidence': validation.confidence,
            'intent': validation.final_intent.value,
            'is_critical': validation.is_critical,
            'source_type': validation.source_type,
            'metadata': metadata or {},
            'timestamp': timestamp,
        }
        # Persist to backend
        self._backend.save(record)
        # Legacy list for backward compatibility with integrations
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
                'final_intent': validation.final_intent.value,
                'source_type': validation.source_type,
                'confidence': validation.confidence,
                'confidence_boost': validation.confidence_boost,
                'is_critical': validation.is_critical,
                'is_valid': validation.is_valid,
                'warning': validation.warning,
                'self_healing_applied': validation.self_healing_applied,
                'healing_notes': validation.healing_notes,
            },
            trust_quotient=trust_quotient,
            timestamp=timestamp,
            content_hash=content_hash,
        )

        logger.info(
            "Memory stored: id=%s, intent=%s, TQ=%.4f, source=%s, "
            "sanitized=%s, dp=%s",
            memory_id, validation.final_intent.value, trust_quotient,
            validation.source_type, result.sanitized, result.privacy_applied,
        )

        return result

    async def recall(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[RecallResult]:
        """Recall memories by semantic similarity with self-healing.

        In production, this queries pgvector with cosine similarity.
        SDK demo uses simple substring matching.

        **Self-Healing Protocol:**
            After retrieving candidates, the validator checks adjacent
            result pairs for category conflicts at high semantic
            similarity.  Conflicting memories are reclassified in-place
            using keyword consensus.

        Args:
            query: Natural language query.
            top_k: Maximum number of results to return.

        Returns:
            List of RecallResult ordered by trust_quotient,
            with self_healing metadata when reclassification occurred.
        """
        # ── Retrieve candidates via pluggable backend ────────────────
        # When a persistent backend is configured (e.g., SqliteBackend),
        # it handles its own search/ranking.  The legacy in-memory path
        # is kept for backward compatibility with MemoryBackend.
        from .backends.memory_backend import MemoryBackend

        if not isinstance(self._backend, MemoryBackend):
            raw = self._backend.recall(
                query=query,
                agent_id=self.agent_id,
                limit=top_k,
            )
            candidates = [(r, 1.0) for r in raw]
        else:
            # Legacy in-memory path (substring matching).
            query_lower = query.lower()
            scored: List[tuple] = []
            for mem in self._memories:
                content_lower = mem['content'].lower()
                query_words = query_lower.split()
                hits = sum(1 for w in query_words if w in content_lower)
                if hits > 0:
                    relevance = hits / len(query_words)
                    scored.append((mem, relevance))

            scored.sort(
                key=lambda x: x[0]['trust_quotient'] * x[1],
                reverse=True,
            )
            candidates = scored[:top_k]

        # ── Self-Healing Pass ───────────────────────────────────────
        # Compare adjacent pairs for category conflicts
        healing_map: Dict[str, SelfHealingResult] = {}

        for i in range(len(candidates) - 1):
            mem_a = candidates[i][0]
            mem_b = candidates[i + 1][0]

            if mem_a['intent'] == mem_b['intent']:
                continue

            # Compute cosine similarity between embeddings
            sim = self._cosine_similarity(
                mem_a.get('embedding', []),
                mem_b.get('embedding', []),
            )

            heal_result = self._validator.heal_conflicts(
                memory_a=mem_a,
                memory_b=mem_b,
                similarity=sim,
            )

            if heal_result and heal_result.reclassified:
                # Reclassify the loser in-place
                loser_id = mem_b['memory_id']
                mem_b['intent'] = heal_result.new_category.value
                healing_map[loser_id] = heal_result

                logger.info(
                    "Self-healing applied during recall: %s → %s",
                    heal_result.original_category.value,
                    heal_result.new_category.value,
                )

        # ── Build results ─────────────────────────────────────────
        return [
            RecallResult(
                content=mem['content'],
                trust_quotient=mem['trust_quotient'],
                memory_id=mem['memory_id'],
                timestamp=mem['timestamp'],
                intent=mem['intent'],
                is_critical=mem.get('is_critical', False),
                self_healing=healing_map.get(mem['memory_id']),
            )
            for mem, _ in candidates
        ]

    # ══ Neural Handover™ API ═════════════════════════════════════════════

    def create_handover(
        self,
        target_agent: str,
        user_id: str,
        *,
        scope: str = "full",
        memory_filter: Optional[Dict[str, Any]] = None,
    ) -> HandoverResult:
        """Create a Neural Handover™ to transfer context to another agent.

        Packages the current agent's stored memories into a signed JWT
        token, persisted in the Status Ledger as PENDING.

        Args:
            target_agent: ID of the destination agent.
            user_id: Owning user ID.
            scope: Access scope ("full", "read_only", "summary").
            memory_filter: Optional filter dict (e.g., {"intent": "preference"}).

        Returns:
            HandoverResult with signed token and handover_id.
        """
        # Collect memories to transfer
        memories_to_transfer = []
        for mem in self._memories:
            # Apply optional filter
            if memory_filter:
                skip = False
                for key, value in memory_filter.items():
                    if mem.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            memories_to_transfer.append({
                'content': mem['content'],
                'confidence': mem.get('confidence', 0.9),
                'intent': mem.get('intent', 'unknown'),
                'trust_quotient': mem.get('trust_quotient', 0.5),
            })

        if not memories_to_transfer:
            raise ValueError("No memories to transfer for this handover.")

        return self._handover.create_handover(
            origin_agent=self.agent_id,
            target_agent=target_agent,
            user_id=user_id,
            memories=memories_to_transfer,
            scope=scope,
        )

    def accept_handover(
        self,
        handover_id: str,
    ) -> HandoverPackage:
        """Accept an incoming handover and load context into this agent.

        Verifies the JWT signature, checks TTL, and imports the
        transferred memories into the local store.

        Args:
            handover_id: The handover to accept.

        Returns:
            The full HandoverPackage.
        """
        package = self._handover.accept_handover(
            handover_id, accepting_agent=self.agent_id,
        )

        # Import transferred memories into local store
        if package.status == HandoverStatus.COMPLETED:
            for mem in package.context_data:
                self._memories.append({
                    'memory_id': hashlib.sha256(
                        mem.get('content', '').encode()
                    ).hexdigest()[:32],
                    'agent_id': self.agent_id,
                    'content': mem.get('content', ''),
                    'embedding': self._generate_pseudo_embedding(
                        mem.get('content', '')
                    ),
                    'trust_quotient': mem.get('trust_quotient', 0.5),
                    'confidence': mem.get('confidence', 0.9),
                    'intent': mem.get('intent', 'unknown'),
                    'is_critical': mem.get('is_critical', False),
                    'source_type': 'handover',
                    'metadata': {'handover_id': handover_id},
                    'timestamp': time.time(),
                })
            logger.info(
                "Imported %d memories from handover %s",
                len(package.context_data), handover_id,
            )

        return package

    def get_latest_handover(
        self,
        user_id: str,
    ) -> Optional[HandoverPackage]:
        """Retrieve the most recent handover for a user.

        If expired within grace period, returns summary instead of raw data.

        Args:
            user_id: The user to query.

        Returns:
            HandoverPackage or None.
        """
        return self._handover.get_latest_handover(user_id=user_id)

    def fail_handover(
        self,
        handover_id: str,
        reason: str = "Target agent unreachable",
    ) -> HandoverPackage:
        """Mark a handover as FAILED, creating an Emergency Checkpoint.

        Args:
            handover_id: The handover to fail.
            reason: Human-readable failure reason.

        Returns:
            Updated HandoverPackage with emergency_checkpoint.
        """
        return self._handover.fail_handover(handover_id, reason=reason)

    # ══ Internal Helpers ════════════════════════════════════════════════

    @staticmethod
    def _generate_pseudo_embedding(
        text: str, dim: int = 384
    ) -> List[float]:
        """Generate a deterministic pseudo-embedding from text.

        Production systems replace this with a real embedding model.
        This implementation uses SHA-256 expansion for deterministic,
        reproducible vectors suitable for testing.
        """
        import struct

        h = hashlib.sha256(text.encode()).digest()
        values: List[float] = []
        i = 0
        while len(values) < dim:
            block = hashlib.sha256(h + struct.pack('>I', i)).digest()
            for j in range(0, 32, 4):
                if len(values) >= dim:
                    break
                raw = struct.unpack('>I', block[j:j + 4])[0]
                val = (raw / 0xFFFFFFFF) * 2.0 - 1.0
                values.append(val)
            i += 1

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]

        return values

    def _compute_tq(self, validation: ValidationResult) -> float:
        """Compute Trust Quotient for a validated memory.

        OSS uses a baseline formula. Enterprise tier adds recency decay,
        agent-reputation weighting, and cross-session normalization.
        """
        tq = round(validation.confidence * validation.validation_score, 4)
        if validation.confidence_boost > 0:
            tq = min(tq + validation.confidence_boost * 0.1, 1.0)
        return tq

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Returns 0.0 if either vector is empty or zero-norm.
        """
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot / (norm_a * norm_b)

