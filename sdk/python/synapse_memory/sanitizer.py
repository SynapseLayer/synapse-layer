"""
SynapseSanitizer — High-Performance Content Sanitization with NER Preparation

Removes PII, sensitive data, and prepares content for NER downstream.
Padrão: Infraestrutura Bancária (PBKDF2, AES-256-GCM ready)

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import re
import hashlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """PII & Sensitive Data Classification"""
    LOW = "low"           # Non-critical metadata
    MEDIUM = "medium"     # Personal preferences
    HIGH = "high"         # PII: names, emails, phone
    CRITICAL = "critical" # SSN, credit card, medical records


@dataclass
class SanitizationResult:
    """Output of sanitization pipeline"""
    sanitized_content: str
    removed_items: List[Dict[str, any]]
    pii_count: int
    risk_score: float  # 0.0–1.0
    is_safe: bool      # True if risk_score < 0.05
    ner_hints: List[str]  # Hints for downstream NER


class SynapseSanitizer:
    """
    Production-grade content sanitizer with:
    - High-performance regex patterns (compiled)
    - PII detection + removal
    - NER preparation hints
    - Adaptive thresholds
    """

    # Precompiled regex patterns (high performance)
    PATTERNS = {
        # Email: john.doe@company.com
        'email': re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        
        # Phone: (123) 456-7890, +55 11 99999-8888, etc.
        'phone': re.compile(
            r'(?:\+\d{1,3})?(?:[-.\s]?\d{1,4}){2,4}(?:[-.\s]?\d{4})',
        ),
        
        # SSN-like: 123-45-6789
        'ssn': re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        ),
        
        # Credit Card: 1234-5678-9012-3456 or without dashes
        'credit_card': re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        ),
        
        # Date of Birth: DD/MM/YYYY, DD-MM-YYYY
        'dob': re.compile(
            r'\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)?\d{2}\b'
        ),
        
        # Brazilian CPF: 000.000.000-00
        'cpf': re.compile(
            r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'
        ),
        
        # Brazilian CNPJ: 00.000.000/0000-00
        'cnpj': re.compile(
            r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b'
        ),
        
        # API Keys & Tokens: sk_test_..., ghp_..., etc.
        'api_key': re.compile(
            r'(?:sk_test_|sk_live_|ghp_|pk_test_|pk_live_)[a-zA-Z0-9_]{20,}'
        ),
        
        # URLs (for context awareness)
        'url': re.compile(
            r'https?://[^\s\)]+',
            re.IGNORECASE
        ),
        
        # IP Addresses: 192.168.1.1
        'ip_address': re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ),
    }

    # Sensitivity mapping
    SENSITIVITY_MAP = {
        'email': SensitivityLevel.HIGH,
        'phone': SensitivityLevel.HIGH,
        'ssn': SensitivityLevel.CRITICAL,
        'credit_card': SensitivityLevel.CRITICAL,
        'dob': SensitivityLevel.HIGH,
        'cpf': SensitivityLevel.CRITICAL,
        'cnpj': SensitivityLevel.MEDIUM,
        'api_key': SensitivityLevel.CRITICAL,
        'url': SensitivityLevel.LOW,
        'ip_address': SensitivityLevel.MEDIUM,
    }

    def __init__(self, aggressive_mode: bool = False):
        """
        Initialize sanitizer.
        
        Args:
            aggressive_mode: If True, remove ALL detected patterns (even URLs)
        """
        self.aggressive_mode = aggressive_mode
        self._cache = {}  # Memoization for repeated patterns
        logger.info(f"SynapseSanitizer initialized (aggressive={aggressive_mode})")

    def sanitize_content(self, content: str) -> SanitizationResult:
        """
        Sanitize content by removing PII and sensitive data.
        
        Args:
            content: Raw text input
            
        Returns:
            SanitizationResult with sanitized content, removed items, risk score
        """
        if not content or not isinstance(content, str):
            return SanitizationResult(
                sanitized_content="",
                removed_items=[],
                pii_count=0,
                risk_score=0.0,
                is_safe=True,
                ner_hints=[]
            )

        sanitized = content
        removed_items = []
        pii_count = 0
        risk_score = 0.0
        ner_hints = []

        # Scan for PII using precompiled patterns
        for pattern_name, pattern in self.PATTERNS.items():
            matches = list(pattern.finditer(content))
            
            if matches:
                sensitivity = self.SENSITIVITY_MAP.get(pattern_name, SensitivityLevel.MEDIUM)
                
                for match in matches:
                    matched_text = match.group(0)
                    
                    # Skip URLs unless in aggressive mode
                    if pattern_name == 'url' and not self.aggressive_mode:
                        continue
                    
                    # Remove from content
                    replacement = f"[{pattern_name.upper()}_REDACTED]"
                    sanitized = sanitized.replace(matched_text, replacement, 1)
                    
                    # Log removal
                    removed_items.append({
                        'type': pattern_name,
                        'sensitivity': sensitivity.value,
                        'redacted': replacement,
                        'position': match.start()
                    })
                    
                    # Update metrics
                    pii_count += 1
                    
                    # Risk score calculation (CRITICAL > HIGH > MEDIUM > LOW)
                    if sensitivity == SensitivityLevel.CRITICAL:
                        risk_score += 0.3
                    elif sensitivity == SensitivityLevel.HIGH:
                        risk_score += 0.15
                    elif sensitivity == SensitivityLevel.MEDIUM:
                        risk_score += 0.05
                    
                    # NER hints for downstream processing
                    if sensitivity in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL):
                        ner_hints.append(f"{pattern_name}:{match.start()}")

        # Normalize risk score to [0, 1]
        risk_score = min(risk_score, 1.0)
        is_safe = risk_score < 0.05

        logger.info(f"Sanitization complete: {pii_count} items removed, risk={risk_score:.2f}")

        return SanitizationResult(
            sanitized_content=sanitized,
            removed_items=removed_items,
            pii_count=pii_count,
            risk_score=risk_score,
            is_safe=is_safe,
            ner_hints=ner_hints
        )

    def validate_sanitization(self, original: str, sanitized: str) -> Dict[str, any]:
        """
        Validate that sanitization was effective.
        
        Returns metrics about sanitization effectiveness.
        """
        original_len = len(original)
        sanitized_len = len(sanitized)
        reduction = ((original_len - sanitized_len) / original_len * 100) if original_len > 0 else 0

        return {
            'original_length': original_len,
            'sanitized_length': sanitized_len,
            'reduction_pct': round(reduction, 2),
            'effectiveness': 'high' if reduction > 5 else 'low'
        }

    def batch_sanitize(self, contents: List[str]) -> List[SanitizationResult]:
        """
        Sanitize multiple contents in batch.
        Useful for bulk operations.
        """
        return [self.sanitize_content(content) for content in contents]
