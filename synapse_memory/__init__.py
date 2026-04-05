"""
Synapse Memory — Zero-Knowledge Memory Layer for AI Agents

Giving Agents a Past. Giving Models a Soul.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .sanitizer import SynapseSanitizer, SanitizationResult, SensitivityLevel
from .privacy import DifferentialPrivacy, PrivacyResult
from .core import SynapseMemory, StoreResult, RecallResult
from .engine.validator import SynapseValidator, ValidationResult, IntentCategory

__version__ = "1.0.4"

__all__ = [
    # Core
    "SynapseMemory",
    "StoreResult",
    "RecallResult",
    # Sanitizer
    "SynapseSanitizer",
    "SanitizationResult",
    "SensitivityLevel",
    # Differential Privacy
    "DifferentialPrivacy",
    "PrivacyResult",
    # Validator
    "SynapseValidator",
    "ValidationResult",
    "IntentCategory",
]
