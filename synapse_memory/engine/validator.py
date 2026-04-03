"""
SynapseValidator — Intelligent Intent Validation with Self-Healing

Categorizes content intent, validates confidence, promotes to CRITICAL automatically.
Padrão: Infraestrutura Bancária

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)


class IntentCategory(Enum):
    """Complete Intent Classification"""
    
    # Core categories
    USER_PROFILE = "user_profile"        # User preferences, settings, metadata
    CONVERSATION = "conversation"        # Dialog, chat history, interaction
    DECISION = "decision"                # Important choices, commitments
    KNOWLEDGE = "knowledge"              # Facts, learning, information
    PREFERENCE = "preference"            # Taste, style, likes/dislikes
    
    # Critical categories (auto-promoted)
    MEDICAL = "medical"                  # Health records, medications
    FINANCIAL = "financial"              # Transactions, accounts, payments
    LEGAL = "legal"                      # Contracts, agreements, disputes
    SECURITY = "security"                # Passwords, access, authentication
    
    # Special
    UNKNOWN = "unknown"                  # Unclassifiable
    INVALID = "invalid"                  # Malformed or spam


@dataclass
class ValidationResult:
    """Output of validation pipeline"""
    intent_category: IntentCategory
    confidence: float           # 0.0–1.0
    is_critical: bool          # Automatically true for MEDICAL, FINANCIAL, LEGAL, SECURITY
    critical_keywords: List[str]  # Keywords that triggered critical classification
    validation_score: float     # 0.0–1.0 (higher = more valid)
    is_valid: bool              # True if validation_score >= 0.85
    self_healing_applied: bool  # True if validation corrected issues
    healing_notes: List[str]    # What was fixed


class SynapseValidator:
    """
    Production-grade intent validator with:
    - Complete IntentCategory enum (7 core + 4 critical)
    - Threshold 0.85 for confidence
    - Automatic CRITICAL promotion
    - Self-healing capabilities
    """

    # Keywords for intent classification (comprehensive)
    INTENT_KEYWORDS = {
        IntentCategory.USER_PROFILE: [
            'name', 'age', 'location', 'occupation', 'background',
            'preference', 'like', 'dislike', 'interest', 'hobby',
            'education', 'experience', 'career'
        ],
        IntentCategory.CONVERSATION: [
            'said', 'told', 'mentioned', 'discussed', 'talked',
            'conversation', 'dialog', 'chat', 'message', 'replied',
            'asked', 'answered', 'question', 'response'
        ],
        IntentCategory.DECISION: [
            'decided', 'committed', 'agreed', 'committed', 'planned',
            'going to', 'will', 'promise', 'objective', 'goal',
            'choose', 'selected', 'determined', 'resolved'
        ],
        IntentCategory.KNOWLEDGE: [
            'learned', 'discovered', 'studied', 'read', 'knows',
            'fact', 'information', 'data', 'understand', 'concept',
            'research', 'analysis', 'theory', 'principle'
        ],
        IntentCategory.PREFERENCE: [
            'prefer', 'favorite', 'enjoy', 'love', 'hate',
            'style', 'taste', 'like', 'choice', 'best',
            'worst', 'prefer', 'ideal', 'want', 'desire'
        ],
        IntentCategory.MEDICAL: [
            'doctor', 'hospital', 'medication', 'disease', 'symptom',
            'treatment', 'prescription', 'health', 'medical', 'diagnosis',
            'patient', 'nurse', 'surgery', 'vaccine', 'allergy',
            'therapy', 'clinical', 'mental', 'depression', 'anxiety'
        ],
        IntentCategory.FINANCIAL: [
            'bank', 'account', 'payment', 'transaction', 'credit',
            'debit', 'invoice', 'salary', 'income', 'expense',
            'investment', 'stock', 'crypto', 'loan', 'mortgage',
            'money', 'revenue', 'profit', 'loss', 'budget'
        ],
        IntentCategory.LEGAL: [
            'contract', 'agreement', 'lawsuit', 'lawyer', 'court',
            'legal', 'law', 'regulation', 'compliance', 'liability',
            'patent', 'copyright', 'trademark', 'dispute', 'attorney'
        ],
        IntentCategory.SECURITY: [
            'password', 'token', 'secret', 'private', 'secure',
            'encryption', 'authentication', 'access', 'permission',
            'credential', 'api_key', '2fa', 'mfa', 'security',
            'breach', 'attack', 'vulnerable', 'exploit'
        ],
    }

    # Critical keywords that auto-promote intent
    CRITICAL_KEYWORDS = [
        'emergency', 'urgent', 'critical', 'danger', 'alert',
        'breach', 'attack', 'hack', 'fraud', 'abuse',
        'immediate', 'now', 'asap', 'today', 'severe'
    ]

    CONFIDENCE_THRESHOLD = 0.85  # Immutable threshold

    def __init__(self, enable_self_healing: bool = True):
        """
        Initialize validator.
        
        Args:
            enable_self_healing: If True, apply automatic fixes to low-confidence content
        """
        self.enable_self_healing = enable_self_healing
        logger.info(f"SynapseValidator initialized (self_healing={enable_self_healing})")

    def validate_intent(self, content: str) -> ValidationResult:
        """
        Validate content intent and confidence.
        
        Args:
            content: Sanitized text content
            
        Returns:
            ValidationResult with category, confidence, criticality
        """
        if not content or not isinstance(content, str):
            return ValidationResult(
                intent_category=IntentCategory.INVALID,
                confidence=0.0,
                is_critical=False,
                critical_keywords=[],
                validation_score=0.0,
                is_valid=False,
                self_healing_applied=False,
                healing_notes=[]
            )

        content_lower = content.lower()
        
        # Check for critical keywords first (auto-promote)
        found_critical_keywords = [
            kw for kw in self.CRITICAL_KEYWORDS 
            if kw in content_lower
        ]
        
        if found_critical_keywords:
            return ValidationResult(
                intent_category=IntentCategory.SECURITY,  # Default to SECURITY for critical
                confidence=1.0,
                is_critical=True,
                critical_keywords=found_critical_keywords,
                validation_score=1.0,
                is_valid=True,
                self_healing_applied=False,
                healing_notes=['Critical keywords detected - auto-promoted to CRITICAL']
            )

        # Classify intent by keyword matching
        intent_scores: Dict[IntentCategory, float] = {}
        
        for category, keywords in self.INTENT_KEYWORDS.items():
            # Count matching keywords
            matches = sum(1 for kw in keywords if kw in content_lower)
            
            # Calculate confidence (matches / total keywords)
            if len(keywords) > 0:
                score = matches / len(keywords)
                intent_scores[category] = score

        # Find best match
        if intent_scores:
            best_category = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_category]
        else:
            best_category = IntentCategory.UNKNOWN
            confidence = 0.0

        # Check if category is inherently critical
        is_critical = best_category in (
            IntentCategory.MEDICAL,
            IntentCategory.FINANCIAL,
            IntentCategory.LEGAL,
            IntentCategory.SECURITY
        )

        # Validation score (same as confidence for now)
        validation_score = confidence
        is_valid = validation_score >= self.CONFIDENCE_THRESHOLD

        # Self-healing: if confidence is low, try to improve it
        healing_notes = []
        self_healing_applied = False
        
        if self.enable_self_healing and not is_valid and confidence > 0.5:
            # Attempt to disambiguate
            if any(word in content_lower for word in ['medical', 'health', 'doctor', 'hospital']):
                best_category = IntentCategory.MEDICAL
                is_critical = True
                validation_score = min(validation_score + 0.1, 1.0)
                self_healing_applied = True
                healing_notes.append("Detected medical context - upgraded to MEDICAL category")
            
            elif any(word in content_lower for word in ['payment', 'transaction', 'bank', 'account']):
                best_category = IntentCategory.FINANCIAL
                is_critical = True
                validation_score = min(validation_score + 0.1, 1.0)
                self_healing_applied = True
                healing_notes.append("Detected financial context - upgraded to FINANCIAL category")
            
            elif any(word in content_lower for word in ['contract', 'legal', 'lawyer', 'court']):
                best_category = IntentCategory.LEGAL
                is_critical = True
                validation_score = min(validation_score + 0.1, 1.0)
                self_healing_applied = True
                healing_notes.append("Detected legal context - upgraded to LEGAL category")

        logger.info(
            f"Intent validation: {best_category.value} "
            f"(confidence={confidence:.2f}, critical={is_critical})"
        )

        return ValidationResult(
            intent_category=best_category,
            confidence=confidence,
            is_critical=is_critical,
            critical_keywords=found_critical_keywords,
            validation_score=validation_score,
            is_valid=is_valid,
            self_healing_applied=self_healing_applied,
            healing_notes=healing_notes
        )

    def batch_validate(self, contents: List[str]) -> List[ValidationResult]:
        """
        Validate multiple contents in batch.
        """
        return [self.validate_intent(content) for content in contents]
