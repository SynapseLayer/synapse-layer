# v1.1.7 — Security Hardening: CVE fixes + MCP Auth Enforcement

**Release Date:** April 13, 2026  
**Codename:** Security Hardening  
**MCP Marketplace Score:** 5.8 → **10.0** (Low Risk) ✅

---

## 🛡️ Security Fixes

### CVE Remediation
| CVE | Package | Fix | Severity |
|-----|---------|-----|:--------:|
| CVE-2026-39892 | `cryptography` | `>=44.0.0` → `>=46.0.7` | HIGH |
| GHSA-r5fr | `lodash` | `4.17.21` → `4.18.1` | HIGH |
| GHSA-mwv6 | `next` | `14.2.28` → `14.2.35` | HIGH |
| GHSA-5j59 | `next` | `14.2.28` → `14.2.35` | HIGH |

### MCP Auth Enforcement
- **Connect Token Validation**: Every `/api/mcp` tool call and `/api/synapse` action now requires `x-connect-token` or `Authorization: Bearer sk_connect_xxx`
- **Quota Enforcement**: `ConnectToken.usedCount` checked before every store. `QUOTA_EXHAUSTED` returned with HTTP 429 when limit reached
- **Counter Calibration**: Atomic `usedCount` increment after every successful memory store
- **userId Scoping**: All `recall` and `search` queries filtered by `WHERE userId = ? OR userId IS NULL` — zero cross-tenant leakage
- **Auth-exempt endpoints**: `initialize`, `tools/list`, `notifications/initialized`, `health_check` (MCP handshake + public status)

### Permission Justification
- `file_system`: Documented as **local-only** (SqliteBackend). Remote mode (`forge.synapselayer.org/api/mcp`) uses PostgreSQL — no filesystem access needed

## 🧪 Production Negative Tests (5/5 PASS)

| Test | Description | Result |
|------|-------------|:------:|
| 1 | MCP without token | ✅ 401 `-32001` |
| 2 | MCP with invalid token | ✅ 401 `INVALID_TOKEN` |
| 3 | Quota exhausted (2/2) | ✅ `QUOTA_EXHAUSTED` blocked |
| 4 | Valid token → store | ✅ Saved + quota incremented |
| 5 | DB verification | ✅ `usedCount: 1`, `userId` correct |

## 📦 Changes

### Python SDK
- `cryptography` floor raised to `>=46.0.7`
- Dropped EOL Python 3.9 — `requires-python >= 3.10`
- Replaced `flake8` with `ruff>=0.3.0`
- Added Python 3.13 classifier

### Next.js (Forge)
- Upgraded `next` to 14.2.35 (2 DoS CVEs patched)
- Upgraded `lodash` to 4.18.1 (Code Injection CVE patched)
- Auth middleware: `lib/connect/auth.ts`
- Schema: `ForgeMemory.userId` (nullable, backward compatible)
- Dashboard Connect: `useSession()` replaces hardcoded `demo_user`

### Manifests
- `server.json`: v1.1.7 + remote endpoint
- `smithery.yaml`: v1.1.7 + all 5 tools (added missing `search`)
- `CHANGELOG.md`: Security hardening entry

## 🔗 Links
- **Forge (Live MCP)**: https://forge.synapselayer.org/api/mcp
- **PyPI**: https://pypi.org/project/synapse-layer/1.1.7/
- **MCP Marketplace**: https://mcp-marketplace.io/server/io-github-synapselayer-synapse-layer
- **Docs**: https://synapselayer.org/docs

---

**Full Changelog**: https://github.com/SynapseLayer/synapse-layer/compare/v1.1.6...v1.1.7
