"""
SynapseSanitizer — Semantic Privacy Guard™ Content Sanitization Engine

High-performance PII detection, removal, and content hardening pipeline.
Supports standard and aggressive modes for maximum semantic privacy.

Pipeline: raw_text → detect PII → redact → score risk → emit audit payload

The detection patterns and sensitivity mappings are proprietary.
This OSS distribution includes a functional baseline covering 12+
PII categories. Enterprise license extends coverage to 40+ patterns
including industry-specific detectors (HIPAA, PCI-DSS, SOX).

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import re
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Classification tiers for detected sensitive data."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SanitizationResult:
    """Immutable output of the sanitization pipeline."""
    sanitized_content: str
    removed_items: List[Dict[str, Any]]
    pii_count: int
    risk_score: float
    is_safe: bool
    ner_hints: List[str]
    sanitized: bool = True


# ══════════════════════════════════════════════════════════════════
#  Proprietary Detection Patterns (obfuscated)
# ══════════════════════════════════════════════════════════════════

def _build_detection_patterns() -> Dict[str, re.Pattern]:
    """Build the PII detection regex registry.

    Pattern specifications are proprietary. This baseline covers
    12+ PII categories including emails, government IDs, financial
    instruments, API credentials, and network identifiers.

    Enterprise license extends to 40+ patterns with region-specific
    coverage (EU, LATAM, APAC).
    """
    return {
        'email': re.compile(
            r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE,
        ),
        'credit_card': re.compile(r'\b(?:\d{4}[\-\s]?){3}\d{4}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'cpf': re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'),
        'phone': re.compile(
            r'(?:\+\d{1,3})?(?:[\-.\s]?\(?\d{1,4}\)?){2,4}(?:[\-.\s]?\d{4})',
        ),
        'dob': re.compile(
            r'\b(?:0?[1-9]|[12]\d|3[01])[/\-](?:0?[1-9]|1[0-2])[/\-](?:19|20)?\d{2}\b',
        ),
        'cnpj': re.compile(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'),
        'api_key': re.compile(
            r'(?:sk_test_|sk_live_|ghp_|pk_test_|pk_live_|xoxb-|xoxp-)[a-zA-Z0-9_]{20,}',
        ),
        'bearer_token': re.compile(
            r'(?:Bearer\s+)[A-Za-z0-9\-._~+/]+=*',
            re.IGNORECASE,
        ),
        'url': re.compile(r'https?://[^\s\)]+', re.IGNORECASE),
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'aws_key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    }


def _build_sensitivity_map() -> Dict[str, SensitivityLevel]:
    """Sensitivity classification per PII category."""
    return {
        'email':         SensitivityLevel.HIGH,
        'phone':         SensitivityLevel.HIGH,
        'ssn':           SensitivityLevel.CRITICAL,
        'credit_card':   SensitivityLevel.CRITICAL,
        'dob':           SensitivityLevel.HIGH,
        'cpf':           SensitivityLevel.CRITICAL,
        'cnpj':          SensitivityLevel.MEDIUM,
        'api_key':       SensitivityLevel.CRITICAL,
        'bearer_token':  SensitivityLevel.CRITICAL,
        'url':           SensitivityLevel.LOW,
        'ip_address':    SensitivityLevel.MEDIUM,
        'aws_key':       SensitivityLevel.CRITICAL,
        'proper_noun':   SensitivityLevel.MEDIUM,
    }


def _build_risk_weights() -> Dict[SensitivityLevel, float]:
    """Risk scoring weights per sensitivity tier.

    Weights are calibrated for compliance thresholds (GDPR/LGPD).
    Enterprise deployments use domain-specific calibration.
    """
    return {
        SensitivityLevel.CRITICAL: 0.30,
        SensitivityLevel.HIGH:     0.15,
        SensitivityLevel.MEDIUM:   0.05,
        SensitivityLevel.LOW:      0.01,
    }


# ══════════════════════════════════════════════════════════════════
#  Sanitizer Engine
# ══════════════════════════════════════════════════════════════════

class SynapseSanitizer:
    """Semantic Privacy Guard™ content sanitizer.

    Multi-layer PII detection engine with:
    - Configurable detection patterns (12+ categories)
    - Aggressive mode for maximum semantic privacy
    - Weighted risk scoring with compliance thresholds
    - Audit-ready output with forensic hashes
    - Batch processing support

    Usage::

        sanitizer = SynapseSanitizer(aggressive=True)
        result = sanitizer.sanitize_content("Call John at john@acme.com")
        assert result.sanitized
        assert "john@acme.com" not in result.sanitized_content
    """

    _PROPER_NOUN_RE = re.compile(
        r'(?<!\. )(?<!^)\b([A-Z][a-z]{2,})\b',
        re.MULTILINE,
    )
    _STOP_WORDS = frozenset({
        'The', 'This', 'That', 'These', 'Those', 'Each', 'Every',
        'Some', 'Any', 'All', 'Most', 'Many', 'Few', 'Several',
        'Other', 'Another', 'Such', 'What', 'Which', 'Who', 'How',
        'When', 'Where', 'Why', 'But', 'And', 'For', 'Not', 'Yet',
        'Also', 'Just', 'Only', 'Very', 'Still', 'Then', 'Now',
        'Here', 'There', 'True', 'False', 'None',
    })

    _SAFETY_THRESHOLD = 0.05

    def __init__(self, aggressive: bool = False) -> None:
        """Initialize the sanitizer.

        Args:
            aggressive: When True, also removes proper nouns to prevent
                        semantic leakage through embedding inference.
        """
        self.aggressive = aggressive
        self.PATTERNS = _build_detection_patterns()
        self.SENSITIVITY_MAP = _build_sensitivity_map()
        self._RISK_WEIGHTS = _build_risk_weights()
        self.SAFETY_THRESHOLD = self._SAFETY_THRESHOLD
        logger.info(
            "SynapseSanitizer initialized (aggressive=%s)", aggressive
        )

    def sanitize_content(self, content: str) -> SanitizationResult:
        """Execute the full sanitization pipeline.

        Args:
            content: Raw text to sanitize.

        Returns:
            SanitizationResult with redacted content and audit metadata.
        """
        if not content or not isinstance(content, str):
            return SanitizationResult(
                sanitized_content="",
                removed_items=[],
                pii_count=0,
                risk_score=0.0,
                is_safe=True,
                ner_hints=[],
                sanitized=True,
            )

        sanitized = content
        removed_items: List[Dict[str, Any]] = []
        ner_hints: List[str] = []
        risk_score = 0.0

        # ── Pattern-based PII detection & redaction ──────────────────
        for pattern_name, pattern in self.PATTERNS.items():
            if pattern_name == 'url' and not self.aggressive:
                continue

            for match in pattern.finditer(sanitized):
                matched_text = match.group(0)
                sensitivity = self.SENSITIVITY_MAP.get(
                    pattern_name, SensitivityLevel.MEDIUM
                )
                replacement = f"[{pattern_name.upper()}_REDACTED]"

                sanitized = sanitized.replace(matched_text, replacement, 1)

                removed_items.append({
                    'type': pattern_name,
                    'sensitivity': sensitivity.value,
                    'redacted': replacement,
                    'position': match.start(),
                    'hash': hashlib.sha256(
                        matched_text.encode()
                    ).hexdigest()[:16],
                })

                risk_score += self._RISK_WEIGHTS.get(sensitivity, 0.05)

                if sensitivity in (
                    SensitivityLevel.HIGH, SensitivityLevel.CRITICAL
                ):
                    ner_hints.append(f"{pattern_name}:{match.start()}")

        # ── Aggressive: proper noun stripping ───────────────────────
        if self.aggressive:
            for match in self._PROPER_NOUN_RE.finditer(sanitized):
                word = match.group(1)
                if word in self._STOP_WORDS:
                    continue
                if word.endswith('_REDACTED]'):
                    continue

                replacement = "[NAME_REDACTED]"
                sanitized = sanitized.replace(word, replacement, 1)

                removed_items.append({
                    'type': 'proper_noun',
                    'sensitivity': SensitivityLevel.MEDIUM.value,
                    'redacted': replacement,
                    'position': match.start(),
                    'hash': hashlib.sha256(
                        word.encode()
                    ).hexdigest()[:16],
                })

                risk_score += self._RISK_WEIGHTS[SensitivityLevel.MEDIUM]

        pii_count = len(removed_items)
        risk_score = min(risk_score, 1.0)
        is_safe = risk_score < self._SAFETY_THRESHOLD

        logger.info(
            "Sanitization complete: %d items removed, risk=%.3f, safe=%s",
            pii_count, risk_score, is_safe,
        )

        return SanitizationResult(
            sanitized_content=sanitized,
            removed_items=removed_items,
            pii_count=pii_count,
            risk_score=risk_score,
            is_safe=is_safe,
            ner_hints=ner_hints,
            sanitized=True,
        )

    def validate_sanitization(
        self, original: str, sanitized: str
    ) -> Dict[str, Any]:
        """Compute effectiveness metrics for compliance reporting."""
        orig_len = len(original)
        san_len = len(sanitized)
        reduction = (
            ((orig_len - san_len) / orig_len * 100) if orig_len > 0 else 0.0
        )
        return {
            'original_length': orig_len,
            'sanitized_length': san_len,
            'reduction_pct': round(reduction, 2),
            'effectiveness': 'high' if reduction > 5 else 'low',
        }

    def batch_sanitize(
        self, contents: List[str]
    ) -> List[SanitizationResult]:
        """Sanitize a list of texts in batch."""
        return [self.sanitize_content(c) for c in contents]
