# Security Policy

## Reporting Vulnerabilities

**Email:** security@synapselayer.org

Do not open public GitHub issues for security vulnerabilities.

### Response Timeline
- **Acknowledgment:** Within 24 hours
- **Assessment:** Within 48 hours
- **Patch & disclosure:** Within 7 days (for critical issues)

---

## Architecture

### Encryption

**Client-Side:** AES-256-GCM on your machine *before* transmission. You own the key. We never store or access it.

**Result:** Even if our database is compromised, your memories remain encrypted.

### Integrity

**Neural Handover™:** Signed with HMAC-SHA256. Proves origin. Prevents tampering.

**Audit Trail:** All operations logged immutably.

### Access Control

- **Authentication:** JWT-based per agent
- **Authorization:** Row-Level Security (RLS)
- **Rate Limiting:** Endpoint protection

---

## What We Don't Do

❌ Log plaintext memories  
❌ Access your encryption keys  
❌ Sell or share your data  
❌ Use memories for model training  
❌ Retain data longer than necessary  

---

## Compliance

- **GDPR** — Data minimization, encryption, user control
- **LGPD** — Explicit consent, right to deletion
- **HIPAA** — Encryption at rest and in transit

---

## Proprietary Components

Some components are closed-source by design:

- **Public:** Python SDK, examples, documentation
- **Proprietary:** Synapse Forge console, TQ engine internals, MCP server implementation

**Why?** These contain competitive advantages we protect for business sustainability.

**Your data remains secure:** Encrypted with keys you control, regardless.

---

## Questions?

**Security:** security@synapselayer.org
