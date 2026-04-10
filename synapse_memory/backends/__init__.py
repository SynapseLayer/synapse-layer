"""
Synapse Layer — Storage Backends

Pluggable persistence layer for SynapseMemory.

Available backends:
    - MemoryBackend:  In-memory (default, non-persistent)
    - SqliteBackend:  Zero-config local persistence via sqlite3

Usage::

    from synapse_memory.backends import SqliteBackend
    memory = SynapseMemory(agent_id="my-agent", backend=SqliteBackend())

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .interface import StorageBackend
from .memory_backend import MemoryBackend
from .sqlite_backend import SqliteBackend

__all__ = [
    "StorageBackend",
    "MemoryBackend",
    "SqliteBackend",
]
