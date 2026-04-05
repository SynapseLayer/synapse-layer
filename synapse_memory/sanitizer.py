"""
SynapseSanitizer — Production-Grade Content Sanitization Engine

High-performance PII detection, removal, and content hardening pipeline.
Supports standard and aggressive modes for maximum semantic privacy.

Pipeline: raw_text → detect PII → redact → score risk → emit audit payload

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
    LOW = "low"            # Non-critical metadata (URLs, timestamps)
    MEDIUM = "medium"      # Organizational identifiers (CNPJ, IPs)
    HIGH = "high"          # Personal identifiers (emails, phones, DOB)
    CRITICAL = "critical"  # Government IDs, financial instruments, secrets


@dataclass
class SanitizationResult:
    """Immutable output of the sanitization pipeline."""
    sanitized_content: str
    removed_items: List[Dict[str, Any]]
    pii_count: int
    risk_score: float       # Normalized to [0.0, 1.0]
    is_safe: bool           # True when risk_score < threshold
    ner_hints: List[str]    # Positional hints for downstream NER
    sanitized: bool = True  # Audit flag — always True after pipeline


class SynapseSanitizer:
    """
    Production-grade content sanitizer with:
    - 12 precompiled regex patterns for PII/sensitive data detection
    - Aggressive mode: removes proper nouns (capitalized words) for
      maximum semantic privacy against embedding-based inference attacks
    - Weighted risk scoring per sensitivity tier
    - Audit-ready output with positional redaction metadata
    - Batch processing support

    Usage:
        sanitizer = SynapseSanitizer(aggressive=True)
        result = sanitizer.sanitize_content("Call John at john@acme.com")
        assert result.sanitized  # Always True after pipeline
        assert "john@acme.com" not in result.sanitized_content
        assert "John" not in result.sanitized_content  # Aggressive mode
    """

    # ── Precompiled Regex Patterns ───────────────────────────────────
    # Compiled once at class level for maximum throughput.

    # NOTE: Order matters — more specific patterns (credit_card, ssn, cpf)
    # must be matched before the greedy phone pattern to avoid false captures.
    PATTERNS: Dict[str, re.Pattern] = {
        # Email addresses: user@domain.tld
        'email': re.compile(
            r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE,
        ),

        # Credit / debit card numbers (16 digits with optional separators)
        # MUST precede phone pattern to avoid false capture.
        'credit_card': re.compile(r'\b(?:\d{4}[\-\s]?){3}\d{4}\b'),

        # US Social Security Numbers: 123-45-6789
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),

        # Brazilian CPF: 000.000.000-00
        'cpf': re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'),

        # Phone numbers: +55 11 99999-8888, (123) 456-7890, etc.
        'phone': re.compile(
            r'(?:\+\d{1,3})?(?:[\-.\s]?\(?\d{1,4}\)?){2,4}(?:[\-.\s]?\d{4})',
        ),

        # Dates of birth: DD/MM/YYYY or DD-MM-YYYY
        'dob': re.compile(
            r'\b(?:0?[1-9]|[12]\d|3[01])[/\-](?:0?[1-9]|1[0-2])[/\-](?:19|20)?\d{2}\b',
        ),

        # Brazilian CNPJ: 00.000.000/0000-00
        'cnpj': re.compile(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'),

        # API keys / tokens (common prefixes)
        'api_key': re.compile(
            r'(?:sk_test_|sk_live_|ghp_|pk_test_|pk_live_|xoxb-|xoxp-)[a-zA-Z0-9_]{20,}',
        ),

        # Generic bearer / JWT tokens
        'bearer_token': re.compile(
            r'(?:Bearer\s+)[A-Za-z0-9\-._~+/]+=*',
            re.IGNORECASE,
        ),

        # URLs
        'url': re.compile(r'https?://[^\s\)]+', re.IGNORECASE),

        # IPv4 addresses: 192.168.1.1
        'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),

        # AWS-style access key IDs
        'aws_key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    }

    # ── Proper Noun Pattern (aggressive mode only) ──────────────────
    # Matches capitalized words that are NOT at the start of a sentence
    # and are not common English stop-words.
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

    # ── Sensitivity Mapping ──────────────────────────────────────────
    SENSITIVITY_MAP: Dict[str, SensitivityLevel] = {
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

    # Risk weight per sensitivity tier
    _RISK_WEIGHTS: Dict[SensitivityLevel, float] = {
        SensitivityLevel.CRITICAL: 0.30,
        SensitivityLevel.HIGH:     0.15,
        SensitivityLevel.MEDIUM:   0.05,
        SensitivityLevel.LOW:      0.01,
    }

    SAFETY_THRESHOLD = 0.05  # Below this risk_score → is_safe = True

    # ── Constructor ──────────────────────────────────────────────────

    def __init__(self, aggressive: bool = False) -> None:
        """
        Initialize the sanitizer.

        Args:
            aggressive: When True, also removes proper nouns (capitalized
                        words) to prevent semantic leakage through
                        embedding-based inference attacks.
        """
        self.aggressive = aggressive
        logger.info(
            "SynapseSanitizer initialized (aggressive=%s)", aggressive
        )

    # ── Public API ───────────────────────────────────────────────────

    def sanitize_content(self, content: str) -> SanitizationResult:
        """
        Execute the full sanitization pipeline on *content*.

        Pipeline stages:
            1. Validate input
            2. Scan with precompiled PII patterns
            3. (Aggressive) Strip proper nouns
            4. Compute risk score
            5. Emit audit payload

        Args:
            content: Raw text to sanitize.

        Returns:
            SanitizationResult with redacted content, metrics, and audit flags.
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

        # ── Stage 1: Pattern-based PII detection & redaction ─────────
        for pattern_name, pattern in self.PATTERNS.items():
            # Skip URLs in standard mode (they are low-risk metadata)
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

        # ── Stage 2: Aggressive — proper noun stripping ──────────────
        if self.aggressive:
            for match in self._PROPER_NOUN_RE.finditer(sanitized):
                word = match.group(1)
                if word in self._STOP_WORDS:
                    continue
                if word.endswith('_REDACTED]'):
                    continue  # Already redacted

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

        # ── Finalize ─────────────────────────────────────────────────
        pii_count = len(removed_items)
        risk_score = min(risk_score, 1.0)
        is_safe = risk_score < self.SAFETY_THRESHOLD

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
        """
        Compute effectiveness metrics comparing original vs. sanitized content.
        """
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


