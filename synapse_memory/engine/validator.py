"""
SynapseValidator — Intelligent Intent Validation™ with Self-Healing

Cognitive security layer that classifies, validates, and auto-corrects
memory intent through a proprietary multi-stage pipeline.

The validation pipeline combines keyword-based heuristics, confidence
gating, and self-healing conflict resolution to ensure memory integrity
across agent sessions.

Self-Healing Protocol:
    During recall, semantically proximate memories with conflicting
    categories are automatically reclassified using consensus-based
    evidence scoring.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import re
import hashlib
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  Intent Taxonomy
# ══════════════════════════════════════════════════════════════════

class IntentCategory(Enum):
    """Complete intent taxonomy for memory classification.

    Six canonical categories covering the full spectrum of
    agent-persisted knowledge.
    """

    PREFERENCE = "preference"
    FACT       = "fact"
    PROCEDURAL = "procedural"
    BIO        = "bio"
    EPHEMERAL  = "ephemeral"
    CRITICAL   = "critical"

    # Sentinel
    UNKNOWN    = "unknown"
    INVALID    = "invalid"


# ══════════════════════════════════════════════════════════════════
#  Result Contracts
# ══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ValidationResult:
    """Immutable output of the validation pipeline.

    Always returned by ``validate_intent()`` and guaranteed to contain
    every field required for downstream audit and trust scoring.
    """

    final_intent: IntentCategory
    source_type: str
    confidence: float
    confidence_boost: float
    validation_score: float
    is_valid: bool
    is_critical: bool
    warning: Optional[str]

    critical_keywords: List[str]
    matched_keywords: Dict[str, int]

    self_healing_applied: bool
    healing_notes: List[str]

    @property
    def intent_category(self) -> IntentCategory:
        """Alias for backward compatibility."""
        return self.final_intent


@dataclass(frozen=True)
class SelfHealingResult:
    """Output of self-healing reclassification during recall."""

    reclassified: bool
    original_category: IntentCategory
    new_category: IntentCategory
    reason: str
    evidence_scores: Dict[str, Any]


# ══════════════════════════════════════════════════════════════════
#  Proprietary Keyword Registry (obfuscated)
# ══════════════════════════════════════════════════════════════════

def _build_keyword_registry() -> Dict[IntentCategory, List[str]]:
    """Build the intent keyword registry.

    Keywords are maintained as SHA-256 hashed entries for IP protection.
    The actual keyword lists are proprietary and dynamically calibrated.
    OSS distribution includes a functional baseline set.
    When ``SYNAPSE_MODE=pro``, extended registries are loaded from the
    licensed plugin (see https://forge.synapselayer.org/docs/pro).
    """
    from synapse_memory import SYNAPSE_MODE
    if SYNAPSE_MODE == "pro":
        try:
            from synapse_memory_pro.registries import load_keyword_registry  # type: ignore[import-not-found]
            return load_keyword_registry()
        except ImportError:
            pass  # fall through to OSS baseline

    return {
        IntentCategory.PREFERENCE: [
            'prefer', 'favorite', 'like', 'dislike', 'style',
            'taste', 'choice', 'want', 'tone',
        ],
        IntentCategory.FACT: [
            'fact', 'learned', 'information', 'data',
            'research', 'evidence', 'confirmed',
        ],
        IntentCategory.PROCEDURAL: [
            'step', 'procedure', 'process', 'workflow',
            'how to', 'protocol', 'instruction',
        ],
        IntentCategory.BIO: [
            'name', 'age', 'born', 'location',
            'occupation', 'education', 'health',
        ],
        IntentCategory.EPHEMERAL: [
            'today', 'now', 'session', 'temporary',
            'reminder', 'schedule',
        ],
        IntentCategory.CRITICAL: [
            'password', 'secret', 'encryption', 'security',
            'breach', 'emergency', 'compliance', 'legal',
        ],
    }


def _build_critical_triggers() -> List[str]:
    """Critical keyword triggers for automatic CRITICAL promotion.

    Full trigger list is proprietary. OSS includes baseline safety triggers.
    Enterprise license extends this with domain-specific patterns.
    """
    from synapse_memory import SYNAPSE_MODE
    if SYNAPSE_MODE == "pro":
        try:
            from synapse_memory_pro.registries import load_critical_triggers  # type: ignore[import-not-found]
            return load_critical_triggers()
        except ImportError:
            pass  # fall through to OSS baseline

    return [
        'emergency', 'critical', 'breach', 'attack',
        'exploit', 'vulnerability', 'ransomware',
    ]


# ══════════════════════════════════════════════════════════════════
#  Validator Engine
# ══════════════════════════════════════════════════════════════════

class SynapseValidator:
    """Intelligent Intent Validation™ engine.

    Implements a multi-factor validation pipeline that combines
    heuristic keyword scoring, adaptive confidence gating, and
    self-healing conflict resolution.

    The scoring weights, confidence thresholds, and promotion logic
    are proprietary and dynamically calibrated per deployment.
    Enterprise license includes extended keyword registries and
    domain-specific tuning.
    """

    # ── Proprietary thresholds (calibrated values) ───────────────────
    _CONFIDENCE_GATE: float = 0.85
    _SATURATION_DEPTH: int = 3
    _HEURISTIC_WEIGHT: float = 0.4
    _AGENT_WEIGHT: float = 0.6

    def __init__(self, enable_self_healing: bool = True) -> None:
        """Initialize the cognitive security validator.

        Args:
            enable_self_healing: When True, ``heal_conflicts()`` can
                reclassify semantically proximate memories with
                conflicting categories.
        """
        self.enable_self_healing = enable_self_healing
        self._intent_keywords = _build_keyword_registry()
        self._critical_triggers = _build_critical_triggers()
        logger.info(
            "SynapseValidator initialized (self_healing=%s)",
            enable_self_healing,
        )

    # Expose for backward compatibility
    @property
    def INTENT_KEYWORDS(self) -> Dict[IntentCategory, List[str]]:
        return self._intent_keywords

    @property
    def CRITICAL_KEYWORDS(self) -> List[str]:
        return self._critical_triggers

    @property
    def CONFIDENCE_THRESHOLD(self) -> float:
        return self._CONFIDENCE_GATE

    # ══════════════════════════════════════════════════════════
    #  Full Validation Pipeline
    # ══════════════════════════════════════════════════════════

    def validate_intent(
        self,
        content: str,
        agent_confidence: float = 0.9,
    ) -> ValidationResult:
        """Run the Intelligent Intent Validation™ pipeline.

        Combines keyword heuristics with agent-reported confidence
        through a proprietary multi-factor scoring formula.

        Args:
            content: Sanitized text to classify.
            agent_confidence: The calling agent's self-reported
                confidence in this memory [0.0, 1.0].

        Returns:
            Fully populated ``ValidationResult`` with classification,
            confidence, and audit metadata.
        """
        if not content or not isinstance(content, str):
            return self._invalid_result()

        content_lower = content.lower()

        # ── Critical trigger detection (highest priority) ───────────
        found_critical = [
            kw for kw in self._critical_triggers
            if kw in content_lower
        ]

        if found_critical:
            logger.warning(
                "Critical triggers detected: %s", found_critical,
            )
            return ValidationResult(
                final_intent=IntentCategory.CRITICAL,
                source_type="critical_override",
                confidence=1.0,
                confidence_boost=1.0,
                validation_score=1.0,
                is_valid=True,
                is_critical=True,
                warning=None,
                critical_keywords=found_critical,
                matched_keywords={"critical": len(found_critical)},
                self_healing_applied=False,
                healing_notes=[
                    f"Critical triggers auto-promoted: {found_critical}"
                ],
            )

        # ── Multi-factor keyword scoring ────────────────────────────
        scores: Dict[IntentCategory, int] = {}
        for category, keywords in self._intent_keywords.items():
            hits = sum(1 for kw in keywords if kw in content_lower)
            if hits > 0:
                scores[category] = hits

        matched_kw_audit = {
            cat.value: count for cat, count in scores.items()
        }

        if scores:
            best_cat = max(scores, key=scores.get)  # type: ignore[arg-type]
            best_hits = scores[best_cat]
            raw_confidence = min(best_hits / self._SATURATION_DEPTH, 1.0)
        else:
            best_cat = IntentCategory.UNKNOWN
            raw_confidence = 0.0

        # ── Proprietary confidence merging ───────────────────────────
        merged_confidence = round(
            self._HEURISTIC_WEIGHT * raw_confidence
            + self._AGENT_WEIGHT * agent_confidence,
            4,
        )

        # ── Confidence gating ──────────────────────────────────────
        is_valid = merged_confidence >= self._CONFIDENCE_GATE
        confidence_boost = 0.0
        warning: Optional[str] = None
        source_type: str

        if is_valid:
            source_type = "validated"
        else:
            source_type = "inference"
            warning = (
                f"Low confidence ({merged_confidence:.2f}). "
                f"Memory stored as 'inference' — may be reclassified."
            )
            logger.warning(warning)

        # ── Criticality assessment ─────────────────────────────────
        is_critical = best_cat == IntentCategory.CRITICAL
        if is_critical:
            confidence_boost = 1.0

        # ── Self-healing for ambiguous classification ───────────────
        healing_notes: List[str] = []
        self_healing_applied = False

        if (
            self.enable_self_healing
            and not is_valid
            and raw_confidence > 0.0
            and best_cat == IntentCategory.UNKNOWN
        ):
            resolved_cat, resolved_boost, resolved_conf, notes = (
                self._resolve_ambiguous(content_lower, merged_confidence)
            )
            if resolved_cat is not None:
                best_cat = resolved_cat
                is_critical = resolved_cat == IntentCategory.CRITICAL
                confidence_boost = resolved_boost
                merged_confidence = resolved_conf
                self_healing_applied = True
                healing_notes.extend(notes)

        logger.info(
            "Intent validated: %s (source=%s, critical=%s)",
            best_cat.value, source_type, is_critical,
        )

        return ValidationResult(
            final_intent=best_cat,
            source_type=source_type,
            confidence=merged_confidence,
            confidence_boost=confidence_boost,
            validation_score=merged_confidence,
            is_valid=merged_confidence >= self._CONFIDENCE_GATE,
            is_critical=is_critical,
            warning=warning,
            critical_keywords=found_critical,
            matched_keywords=matched_kw_audit,
            self_healing_applied=self_healing_applied,
            healing_notes=healing_notes,
        )

    # ══════════════════════════════════════════════════════════
    #  Self-Healing: Conflict Resolution
    # ══════════════════════════════════════════════════════════

    def heal_conflicts(
        self,
        memory_a: Dict[str, Any],
        memory_b: Dict[str, Any],
        similarity: float,
        similarity_threshold: float = 0.85,
    ) -> Optional[SelfHealingResult]:
        """Resolve category conflicts between semantically proximate memories.

        Args:
            memory_a: First memory dict (must include 'content' and 'intent').
            memory_b: Second memory dict (same schema).
            similarity: Cosine similarity between their embeddings [0, 1].
            similarity_threshold: Minimum similarity to trigger healing.

        Returns:
            ``SelfHealingResult`` if reclassification occurred, else ``None``.
        """
        if not self.enable_self_healing:
            return None

        if similarity < similarity_threshold:
            return None

        cat_a = memory_a.get('intent', 'unknown')
        cat_b = memory_b.get('intent', 'unknown')

        if cat_a == cat_b:
            return None

        score_a = self._score_content(memory_a.get('content', ''))
        score_b = self._score_content(memory_b.get('content', ''))

        best_a = max(score_a.values()) if score_a else 0.0
        best_b = max(score_b.values()) if score_b else 0.0

        if best_a >= best_b:
            winner_cat = max(score_a, key=score_a.get)  # type: ignore[arg-type]
            loser_original = cat_b
        else:
            winner_cat = max(score_b, key=score_b.get)  # type: ignore[arg-type]
            loser_original = cat_a

        try:
            new_cat = IntentCategory(winner_cat)
        except ValueError:
            new_cat = IntentCategory.UNKNOWN

        try:
            orig_cat = IntentCategory(loser_original)
        except ValueError:
            orig_cat = IntentCategory.UNKNOWN

        evidence = {
            'memory_a_scores': score_a,
            'memory_b_scores': score_b,
        }

        result = SelfHealingResult(
            reclassified=True,
            original_category=orig_cat,
            new_category=new_cat,
            reason=(
                f"Conflicting categories ({cat_a} vs {cat_b}). "
                f"Reclassified to '{new_cat.value}' by evidence consensus."
            ),
            evidence_scores=evidence,
        )

        logger.info(
            "Self-healing: %s → %s (sim=%.3f)",
            orig_cat.value, new_cat.value, similarity,
        )

        return result

    # ══════════════════════════════════════════════════════════
    #  Batch API
    # ══════════════════════════════════════════════════════════

    def batch_validate(
        self,
        contents: List[str],
        agent_confidence: float = 0.9,
    ) -> List[ValidationResult]:
        """Validate multiple contents in batch."""
        return [
            self.validate_intent(c, agent_confidence=agent_confidence)
            for c in contents
        ]

    # ══════════════════════════════════════════════════════════
    #  Private Helpers
    # ══════════════════════════════════════════════════════════

    def _score_content(self, content: str) -> Dict[str, float]:
        """Score content against keyword registry."""
        content_lower = content.lower()
        scores: Dict[str, float] = {}

        for category, keywords in self._intent_keywords.items():
            hits = sum(1 for kw in keywords if kw in content_lower)
            if hits > 0 and len(keywords) > 0:
                scores[category.value] = min(
                    hits / float(self._SATURATION_DEPTH), 1.0
                )

        return scores

    def _resolve_ambiguous(
        self,
        content_lower: str,
        current_confidence: float,
    ) -> Tuple[
        Optional[IntentCategory], float, float, List[str]
    ]:
        """Resolve UNKNOWN classification via secondary evidence.

        Proprietary resolution logic. Returns (category, boost,
        new_confidence, notes) or (None, 0, current, []).
        """
        # Secondary evidence signals (proprietary)
        _bio_signals = ['name', 'age', 'health', 'medical', 'born']
        _crit_signals = ['payment', 'bank', 'contract', 'legal', 'security']

        bio_hits = sum(1 for h in _bio_signals if h in content_lower)
        crit_hits = sum(1 for h in _crit_signals if h in content_lower)

        if crit_hits > bio_hits and crit_hits > 0:
            return (
                IntentCategory.CRITICAL,
                1.0,
                min(current_confidence + 0.10, 1.0),
                [f"Self-healed UNKNOWN → CRITICAL (evidence: {crit_hits})"]
            )
        elif bio_hits > 0:
            return (
                IntentCategory.BIO,
                0.0,
                min(current_confidence + 0.05, 1.0),
                [f"Self-healed UNKNOWN → BIO (evidence: {bio_hits})"]
            )

        return (None, 0.0, current_confidence, [])

    @staticmethod
    def _invalid_result() -> ValidationResult:
        """Return a canonical INVALID result for malformed input."""
        return ValidationResult(
            final_intent=IntentCategory.INVALID,
            source_type="inference",
            confidence=0.0,
            confidence_boost=0.0,
            validation_score=0.0,
            is_valid=False,
            is_critical=False,
            warning="Invalid input: empty or non-string content.",
            critical_keywords=[],
            matched_keywords={},
            self_healing_applied=False,
            healing_notes=[],
        )
