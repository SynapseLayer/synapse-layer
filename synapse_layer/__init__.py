"""
Synapse Layer — Persistent Memory Infrastructure for AI Agents

This module provides the public API surface matching the package name.
``from synapse_layer import ...`` works as expected after
``pip install synapse-layer``.

Canonical implementation lives in ``synapse_memory``.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

# Re-export everything from synapse_memory so that
# `from synapse_layer import SynapseMemory` works.
from synapse_memory import *  # noqa: F401,F403
from synapse_memory import __version__, __all__ as _upstream_all

# ── Public Aliases ───────────────────────────────────────────
# SynapseClient is the documented public-facing name.
# Internally it is SynapseMemory — same class, same API.
from synapse_memory.core import SynapseMemory as SynapseClient  # noqa: F401

__all__ = [*_upstream_all, "SynapseClient"]
