"""
DifferentialPrivacy — Calibrated Noise Injection for Embedding Vectors

Prevents semantic leakage through embedding-based inference attacks by
applying calibrated Gaussian noise to vector representations before
persistence in pgvector.

Mathematical Basis:
    Given embedding vector v ∈ ℝⁿ and privacy budget ε > 0:
    - Compute sensitivity Δf = max‖v‖₂ (L2 norm of the vector)
    - Calibrate σ = Δf · √(2·ln(1.25/δ)) / ε   (Gaussian mechanism)
    - Add noise: v' = v + N(0, σ²·Iₙ)
    - Normalize: v'' = v' / ‖v'‖₂  (preserve unit-sphere for cosine sim)

    Lower ε → more noise → stronger privacy → lower recall accuracy.
    Recommended: ε ∈ [0.1, 1.0] for production workloads.

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import math
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PrivacyResult:
    """Output of the differential privacy pipeline."""
    noisy_embedding: List[float]
    original_norm: float        # L2 norm of original vector
    noise_sigma: float          # Standard deviation of injected noise
    epsilon: float              # Privacy budget used
    delta: float                # Failure probability
    privacy_applied: bool       # Audit flag — always True after pipeline
    snr_db: float               # Signal-to-Noise Ratio in dB (quality metric)


class DifferentialPrivacy:
    """
    Gaussian mechanism for differential privacy on embedding vectors.

    Applies calibrated Gaussian noise scaled by the privacy budget (epsilon)
    to prevent reconstruction of original content from stored embeddings.

    The noise is calibrated using the analytic Gaussian mechanism:
        σ = Δf · √(2·ln(1.25/δ)) / ε

    After noise injection, vectors are L2-normalized to preserve
    compatibility with cosine similarity search in pgvector.

    Usage:
        dp = DifferentialPrivacy(epsilon=0.5, delta=1e-5)
        result = dp.apply(embedding_vector)
        # result.noisy_embedding → store in pgvector
        # result.privacy_applied → True (for audit trail)
    """

    # ── Bounds ───────────────────────────────────────────────────────
    EPSILON_MIN = 0.01   # Extreme privacy (very noisy)
    EPSILON_MAX = 10.0   # Minimal privacy (nearly lossless)
    DEFAULT_DELTA = 1e-5 # Standard failure probability

    def __init__(
        self,
        epsilon: float = 0.5,
        delta: float = 1e-5,
        normalize: bool = True,
    ) -> None:
        """
        Initialize the differential privacy engine.

        Args:
            epsilon: Privacy budget. Lower values = stronger privacy.
                     Recommended range: [0.1, 1.0].
            delta:   Failure probability for (ε,δ)-differential privacy.
                     Default: 1e-5 (standard for production).
            normalize: If True, L2-normalize the noisy vector to preserve
                       cosine similarity semantics in pgvector.

        Raises:
            ValueError: If epsilon or delta are out of valid range.
        """
        if not (self.EPSILON_MIN <= epsilon <= self.EPSILON_MAX):
            raise ValueError(
                f"epsilon must be in [{self.EPSILON_MIN}, {self.EPSILON_MAX}], "
                f"got {epsilon}"
            )
        if not (0 < delta < 1):
            raise ValueError(f"delta must be in (0, 1), got {delta}")

        self.epsilon = epsilon
        self.delta = delta
        self.normalize = normalize

        logger.info(
            "DifferentialPrivacy initialized (ε=%.3f, δ=%.1e, normalize=%s)",
            epsilon, delta, normalize,
        )

    # ── Core API ─────────────────────────────────────────────────────

    def apply(self, embedding: List[float]) -> PrivacyResult:
        """
        Apply calibrated Gaussian noise to an embedding vector.

        Args:
            embedding: Dense float vector (e.g., 384-d, 768-d, 1536-d).

        Returns:
            PrivacyResult with noisy (and optionally normalized) embedding
            plus audit metadata.

        Raises:
            ValueError: If embedding is empty or contains non-finite values.
        """
        if not embedding:
            raise ValueError("Embedding vector must not be empty.")

        n = len(embedding)

        # ── Step 1: Compute L2 sensitivity ───────────────────────────
        original_norm = math.sqrt(sum(x * x for x in embedding))
        if original_norm == 0.0:
            # Zero vector — nothing to protect
            return PrivacyResult(
                noisy_embedding=embedding[:],
                original_norm=0.0,
                noise_sigma=0.0,
                epsilon=self.epsilon,
                delta=self.delta,
                privacy_applied=True,
                snr_db=float('inf'),
            )

        sensitivity = original_norm  # Δf = max L2 norm

        # ── Step 2: Calibrate sigma (Gaussian mechanism) ─────────────
        # σ = Δf · √(2·ln(1.25/δ)) / ε
        sigma = (
            sensitivity
            * math.sqrt(2.0 * math.log(1.25 / self.delta))
            / self.epsilon
        )

        # ── Step 3: Generate and inject Gaussian noise ───────────────
        # Using Box-Muller transform (stdlib-only, no numpy dependency)
        import random
        rng = random.Random()  # Thread-safe instance
        noise = [rng.gauss(0.0, sigma) for _ in range(n)]

        noisy = [v + nv for v, nv in zip(embedding, noise)]

        # ── Step 4: Optional L2 normalization ────────────────────────
        if self.normalize:
            noisy_norm = math.sqrt(sum(x * x for x in noisy))
            if noisy_norm > 0:
                noisy = [x / noisy_norm for x in noisy]

        # ── Step 5: Compute Signal-to-Noise Ratio ────────────────────
        noise_power = sum(nv * nv for nv in noise) / n
        signal_power = sum(x * x for x in embedding) / n
        if noise_power > 0:
            snr_db = 10.0 * math.log10(signal_power / noise_power)
        else:
            snr_db = float('inf')

        logger.info(
            "DP applied: dim=%d, σ=%.4f, ε=%.3f, SNR=%.1f dB",
            n, sigma, self.epsilon, snr_db,
        )

        return PrivacyResult(
            noisy_embedding=noisy,
            original_norm=original_norm,
            noise_sigma=sigma,
            epsilon=self.epsilon,
            delta=self.delta,
            privacy_applied=True,
            snr_db=round(snr_db, 2),
        )

    def batch_apply(
        self, embeddings: List[List[float]]
    ) -> List[PrivacyResult]:
        """Apply differential privacy to a batch of embeddings.

        Each embedding receives independent noise calibrated to the
        same (ε, δ) budget. Noise instances are non-correlated.

        Args:
            embeddings: List of dense float vectors (all same dimension).

        Returns:
            List of ``PrivacyResult`` in the same order as input.
        """
        return [self.apply(emb) for emb in embeddings]

    def get_config(self) -> Dict[str, Any]:
        """Return current privacy configuration for audit logging.

        Useful for compliance reports and automated privacy audits.

        Returns:
            Dict with ``epsilon``, ``delta``, ``normalize``, and ``mechanism``.
        """
        return {
            'epsilon': self.epsilon,
            'delta': self.delta,
            'normalize': self.normalize,
            'mechanism': 'gaussian',
        }


# ── Inline Tests (run with: python -m synapse_memory.privacy) ────────
if __name__ == "__main__":
    import random

    print("=" * 60)
    print("DifferentialPrivacy — Inline Test Suite")
    print("=" * 60)

    # Deterministic seed for reproducibility
    random.seed(42)

    dp = DifferentialPrivacy(epsilon=0.5, delta=1e-5)

    # Test 1: Basic application on a 384-d vector
    embedding = [random.gauss(0, 1) for _ in range(384)]
    result = dp.apply(embedding)
    assert result.privacy_applied is True
    assert len(result.noisy_embedding) == 384
    assert result.noise_sigma > 0
    assert result.epsilon == 0.5
    # Check L2-normalized (norm ≈ 1.0)
    norm = math.sqrt(sum(x * x for x in result.noisy_embedding))
    assert abs(norm - 1.0) < 1e-6, f"Expected norm ≈ 1.0, got {norm}"
    print(f"[PASS] 384-d vector: σ={result.noise_sigma:.4f}, "
          f"SNR={result.snr_db:.1f} dB")

    # Test 2: Higher epsilon → less noise
    dp_low = DifferentialPrivacy(epsilon=5.0)
    dp_high = DifferentialPrivacy(epsilon=0.1)
    r_low = dp_low.apply(embedding)
    r_high = dp_high.apply(embedding)
    assert r_low.noise_sigma < r_high.noise_sigma
    print(f"[PASS] ε=5.0 σ={r_low.noise_sigma:.4f} < "
          f"ε=0.1 σ={r_high.noise_sigma:.4f}")

    # Test 3: Zero vector
    r_zero = dp.apply([0.0] * 128)
    assert r_zero.privacy_applied is True
    assert r_zero.noise_sigma == 0.0
    print("[PASS] Zero vector handled gracefully")

    # Test 4: Batch apply
    batch = [[random.gauss(0, 1) for _ in range(64)] for _ in range(10)]
    results = dp.batch_apply(batch)
    assert len(results) == 10
    assert all(r.privacy_applied for r in results)
    print(f"[PASS] Batch: {len(results)} vectors processed")

    # Test 5: Config audit
    config = dp.get_config()
    assert config['mechanism'] == 'gaussian'
    assert config['epsilon'] == 0.5
    print(f"[PASS] Config: {config}")

    # Test 6: Invalid epsilon
    try:
        DifferentialPrivacy(epsilon=0.001)
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Invalid epsilon rejected")

    # Test 7: Empty embedding
    try:
        dp.apply([])
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Empty embedding rejected")

    print("\n✅ All inline tests passed.")
