# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.4.x | ✅ Active |
| 2.3.x | ⚠️ Security fixes only |
| 1.2.x | ⚠️ Security fixes only |
| < 1.2.0 | ❌ End of life |

## Reporting

**Do NOT open public issues for security vulnerabilities.**

- Email: security@synapselayer.org
- Response: 48 hours

## Security Features

- AES-256-GCM encryption at rest
- Header-first auth (`x-connect-token`)
- Tokens never in URLs or logs
- CI secret scanning on every commit
- Content sanitization before encryption
- Encryption: AES-256-GCM at rest with per-operation random IV — content cleared after encryption

## Dependency Advisory

- **cryptography**: production deployments that pin dependencies should use `cryptography>=50.0.1`. Earlier pins are affected by GHSA-537c-gmf6-5ccf / CVE-2026-69247. The published 2.4.6 SDK metadata allows `>=48.0.1`, so `pip` resolves the latest fixed release; an explicit `>=50.0.1` floor ships in the next coordinated release.

## Data Retention

Memories with a TTL (`expiresAt` field) are automatically hard-deleted when expired:

- **Mechanism**: Automated GC cron runs daily, deleting expired rows in batches
- **Auth**: Bearer token (`CRON_SECRET`) with constant-time comparison
- **Batching**: Max 50 rows per query, max 10 iterations per run (500 rows cap)
- **Audit**: Every GC run is logged to `ForgeGcAuditLog` (timestamp, count, duration, status)
- **LGPD/GDPR**: Hard delete (erasure) — no soft-delete for expired data
- **Fail-closed**: Auth failure returns 401, never exposes data
