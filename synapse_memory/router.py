"""
Synapse Memory — RecallRouter

Intelligent recall-mode routing for the Synapse Layer SDK.
Detects intent from natural-language queries and routes to the
optimal recall strategy: temporal, semantic, priority, or hybrid.

Usage:
    from synapse_memory.router import RecallRouter, RecallMode

    router = RecallRouter()
    mode   = router.detect("what did I say yesterday?")
    # => RecallMode.TEMPORAL

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


# ── Recall Modes ──────────────────────────────────────────────

class RecallMode(str, Enum):
    """Supported recall routing strategies."""
    AUTO     = "auto"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    PRIORITY = "priority"
    HYBRID   = "hybrid"


# ── Keyword registries ────────────────────────────────────────

TEMPORAL_KEYWORDS: list[str] = [
    # English — aligned with recall-router.ts
    "last", "latest", "recent", "most recent", "newest",
    "just now", "today", "yesterday", "this week", "moments ago",
    "minutes ago", "hours ago", "what did i just",
    "last week", "last month", "recently", "earlier today",
    "this morning", "last night", "few days ago",
    "chronological", "timeline", "history",
    "when did", "sequence", "order", "progression",
    # pt-BR — aligned with recall-router.ts
    "última", "ultimo", "último", "mais recente", "recente", "agora", "hoje",
    "acabei", "acabou", "ontem", "esta semana", "esta hora",
    "há pouco", "pouco atrás", "minutos atrás", "horas atrás",
    "semana passada", "mês passado", "recentemente",
    "cronológico", "cronológica", "histórico", "quando",
]

PRIORITY_KEYWORDS: list[str] = [
    # English — aligned with recall-router.ts
    "critical", "important", "priority", "urgent", "must",
    "never forget", "essential", "vital", "mandatory", "high priority",
    "must know", "key decision", "blocking", "milestone", "crucial",
    # pt-BR — aligned with recall-router.ts
    "crítico", "critico", "importante", "urgente", "prioridade",
    "nunca esquecer", "essencial", "vital", "obrigatório",
    "crítica", "decisão chave", "bloqueante", "crucial",
]


# ── Detection helpers ─────────────────────────────────────────

def _build_pattern(keywords: Sequence[str]) -> re.Pattern[str]:
    """Build a case-insensitive alternation pattern."""
    escaped = [re.escape(kw) for kw in sorted(keywords, key=len, reverse=True)]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


_TEMPORAL_RE = _build_pattern(TEMPORAL_KEYWORDS)
_PRIORITY_RE = _build_pattern(PRIORITY_KEYWORDS)


def detect_recall_mode(query: str) -> RecallMode:
    """Auto-detect the best recall mode from a natural-language query.

    Precedence: temporal > priority > semantic (default).
    Temporal always wins when the query expresses recency intent.
    """
    if _TEMPORAL_RE.search(query):
        return RecallMode.TEMPORAL
    if _PRIORITY_RE.search(query):
        return RecallMode.PRIORITY
    return RecallMode.SEMANTIC


def resolve_recall_mode(mode: RecallMode | str, query: str = "") -> RecallMode:
    """Resolve a mode value — 'auto' triggers detection, unknown → semantic."""
    if isinstance(mode, str):
        try:
            mode = RecallMode(mode.lower())
        except ValueError:
            return RecallMode.SEMANTIC
    if mode == RecallMode.AUTO:
        return detect_recall_mode(query)
    return mode


def is_valid_recall_mode(value: str) -> bool:
    """Check whether *value* is a recognised RecallMode string."""
    try:
        RecallMode(value.lower())
        return True
    except (ValueError, AttributeError):
        return False


# ── Hybrid scoring ────────────────────────────────────────────

def compute_hybrid_score(
    semantic_score: float = 0.0,
    recency_score: float = 0.0,
    tq_score: float = 0.0,
    *,
    w_semantic: float = 0.5,
    w_recency: float = 0.3,
    w_tq: float = 0.2,
) -> float:
    """Weighted blend: ``w_semantic * semantic + w_recency * recency + w_tq * tq``."""
    return w_semantic * semantic_score + w_recency * recency_score + w_tq * tq_score


# ── RecallRouter (stateful convenience wrapper) ───────────────

@dataclass
class RecallRouter:
    """High-level router that wraps detection + resolution.

    Example::

        router = RecallRouter()
        result = router.route("what happened yesterday?", mode="auto")
        print(result.mode)  # RecallMode.TEMPORAL
    """

    default_mode: RecallMode = RecallMode.AUTO

    # Allow custom keyword lists (pro tier)
    extra_temporal_keywords: list[str] = field(default_factory=list)
    extra_priority_keywords: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Rebuild patterns if custom keywords provided
        if self.extra_temporal_keywords:
            all_temporal = TEMPORAL_KEYWORDS + self.extra_temporal_keywords
            self._temporal_re = _build_pattern(all_temporal)
        else:
            self._temporal_re = _TEMPORAL_RE

        if self.extra_priority_keywords:
            all_priority = PRIORITY_KEYWORDS + self.extra_priority_keywords
            self._priority_re = _build_pattern(all_priority)
        else:
            self._priority_re = _PRIORITY_RE

    def detect(self, query: str) -> RecallMode:
        """Detect mode from query using this router's keyword sets."""
        if self._temporal_re.search(query):
            return RecallMode.TEMPORAL
        if self._priority_re.search(query):
            return RecallMode.PRIORITY
        return RecallMode.SEMANTIC

    def route(
        self,
        query: str,
        *,
        mode: RecallMode | str | None = None,
    ) -> "RouteResult":
        """Resolve mode and return a RouteResult."""
        effective = mode or self.default_mode
        resolved = resolve_recall_mode(effective, query)
        if resolved == RecallMode.AUTO:
            resolved = self.detect(query)
        return RouteResult(mode=resolved, query=query)


@dataclass(frozen=True)
class RouteResult:
    """Immutable result of a route() call."""
    mode: RecallMode
    query: str

    def to_dict(self) -> Dict[str, Any]:
        return {"mode": self.mode.value, "query": self.query}


__all__ = [
    "RecallMode",
    "RecallRouter",
    "RouteResult",
    "detect_recall_mode",
    "resolve_recall_mode",
    "is_valid_recall_mode",
    "compute_hybrid_score",
    "TEMPORAL_KEYWORDS",
    "PRIORITY_KEYWORDS",
]
