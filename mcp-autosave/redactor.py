"""
Synapse Layer — PII & Secrets Redactor

Strict-mode redaction layer that MUST run before any content is sent to
embedding providers or stored in the database. Implements the Semantic
Privacy Guard™ pipeline for the Auto-Save MCP Bridge.

Security Contract:
    - No PII/secrets ever reach the embedding provider.
    - No raw content is ever logged (only IDs + counters).
    - Redaction metadata is attached to every memory for audit.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger("synapse.redactor")


@dataclass(frozen=True)
class RedactionResult:
    """Immutable result of the redaction pipeline."""
    content: str                   # Redacted content (safe for storage/embedding)
    pii_redacted: bool             # True if any PII was found and removed
    secrets_filtered: bool         # True if any secrets were found and removed
    redaction_level: str           # 'strict' or 'standard'
    pii_count: int                 # Number of PII matches redacted
    secret_count: int              # Number of secret matches redacted
    categories_found: List[str]    # Which categories triggered


# ── Pattern Registry ───────────────────────────────────────────────────────
# OSS baseline: functional detection set.
# Enterprise extends with domain-specific patterns (40+ categories).
# ────────────────────────────────────────────────────────────────────────

_PII_PATTERNS: Dict[str, re.Pattern] = {
    'email': re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ),
    'phone_br': re.compile(
        r'(?:\+55\s?)?\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}',
    ),
    'phone_intl': re.compile(
        r'\+\d{1,3}[\s.-]?\d{6,14}',
    ),
    'cpf': re.compile(
        r'\d{3}\.\d{3}\.\d{3}-\d{2}',
    ),
    'cnpj': re.compile(
        r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',
    ),
    'ssn': re.compile(
        r'\d{3}-\d{2}-\d{4}',
    ),
    'credit_card': re.compile(
        r'\b(?:\d[ -]*?){13,19}\b',
    ),
    'ip_address': re.compile(
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    ),
}

_SECRET_PATTERNS: Dict[str, re.Pattern] = {
    'api_key': re.compile(
        r'(?:api[_-]?key|apikey)[\s:="\']+[a-zA-Z0-9_\-]{20,}',
        re.IGNORECASE,
    ),
    'bearer_token': re.compile(
        r'[Bb]earer\s+[a-zA-Z0-9_.\-]+',
    ),
    'aws_key': re.compile(
        r'(?:AKIA|ASIA)[A-Z0-9]{16}',
    ),
    'openai_key': re.compile(
        r'sk-[a-zA-Z0-9]{20,}',
    ),
    'supabase_key': re.compile(
        r'eyJ[a-zA-Z0-9_\-]{30,}\.[a-zA-Z0-9_\-]{30,}\.[a-zA-Z0-9_\-]{30,}',
    ),
    'github_token': re.compile(
        r'gh[pousr]_[a-zA-Z0-9]{36,}',
    ),
    'password_field': re.compile(
        r'(?:password|passwd|pwd|secret)[\s:="\']+\S{6,}',
        re.IGNORECASE,
    ),
    'private_endpoint': re.compile(
        r'https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)[:\d/]*',
    ),
    'connection_string': re.compile(
        r'(?:postgres|mysql|mongodb|redis)://[^\s]+',
        re.IGNORECASE,
    ),
}


def redact(content: str, level: str = "strict") -> RedactionResult:
    """Run the full PII + secrets redaction pipeline.

    Parameters
    ----------
    content : str
        Raw content to redact.
    level : str
        'strict' (default) — redact all detected patterns.
        'standard' — redact only high-risk patterns.

    Returns
    -------
    RedactionResult
        Redacted content + audit metadata.
    """
    if not content or not isinstance(content, str):
        return RedactionResult(
            content=content or "",
            pii_redacted=False,
            secrets_filtered=False,
            redaction_level=level,
            pii_count=0,
            secret_count=0,
            categories_found=[],
        )

    working = content
    pii_count = 0
    secret_count = 0
    categories: List[str] = []

    # Stage 1: Secrets (higher priority — redact first)
    for name, pattern in _SECRET_PATTERNS.items():
        matches = pattern.findall(working)
        if matches:
            secret_count += len(matches)
            categories.append(f"secret:{name}")
            working = pattern.sub(f"[REDACTED:{name.upper()}]", working)

    # Stage 2: PII
    for name, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(working)
        if matches:
            pii_count += len(matches)
            categories.append(f"pii:{name}")
            working = pattern.sub(f"[REDACTED:{name.upper()}]", working)

    # SECURITY: Never log content, only counts
    if pii_count > 0 or secret_count > 0:
        logger.info(
            "Redaction complete: pii=%d, secrets=%d, categories=%s",
            pii_count, secret_count, categories,
        )

    return RedactionResult(
        content=working,
        pii_redacted=pii_count > 0,
        secrets_filtered=secret_count > 0,
        redaction_level=level,
        pii_count=pii_count,
        secret_count=secret_count,
        categories_found=categories,
    )
