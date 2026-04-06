# SECURITY.md — Synapse Layer Cognitive Security Architecture

**Version:** 1.0.6  
**Last Updated:** April 2026  
**Classification:** Public  
**Standard:** Banking-Grade Infrastructure (Padrão Bancário BR)

---

## Executive Summary

Synapse Layer v1.0.6 implements a **Cognitive Security Protocol** — four independent, non-bypassable security layers that protect every memory operation from ingestion to cross-agent transfer.

| Seal | Component | Function |
|------|-----------|----------|
| 1 | **Semantic Privacy Guard™** | PII detection, removal, forensic hashing |
| 2 | **Differential Privacy** | Gaussian noise on embeddings (ε-bounded) |
| 3 | **Intelligent Intent Validation™** | Two-step confidence gate + self-healing |
| 4 | **Persistence-First Neural Handover™** | JWT-signed vault-first cross-agent transfer |

**Architecture:** Zero-Knowledge. You own encryption keys. The server never sees plaintext.

**Compliance:** GDPR, LGPD, HIPAA ready.

---

## Cognitive Security Pipeline

Every `store()` call passes through this pipeline. No exceptions. No bypasses.

```
Agent Input
  │
  ├── Seal 1: Semantic Privacy Guard™
  │     ├─ 12 regex patterns detect PII (email, SSN, CPF, credit cards, etc.)
  │     ├─ SHA-256 hash of each redacted item (forensic audit)
  │     ├─ Aggressive mode: proper noun stripping
  │     └─ Risk score + sensitivity classification
  │
  ├── Seal 2: Differential Privacy
  │     ├─ Gaussian noise injection on embedding vector
  │     ├─ σ = Δf · √(2·ln(1.25/δ)) / ε
  │     ├─ L2 normalization preserves cosine similarity
  │     └─ SNR metric in audit payload
  │
  ├── Seal 3: Intelligent Intent Validation™
  │     ├─ Step 1: Agent suggests intent (keyword heuristic)
  │     ├─ Step 2: Synapse validates (confidence gate ≥ 0.85)
  │     ├─ 19 critical keywords → auto-promote to CRITICAL
  │     └─ Self-healing on recall: keyword consensus reclassification
  │
  ├── Encryption: AES-256-GCM (client-side)
  │     ├─ 256-bit key, 96-bit IV, 128-bit auth tag
  │     └─ PBKDF2-SHA256 key derivation (210k iterations)
  │
  └── Vault Persistence
        ├─ Encrypted blob + noise-injected embedding
        └─ Immutable audit trail with all flags
```

---

## Seal 1 — Semantic Privacy Guard™

**Module:** `synapse_memory/sanitizer.py`  
**Status:** Mandatory — cannot be bypassed in the standard pipeline

### Detection Patterns (12 Precompiled)

| Pattern | Example | Sensitivity |
|---------|---------|-------------|
| Email addresses | `john@example.com` | MEDIUM |
| Phone numbers | `+55 11 99999-8888` | MEDIUM |
| SSN (US) | `123-45-6789` | CRITICAL |
| CPF (BR) | `123.456.789-00` | CRITICAL |
| Credit cards | `4111-1111-1111-1111` | CRITICAL |
| IP addresses | `192.168.1.1` | LOW |
| Dates of birth | `1990-01-15` | MEDIUM |
| Bearer tokens | `Bearer eyJhbGci...` | CRITICAL |
| AWS access keys | `AKIA...` | CRITICAL |
| Generic API keys | `sk_test_...`, `ghp_...` | CRITICAL |
| URLs | `https://internal.corp/...` | LOW |
| Passport numbers | `AB1234567` | HIGH |

### Aggressive Mode

When `aggressive_sanitize=True`, proper nouns (capitalized words not at sentence start) are stripped. This prevents name-based correlation attacks across memory pools.

```python
memory = SynapseMemory(agent_id="secure", aggressive_sanitize=True)
# "John Smith prefers dark mode" → "[REDACTED_NAME] prefers dark mode"
```

### Forensic Audit

Every redacted item produces a SHA-256 hash stored in the audit payload. This enables:
- **Non-repudiation**: Prove a specific item was redacted without revealing it
- **Compliance reporting**: Count and classify PII encounters
- **Forensic investigation**: Match hashes against known PII if legally required

---

## Seal 2 — Differential Privacy

**Module:** `synapse_memory/privacy.py`  
**Status:** Enabled by default (ε = 0.5)

### Mechanism

Calibrated Gaussian noise is injected into embedding vectors **before** they are stored in pgvector. This prevents semantic inference attacks — even with full database access, the original semantic fingerprint cannot be reconstructed.

```
σ = Δf · √(2 · ln(1.25 / δ)) / ε

where:
  Δf = L2 sensitivity of the embedding function
  ε  = privacy budget (default 0.5)
  δ  = failure probability (default 1e-5)
```

