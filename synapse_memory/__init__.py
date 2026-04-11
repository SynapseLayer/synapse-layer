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
from .backends import StorageBackend, MemoryBackend, SqliteBackend
from .crypto import SynapseCrypto
from .wrapper import remember
from .autosave import AutoSaveEngine, AutoSaveEvent, SaveResult
from .plugins import (
    ImportanceScorer,
    ConflictResolver,
    DedupStrategy,
    RedactionStrategy,
    SynapseProPlugin,
    DefaultImportanceScorer,
    DefaultConflictResolver,
    DefaultDedupStrategy,
    load_pro_plugin,
)

__version__ = "1.1.4"

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
    # Integrations (lazy — import from synapse_memory.integrations)
    # "SynapseChatMessageHistory",
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
    # Crypto
    "SynapseCrypto",
    # Wrapper
    "remember",
    # Storage Backends
    "StorageBackend",
    "MemoryBackend",
    "SqliteBackend",
    # Auto-Save
    "AutoSaveEngine",
    "AutoSaveEvent",
    "SaveResult",
    # Plugin Architecture
    "ImportanceScorer",
    "ConflictResolver",
    "DedupStrategy",
    "RedactionStrategy",
    "SynapseProPlugin",
    "DefaultImportanceScorer",
    "DefaultConflictResolver",
    "DefaultDedupStrategy",
    "load_pro_plugin",
]
