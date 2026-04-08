"""
Synapse Layer — Auto-Save Trigger Detector

Autonomously detects milestones, decisions, alerts, and strategic events
in free-form text. Produces AutoSaveEvent instances for the engine.

Detection categories:
    - JSON classification blocks ([AUTO-STRAT], [AUTO-OP])
    - Milestone phrases (deployed, launched, first customer, etc.)
    - Decision phrases (decided to, strategy is, going with, etc.)
    - Alert phrases (security issue, breach, critical bug, etc.)

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import re
import json
import logging
from typing import List, Optional, Set

from .types import AutoSaveEvent, ALL_PROJECTS

logger = logging.getLogger("synapse.autosave.triggers")

# ── Trigger Pattern Registries ────────────────────────────────────────
# OSS baseline triggers. Enterprise extends with domain-specific sets.

_MILESTONE_PATTERNS: List[re.Pattern] = [
    re.compile(r'\b(?:deployed|launched|shipped|released)\b', re.I),
    re.compile(r'\bfirst\s+(?:paying\s+)?customer\b', re.I),
    re.compile(r'\b(?:PR|pull\s+request)\s+merged\b', re.I),
    re.compile(r'\bv\d+\.\d+(?:\.\d+)?\b', re.I),
    re.compile(r'\bmilestone\b', re.I),
    re.compile(r'\bfirst\s+flight\b', re.I),
    re.compile(r'\bgone\s+live\b', re.I),
    re.compile(r'\bpublished\s+(?:to|on)\b', re.I),
]

_DECISION_PATTERNS: List[re.Pattern] = [
    re.compile(r'\bdecided\s+to\b', re.I),
    re.compile(r'\bwe\s+will\b', re.I),
    re.compile(r'\bstrategy\s+is\b', re.I),
    re.compile(r'\bgoing\s+with\b', re.I),
    re.compile(r'\bfinal\s+decision\b', re.I),
    re.compile(r'\bchose\s+to\b', re.I),
    re.compile(r'\bpivot(?:ing)?\s+to\b', re.I),
]

_ALERT_PATTERNS: List[re.Pattern] = [
    re.compile(r'\bsecurity\s+issue\b', re.I),
    re.compile(r'\b(?:data\s+)?breach\b', re.I),
    re.compile(r'\bcritical\s+bug\b', re.I),
    re.compile(r'\bdata\s+leak\b', re.I),
    re.compile(r'\burgent\b', re.I),
    re.compile(r'\bincident\b', re.I),
    re.compile(r'\bdowntime\b', re.I),
]

# JSON classification block pattern
_JSON_CLASSIFICATION_RE = re.compile(
    r'\{[^}]*"classification"\s*:\s*"(\[AUTO-(?:STRAT|OP|INSIGHT|DECISION|CONTEXT)\])"[^}]*\}',
    re.I | re.DOTALL,
)

# Project mention patterns
_PROJECT_PATTERNS = {
    project: re.compile(r'\b' + re.escape(project) + r'\b', re.I)
    for project in ALL_PROJECTS
}
# Also match shortened forms
_PROJECT_PATTERNS["SAFEZAP_BRASIL"] = re.compile(
    r'\b(?:SAFEZAP_BRASIL|SAFEZAP|SafeZap)\b', re.I,
)


class TriggerDetector:
    """Detect auto-save triggers in free-form text.

    Scans content for milestone phrases, decision language, alert
    indicators, and structured JSON classification blocks.
    Returns a list of AutoSaveEvent instances.
    """

    def __init__(
        self,
        default_project: str = "SYNAPSE_LAYER",
        default_source: str = "auto",
    ) -> None:
        self._default_project = default_project
        self._default_source = default_source

    def detect(
        self,
        text: str,
        source: Optional[str] = None,
        project_override: Optional[str] = None,
    ) -> List[AutoSaveEvent]:
        """Scan text and return detected auto-save events.

        Parameters
        ----------
        text : str
            Free-form text to analyze.
        source : str | None
            Override source identifier.
        project_override : str | None
            Force a specific project (skip detection).

        Returns
        -------
        list[AutoSaveEvent]
            Detected events (may be empty if no triggers found).
        """
        if not text or not isinstance(text, str):
            return []

        events: List[AutoSaveEvent] = []
        src = source or self._default_source
        project = project_override or self._detect_project(text)
        tags = self._extract_tags(text)

        # 1. JSON classification blocks (highest priority)
        json_events = self._detect_json_blocks(text, project, src, tags)
        events.extend(json_events)

        # 2. Alert triggers (highest severity)
        if self._matches_any(text, _ALERT_PATTERNS):
            events.append(AutoSaveEvent(
                content=text,
                project=project,
                type="[ALERT]",
                importance=5,
                source=src,
                tags=tags + ["alert"],
            ))

        # 3. Milestone triggers
        elif self._matches_any(text, _MILESTONE_PATTERNS):
            events.append(AutoSaveEvent(
                content=text,
                project=project,
                type="[MILESTONE]",
                importance=4,
                source=src,
                tags=tags + ["milestone"],
            ))

        # 4. Decision triggers
        elif self._matches_any(text, _DECISION_PATTERNS):
            events.append(AutoSaveEvent(
                content=text,
                project=project,
                type="[DECISION]",
                importance=3,
                source=src,
                tags=tags + ["decision"],
            ))

        # SECURITY: Never log content, only event counts
        if events:
            logger.info(
                "Triggers detected: count=%d, project=%s, types=%s",
                len(events), project,
                [e.type for e in events],
            )

        return events

    # ── Internal Methods ───────────────────────────────────────────────

    def _detect_project(self, text: str) -> str:
        """Detect project name from text content."""
        for project, pattern in _PROJECT_PATTERNS.items():
            if pattern.search(text):
                return project
        return self._default_project

    def _detect_json_blocks(
        self, text: str, project: str, source: str, tags: List[str],
    ) -> List[AutoSaveEvent]:
        """Extract structured JSON classification blocks."""
        events: List[AutoSaveEvent] = []
        for match in _JSON_CLASSIFICATION_RE.finditer(text):
            classification = match.group(1).upper()
            # Try to parse the full JSON block for extra metadata
            try:
                block = json.loads(match.group(0))
                content = block.get("content", block.get("summary", text))
                importance = int(block.get("importance", 3))
                extra_tags = block.get("tags", [])
            except (json.JSONDecodeError, ValueError):
                content = text
                importance = 3
                extra_tags = []

            events.append(AutoSaveEvent(
                content=content,
                project=project,
                type=classification,
                importance=importance,
                source=source,
                tags=tags + extra_tags + [classification.strip("[]").lower()],
            ))
        return events

    @staticmethod
    def _matches_any(text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any pattern in the list."""
        return any(p.search(text) for p in patterns)

    @staticmethod
    def _extract_tags(text: str) -> List[str]:
        """Extract top keywords as tags from content."""
        # Simple keyword extraction: words 4+ chars, deduplicated, top 5
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Remove common stopwords
        stopwords = {
            'that', 'this', 'with', 'from', 'have', 'been',
            'will', 'were', 'they', 'their', 'what', 'when',
            'where', 'which', 'about', 'would', 'could', 'should',
            'some', 'them', 'than', 'into', 'also', 'just',
            'more', 'very', 'each', 'much', 'your', 'only',
        }
        filtered: list[str] = []
        seen: Set[str] = set()
        for w in words:
            if w not in stopwords and w not in seen:
                seen.add(w)
                filtered.append(w)
            if len(filtered) >= 5:
                break
        return filtered