### Privacy Budget (ε)

| ε Value | Privacy Level | Use Case |
|---------|---------------|----------|
| 0.01–0.1 | Maximum privacy | Healthcare, legal |
| 0.5 | Balanced (default) | General use |
| 1.0–10.0 | Relaxed privacy | Analytics, aggregation |

### Post-Noise Normalization

After noise injection, vectors are L2-normalized to unit length. This preserves cosine similarity semantics for recall operations while maintaining the privacy guarantee.

### Audit Payload

Every `store()` includes:
```json
{
  "privacy_applied": true,
  "epsilon": 0.5,
  "noise_sigma": 0.0234,
  "snr_db": 18.7
}
```

---

## Seal 3 — Intelligent Intent Validation™

**Module:** `synapse_memory/engine/validator.py`  
**Status:** Mandatory on every `store()` call

### Intent Categories

| Category | Description | Auto-Critical |
|----------|-------------|:---:|
| `PREFERENCE` | Taste, style, language, tone | — |
| `FACT` | Verified knowledge, research, data | — |
| `PROCEDURAL` | Steps, workflows, protocols | — |
| `BIO` | Personal info, identity, demographics | — |
| `EPHEMERAL` | Session-scoped, transient context | — |
| `CRITICAL` | Security, compliance, legal, financial | ✅ |

### Two-Step Validation

1. **Agent Suggestion**: Keyword heuristic scoring across all categories
   (saturation normalization with `SATURATION_HITS=3`)
2. **Synapse Validation**: Confidence gate, critical override, source assignment

### Confidence Contract

| Condition | Result |
|-----------|--------|
| `confidence ≥ 0.85` | `source_type = "validated"` |
| `confidence < 0.85` | `source_type = "inference"` + warning |
| Critical keyword detected | `source_type = "critical_override"`, `confidence_boost = 1.0` |

### Critical Keywords (19)

`emergency`, `breach`, `attack`, `ransomware`, `warrant`, `subpoena`, `exploit`,
`vulnerability`, `incident`, `threat`, `unauthorized`, `compromise`, `malware`,
`phishing`, `fraud`, `violation`, `compliance`, `audit`, `lawsuit`

Any of these triggers automatic promotion to `CRITICAL` with `confidence_boost = 1.0`,
regardless of agent-reported confidence.

### Self-Healing on Recall

During `recall()`, semantically proximate memories (cosine ≥ 0.85) with conflicting
categories are detected. The weaker classification is corrected via keyword consensus.

Full `SelfHealingResult` audit payload:
```python
@dataclass(frozen=True)
class SelfHealingResult:
    reclassified: bool
    original_category: IntentCategory
    new_category: IntentCategory
    reason: str
    evidence_scores: dict[str, float]
```

This prevents **category drift attacks** where adversaries store conflicting metadata
to downgrade memory criticality over time.

---

## Seal 4 — Persistence-First Neural Handover™

**Module:** `synapse_memory/engine/handover.py`  
**Status:** Production

### Architecture: Vault-First

Memories are persisted to the Status Ledger **before** any network transmission.
If the target agent crashes, disconnects, or times out — nothing is lost.

### Status Ledger State Machine

```
PENDING → ACCEPTED → COMPLETED    (normal flow)
PENDING → FAILED                   (Emergency Checkpoint created)
PENDING → EXPIRED                  (grace period: summary returned)
```

**Transition rules are strict and immutable.** A `COMPLETED` handover cannot
be reverted. A `FAILED` handover always creates an Emergency Checkpoint.

### JWT Token Structure (SHT — Synapse Handover Token)

```json
{
  "origin_agent": "gpt-4",
  "target_agent": "claude-3.5",
  "user_id": "user-123",
  "scope": "full",
  "memory_count": 42,
  "iat": 1712361600,
  "exp": 1712365200
}
```

**Signature:** HMAC-SHA256 with per-instance secret key.

### Security Properties

| Property | Mechanism |
|----------|----------|
| **Authentication** | HMAC-SHA256 signature verification |
| **Integrity** | Signature covers full payload |
| **Freshness** | `iat` + `exp` timestamps, TTL enforcement |
| **Non-repudiation** | All transitions logged in Status Ledger |
| **Fault tolerance** | Emergency Checkpoint on failure |
| **Privacy** | Content sanitized + intent-validated before packaging |

### Grace Period Protocol

When TTL expires but the handover is within the 15-minute grace window:
- Raw memory data is **not** returned
- A compact summary is auto-generated
- Summary is sufficient for the target agent to understand context
- Original data remains encrypted in the vault

### Emergency Checkpoint

On `fail_handover()`:
- Full context snapshot is frozen
- Checkpoint is vault-persisted with failure reason
- Recovery can be manual or automated
- Checkpoint preserves all metadata including intent classifications

