"""
Synapse Layer — Auto-Save Policy Engine

Determines WHAT and WHEN to save. Enforces security blocklists,
importance elevation, semantic deduplication, and OSS/PRO gating.

The policy pipeline is the first gate — events that fail policy
evaluation are never persisted or sent to embedding providers.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import os
import re
import time
import logging
from typing import Dict, List, Optional, Tuple

from .types import (
    AutoSaveEvent,
    PolicyDecision,
    ALL_PROJECTS,
    ALL_EVENT_TYPES,
)

logger = logging.getLogger("synapse.autosave.policy")

# ── Security Blocklist Patterns ───────────────────────────────────────
# Content matching ANY of these is ALWAYS blocked.
_BLOCK_PATTERNS: List[re.Pattern] = [
    re.compile(r'(?:api[_-]?key|apikey)[\s:="\']+[a-zA-Z0-9_\-]{20,}', re.I),
    re.compile(r'[Bb]earer\s+[a-zA-Z0-9_.\-]{20,}'),
    re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'gh[pousr]_[a-zA-Z0-9]{36,}'),
    re.compile(r'(?:password|passwd|pwd|secret)[\s:="\']+\S{8,}', re.I),
    re.compile(r'(?:postgres|mysql|mongodb|redis)://[^\s]{10,}', re.I),
    re.compile(r'-----BEGIN\s(?:RSA\s)?PRIVATE\sKEY-----'),
]

# Tags that trigger importance elevation
_ELEVATION_TAGS: frozenset[str] = frozenset({
    "launch", "monetization", "security", "funding", "acquisition",
    "partnership", "compliance", "audit",
})


class PolicyEngine:
    """Evaluate whether an AutoSaveEvent should be persisted.

    The engine applies a strict sequence of checks:
    1. Absolute security blocklist (secrets, tokens, keys)
    2. Project & type allowlist validation
    3. Importance floor (OSS vs PRO)
    4. Automatic importance elevation
    5. Semantic deduplication (recent event cache)
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        allowed_projects: Optional[frozenset[str]] = None,
        dedup_window_seconds: float = 60.0,
    ) -> None:
        self._mode = (mode or os.getenv("SYNAPSE_MODE", "oss")).lower()
        self._allowed_projects = allowed_projects or ALL_PROJECTS
        self._dedup_window = dedup_window_seconds
        # Recent event cache: (project, type, normalized_content) -> timestamp
        self._recent: Dict[Tuple[str, str, str], float] = {}

    # ── Public API ─────────────────────────────────────────────────────

    def evaluate(self, event: AutoSaveEvent) -> PolicyDecision:
        """Evaluate an event against all policy rules.

        Returns a PolicyDecision indicating whether the event should
        be saved, and if not, why it was blocked.
        """
        # 1. Security blocklist (absolute)
        block = self._check_security_block(event.content)
        if block:
            logger.warning("Policy BLOCKED: security trigger detected")
            return PolicyDecision(
                should_save=False,
                reason="security_blocked",
                adjusted_importance=0,
                blocked_reason=block,
            )

        # 2. Zero importance
        if event.importance <= 0:
            return PolicyDecision(
                should_save=False,
                reason="zero_importance",
                adjusted_importance=0,
                blocked_reason="Importance must be >= 1",
            )

        # 3. Project allowlist
        project_upper = event.project.strip().upper()
        if project_upper not in self._allowed_projects:
            return PolicyDecision(
                should_save=False,
                reason="project_not_allowed",
                adjusted_importance=0,
                blocked_reason=f"Project '{event.project}' not in allowlist",
            )

        # 4. Type allowlist
        if event.type not in ALL_EVENT_TYPES:
            return PolicyDecision(
                should_save=False,
                reason="type_not_allowed",
                adjusted_importance=0,
                blocked_reason=f"Type '{event.type}' not in allowlist",
            )

        # 5. Importance elevation
        adjusted = self._elevate_importance(event)

        # 6. OSS/PRO gate
        min_importance = 1 if self._mode == "pro" else 3
        if adjusted < min_importance:
            return PolicyDecision(
                should_save=False,
                reason=f"below_{self._mode}_threshold",
                adjusted_importance=adjusted,
                blocked_reason=(
                    f"Importance {adjusted} < {min_importance} "
                    f"({self._mode} mode)"
                ),
            )

        # 7. Semantic deduplication
        if self._is_duplicate(event):
            return PolicyDecision(
                should_save=False,
                reason="semantic_duplicate",
                adjusted_importance=adjusted,
                blocked_reason="Identical event within dedup window",
            )

        # All checks passed
        self._record_event(event)
        return PolicyDecision(
            should_save=True,
            reason="approved",
            adjusted_importance=adjusted,
        )

    # ── Internal Methods ───────────────────────────────────────────────

    @staticmethod
    def _check_security_block(content: str) -> Optional[str]:
        """Return a reason string if content matches any blocklist pattern."""
        for pattern in _BLOCK_PATTERNS:
            if pattern.search(content):
                return f"Matched security pattern: {pattern.pattern[:40]}..."
        return None

    @staticmethod
    def _elevate_importance(event: AutoSaveEvent) -> int:
        """Apply automatic importance elevation rules."""
        imp = event.importance

        # Type-based elevation
        if event.type == "[MILESTONE]":
            imp = max(imp, 4)
        elif event.type in ("[DECISION]", "[AUTO-DECISION]"):
            imp = max(imp, 3)
        elif event.type == "[ALERT]":
            imp = max(imp, 5)

        # Tag-based elevation
        event_tags = {t.lower() for t in event.tags}
        if event_tags & _ELEVATION_TAGS:
            imp = min(imp + 1, 5)

        return imp

    def _normalize(self, text: str) -> str:
        """Normalize text for dedup comparison."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _dedup_key(self, event: AutoSaveEvent) -> Tuple[str, str, str]:
        return (
            event.project.strip().upper(),
            event.type,
            self._normalize(event.content),
        )

    def _is_duplicate(self, event: AutoSaveEvent) -> bool:
        """Check if an identical event was recorded within the dedup window."""
        self._prune_expired()
        key = self._dedup_key(event)
        return key in self._recent

    def _record_event(self, event: AutoSaveEvent) -> None:
        """Record event in the recent cache."""
        key = self._dedup_key(event)
        self._recent[key] = time.time()

    def _prune_expired(self) -> None:
        """Remove expired entries from the recent cache."""
        cutoff = time.time() - self._dedup_window
        expired = [k for k, ts in self._recent.items() if ts < cutoff]
        for k in expired:
            del self._recent[k]
