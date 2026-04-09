"""
Synapse Layer — Ecosystem Integrations

Official adapters for popular AI frameworks.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

# Lazy imports to avoid pulling in optional dependencies at import time.
# Users import directly from the submodule they need:
#   from synapse_memory.integrations.langchain_memory import SynapseChatMessageHistory
#   from synapse_memory.integrations.crewai_memory import SynapseCrewStorage

__all__ = ["SynapseChatMessageHistory", "SynapseCrewStorage"]


def __getattr__(name: str):
    if name == "SynapseChatMessageHistory":
        from .langchain_memory import SynapseChatMessageHistory
        return SynapseChatMessageHistory
    if name == "SynapseCrewStorage":
        from .crewai_memory import SynapseCrewStorage
        return SynapseCrewStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
