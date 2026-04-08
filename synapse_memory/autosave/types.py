"""
Synapse Layer — Auto-Save Type Definitions

Canonical types for the autonomous memory persistence engine.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# ── Project & Type Enums ─────────────────────────────────────────────────

ProjectName = Literal[
    "OFFLY", "SYNAPSE_LAYER", "GOARQIA", "NEXUMI", "SAFEZAP_BRASIL",
]

EventType = Literal[
    "[AUTO-STRAT]", "[AUTO-OP]", "[MILESTONE]", "[DECISION]", "[ALERT]",
    "[AUTO-INSIGHT]", "[AUTO-DECISION]", "[AUTO-CONTEXT]", "[MANUAL]",
]

ALL_PROJECTS: frozenset[str] = frozenset({
    "OFFLY", "SYNAPSE_LAYER", "GOARQIA", "NEXUMI", "SAFEZAP_BRASIL",
})

ALL_EVENT_TYPES: frozenset[str] = frozenset({
    "[AUTO-STRAT]", "[AUTO-OP]", "[MILESTONE]", "[DECISION]", "[ALERT]",
    "[AUTO-INSIGHT]", "[AUTO-DECISION]", "[AUTO-CONTEXT]", "[MANUAL]",
})


# ── Core Data Classes ───────────────────────────────────────────────────

@dataclass
class AutoSaveEvent:
    """An event captured for autonomous persistence."""
    content: str
    project: str                                  # One of ALL_PROJECTS
    type: str                                     # One of ALL_EVENT_TYPES
    importance: int = 3                           # 1..5
    source: str = "auto"                          # Origin identifier
    tags: List[str] = field(default_factory=list)
    source_ref: Dict[str, Any] = field(default_factory=dict)
    redaction: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.importance = max(0, min(5, self.importance))


@dataclass(frozen=True)
class PolicyDecision:
    """Result of the policy engine evaluation."""
    should_save: bool
    reason: str
    adjusted_importance: int
    blocked_reason: Optional[str] = None


@dataclass
class SaveResult:
    """Outcome of an auto-save operation."""
    id: Optional[str]                             # UUID or None
    status: str                                   # saved|deduplicated|blocked|error
    project: str = ""
    type: str = ""
    importance: int = 0
    created_at: str = ""
    reason: str = ""                              # Explanation of outcome
