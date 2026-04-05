# Changelog

## [1.0.4] - 2026-04-05

### Added — Semantic Privacy Guard™
- **DifferentialPrivacy engine** (`privacy.py`): Calibrated Gaussian noise
  injection on embedding vectors before pgvector upsert. Prevents semantic
  leakage through embedding-based inference attacks.
  - Configurable privacy budget (ε): default 0.5, range [0.01, 10.0]
  - Analytic Gaussian mechanism: σ = Δf · √(2·ln(1.25/δ)) / ε
  - L2 normalization post-noise to preserve cosine similarity semantics
  - SNR (Signal-to-Noise Ratio) metric in audit payload
- **SynapseMemory core** (`core.py`): Unified memory pipeline orchestrator.
  - `store()` method with mandatory sanitization + differential privacy
  - Full audit payload: `{sanitized: True, privacy_applied: True}`
  - Constructor flags: `sanitize_enabled`, `privacy_enabled`, `privacy_epsilon`,
    `aggressive_sanitize`
  - `recall()` method with semantic similarity search
- **Aggressive sanitizer mode**: Strips proper nouns (capitalized words) to
  prevent name-based inference attacks on embeddings.
- **New patterns**: Bearer tokens, AWS access key IDs, expanded regex coverage
  (12 precompiled patterns total)
- **Inline test suites** for sanitizer, privacy, and core modules

### Changed
- `SynapseSanitizer` now returns `sanitized: True` audit flag in result
- `SanitizationResult` includes SHA-256 hash of each redacted item for
  forensic audit trail
- Risk scoring includes per-item hashing for non-repudiation

### Security
- Embedding vectors are noise-injected before persistence — original semantic
  fingerprint cannot be reconstructed from stored vectors
- Proper noun stripping (aggressive mode) eliminates name-based correlation
  attacks across memory pools
- All flags are audit-ready for GDPR / LGPD compliance reporting

## [1.0.3] - 2026-04-02

### Added
- Python SDK public release
- AES-256-GCM encryption (client-side)
- MCP Server compatibility
- Neural Handover™ cross-model context transfer
- Trust Quotient™ automatic conflict resolution
- Comprehensive security documentation
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
- No hardcoded secrets in repository

## [1.0.0] - 2026-03-15

### Initial Release
- Zero-Knowledge Memory Layer
- Neural Handover™ technology
- Trust Quotient™ conflict resolution
- MCP Server compatibility
- Full test coverage

See git log for complete history.
