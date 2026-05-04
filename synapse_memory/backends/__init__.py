"""
Synapse Layer — Storage Backends

Pluggable persistence layer for SynapseMemory.

Available backends:
    - MemoryBackend:  In-memory (default, non-persistent)
    - SqliteBackend:  Zero-config local persistence via sqlite3
    - ForgeBackend:   Encrypted cloud via Forge API (AES-256-GCM)

Usage::

    from synapse_memory.backends import SqliteBackend
    memory = SynapseMemory(agent_id="my-agent", backend=SqliteBackend())

    # Encrypted cloud backend
    from synapse_memory.backends import ForgeBackend
    backend = ForgeBackend(api_key="sk_connect_...", encryption_key=b"\\x00"*32)

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .interface import StorageBackend
from .memory_backend import MemoryBackend
from .sqlite_backend import SqliteBackend
from .forge_backend import ForgeBackend

__all__ = [
    "StorageBackend",
    "MemoryBackend",
    "SqliteBackend",
    "ForgeBackend",
]
