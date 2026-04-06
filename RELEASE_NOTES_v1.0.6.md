# Release Notes — Synapse Layer v1.0.6

**Codename:** Cognitive Security Protocol  
**Date:** 2026-04-05  
**Author:** Ismael Marchi (founder.synapselayer@proton.me)  
**License:** Apache 2.0 (SDK) | Proprietary (Forge)

---

## What Changed and Why It Matters

Synapse Layer v1.0.6 transitions from a memory SDK to a **complete Cognitive Security Protocol for enterprise AI agents**. Every memory now passes through four independent, non-bypassable security layers before persistence.

This is not an incremental update. It is a protocol-level upgrade.

### The Four Seals

**Seal 1 — Semantic Privacy Guard™** (mandatory, cannot be bypassed)  
PII is detected and removed at the semantic level using 12 precompiled regex patterns. SHA-256 forensic hashes enable non-repudiation without exposing redacted content. Aggressive mode strips proper nouns to prevent cross-pool correlation attacks.

**Seal 2 — Differential Privacy**  
Calibrated Gaussian noise is injected into embedding vectors before pgvector storage. Even with full database access, the original semantic fingerprint cannot be reconstructed. Configurable ε budget (default 0.5) with SNR audit metrics.

**Seal 3 — Intelligent Intent Validation™**  
Every `store()` call passes through a two-step validation: the agent suggests an intent category, then Synapse validates independently with a confidence gate (≥ 0.85). 19 critical keywords trigger automatic promotion. Self-healing on `recall()` corrects category drift attacks via keyword consensus.

**Seal 4 — Persistence-First Neural Handover™**  
Cross-agent context transfer with vault-first persistence. Memories are stored in the Status Ledger before any network operation. HMAC-SHA256 signed JWT tokens, Emergency Checkpoints on failure, and 15-minute grace period with auto-summary.

### Why This Matters

- **Security posture**: Every memory is sanitized, noise-injected, intent-validated, and encrypted before persistence. The server never sees plaintext.
- **Fault tolerance**: Neural Handover™ is persistence-first. Target agent crashes don’t lose data.
- **Compliance**: Full GDPR/LGPD/HIPAA audit trail with immutable logging and SHA-256 forensic hashes.
- **Self-defense**: Self-healing prevents category drift attacks. Semantic Privacy Guard™ is mandatory.

---

## Migration Notes

**No breaking changes.** v1.0.6 is fully backward-compatible with v1.0.4+.

- New methods are additive: `create_handover()`, `accept_handover()`, `fail_handover()`, `get_latest_handover()`
- Existing `store()` and `recall()` signatures unchanged
- `validation_details` dict has new keys; old keys remain
- `RecallResult` has new optional fields (`intent`, `is_critical`, `self_healing`) defaulting to `None`
- **Recommended action**: Update to v1.0.6 and set `aggressive_sanitize=True`

---

## Files Changed

### SDK — Core (`synapse_memory/`)

| File | Action | Description |
|------|--------|-------------|
| `core.py` | **Modified** | Integrated NeuralHandover engine, added 4 handover methods, self-healing on recall, expanded validation_details |
| `sanitizer.py` | **Stable** | 12 regex patterns, aggressive mode, SHA-256 hashes (unchanged from v1.0.4) |
| `privacy.py` | **Stable** | Gaussian noise, ε-bounded, L2 normalization (unchanged from v1.0.4) |
| `__init__.py` | **Modified** | Exports all handover types, version bumped to 1.0.6 |

### SDK — Engine (`synapse_memory/engine/`)

| File | Action | Description |
|------|--------|-------------|
| `validator.py` | **Created (v1.0.5)** | IntentCategory enum, two-step validation, confidence gate, 19 critical keywords, self-healing |
| `handover.py` | **Created (v1.0.6)** | NeuralHandover engine, Status Ledger, JWT tokens, Emergency Checkpoint, grace period |
| `__init__.py` | **Modified** | Exports all validator + handover types |

### Documentation

| File | Action | Description |
|------|--------|-------------|
| `README.md` | **Rewritten** | TL;DR, competitive table, 4 seals, pricing, waitlist, embedded changelog |
| `CHANGELOG.md` | **Rewritten** | Complete v1.0.3–1.0.6 history with Keep a Changelog format |
| `SECURITY.md` | **Rewritten** | Full Cognitive Security Pipeline, 4 seals, threat model, compliance tables |
| `ARCHITECTURE.md` | **Updated** | Mermaid state machine + sequence diagrams for handover |
| `RELEASE_NOTES_v1.0.6.md` | **Created** | This file |

### Configuration

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | **Updated** | Version 1.0.6, new keywords, classifiers, package includes, tool config |

### Website (`synapselayer.org`)

