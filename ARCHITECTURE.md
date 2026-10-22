# ARCHITECTURE.md — Synapse Layer Complete Data Flow

## System Overview

Synapse Layer is a **Persistent Encrypted Memory Layer for AI Agents** with AES-256-GCM encryption at rest, intent validation, and trust-based conflict resolution.

### Core Principles

1. **Encrypted at Rest:** AES-256-GCM with per-operation random IV and HMAC-SHA-256 integrity
2. **Client-Side Sanitization:** PII removal before transmission
3. **Intent Validation:** Intelligent categorization with self-healing
4. **Trust Quotient:** Adaptive conflict resolution algorithm
5. **Fixed-order pipeline:** sanitize → validate → encrypt → embed → store

---

## Complete Data Flow (Mermaid Diagram)

```mermaid
graph TD
    A["Raw Text Input"] -->|user.store_memory| B["SynapseSanitizer"]
    
    B -->|detect & remove PII| C{PII Found?}
    C -->|Yes| D["Log Removed Items"]
    C -->|No| E["Sanitized Content"]
    D --> E
    
    E -->|low risk score| F["SynapseValidator"]
    E -->|high risk score| G["RISK FLAG"]
    G --> F
    
    F -->|classify intent| H{Intent Category}
    H -->|USER_PROFILE| I["Confidence Score"]
    H -->|MEDICAL/FINANCIAL/LEGAL| J["Auto-CRITICAL"]
    H -->|SECURITY| J
    H -->|UNKNOWN| K["Self-Healing"]
    
    J --> L["Validation Score"]
    I --> L
    K --> L
    
    L -->|score >= 0.85| M["AES-256-GCM Encryption"]
    L -->|score < 0.85| N["VALIDATION FAILED"]
    N -->|store anyway?| O{User Choice}
    O -->|proceed| M
    O -->|reject| P["Drop Memory"]
    
    M -->|encrypt with per-tenant key (HKDF over master key)| Q["Encrypted Blob"]
    Q --> R["Generate Embeddings"]
    
    R -->|semantic search vector| S["pgvector Index"]
    S --> T["PostgreSQL Storage"]
    
    T --> U["Audit Log (append-only)"]
    U --> V["Memory Successfully Stored"]
    
    V --> W["Return Handle & Proof"]
    W --> X["Client Application"]
    
    style B fill:#4f46e5,color:#fff
    style F fill:#4f46e5,color:#fff
    style M fill:#dc2626,color:#fff
    style J fill:#ea580c,color:#fff
    style T fill:#059669,color:#fff
```

---

## Component Descriptions

### 1. SynapseSanitizer

**Purpose:** Remove PII before encryption

**Patterns Detected:**
- Email: `john@example.com`
- Phone: `+55 11 99999-8888`, `(123) 456-7890`
- SSN/CPF: `123-45-6789`, `123.456.789-00`
- Credit Card: `1234-5678-9012-3456`
- API Keys: `sk_test_...`, `ghp_...`
- URLs: `https://example.com`
- IP Addresses: `192.168.1.1`

**Output:** `SanitizationResult` with:
- `sanitized_content`: Content with PII replaced with `[TYPE_REDACTED]`
- `pii_count`: Number of PII items removed
- `risk_score`: 0.0–1.0 (CRITICAL: 0.3, HIGH: 0.15, MEDIUM: 0.05 per item)
- `ner_hints`: Hints for downstream NER processing
- `is_safe`: True if risk_score < 0.05

### 2. SynapseValidator

**Purpose:** Classify intent and validate confidence

**IntentCategory Enum:**
- `USER_PROFILE` (preferences, metadata)
- `CONVERSATION` (dialogs, chats)
- `DECISION` (commitments, goals)
- `KNOWLEDGE` (facts, learning)
- `PREFERENCE` (tastes, likes/dislikes)
- `MEDICAL` (health — **auto-critical**)
- `FINANCIAL` (payments — **auto-critical**)
- `LEGAL` (contracts — **auto-critical**)
- `SECURITY` (passwords — **auto-critical**)
- `UNKNOWN` / `INVALID`

