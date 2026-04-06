# Changelog

All notable changes to [Synapse Layer](https://github.com/SynapseLayer/synapse-layer) are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.6] — 2026-04-05

### 🎯 Summary

**Codename: Cognitive Security Protocol**

This release elevates Synapse Layer from a memory SDK to a **complete Cognitive Security Protocol for AI Agents**. Four proprietary security seals now protect every memory operation:

| Seal | Layer | Status |
|------|-------|--------|
| 🛡️ Semantic Privacy Guard™ | PII sanitization + SHA-256 forensic hashes | Production |
| 🔐 Differential Privacy | Gaussian noise on embeddings (ε-bounded) | Production |
| 🧠 Intelligent Intent Validation™ | Two-step confidence gate + self-healing | Production |
| ⚡ Persistence-First Neural Handover™ | JWT-signed vault-first cross-agent transfer | Production |

### Added

#### Comprehensive Test Suite (`tests/`)
- **158 pytest tests** across 6 test files covering all Cognitive Security layers
- **95% code coverage** (excluding inline `__main__` demos) verified via `pytest-cov`
- Test files: `test_sanitizer.py` (24), `test_privacy.py` (23), `test_validator.py` (41),
  `test_handover.py` (20), `test_core_integration.py` (26), `test_coverage_boost.py` (24)
- Security-specific tests: PII leakage prevention, embedding noise guarantees,
  similarity preservation under DP, forensic hash integrity, JWT tamper detection
- Integration tests: full store → sanitize → privacy → validate pipeline,
  cross-agent handover flow, self-healing during recall
- Edge case coverage: zero vectors, empty inputs, invalid epsilon/delta,
  max memories exceeded, expired tokens, grace period behavior
- Shared fixtures in `conftest.py` with deterministic seeds for reproducibility
- Run: `pytest -v` | Coverage: `pytest --cov=synapse_memory --cov-report=term-missing`

#### Persistence-First Neural Handover™ (`engine/handover.py`)
- **NeuralHandover engine**: Complete cross-agent context transfer system
  with vault-first persistence and multi-layer fault tolerance
- `create_handover(target_agent, user_id, scope, memory_filter)` —
  Packages memories through sanitize → validate → JWT sign pipeline,
  persists to Status Ledger as `PENDING` before any network operation
- `accept_handover(handover_id)` — Verifies JWT signature (HMAC-SHA256),
  validates agent identity, checks TTL, transitions `PENDING` → `ACCEPTED` → `COMPLETED`
- `fail_handover(handover_id, reason)` — Automatic fallback: creates
  Emergency Checkpoint with full context snapshot for manual or automated recovery
- `get_latest_handover(user_id)` — Retrieves most recent handover for a
  user with auto-expiry detection and grace period summary generation
- **HandoverStatus state machine**: `PENDING` → `ACCEPTED` → `COMPLETED` | `FAILED` | `EXPIRED`
  with strict transition rules and immutable audit trail
- **JWT Tokenization**: HMAC-SHA256 signed Synapse Handover Tokens (SHT)
  carrying `origin_agent`, `target_agent`, `user_id`, `scope`, `iat`, `exp`
- **Grace Period Protocol**: When TTL expires but within 15-minute grace
  window, auto-generates compact summary instead of returning raw context
- **Emergency Checkpoint**: On target agent failure, full context is
  preserved as a frozen checkpoint for forensic recovery
- **Immutable data contracts**: `HandoverToken`, `HandoverPackage`,
  `HandoverResult`, `HandoverStatus` (frozen dataclasses)

#### Intelligent Intent Validation™ (`engine/validator.py`)
- **Complete IntentCategory taxonomy**: `PREFERENCE`, `FACT`, `PROCEDURAL`,
  `BIO`, `EPHEMERAL`, `CRITICAL` (+ sentinel `UNKNOWN`, `INVALID`)
- **Two-step validation pipeline** in `validate_intent()`:
  - Step 1 — Agent Suggestion: keyword heuristic scoring across all categories
  - Step 2 — Synapse Validation: confidence gate (≥ 0.85), critical-keyword
    override, source-type assignment
- **Confidence contract**:
  - `confidence ≥ 0.85` → `source_type = "validated"`
  - `confidence < 0.85` → `source_type = "inference"` + `warning` string
  - Critical keyword hit → `source_type = "critical_override"`,
    `confidence_boost = 1.0`
- **19 critical keywords**: `emergency`, `breach`, `attack`, `ransomware`,
  `warrant`, `subpoena`, `exploit`, `vulnerability`, `incident`, `threat`,
  `unauthorized`, `compromise`, `malware`, `phishing`, `fraud`, `violation`,
  `compliance`, `audit`, `lawsuit`
- **Self-healing on recall**: `heal_conflicts()` detects semantically
  proximate memories (cosine ≥ 0.85) with conflicting categories and
  reclassifies via keyword consensus. Returns `SelfHealingResult` audit payload
- **`SelfHealingResult` dataclass**: `reclassified`, `original_category`,
  `new_category`, `reason`, `evidence_scores`
- **`RecallResult` enhanced**: now includes `intent`, `is_critical`, and
  optional `self_healing` metadata per result
- **Backward-compatible**: `intent_category` property alias preserved for
  v1.0.4 callers

#### Semantic Privacy Guard™ (`sanitizer.py`)
- **12 precompiled regex patterns**: emails, phone numbers, SSNs, CPFs,
  credit cards, IP addresses, dates of birth, Bearer tokens, AWS access
  key IDs, generic API keys, URLs, passport numbers
- **Aggressive sanitization mode**: Strips proper nouns (capitalized words)
  to prevent name-based correlation attacks across memory pools
- **SHA-256 forensic hashes**: Every redacted item produces a hash for
  non-repudiation audit trail
- **Risk scoring**: Weighted per sensitivity level (LOW, MEDIUM, HIGH, CRITICAL)

#### Differential Privacy (`privacy.py`)
- **Calibrated Gaussian noise**: σ = Δf · √(2·ln(1.25/δ)) / ε
- **Configurable privacy budget**: ε default 0.5, range [0.01, 10.0]
- **L2 normalization** post-noise to preserve cosine similarity semantics
- **SNR metric** in audit payload for privacy/utility tradeoff monitoring

### Changed

- `SynapseMemory.__init__()` now initializes both `SynapseValidator` and
  `NeuralHandover` engines alongside existing sanitizer and privacy modules
- `SynapseMemory.store()` passes `agent_confidence` to the validator,
  enabling two-step pipeline with merged confidence (40% heuristic + 60% agent)
- `SynapseMemory.recall()` runs self-healing pass on candidates before
  returning — conflicting categories are corrected in-place
- `validation_details` in `StoreResult` expanded: `final_intent`,
  `source_type`, `confidence_boost`, `warning`, `is_critical`,
  `self_healing_applied`, `healing_notes`
- `engine/__init__.py` exports all handover and validator types
- `__init__.py` exports full public API including handover types
- Version bumped to `1.0.6` across all modules
- README.md completely rewritten with TL;DR, competitive table, 4 seals,
  pricing, waitlist CTA, embedded changelog
- ARCHITECTURE.md updated with 2 Mermaid diagrams (state machine + sequence)
- SECURITY.md updated with all 4 security layers and v1.0.6 threat model

### Security

- **Handover tokens are HMAC-SHA256 signed** — tampering is cryptographically
  detectable before any memory import occurs
- **Agent identity verification** on `accept_handover()` prevents
  unauthorized cross-agent memory injection
- **Content sanitized and intent-validated before packaging** — handover
  payloads never contain raw PII, regardless of source agent behavior
- **Emergency Checkpoints preserve full context** for forensic recovery
  without exposing data to the transport layer
- **All state transitions logged** with timestamps for GDPR/LGPD/HIPAA
  compliance audit trail
- **Self-healing prevents category drift attacks** where adversaries store
  conflicting metadata to downgrade memory criticality over time
- **Differential Privacy on embeddings** prevents semantic inference attacks
  even with full database access
- **Semantic Privacy Guard™ is mandatory** — cannot be bypassed in the
  standard pipeline. PII sanitization runs before encryption, always.

### Migration Notes

- **No breaking changes.** v1.0.6 is fully backward-compatible with v1.0.4+
- New methods (`create_handover`, `accept_handover`, `fail_handover`,
  `get_latest_handover`) are additive — existing `store()` and `recall()`
  signatures unchanged
- `validation_details` dict in `StoreResult` has new keys but old keys
  remain present
- `RecallResult` has new optional fields (`intent`, `is_critical`,
  `self_healing`) that default to `None` for backward compatibility
- **Recommended**: Update to v1.0.6 and enable `aggressive_sanitize=True`
  for maximum PII protection

---

## [1.0.4] — 2026-04-05

### Added
- **DifferentialPrivacy engine** (`privacy.py`): Gaussian noise injection
- **SynapseMemory core** (`core.py`): Unified pipeline orchestrator
- **Aggressive sanitizer mode**: Proper noun stripping
- **New regex patterns**: Bearer tokens, AWS key IDs (12 total)
- Inline test suites for sanitizer, privacy, and core

### Changed
- `SynapseSanitizer` returns `sanitized: True` audit flag
- `SanitizationResult` includes SHA-256 hashes for forensic trail
- Risk scoring includes per-item hashing for non-repudiation

### Security
- Embedding vectors noise-injected before persistence
- Proper noun stripping eliminates name-based correlation attacks
- All flags audit-ready for GDPR/LGPD compliance

---

## [1.0.3] — 2026-04-02

### Added
- Python SDK public release
- AES-256-GCM encryption (client-side)
- MCP Server compatibility
- Neural Handover™ cross-model context transfer
- Trust Quotient™ automatic conflict resolution
- Security documentation
- Public GitHub repository launch
- Apache 2.0 open-source license
- GitHub branch protection + Secret Scanning
- Dependabot security alerts

### Fixed
- PyPI package structure
- Build pipeline
- Documentation clarity

### Security
- GitHub Secret Scanning + Push Protection enabled
- Branch protection on main
- Dependabot alerts enabled

---

## [1.0.0] — 2026-03-15

### Initial Release
- Zero-Knowledge Memory Layer architecture
- Neural Handover™ technology (prototype)
- Trust Quotient™ conflict resolution
- MCP Server compatibility
- Full test coverage

---

[1.0.6]: https://github.com/SynapseLayer/synapse-layer/compare/v1.0.4...v1.0.6
[1.0.4]: https://github.com/SynapseLayer/synapse-layer/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/SynapseLayer/synapse-layer/compare/v1.0.0...v1.0.3
[1.0.0]: https://github.com/SynapseLayer/synapse-layer/releases/tag/v1.0.0
