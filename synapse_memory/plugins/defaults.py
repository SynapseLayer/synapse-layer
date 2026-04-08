"""
Synapse Layer — Default OSS Implementations

Baseline strategies that provide predictable, "good enough" behavior
without any proprietary logic. Designed for transparency and simplicity.

PRO implementations (ML-powered scoring, semantic dedup, conflict
resolution) are available via ``synapse-layer-pro``.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import List

from synapse_memory.autosave.types import AutoSaveEvent


class DefaultImportanceScorer:
    """Baseline importance scorer.

    Normalizes the integer importance (0–5) to a 0.0–1.0 float.
    No heuristics, no ML — pure linear mapping.
    """

    def score(self, event: AutoSaveEvent) -> float:
        """Return event.importance / 5.0, clamped to [0.0, 1.0]."""
        raw = max(0, min(5, event.importance))
        return round(raw / 5.0, 2)


class DefaultConflictResolver:
    """Baseline conflict resolver.

    When multiple events compete, keeps the most recent one
    (highest importance as tiebreaker).
    """

    def resolve(self, events: List[AutoSaveEvent]) -> AutoSaveEvent:
        """Return the event with highest importance; last wins on tie."""
        if not events:
            raise ValueError("Cannot resolve empty event list")
        return max(events, key=lambda e: (e.importance, id(e)))


class DefaultDedupStrategy:
    """Baseline deduplication via SHA-256 content hash.

    Compares normalized (project + content + type) hashes.
    No semantic analysis, no embedding similarity.
    """

    def is_duplicate(
        self,
        event: AutoSaveEvent,
        recent_events: List[AutoSaveEvent],
    ) -> bool:
        """True if any recent event has identical normalized hash."""
        event_hash = self._hash(event)
        return any(self._hash(r) == event_hash for r in recent_events)

    @staticmethod
    def _hash(event: AutoSaveEvent) -> str:
        """SHA-256 of normalized project + content + type."""
        normalized = re.sub(r'\s+', ' ', event.content.strip().lower())
        payload = json.dumps(
            {
                "project": event.project.upper(),
                "content": normalized,
                "type": event.type,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
