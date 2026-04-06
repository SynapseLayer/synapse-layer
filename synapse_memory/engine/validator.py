"""
SynapseValidator — Intelligent Intent Validation™ with Self-Healing

Production-grade cognitive security layer that classifies, validates,
and auto-corrects memory intent in a two-step pipeline:

    Step 1 (Agent Suggestion):  Keyword heuristics + scoring → proposed intent
    Step 2 (Synapse Validation): Confidence gate, critical promotion, self-healing

Self-Healing Protocol:
    During recall, when two semantically proximate memories carry
    conflicting categories, the validator triggers automatic
    reclassification using keyword consensus — the category with the
    highest aggregate evidence wins.

Confidence Contract:
    - confidence ≥ 0.85  → source_type = "validated"
    - confidence <  0.85  → source_type = "inference", warning emitted
    - critical_keyword hit → confidence_boost = 1.0, category forced CRITICAL

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import re
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Intent Taxonomy
# ══════════════════════════════════════════════════════════════════════

class IntentCategory(Enum):
    """Complete intent taxonomy for memory classification.

    Six canonical categories covering the full spectrum of
    agent-persisted knowledge.  Each category carries implicit
    retention and sensitivity semantics.
    """

    PREFERENCE = "preference"      # Taste, style, language, tone, likes/dislikes
    FACT       = "fact"            # Verified knowledge, data, research, learning
    PROCEDURAL = "procedural"      # Steps, workflows, how-to, recipes, protocols
    BIO        = "bio"             # Personal info, identity, demographics, health
    EPHEMERAL  = "ephemeral"       # Transient context, session-scoped, expirable
    CRITICAL   = "critical"        # Security, compliance, emergency, legal, financial

    # Sentinel
    UNKNOWN    = "unknown"         # Unclassifiable — requires manual review
    INVALID    = "invalid"         # Malformed, empty, or spam input


# ══════════════════════════════════════════════════════════════════════
#  Result Contracts
# ══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ValidationResult:
    """Immutable output of the two-step validation pipeline.

    Always returned by ``validate_intent()`` and guaranteed to contain
    every field required for downstream audit and trust scoring.
    """

    # ── Core classification ───────────────────────────────────────
    final_intent: IntentCategory          # Final resolved category
    source_type: str                      # "validated" | "inference" | "critical_override"
    confidence: float                     # Agent-side confidence [0.0, 1.0]
    confidence_boost: float               # Post-validation boost (0.0 or 1.0)
    validation_score: float               # Synapse-side score [0.0, 1.0]
    is_valid: bool                        # True when validation_score ≥ threshold
    is_critical: bool                     # True for CRITICAL or critical-keyword hits
    warning: Optional[str]                # Human-readable warning (or None)

    # ── Keywords & evidence ───────────────────────────────────────
    critical_keywords: List[str]          # Keywords that triggered CRITICAL
    matched_keywords: Dict[str, int]      # {category: match_count}

    # ── Self-healing audit ────────────────────────────────────────
    self_healing_applied: bool            # True if any correction was made
    healing_notes: List[str]              # What was fixed and why

    # ── Legacy compat aliases ─────────────────────────────────────
    @property
    def intent_category(self) -> IntentCategory:
        """Alias for backward compatibility with v1.0.4 callers."""
        return self.final_intent


@dataclass(frozen=True)
class SelfHealingResult:
    """Output of self-healing reclassification during recall."""

    reclassified: bool
    original_category: IntentCategory
    new_category: IntentCategory
    reason: str
    evidence_scores: Dict[str, float]


# ══════════════════════════════════════════════════════════════════════
#  Validator Engine
# ══════════════════════════════════════════════════════════════════════

class SynapseValidator:
    """Intelligent Intent Validation™ — Cognitive Security Layer.

    Two-step pipeline:
        1. **Agent suggestion** — keyword heuristics produce a proposed
           intent and raw confidence score.
        2. **Synapse validation** — confidence gate (≥ 0.85), critical
           keyword promotion, and source-type assignment.

    Self-healing (optional, on by default):
        When ``heal_conflicts()`` is called with two semantically
        proximate memories that carry different categories, the engine
        re-evaluates both using keyword consensus and promotes the
        winner, logging the reclassification for audit.

    Usage::

        validator = SynapseValidator()
        result = validator.validate_intent(
            content="User prefers dark mode",
            agent_confidence=0.92,
        )
        assert result.final_intent == IntentCategory.PREFERENCE
        assert result.source_type == "validated"
    """

    # ── Confidence threshold (immutable) ──────────────────────────
    CONFIDENCE_THRESHOLD: float = 0.85

    # ── Keyword dictionaries per category ─────────────────────────
    INTENT_KEYWORDS: Dict[IntentCategory, List[str]] = {
        IntentCategory.PREFERENCE: [
            'prefer', 'preference', 'favorite', 'enjoy', 'love', 'hate',
            'like', 'dislike', 'style', 'taste', 'choice', 'want',
            'desire', 'ideal', 'best', 'worst', 'tone', 'language',
            'theme', 'dark mode', 'light mode', 'concise', 'verbose',
        ],
        IntentCategory.FACT: [
            'fact', 'learned', 'discovered', 'studied', 'knows',
            'information', 'data', 'understand', 'concept', 'research',
            'analysis', 'theory', 'principle', 'evidence', 'proven',
            'true', 'false', 'confirmed', 'verified', 'scientific',
        ],
        IntentCategory.PROCEDURAL: [
            'step', 'steps', 'procedure', 'process', 'workflow',
            'how to', 'how-to', 'recipe', 'protocol', 'instruction',
            'guide', 'tutorial', 'method', 'algorithm', 'pipeline',
            'sequence', 'first', 'then', 'finally', 'next',
        ],
        IntentCategory.BIO: [
            'name', 'age', 'born', 'birthday', 'location', 'city',
            'country', 'occupation', 'job', 'career', 'education',
            'school', 'university', 'family', 'married', 'children',
            'health', 'medical', 'diagnosis', 'allergy', 'medication',
        ],
        IntentCategory.EPHEMERAL: [
            'today', 'now', 'currently', 'session', 'temporary',
            'right now', 'this moment', 'at the moment', 'transient',
            'short-term', 'expiring', 'until', 'deadline', 'timer',
            'reminder', 'calendar', 'schedule', 'meeting',
        ],
        IntentCategory.CRITICAL: [
            'password', 'token', 'secret', 'api_key', 'credential',
            'encryption', 'security', 'breach', 'attack', 'fraud',
            'emergency', 'urgent', 'critical', 'danger', 'alert',
            'compliance', 'gdpr', 'lgpd', 'hipaa', 'legal',
            'contract', 'lawsuit', 'bank', 'payment', 'transaction',
            'credit', 'financial', 'invoice', 'audit', 'warrant',
        ],
    }

    # ── Critical keywords: instant promotion to CRITICAL ──────────
    CRITICAL_KEYWORDS: List[str] = [
        'emergency', 'urgent', 'critical', 'danger', 'alert',
        'breach', 'attack', 'hack', 'fraud', 'abuse',
        'exploit', 'vulnerability', 'ransomware', 'warrant',
        'subpoena', 'immediate', 'severe', 'fatal', 'lethal',
    ]

    # ── Constructor ───────────────────────────────────────────────

    def __init__(self, enable_self_healing: bool = True) -> None:
        """Initialize the cognitive security validator.

        Args:
            enable_self_healing: When True, ``heal_conflicts()`` can
                reclassify semantically proximate memories with
                conflicting categories.
        """
        self.enable_self_healing = enable_self_healing
        logger.info(
            "SynapseValidator initialized (self_healing=%s)",
            enable_self_healing,
        )

    # ══════════════════════════════════════════════════════════════
    #  Step 1+2: validate_intent()  —  Full Two-Step Pipeline
    # ══════════════════════════════════════════════════════════════

    def validate_intent(
        self,
        content: str,
        agent_confidence: float = 0.9,
    ) -> ValidationResult:
        """Run the two-step Intelligent Intent Validation™ pipeline.

        **Step 1 — Agent Suggestion:**
            Scan *content* against keyword dictionaries and rank
            categories by match density.

        **Step 2 — Synapse Validation:**
            Apply confidence gate, critical-keyword override, and
            assign ``source_type``.

        Args:
            content: Sanitized text to classify.
            agent_confidence: The calling agent's self-reported
                confidence in this memory [0.0, 1.0].

        Returns:
            Fully populated ``ValidationResult`` with ``final_intent``,
            ``source_type``, ``warning``, and ``confidence_boost``.
        """
        # ── Guard: invalid input ──────────────────────────────────
        if not content or not isinstance(content, str):
            return self._invalid_result()

        content_lower = content.lower()

        # ── Step 1a: Detect critical keywords (highest priority) ──
        found_critical = [
            kw for kw in self.CRITICAL_KEYWORDS
            if kw in content_lower
        ]

        if found_critical:
            logger.warning(
                "Critical keywords detected: %s — forcing CRITICAL",
                found_critical,
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
                    f"Critical keywords auto-promoted: {found_critical}"
                ],
            )

        # ── Step 1b: Keyword scoring per category ─────────────────
        # Normalization: min(hits / SATURATION_HITS, 1.0)
        # 3 keyword matches = full raw confidence for that category.
        SATURATION_HITS = 3
        scores: Dict[IntentCategory, int] = {}
        for category, keywords in self.INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in content_lower)
            if hits > 0:
                scores[category] = hits

        matched_kw_audit = {
            cat.value: count for cat, count in scores.items()
        }

        # ── Step 1c: Select best category ─────────────────────────
        if scores:
            best_cat = max(scores, key=scores.get)  # type: ignore[arg-type]
            best_hits = scores[best_cat]
            raw_confidence = min(best_hits / SATURATION_HITS, 1.0)
        else:
            best_cat = IntentCategory.UNKNOWN
            raw_confidence = 0.0

        # ── Step 2a: Merge agent confidence with heuristic ────────
        # Weighted average: 40% heuristic, 60% agent-reported
        merged_confidence = round(
            0.4 * raw_confidence + 0.6 * agent_confidence, 4
        )

        # ── Step 2b: Confidence gate ──────────────────────────────
        is_valid = merged_confidence >= self.CONFIDENCE_THRESHOLD
        confidence_boost = 0.0
        warning: Optional[str] = None
        source_type: str

        if is_valid:
            source_type = "validated"
        else:
            source_type = "inference"
            warning = (
                f"Low confidence ({merged_confidence:.2f} < "
                f"{self.CONFIDENCE_THRESHOLD}). Memory stored as "
                f"'inference' — may be reclassified during recall."
            )
            logger.warning(warning)

        # ── Step 2c: Inherent criticality check ───────────────────
        is_critical = best_cat == IntentCategory.CRITICAL
        if is_critical:
            confidence_boost = 1.0

        # ── Step 2d: Self-healing boost for ambiguous low-conf ────
        healing_notes: List[str] = []
        self_healing_applied = False

        if (
            self.enable_self_healing
            and not is_valid
            and raw_confidence > 0.0
            and best_cat == IntentCategory.UNKNOWN
        ):
            # Try secondary evidence: check for BIO or CRITICAL hints
            bio_hints = ['name', 'age', 'health', 'medical', 'born']
            crit_hints = ['payment', 'bank', 'contract', 'legal', 'security']

            bio_hits = sum(1 for h in bio_hints if h in content_lower)
            crit_hits = sum(1 for h in crit_hints if h in content_lower)

            if crit_hits > bio_hits and crit_hits > 0:
                best_cat = IntentCategory.CRITICAL
                is_critical = True
                confidence_boost = 1.0
                merged_confidence = min(merged_confidence + 0.10, 1.0)
                self_healing_applied = True
                healing_notes.append(
                    f"Self-healed UNKNOWN → CRITICAL (evidence: {crit_hits} hints)"
                )
            elif bio_hits > 0:
                best_cat = IntentCategory.BIO
                merged_confidence = min(merged_confidence + 0.05, 1.0)
                self_healing_applied = True
                healing_notes.append(
                    f"Self-healed UNKNOWN → BIO (evidence: {bio_hits} hints)"
                )

        # ── Build result ──────────────────────────────────────────
        logger.info(
            "Intent validated: %s (conf=%.2f, source=%s, critical=%s)",
            best_cat.value, merged_confidence, source_type, is_critical,
        )

        return ValidationResult(
            final_intent=best_cat,
            source_type=source_type,
            confidence=merged_confidence,
            confidence_boost=confidence_boost,
            validation_score=merged_confidence,
            is_valid=merged_confidence >= self.CONFIDENCE_THRESHOLD,
            is_critical=is_critical,
            warning=warning,
            critical_keywords=found_critical,
            matched_keywords=matched_kw_audit,
            self_healing_applied=self_healing_applied,
            healing_notes=healing_notes,
        )

    # ══════════════════════════════════════════════════════════════
    #  Self-Healing: Conflict Resolution During Recall
    # ══════════════════════════════════════════════════════════════

    def heal_conflicts(
        self,
        memory_a: Dict[str, Any],
        memory_b: Dict[str, Any],
        similarity: float,
        similarity_threshold: float = 0.85,
    ) -> Optional[SelfHealingResult]:
        """Resolve category conflicts between semantically proximate memories.

        When two memories have high cosine similarity (≥ *similarity_threshold*)
        but different intent categories, this method re-evaluates both using
        keyword consensus and reclassifies the weaker one.

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
            return None  # No conflict

        # Re-score both using keyword evidence
        score_a = self._score_content(memory_a.get('content', ''))
        score_b = self._score_content(memory_b.get('content', ''))

        # Determine winner by total evidence strength
        best_a = max(score_a.values()) if score_a else 0.0
        best_b = max(score_b.values()) if score_b else 0.0

        if best_a >= best_b:
            winner_cat = max(score_a, key=score_a.get)  # type: ignore[arg-type]
            loser_original = cat_b
        else:
            winner_cat = max(score_b, key=score_b.get)  # type: ignore[arg-type]
            loser_original = cat_a

        # Resolve enum
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
                f"Semantic similarity {similarity:.3f} ≥ {similarity_threshold} "
                f"with conflicting categories ({cat_a} vs {cat_b}). "
                f"Reclassified to '{new_cat.value}' by keyword consensus."
            ),
            evidence_scores=evidence,
        )

        logger.info(
            "Self-healing: %s → %s (sim=%.3f, reason: keyword consensus)",
            orig_cat.value, new_cat.value, similarity,
        )

        return result

    # ══════════════════════════════════════════════════════════════
    #  Batch API
    # ══════════════════════════════════════════════════════════════

    def batch_validate(
        self,
        contents: List[str],
        agent_confidence: float = 0.9,
    ) -> List[ValidationResult]:
        """Validate multiple contents in batch.

        Args:
            contents: List of sanitized text strings.
            agent_confidence: Shared confidence for the batch.

        Returns:
            List of ``ValidationResult`` in the same order.
        """
        return [
            self.validate_intent(c, agent_confidence=agent_confidence)
            for c in contents
        ]

    # ══════════════════════════════════════════════════════════════
    #  Private Helpers
    # ══════════════════════════════════════════════════════════════

    def _score_content(self, content: str) -> Dict[str, float]:
        """Score content against all keyword dictionaries.

        Returns:
            Dict mapping category value strings to normalized scores.
        """
        content_lower = content.lower()
        scores: Dict[str, float] = {}

        for category, keywords in self.INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in content_lower)
            if hits > 0 and len(keywords) > 0:
                scores[category.value] = min(hits / 3.0, 1.0)

        return scores

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


