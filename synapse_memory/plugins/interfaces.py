"""
Synapse Layer — Core Plugin Interfaces

Immutable contracts that define extension points for the
autonomous memory persistence engine. All strategies follow
the Strategy pattern for clean OSS/PRO separation.

These interfaces are STABLE — changes require a major version bump.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, runtime_checkable

# Avoid circular imports — use string annotation for AutoSaveEvent
# and import the type only for type-checking.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from synapse_memory.autosave.types import AutoSaveEvent


# ── Data Types ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class RedactionResult:
    """Result of a content redaction operation."""
    content: str
    pii_redacted: bool = False
    secrets_filtered: bool = False
    redaction_level: str = "strict"


# ── Strategy Interfaces ─────────────────────────────────────────────

@runtime_checkable
class ImportanceScorer(Protocol):
    """Score event importance on a normalized 0.0–1.0 scale.

    Implementations may use heuristics, ML models, or domain-specific
    logic to evaluate the significance of an event.
    """

    def score(self, event: "AutoSaveEvent") -> float:
        """Return importance score in [0.0, 1.0].

        Parameters
        ----------
        event : AutoSaveEvent
            The event to score.

        Returns
        -------
        float
            Normalized importance, where 0.0 = irrelevant, 1.0 = critical.
        """
        ...


@runtime_checkable
class ConflictResolver(Protocol):
    """Resolve conflicts when multiple events compete for persistence.

    Given a list of potentially conflicting events, select the one
    that should be persisted.
    """

    def resolve(self, events: List["AutoSaveEvent"]) -> "AutoSaveEvent":
        """Choose the winning event from a list of candidates.

        Parameters
        ----------
        events : list[AutoSaveEvent]
            Two or more competing events.

        Returns
        -------
        AutoSaveEvent
            The selected winner.
        """
        ...


@runtime_checkable
class DedupStrategy(Protocol):
    """Determine whether an event is a duplicate of recent events.

    Implementations may use hash-based, semantic, or ML-powered
    deduplication strategies.
    """

    def is_duplicate(
        self,
        event: "AutoSaveEvent",
        recent_events: List["AutoSaveEvent"],
    ) -> bool:
        """Check if event duplicates any recent event.

        Parameters
        ----------
        event : AutoSaveEvent
            The candidate event.
        recent_events : list[AutoSaveEvent]
            Events saved within the dedup window.

        Returns
        -------
        bool
            True if the event should be considered a duplicate.
        """
        ...


@runtime_checkable
class RedactionStrategy(Protocol):
    """Redact sensitive content before persistence.

    Extension point for advanced redaction strategies
    (entity-aware, context-sensitive, ML-powered).
    """

    def redact(self, content: str) -> RedactionResult:
        """Redact sensitive information from content.

        Parameters
        ----------
        content : str
            Raw content to redact.

        Returns
        -------
        RedactionResult
            Redacted content with metadata.
        """
        ...


# ── Plugin Bundle Interface ─────────────────────────────────────────

@runtime_checkable
class SynapseProPlugin(Protocol):
    """Bundle interface for PRO plugin injection.

    A conforming plugin exposes strategy instances that the
    AutoSaveEngine will use in place of OSS defaults.

    Install ``synapse-layer-pro`` to enable.
    """

    importance_scorer: ImportanceScorer
    conflict_resolver: ConflictResolver
    dedup_strategy: DedupStrategy
