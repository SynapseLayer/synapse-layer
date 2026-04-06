"""
Shared fixtures for Synapse Layer Cognitive Security test suite.

Provides pre-configured instances, sample data, and deterministic
random seeds for reproducible testing across all modules.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import math
import random
import pytest
from typing import List, Dict, Any

from synapse_memory.sanitizer import SynapseSanitizer
from synapse_memory.privacy import DifferentialPrivacy
from synapse_memory.engine.validator import SynapseValidator, IntentCategory
from synapse_memory.engine.handover import NeuralHandover, HandoverStatus
from synapse_memory.core import SynapseMemory


# ══ Constants ════════════════════════════════════════════════════════════

SIGNING_KEY = "test-key-for-unit-tests-256-bit-min!"
EMBEDDING_DIM = 384


# ══ Sanitizer Fixtures ══════════════════════════════════════════════════

@pytest.fixture
def sanitizer_standard() -> SynapseSanitizer:
    """Standard sanitizer (aggressive=False)."""
    return SynapseSanitizer(aggressive=False)


@pytest.fixture
def sanitizer_aggressive() -> SynapseSanitizer:
    """Aggressive sanitizer with proper-noun stripping."""
    return SynapseSanitizer(aggressive=True)


# ══ Privacy Fixtures ════════════════════════════════════════════════════

@pytest.fixture
def dp_default() -> DifferentialPrivacy:
    """Default DP engine (ε=0.5)."""
    return DifferentialPrivacy(epsilon=0.5)


@pytest.fixture
def dp_strict() -> DifferentialPrivacy:
    """Strict DP engine (ε=0.1) — maximum noise."""
    return DifferentialPrivacy(epsilon=0.1)


@pytest.fixture
def dp_relaxed() -> DifferentialPrivacy:
    """Relaxed DP engine (ε=5.0) — minimal noise."""
    return DifferentialPrivacy(epsilon=5.0)


# ══ Embedding Fixtures ══════════════════════════════════════════════════

@pytest.fixture
def sample_embedding() -> List[float]:
    """Deterministic 384-d embedding for reproducible tests."""
    rng = random.Random(42)
    return [rng.gauss(0, 1) for _ in range(EMBEDDING_DIM)]


@pytest.fixture
def zero_embedding() -> List[float]:
    """Zero vector (edge case)."""
    return [0.0] * EMBEDDING_DIM


# ══ Validator Fixtures ══════════════════════════════════════════════════

@pytest.fixture
def validator() -> SynapseValidator:
    """Validator with self-healing enabled."""
    return SynapseValidator(enable_self_healing=True)


@pytest.fixture
def validator_no_healing() -> SynapseValidator:
    """Validator with self-healing disabled."""
    return SynapseValidator(enable_self_healing=False)


# ══ Handover Fixtures ══════════════════════════════════════════════════

@pytest.fixture
def handover_engine() -> NeuralHandover:
    """Handover engine with short TTL for test speed."""
    return NeuralHandover(signing_key=SIGNING_KEY, ttl=3600)


@pytest.fixture
def sample_memories() -> List[Dict[str, Any]]:
    """Standard memory payload for handover tests."""
    return [
        {"content": "User prefers dark mode", "confidence": 0.95},
        {"content": "Project deadline is Friday", "confidence": 0.90},
        {"content": "Important security audit scheduled", "confidence": 0.99},
    ]


# ══ Core Fixtures ═══════════════════════════════════════════════════════

@pytest.fixture
def memory_default() -> SynapseMemory:
    """Full-pipeline SynapseMemory instance."""
    return SynapseMemory(agent_id="test-agent")


@pytest.fixture
def memory_aggressive() -> SynapseMemory:
    """SynapseMemory with aggressive sanitization."""
    return SynapseMemory(
        agent_id="aggressive-agent",
        aggressive_sanitize=True,
    )


@pytest.fixture
def memory_no_privacy() -> SynapseMemory:
    """SynapseMemory with DP disabled."""
    return SynapseMemory(
        agent_id="no-dp-agent",
        privacy_enabled=False,
    )


@pytest.fixture
def memory_raw() -> SynapseMemory:
    """SynapseMemory with sanitization disabled."""
    return SynapseMemory(
        agent_id="raw-agent",
        sanitize_enabled=False,
    )


# ══ Helpers ══════════════════════════════════════════════════════════

def l2_norm(v: List[float]) -> float:
    """Compute L2 norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = l2_norm(a)
    nb = l2_norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