# ══════════════════════════════════════════════════════════════════════
#  Inline Tests (run with: python -m synapse_memory.engine.validator)
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("SynapseValidator — Inline Test Suite (v1.0.5)")
    print("=" * 60)

    v = SynapseValidator(enable_self_healing=True)

    # Test 1: PREFERENCE classification
    r1 = v.validate_intent("User prefers dark mode and concise answers", agent_confidence=0.95)
    assert r1.final_intent == IntentCategory.PREFERENCE
    assert r1.source_type == "validated"
    assert r1.confidence >= 0.85
    assert r1.warning is None
    print(f"[PASS] PREFERENCE: {r1.final_intent.value}, conf={r1.confidence:.2f}")

    # Test 2: CRITICAL via keyword override
    r2 = v.validate_intent("There is a security breach in the system", agent_confidence=0.5)
    assert r2.final_intent == IntentCategory.CRITICAL
    assert r2.source_type == "critical_override"
    assert r2.confidence_boost == 1.0
    assert r2.is_critical is True
    assert 'breach' in r2.critical_keywords
    print(f"[PASS] CRITICAL override: {r2.critical_keywords}")

    # Test 3: Low confidence → source_type = "inference" + warning
    r3 = v.validate_intent("something happened somewhere", agent_confidence=0.3)
    assert r3.source_type == "inference"
    assert r3.warning is not None
    assert r3.confidence < 0.85
    print(f"[PASS] Low confidence: source={r3.source_type}, warning='{r3.warning[:50]}...'")

    # Test 4: PROCEDURAL
    r4 = v.validate_intent(
        "Follow these steps: first install the package, then configure the pipeline",
        agent_confidence=0.92,
    )
    assert r4.final_intent == IntentCategory.PROCEDURAL
    print(f"[PASS] PROCEDURAL: {r4.final_intent.value}, conf={r4.confidence:.2f}")

    # Test 5: BIO
    r5 = v.validate_intent(
        "My name is Ismael, born in Brazil, working in AI",
        agent_confidence=0.93,
    )
    assert r5.final_intent == IntentCategory.BIO
    print(f"[PASS] BIO: {r5.final_intent.value}, conf={r5.confidence:.2f}")

    # Test 6: EPHEMERAL
    r6 = v.validate_intent(
        "I have a meeting today at 3pm, remind me now",
        agent_confidence=0.88,
    )
    assert r6.final_intent == IntentCategory.EPHEMERAL
    print(f"[PASS] EPHEMERAL: {r6.final_intent.value}, conf={r6.confidence:.2f}")

    # Test 7: Self-healing during conflict
    healing = v.heal_conflicts(
        memory_a={'content': 'User prefers concise answers', 'intent': 'preference'},
        memory_b={'content': 'User likes short responses in English', 'intent': 'fact'},
        similarity=0.92,
    )
    assert healing is not None
    assert healing.reclassified is True
    print(f"[PASS] Self-healing: {healing.original_category.value} → {healing.new_category.value}")

    # Test 8: No healing when similarity is low
    no_heal = v.heal_conflicts(
        memory_a={'content': 'Payment info', 'intent': 'critical'},
        memory_b={'content': 'Favorite color', 'intent': 'preference'},
        similarity=0.30,
    )
    assert no_heal is None
    print("[PASS] No healing when similarity < threshold")

    # Test 9: Invalid input
    r9 = v.validate_intent("")
    assert r9.final_intent == IntentCategory.INVALID
    assert r9.is_valid is False
    print(f"[PASS] Invalid input: {r9.final_intent.value}")

    # Test 10: Batch validate
    batch = v.batch_validate([
        "User prefers dark mode",
        "There was a security breach",
        "Follow these steps to deploy",
    ], agent_confidence=0.90)
    assert len(batch) == 3
    assert batch[0].final_intent == IntentCategory.PREFERENCE
    assert batch[1].final_intent == IntentCategory.CRITICAL
    assert batch[2].final_intent == IntentCategory.PROCEDURAL
    print(f"[PASS] Batch: {[r.final_intent.value for r in batch]}")

    # Test 11: backward compat — intent_category alias
    assert r1.intent_category == r1.final_intent
    print("[PASS] Backward compat: intent_category alias works")

    print("\n✅ All inline tests passed.")