# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.2.x | ✅ Active |
| 1.1.x | ⚠️ Security fixes only |
| < 1.1.0 | ❌ End of life |

## Reporting

**Do NOT open public issues for security vulnerabilities.**

- Email: security@synapselayer.org
- Response: 48 hours

## Security Features

- AES-256-GCM encryption at rest
- Header-first auth (`x-connect-token`)
- Tokens never in URLs or logs
- CI secret scanning on every commit
- PII redaction pipeline
- Encryption: AES-256-GCM at rest with per-operation random IV — content cleared after encryption