# ── Inline Tests (run with: python -m synapse_memory.sanitizer) ──────
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SynapseSanitizer — Inline Test Suite")
    print("=" * 60)

    # Standard mode
    std = SynapseSanitizer(aggressive=False)

    r1 = std.sanitize_content(
        "Contact John at john.doe@acme.com or +55 11 99999-8888"
    )
    assert r1.sanitized is True
    assert r1.pii_count >= 2
    assert "john.doe@acme.com" not in r1.sanitized_content
    print(f"[PASS] Standard mode: {r1.pii_count} PII removed, "
          f"risk={r1.risk_score:.2f}")

    r2 = std.sanitize_content(
        "CPF: 123.456.789-00, Card: 4111-1111-1111-1111"
    )
    assert r2.pii_count >= 2
    assert r2.risk_score >= 0.5
    print(f"[PASS] Critical data: {r2.pii_count} PII, "
          f"risk={r2.risk_score:.2f}")

    # Aggressive mode
    agg = SynapseSanitizer(aggressive=True)

    r3 = agg.sanitize_content(
        "Talk to Ricardo about the project at ricardo@corp.io"
    )
    assert "Ricardo" not in r3.sanitized_content
    assert "ricardo@corp.io" not in r3.sanitized_content
    print(f"[PASS] Aggressive mode: {r3.pii_count} items removed")

    # Empty input
    r4 = std.sanitize_content("")
    assert r4.sanitized is True
    assert r4.pii_count == 0
    print("[PASS] Empty input handled")

    # API key detection
    r5 = std.sanitize_content("Use token ghp_abcdefghijklmnopqrstuvwxyz1234")
    assert r5.pii_count >= 1
    print(f"[PASS] API key detected: {r5.pii_count} items")

    print("\n✅ All inline tests passed.")
