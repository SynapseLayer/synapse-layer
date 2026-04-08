"""
Synapse Layer — Auto-Save Memory Engine

Autonomous memory persistence for AI agents. Detects milestones,
decisions, and strategic events — then saves them with built-in
PII redaction, deduplication, and async embedding generation.

Usage:
    from synapse_memory.autosave import AutoSaveEngine, AutoSaveEvent

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .types import AutoSaveEvent, PolicyDecision, SaveResult
from .engine import AutoSaveEngine
from .policy import PolicyEngine
from .triggers import TriggerDetector
from .formatter import EventFormatter

__all__ = [
    "AutoSaveEngine",
    "AutoSaveEvent",
    "SaveResult",
    "PolicyDecision",
    "PolicyEngine",
    "TriggerDetector",
    "EventFormatter",
]
