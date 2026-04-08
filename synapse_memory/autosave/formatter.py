"""
Synapse Layer — Auto-Save Event Formatter

Produces canonical payloads for database insertion.
Ensures consistent structure across all auto-save operations.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

from typing import Any, Dict

from .types import AutoSaveEvent

_ENGINE_VERSION = "1.0.0"


class EventFormatter:
    """Format AutoSaveEvent into canonical database payloads."""

    def __init__(self, synapse_version: str = "1.0.7") -> None:
        self._synapse_version = synapse_version

    def format(self, event: AutoSaveEvent, content_override: str = "") -> Dict[str, Any]:
        """Produce a canonical payload for insertion.

        Parameters
        ----------
        event : AutoSaveEvent
            The event to format.
        content_override : str
            If provided, replaces event.content (e.g., redacted version).

        Returns
        -------
        dict
            Ready-to-insert payload with content, metadata, and project.
        """
        return {
            "content": content_override or event.content,
            "metadata": {
                "type": event.type,
                "importance": event.importance,
                "source": event.source,
                "tags": event.tags,
                "source_ref": event.source_ref,
                "redaction": event.redaction,
                "synapse_version": self._synapse_version,
                "autosave_engine": _ENGINE_VERSION,
            },
            "project": event.project.strip().upper(),
        }
