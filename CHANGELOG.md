# Changelog

## [Unreleased]

### Added
- **GC Cron for expired memories** (P1, LGPD compliance)
  - `POST /api/cron/gc` — automated garbage collection endpoint
  - Bearer token auth via `CRON_SECRET` (constant-time comparison)
  - Hard-deletes `ForgeMemory` rows where `expiresAt < NOW()`
  - Batched: 50 rows per DELETE, max 10 iterations (500 rows/run cap)
  - `ForgeGcAuditLog` table — append-only audit trail (ranAt, deletedCount, durationMs, status)
  - FK-aware: cascades QualityGateResult cleanup before memory deletion
  - Fail-closed: missing env → 503, wrong/missing auth → 401, never 200 on auth failure

### Security
- LGPD Article 16 compliance: expired data is hard-deleted (erasure), not soft-deleted
- Zero PII in logs (only counts + duration)
- Parameterized queries only (zero string interpolation)
- Constant-time secret comparison (`crypto.timingSafeEqual`)


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