| File | Action | Description |
|------|--------|-------------|
| `components/hero-section.tsx` | **Rewritten** | 4 seal badges, v1.0.6 tag, pip install copy, 3 CTAs |
| `components/core-mechanisms.tsx` | **Rewritten** | 4 proprietary seals with Seal 1–4 labels |
| `components/cognitive-security.tsx` | **Created** | Pipeline visualization + code example |
| `components/competitive-comparison.tsx` | **Created** | 10-feature table vs Mem0/Zep/pgvector |
| `components/pricing.tsx` | **Updated** | Free (1K), Pro $29, Enterprise custom |
| `components/waitlist-cta.tsx` | **Created** | Forge link, 5 benefits, Adopt-an-Agent badge |
| `components/security-assumptions.tsx` | **Updated** | References to 4 security layers |
| `components/footer.tsx` | **Updated** | Forge, GitHub, PyPI links |
| `app/page.tsx` | **Updated** | New section order with all components |

---

## Commit Message

```
release: v1.0.6 — Cognitive Security Protocol

Introduce four proprietary security seals protecting every memory operation:

- Seal 1: Semantic Privacy Guard™ (mandatory PII sanitization + SHA-256 forensic hashes)
- Seal 2: Differential Privacy (Gaussian noise on embeddings, ε-bounded)
- Seal 3: Intelligent Intent Validation™ (confidence gate ≥ 0.85, 19 critical keywords, self-healing)
- Seal 4: Persistence-First Neural Handover™ (JWT-signed vault-first transfers, Status Ledger, Emergency Checkpoint)

New: NeuralHandover engine with HMAC-SHA256 tokens, HandoverStatus state machine,
grace period protocol, and Emergency Checkpoint fault tolerance.

New: SynapseValidator with IntentCategory taxonomy, two-step validation pipeline,
critical keyword auto-promotion, and self-healing on recall.

Updated: README (full rewrite), CHANGELOG (Keep a Changelog), SECURITY.md (v1.0.6),
ARCHITECTURE.md (Mermaid diagrams), pyproject.toml (classifiers, keywords).

Updated: Website with cognitive security pipeline, competitive comparison table,
updated pricing (Pro $29), waitlist CTA, and 4-seal hero section.

No breaking changes. Fully backward-compatible with v1.0.4+.
Semantic Privacy Guard™ is now mandatory — cannot be bypassed in the standard pipeline.

Signed-off-by: Ismael Marchi <founder.synapselayer@proton.me>
```

---

## PR Description (GitHub)

```markdown
## 🛡️ Release v1.0.6 — Cognitive Security Protocol

[![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![Security](https://img.shields.io/badge/Security-4_Seals-blueviolet)](#cognitive-security-pipeline)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

### Summary

This release upgrades Synapse Layer from a memory SDK to a **complete Cognitive Security Protocol** for enterprise AI agents. Every memory operation now passes through four independent, non-bypassable security layers.

### Four Proprietary Security Seals

| Seal | Component | New in |
|------|-----------|--------|
| 🛡️ | **Semantic Privacy Guard™** — PII sanitization + SHA-256 forensic hashes | v1.0.4 |
| 🔐 | **Differential Privacy** — Gaussian noise on embeddings (ε-bounded) | v1.0.4 |
| 🧠 | **Intelligent Intent Validation™** — Two-step confidence gate + self-healing | v1.0.5 |
| ⚡ | **Persistence-First Neural Handover™** — JWT-signed vault-first transfers | v1.0.6 |

### Key Changes

**Engine:**
- `NeuralHandover` engine with Status Ledger, HMAC-SHA256 JWT, Emergency Checkpoint, grace period
- `SynapseValidator` with 6 intent categories, 19 critical keywords, self-healing on recall
- Full integration in `SynapseMemory.store()` and `SynapseMemory.recall()`

**Documentation:**
- README.md — complete rewrite (TL;DR, competitive table, pricing, waitlist)
- SECURITY.md — v1.0.6 with full pipeline docs and threat model
- CHANGELOG.md — Keep a Changelog format with migration notes
- ARCHITECTURE.md — Mermaid diagrams for handover flow

**Website (synapselayer.org):**
- Cognitive Security Pipeline section
- Competitive comparison table (vs Mem0, Zep, pgvector)
- Updated pricing (Free 1K / Pro $29 / Enterprise)
- Join Waitlist CTA with Forge link
- 4-seal hero section with v1.0.6 badge

### Migration

**No breaking changes.** Fully backward-compatible with v1.0.4+. New methods and fields are additive.

**Recommended:** `pip install --upgrade synapse-layer` and set `aggressive_sanitize=True`.

### Testing

- [x] Inline tests: sanitizer (5), privacy (7), core (10), validator (11), handover (11) — all pass
- [x] TypeScript compilation (website) — clean
- [x] Next.js production build — clean
- [x] Backward compatibility with v1.0.4 API surface — verified

---

*Semantic Privacy Guard™ is now mandatory. The server never sees plaintext.*

**Giving Agents a Past. Giving Models a Soul. ⚗️**
```

---

*End of Release Notes — v1.0.6*
