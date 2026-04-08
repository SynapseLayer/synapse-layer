"""
Synapse Layer — Core Abstractions & Plugin Architecture

Immutable contracts for extensibility:
    - ImportanceScorer
    - ConflictResolver
    - DedupStrategy
    - RedactionStrategy

Default OSS implementations provided. PRO implementations
injected dynamically via ``synapse_memory_pro`` package.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .interfaces import (
    ImportanceScorer,
    ConflictResolver,
    DedupStrategy,
    RedactionStrategy,
    RedactionResult,
    SynapseProPlugin,
)
from .defaults import (
    DefaultImportanceScorer,
    DefaultConflictResolver,
    DefaultDedupStrategy,
)
from .plugin_loader import load_pro_plugin

__all__ = [
    # Interfaces
    "ImportanceScorer",
    "ConflictResolver",
    "DedupStrategy",
    "RedactionStrategy",
    "RedactionResult",
    "SynapseProPlugin",
    # Defaults
    "DefaultImportanceScorer",
    "DefaultConflictResolver",
    "DefaultDedupStrategy",
    # Loader
    "load_pro_plugin",
]
