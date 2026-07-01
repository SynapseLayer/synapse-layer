# Changelog

## [2.4.4] - 2026-07-01

### Fixed
- Restore mandatory `mcp-name` ownership marker in README for Official MCP Registry validation.
- No functional or security changes; retains all v2.4.3 remediations.

## [2.4.3] - 2026-07-01

### Security
- Pinned `cryptography>=48.0.1` to resolve GHSA-537c-gmf6-5ccf, which affects cryptography wheels bundling vulnerable OpenSSL versions. The previous floor `cryptography>=46.0.7` allowed the vulnerable range `[46.0.7, 48.0.1)`.

### Changed
- Dependency floor update only. No functional, API, MCP tool, or runtime behavior changes.

## [2.4.2] - 2026-06-28

### Fixed
- **Governance**: Removed prohibited compliance claims and sensitive terminology from public manifests.
- **Forge**: Rectified `llms.txt` with canonical Markdown links and validated URL health (100/100 PageSpeed).
- **Metadata**: Synchronized canonical versioning across all package authorities.

## [2.4.1] - 2026-06-28

### Added
- Canonical version governance: single source of truth (`VERSION`) with Hub-and-Spoke sync to public surfaces
- `version-gate` CI workflow enforcing version consistency across all manifests
- Official TypeScript SDK synced under `sdk-typescript/` plus `skill.md` for agent discovery
- Glama registry metadata with quality-optimized tool definitions
- `server.json` for the MCP Official Registry
- Agent discovery files finalized for crawler and agent ingestion

### Changed
- Aligned all version manifests to canonical `2.4.1`
- Smithery: tool annotations and `outputSchema` on all 13 tools; canonical configSchema
- README: added Use Cases, MCP Tools, and Deployment Modes sections; Smithery backlink badge
- npm publish workflow made manual with skip-if-version-exists guard
- Cleaned `registry-playbook.md`

### Fixed
- Removed duplicate npm badges from README

## [2.4.0] - 2026-05-15

### Added
- Static MCP server-card with 13 tools for Smithery indexing
- Secure Agent Handover branding and skill integration (PR #6)
- Smithery publish automation with GitHub Action for registry refresh
- **GC Cron for expired memories** (P1, LGPD compliance)
  - `POST /api/cron/gc` — automated garbage collection endpoint
  - Bearer token auth via `CRON_SECRET` (constant-time comparison)
  - Hard-deletes `ForgeMemory` rows where `expiresAt < NOW()`
  - Batched: 50 rows per DELETE, max 10 iterations (500 rows/run cap)
  - `ForgeGcAuditLog` table — append-only audit trail (ranAt, deletedCount, durationMs, status)
  - FK-aware: cascades QualityGateResult cleanup before memory deletion
  - Fail-closed: missing env → 503, wrong/missing auth → 401, never 200 on auth failure

### Changed
- Smithery metadata cleanup — canonical tool descriptions, enterprise-grade copy

### Security
- LGPD Article 16 compliance: expired data is hard-deleted (erasure), not soft-deleted
- Zero PII in logs (only counts + duration)
- Parameterized queries only (zero string interpolation)
- Constant-time secret comparison (`crypto.timingSafeEqual`)

### Fixed
- Governance: replaced "End-to-end encrypted" with "AES-256-GCM encrypted at rest" across surfaces
- Governance: removed the last zero-knowledge claim from the Hermes skill


## [2.3.7] - 2026-05-04

### Changed
- Public surface governance: claims matrix v1.0 applied
- Removed deprecated claims from all public surfaces
- Aligned descriptions, topics and metadata across all public repos
- Version synchronized across all distribution channels


## [1.2.0] — 2026-04-21

### Added
- Header-first auth via `x-connect-token`
- Canonical agent identity (`normalizeAgentId()`)
- Token telemetry: `usedCount` + `lastUsedAt`
- CI secret scanning (3 repositories)

### Security
- Header takes priority over query param
- AES-256-GCM hardened
- Zero hardcoded secrets (CI enforced)

### Verified in Production
- `curl -H "x-connect-token: VALID"` → 200 OK ✅
- No token → 401 ✅
- Invalid token → 401 ✅

## [1.1.8] — 2026-04-15
- Supabase → PostgreSQL migration
- Tests: 496 | Coverage: 88%

## [1.1.7] — 2026-04-10
- Initial MCP Marketplace listing