**Thresholds:**
- Confidence: 0.0–1.0
- **Valid if confidence >= 0.85** (immutable threshold)
- **Auto-critical** for MEDICAL, FINANCIAL, LEGAL, SECURITY
- **Critical keywords:** emergency, urgent, breach, attack, fraud → auto-promote

**Self-Healing:** When confidence 0.5–0.85, detect context and upgrade category

### 3. AES-256-GCM Encryption

**Key Derivation:** per-tenant key from the master key
- Master key: `SYNAPSE_ENCRYPTION_KEY` (64 hex chars = 256-bit), held in
  the environment. It is never a client credential.
- Per-tenant derivation: HKDF-Expand over HMAC-SHA256 —
  `HMAC-SHA256(masterKey, tenantId + ":synapse-memory-v1")` → 256-bit key,
  giving cryptographic separation between tenants.
- Enabled by `SYNAPSE_HKDF_ENABLED=true` (encryption version `v1.1-hkdf`).
  Memories written before that (version `v1.0`) use the master key
  directly and are still readable.
- Output: 256-bit encryption key

**Encryption Mode:**
- Algorithm: AES-256-GCM
- IV: 96 bits, randomly generated per message
- Auth Tag: 128 bits (verifies integrity & authenticity)

**Process:**
```
Master Key (env) + tenantId → HKDF-Expand (HMAC-SHA256) → 256-bit per-tenant key
                                                     ↓
                                          AES-256-GCM Encryption
                                                     ↓
                                          Encrypted Blob + Auth Tag
```

### 4. Embedding Generation

**Semantic Search:**
- Convert sanitized content to vector
- Dimension: 1536 (e.g., OpenAI embeddings)
- Index: pgvector (PostgreSQL vector extension with HNSW)

### 5. PostgreSQL + pgvector

**Schema:**
```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    encrypted_blob BYTEA NOT NULL,        -- AES-256-GCM ciphertext
    embedding vector(1536) NOT NULL,     -- Semantic search vector
    intent_category VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    is_critical BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Isolation is enforced by the application layer:
-- every read/write is scoped by tenant_id (fail-closed).
-- No Row-Level Security policy is enabled on these tables.
```

**Constraints:**
- Tenant isolation enforced in the application layer: every query is
  scoped by `tenantId` and fails closed. No database RLS policy is
  enabled — the guarantee comes from the query layer, not from Postgres
- Append-only audit trail (application level)
- Automatic deletion on TTL

### 6. Trust Quotient Calculation

```
TQ = f(Recency, Consistency, Confidence, Relevance)

Recency:     How fresh the memory (0-1)
Consistency: Agreement with other memories (0-1)
Confidence:  Validation confidence from SynapseValidator (0-1)
Relevance:   Semantic similarity to query (0-1)

Weights are proprietary and dynamically calibrated.
Full algorithm available under Enterprise license.
```

**Conflict Resolution:**
- When memories conflict, highest TQ wins
- Tie-breaker: Most recent timestamp
- Audit log records all conflicts and resolutions

---

## Pipeline Sequence (fixed order)

The following sequence is **mandatory and non-negotiable**:

1. **INPUT** → Raw text
2. **SANITIZE** → Remove PII (SynapseSanitizer)
3. **VALIDATE** → Classify intent (SynapseValidator)
4. **ENCRYPT** → AES-256-GCM with the per-tenant key
5. **EMBED** → Generate semantic vector
6. **STORE** → Upsert to pgvector + audit log
7. **OUTPUT** → Memory handle + proof of storage

**No step can be skipped or reordered.**

---

## File Structure

```
synapse-layer/
├── synapse_memory/
│   ├── __init__.py
│   ├── core.py                    ← SynapseMemory (orchestrator)
│   ├── sanitizer.py               ← SynapseSanitizer (PII removal)
│   ├── privacy.py                 ← DifferentialPrivacy (DP noise)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── validator.py           ← SynapseValidator (intent validation)
│   │   └── handover.py            ← NeuralHandover (cross-agent transfer)
│   └── crypto/
│       └── __init__.py
├── ARCHITECTURE.md                ← This file
├── SECURITY.md
├── README.md
├── CHANGELOG.md
└── pyproject.toml
```

---

## Neural Handover — Persistence-First Architecture

