"""
Synapse Memory — Zero-Knowledge Memory Layer for AI Agents

Giving Agents a Past. Giving Models a Soul.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .sanitizer import SynapseSanitizer, SanitizationResult, SensitivityLevel
from .privacy import DifferentialPrivacy, PrivacyResult
from .core import SynapseMemory, StoreResult, RecallResult
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

__version__ = "1.0.7"

import os as _os
SYNAPSE_MODE: str = _os.environ.get("SYNAPSE_MODE", "oss").lower()
"""Runtime mode: 'oss' (default) or 'pro'.

Set ``SYNAPSE_MODE=pro`` to unlock extended keyword registries,
adaptive confidence curves, and multi-factor Trust Quotient™.
See https://forge.synapselayer.org/docs/pro for details.
"""

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
    "SelfHealingResult",
    "IntentCategory",
    # Neural Handover
    "NeuralHandover",
    "HandoverResult",
    "HandoverPackage",
    "HandoverStatus",
    "HandoverToken",
]
