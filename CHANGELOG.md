# Changelog

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