Cross-agent context transfer with Status Ledger, JWT signing, and automatic fallback.

### Handover State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: create_handover()

    PENDING --> ACCEPTED: accept_handover() [valid JWT + within TTL]
    ACCEPTED --> COMPLETED: Context imported to target agent

    PENDING --> EXPIRED: TTL exceeded
    EXPIRED --> GracePeriod: Within 15min grace window
    GracePeriod --> SummaryReturned: Summary generated, raw data cleared

    PENDING --> FAILED: Target agent error
    FAILED --> EmergencyCheckpoint: Full context preserved for recovery

    COMPLETED --> [*]
    SummaryReturned --> [*]
    EmergencyCheckpoint --> [*]
```

### Handover Data Flow

```mermaid
sequenceDiagram
    participant A as Agent A (Origin)
    participant S as Synapse Layer
    participant V as Vault (Status Ledger)
    participant B as Agent B (Target)

    A->>S: create_handover(memories, target_agent)
    S->>S: Sanitize content (PII removal)
    S->>S: Validate intent (Cognitive Security)
    S->>S: Sign JWT (HMAC-SHA256)
    S->>V: Persist as PENDING
    S-->>A: HandoverResult {token, handover_id}

    A->>B: Transmit signed JWT token

    B->>S: accept_handover(handover_id)
    S->>S: Verify JWT signature
    S->>S: Check TTL expiration

    alt Valid & Within TTL
        S->>V: Update → ACCEPTED → COMPLETED
        S-->>B: Full context data
        B->>B: Import memories into local store
    else TTL Expired (Grace Period)
        S->>S: Generate summary from context
        S->>V: Update → EXPIRED
        S-->>B: Summary only (raw data cleared)
    else TTL Expired (Beyond Grace)
        S-->>B: TimeoutError
    end

    alt Target Agent Fails
        S->>V: Update → FAILED
        S->>V: Create Emergency Checkpoint
        Note over V: Full context preserved<br/>for recovery via<br/>get_latest_handover()
    end
```

### Handover JWT Token Structure

```
Header:   {"alg": "HS256", "typ": "SHT"}
Payload:  {"tid": "ho_...", "org": "gpt-4", "tgt": "claude-3.5",
           "uid": "user-123", "scp": "full", "iat": ..., "exp": ...}
Signature: HMAC-SHA256(header.payload, signing_key)
```

### Recovery Mechanisms

| Scenario | Action | Data Available |
|----------|--------|:-:|
| Normal | `accept_handover()` | Full context |
| Grace Period | Auto-summary | Summary only |
| Agent Failure | Emergency Checkpoint | Full context (frozen) |
| Full Expiry | `get_latest_handover()` | Summary only |

---

## Security Principles

- **Encrypted at Rest:** AES-256-GCM with per-operation random IV — content cleared after encryption
- **Client-Side Sanitization:** PII removed before leaving client
- **Audit trail:** every operation logged in `ForgeEvent` (append-only in
  the application; the database layer does not enforce immutability)
- **Differential Privacy:** Aggregate queries don't leak individual data
- **Handover Verification:** HMAC-SHA256 signed JWT tokens on cross-model transfers
- **Persistence-First:** All handovers vault-persisted before transmission

---

## Compliance & Standards

- **LGPD-ready:** consent records, encryption at rest, right to deletion
  (soft and hard), audit trail. "Ready" means the controls exist — it is
  not a certification and no certification is claimed.
- **GDPR-aligned controls:** data minimisation, encryption at rest, right
  to deletion. No GDPR certification is claimed.
- **HIPAA / SOC 2:** the technical controls (encryption, audit trail,
  tenant isolation) are the building blocks, but the platform holds **no
  HIPAA or SOC 2 certification**. Do not present it as certified.

---

## Performance Metrics

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| Sanitize | < 10ms | 1000+ items/sec |
| Validate | < 5ms | 2000+ items/sec |
| Key derivation (HKDF-Expand) | < 1ms | Per tenant, cached in memory |
| AES-256-GCM | < 5ms | ~100MB/sec |
| Embedding (API) | 100-500ms | Depends on provider |
| pgvector Search | < 50ms | HNSW index |

---

End of ARCHITECTURE.md