---

## Encryption & Key Management

### AES-256-GCM

| Parameter | Value |
|-----------|-------|
| Algorithm | AES-256-GCM |
| Key size | 256 bits (32 bytes) |
| IV | 96 bits (12 bytes), random per message |
| Auth tag | 128 bits (16 bytes) |
| Mode | Authenticated encryption (confidentiality + integrity) |

### Key Derivation (PBKDF2-SHA256)

| Parameter | Value |
|-----------|-------|
| Algorithm | PBKDF2-SHA256 |
| Iterations | 210,000 (NIST SP 800-132, 2023) |
| Salt | 32 bytes, random |
| Output | 256-bit encryption key |

```
user_password + random_salt → PBKDF2(210k iterations) → 256-bit key
```

---

## Data at Rest

### PostgreSQL + pgvector

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    encrypted_blob BYTEA NOT NULL,       -- AES-256-GCM ciphertext
    embedding vector(1536) NOT NULL,     -- Noise-injected semantic vector
    intent_category VARCHAR(50) NOT NULL,
    is_critical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Row-Level Security
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_isolation ON memories
    FOR SELECT USING (agent_id = current_user_id());
```

**Key points:**
- `encrypted_blob` = AES-256-GCM ciphertext (server cannot decrypt)
- `embedding` = noise-injected vector (original semantics unrecoverable)
- `intent_category` = validated classification (not raw agent input)
- Row-Level Security isolates agents from each other

---

## Transport Security

| Layer | Implementation |
|-------|---------------|
| Protocol | HTTPS (TLS 1.3) |
| Ciphers | AES-256-GCM or ChaCha20-Poly1305 |
| Certificate | Pinning (MITM prevention) |
| mTLS | Optional for enterprise |
| Auth | Bearer token (1h) + refresh token + API key |

---

## Compliance

### GDPR (EU)

| Requirement | Implementation |
|-------------|---------------|
| Data minimization | Semantic Privacy Guard™ (PII removed client-side) |
| Encryption | AES-256-GCM at rest + TLS 1.3 in transit |
| Purpose limitation | Data used only for memory/retrieval |
| Right to deletion | User can delete all memories + audit trail (1y retention) |
| Right to access | Full encrypted export available |
| Data controller | User owns data; Synapse is processor |

### LGPD (Brazil)

| Requirement | Implementation |
|-------------|---------------|
| Consentimento explícito | User opt-in required |
| Segurança | AES-256-GCM per § 5.10 |
| Transparência | Clear privacy policy |
| Direito de exclusão | Permanent deletion available |
| Padrão Bancário | BACEN standards implemented |

### HIPAA (US)

| Requirement | Implementation |
|-------------|---------------|
| Encryption | AES-256-GCM for all health data |
| Access controls | User-based encryption (PBKDF2) |
| Audit trail | Immutable log of all access |
| BAA | Required for healthcare apps |

---

## Threat Model

| Threat | Probability | Impact | Mitigation |
|--------|:-----------:|:------:|------------|
| Plaintext data breach | HIGH | CRITICAL | AES-256-GCM + zero-knowledge |
| Semantic inference attack | HIGH | HIGH | Differential Privacy (ε=0.5) |
| PII leakage through embeddings | HIGH | CRITICAL | Semantic Privacy Guard™ |
| Category drift attack | MEDIUM | HIGH | Self-healing + keyword consensus |
| Unauthorized handover | MEDIUM | HIGH | HMAC-SHA256 + agent identity check |
| SQL injection | MEDIUM | HIGH | Parameterized queries, ORM |
| API key leak | MEDIUM | CRITICAL | Sanitizer detects and removes |
| Handover token tampering | LOW | HIGH | HMAC-SHA256 signature |
| Man-in-the-middle | LOW | HIGH | TLS 1.3 + certificate pinning |
| Brute force | LOW | MEDIUM | PBKDF2 210k + rate limiting |
| Replay attack | LOW | MEDIUM | Handover TTL + single-use tokens |
| Insider threat | LOW | CRITICAL | Zero-knowledge (employees can't decrypt) |
| Target agent crash | MEDIUM | MEDIUM | Emergency Checkpoint |

---

## Responsible Disclosure

If you discover a security vulnerability:

1. **Do NOT** file a public GitHub issue
2. **Email:** security@synapselayer.org
3. **Include:** Description, reproduction steps, potential impact
4. **Timeline:** 48h response, 7-day patch target, public disclosure after fix

---

## Security Contact

**Email:** security@synapselayer.org  
**Founder:** founder.synapselayer@proton.me  
**Subscribe:** https://synapselayer.org/security

---

*Synapse Layer — Cognitive Security Protocol for AI Agents*  
*v1.0.6 — April 2026*
