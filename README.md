<div align="center">
  <h1>Synapse Layer</h1>
  <h3>Zero-Knowledge Universal Memory for MCP</h3>
  <p><strong>The privacy-first, persistent memory infrastructure for AI agents.<br>MCP-native, secure-by-design.</strong></p>
  <p><em>Giving Agents a Past. Giving Models a Soul. ⚗️</em></p>

  [![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
  [![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
  [![Security](https://img.shields.io/badge/Security-4_Seals-blueviolet)](#cognitive-security-pipeline)
  [![v1.0.6](https://img.shields.io/badge/version-1.0.6-informational)](CHANGELOG.md)
  [![Adopt an Agent](https://img.shields.io/badge/🧠_Adopt_an_Agent-Synapse_Layer-purple)](https://synapselayer.org/forge)
  [![MCP Reference](https://img.shields.io/badge/MCP_Registry-PR_%231129-00d4aa)](https://github.com/modelcontextprotocol/registry/pull/1129)
  [![Technical Deep-Dive](https://img.shields.io/badge/dev.to-Technical_Deep--Dive-0A0A0A?logo=devdotto)](https://dev.to/synapselayer/beyond-context-windows-a-zero-knowledge-memory-reference-implementation-for-the-mcp-ecosystem-4bcg)

  [Website](https://synapselayer.org) · [Forge](https://synapselayer.org/forge) · [Docs](https://synapseforge.abacusai.app/docs) · [GitHub](https://github.com/SynapseLayer/synapse-layer) · [PyPI](https://pypi.org/project/synapse-layer/)

  <!-- mcp-name: io.github.synapselayer/synapse-secure-memory -->
</div>

---

## Overview

Synapse Layer is the **reference implementation** of a universal memory layer for AI agents in the **Model Context Protocol (MCP)** ecosystem.

It solves the fundamental problem of **agent amnesia** by providing reliable, long-term and short-term context persistence with strong cryptographic guarantees.

Every memory operation passes through a **non-bypassable 4-layer Cognitive Security Pipeline**:

| Seal | Name | Function |
|:---:|---|---|
| 1 | **Semantic Privacy Guard™** | Automatic PII sanitization (12+ patterns) |
| 2 | **Intelligent Intent Validation™** | Auto-categorization + self-healing |
| 3 | **Differential Privacy** | Calibrated Gaussian noise (ε-DP) |
| 4 | **Neural Handover™** | HMAC-signed cross-model transfer |

---

## Key Differentiators

- 🔐 **True zero-knowledge architecture** — raw content never exposed to the server
- 🏛️ **Official MCP reference server** — [PR #1129](https://github.com/modelcontextprotocol/registry/pull/1129) submitted to the MCP Registry
- 🤖 **Native compatibility** with Claude Desktop, LangChain, CrewAI and custom agents
- 📦 **Full SDK** available via PyPI (`pip install synapse-layer`)
- 🔍 **Cryptographic audit trails** and Trust Quotient™ scoring on every operation

---

## Ideal For

- Agents requiring **reliable long-term memory**
- **Secure multi-agent orchestration** workflows
- **Regulated environments** requiring GDPR, LGPD and SOC2 compliance

---

## Quick Start

```bash
pip install synapse-layer
```

```python
from synapse_layer import SynapseMemory
import asyncio

async def main():
    mem = SynapseMemory(agent_id="my-agent")
    await mem.store("User prefers dark mode", confidence=0.95)
    results = await mem.recall("user preferences")
    for r in results:
        print(f"{r.content} (TQ: {r.trust_quotient:.3f})")

asyncio.run(main())
```

**MCP (Claude Desktop / LangChain / CrewAI):**

```json
{
  "mcpServers": {
    "synapse-layer": {
      "command": "uvx",
      "args": ["synapse-layer"]
    }
  }
}
```

That's it. AES-256-GCM encryption, PII sanitization, differential privacy noise, intent validation, and trust scoring — all happen automatically under the hood.

---

## Why Synapse Layer

AI agents are stateless. They forget everything between sessions, waste tokens re-asking questions, and lose context when switching models. Existing solutions either store plaintext embeddings (security risk), lack cross-model support, or require you to manage vector DBs manually.

**Synapse Layer** is a persistent, encrypted, cross-model memory infrastructure with four proprietary security layers and cryptographic guarantees. The server never sees plaintext.

---

## Competitive Comparison

| Capability | Synapse Layer | Mem0 | Zep | pgvector (raw) |
|---|:---:|:---:|:---:|:---:|
| Client-side AES-256-GCM | ✅ | ❌ | ❌ | ❌ |
| Semantic PII Sanitization | ✅ | ❌ | ❌ | ❌ |
| Differential Privacy on Embeddings | ✅ | ❌ | ❌ | ❌ |
| Intent Validation Pipeline | ✅ | ❌ | ❌ | ❌ |
| Cross-Model Handover (JWT) | ✅ | ❌ | partial | ❌ |
| Trust Quotient™ Scoring | ✅ | ❌ | ❌ | ❌ |
| Self-Healing on Recall | ✅ | ❌ | ❌ | ❌ |
| MCP Native | ✅ | ❌ | ❌ | ❌ |
| Open SDK (Apache 2.0) | ✅ | ✅ | partial | ✅ |
| Zero-Knowledge Guarantee | ✅ | ❌ | ❌ | ❌ |

---

## Cognitive Security Pipeline

Every memory passes through four proprietary security layers before persistence:

```
Agent → Sanitize (PII) → Validate Intent → Encrypt (AES-256) → DP Noise → Vault
              ↓                  ↓                                          ↓
    Semantic Privacy Guard™   Intelligent Intent         Differential Privacy
                              Validation™                 (Gaussian, ε-bounded)
```

### Seal 1 — Semantic Privacy Guard™

PII is detected and removed at the semantic level before encryption. 12 precompiled regex patterns cover emails, phone numbers, SSNs, credit cards, Bearer tokens, AWS keys, and more. Aggressive mode strips proper nouns to prevent name-based correlation attacks.

```python
memory = SynapseMemory(agent_id="secure-agent", aggressive_sanitize=True)
await memory.store("John Smith's SSN is 123-45-6789", confidence=0.9)
# Stored content: "[REDACTED_NAME]'s SSN is [REDACTED_SSN]"
# SHA-256 hash of each redacted item preserved for forensic audit
```

### Seal 2 — Differential Privacy

Calibrated Gaussian noise is injected into embedding vectors before storage. This prevents semantic inference attacks — even with database access, the original semantic fingerprint cannot be reconstructed.

```python
memory = SynapseMemory(agent_id="dp-agent", privacy_epsilon=0.5)
# σ = Δf · √(2·ln(1.25/δ)) / ε
# L2 normalization post-noise preserves cosine similarity semantics
# SNR metric included in audit payload
```

### Seal 3 — Intelligent Intent Validation™

Two-step cognitive security: the agent suggests an intent category, then Synapse validates it independently.

| Category | Description | Auto-Critical |
|---|---|:---:|
| `PREFERENCE` | Taste, style, language, tone | — |
| `FACT` | Verified knowledge, research, data | — |
| `PROCEDURAL` | Steps, workflows, protocols | — |
| `BIO` | Personal info, identity, demographics | — |
| `EPHEMERAL` | Session-scoped, transient context | — |
| `CRITICAL` | Security, compliance, legal, financial | ✅ |

**Confidence Contract:**
- `confidence ≥ 0.85` → `source_type = "validated"`
- `confidence < 0.85` → `source_type = "inference"` + warning
- Critical keyword detected → `confidence_boost = 1.0`, forced `CRITICAL`

**Self-Healing:** During `recall()`, semantically proximate memories with conflicting categories are automatically reclassified via keyword consensus.

```python
result = await memory.store("Security breach in auth system", confidence=0.5)
assert result.validation_details['source_type'] == 'critical_override'
assert result.validation_details['is_critical'] is True

# Self-healing on recall
results = await memory.recall("security events")
for item in results:
    if item.self_healing:
        print(f"⚕️ {item.self_healing.original_category} → {item.self_healing.new_category}")
```

### Seal 4 — Persistence-First Neural Handover™

Secure, fault-tolerant context transfer between AI agents. Memories are vault-persisted **before** transmission — if the target agent crashes, nothing is lost.

```python
from synapse_layer import SynapseMemory, HandoverStatus

agent_a = SynapseMemory(agent_id="gpt-4")
handover = agent_a.create_handover(target_agent="claude-3.5", user_id="user-123")
# JWT signed (HMAC-SHA256), persisted to Status Ledger as PENDING

agent_b = SynapseMemory(agent_id="claude-3.5")
package = agent_b.accept_handover(handover.handover_id)
# PENDING → ACCEPTED → COMPLETED
```

**Status Ledger:**
```
PENDING → ACCEPTED → COMPLETED    (normal flow)
PENDING → FAILED                   (Emergency Checkpoint created)
PENDING → EXPIRED                  (grace period: summary returned)
```

**Fault tolerance:** `fail_handover()` creates an Emergency Checkpoint with full context snapshot. Grace period (15 min) auto-generates compact summaries instead of raw data.

---

## Architecture

```
Your Agent → Synapse SDK → Sanitize → Validate Intent → Encrypt → DP Noise → Vault
                                         ↑                                      ↓
                                    Self-Healing  ←  Recall  ←  Cosine Search  ←

Cross-Agent: Agent A → create_handover() → JWT Token → Agent B → accept_handover()
                                              ↓
                                     Status Ledger (Vault)
```

The server **never** sees plaintext. Embeddings are noise-injected before persistence. Handovers are vault-persisted before transmission.

See [ARCHITECTURE.md](ARCHITECTURE.md) for Mermaid diagrams and deep-dive.

---

## Pricing

| Plan | Price | Memories | Includes |
|---|---|---|---|
| **Free** | $0 | 1,000/month | Core encryption, sanitization, community support |
| **Pro** | $29/mo | 100K/month | All Free + priority support, analytics, API access, advanced integrations |
| **Enterprise** | Custom | Unlimited | All Pro + dedicated support, custom SLA, on-premise, security audit |

→ [Start Free](https://synapselayer.org/forge) · [Join Waitlist](https://synapselayer.org/forge)

---

## Join the Waitlist

Early access to Synapse Forge — the visual memory debugger and agent orchestrator.

**Benefits:**
- 🔑 Early access to Forge (private beta)
- 📋 NDA-protected feature previews
- 🧪 Forge Live — real-time memory inspection
- 🧠 "Adopt an Agent" program access
- 💬 Direct channel with the core team

→ **[Join Waitlist](https://synapselayer.org/forge)**

[![Adopt an Agent](https://img.shields.io/badge/🧠_Adopt_an_Agent-Synapse_Layer-purple)](https://synapselayer.org/forge)

---

## Status

| Component | Status |
|---|---|
| SDK (PyPI) | `v1.0.6` — stable |
| Semantic Privacy Guard™ | ✅ Production |
| Differential Privacy | ✅ Production |
| Intelligent Intent Validation™ | ✅ Production |
| Persistence-First Neural Handover™ | ✅ Production |
| Trust Quotient™ | ✅ Production |
| MCP Server | ✅ Compatible |
| Synapse Forge | ✅ [Live Dashboard](https://synapselayer.org/forge) |
| CI/CD Pipeline | 🔄 In Progress |
| **Latest Release** | [**v1.0.6 — Cognitive Security Protocol**](https://github.com/SynapseLayer/synapse-layer/releases/tag/v1.0.6) |

---

## Changelog (v1.0.6)

### Added — Neural Handover™: Persistence-First Architecture
- **NeuralHandover engine**: Complete cross-agent context transfer with vault-first persistence
  - `create_handover()` → sanitize → validate → JWT sign → persist as PENDING
  - `accept_handover()` → verify JWT (HMAC-SHA256) → check TTL → COMPLETED
  - `fail_handover()` → Emergency Checkpoint with full context snapshot
  - `get_latest_handover()` → auto-expiry + grace period summary
- **HandoverStatus state machine**: PENDING → ACCEPTED → COMPLETED | FAILED | EXPIRED
- **JWT Tokenization**: HMAC-SHA256 signed tokens with origin/target/scope/TTL
- **Grace Period Protocol**: 15-min window, auto-generates compact summary
- **Emergency Checkpoint**: Frozen context for recovery on target failure

### Security
- HMAC-SHA256 token signatures — tampering is detectable
- Agent identity verification prevents unauthorized access
- Content sanitized and intent-validated before packaging
- All state transitions logged for GDPR/LGPD compliance

→ [Full Changelog](CHANGELOG.md)

---

## Official Links

| Resource | URL |
|---|---|
| **GitHub** | [github.com/SynapseLayer/synapse-layer](https://github.com/SynapseLayer/synapse-layer) |
| **Documentation** | [synapseforge.abacusai.app/docs](https://synapseforge.abacusai.app/docs) |
| **Forge Dashboard** | [synapselayer.org/forge](https://synapselayer.org/forge) |
| **PyPI** | [pypi.org/project/synapse-layer](https://pypi.org/project/synapse-layer/) |
| **Technical Deep-Dive** | [dev.to — Beyond Context Windows](https://dev.to/synapselayer/beyond-context-windows-a-zero-knowledge-memory-reference-implementation-for-the-mcp-ecosystem-4bcg) |
| **MCP Registry PR** | [PR #1129](https://github.com/modelcontextprotocol/registry/pull/1129) |

---

## Tags

`mcp` · `memory` · `zero-knowledge` · `ai-agents` · `persistent-memory` · `privacy` · `langchain` · `claude` · `crewai` · `security`

---

## Security

See [SECURITY.md](SECURITY.md) for full architecture, key management, and compliance documentation (GDPR / LGPD / HIPAA ready).

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

**Open-core model:** SDK is fully open source. The Synapse Forge platform and advanced engine internals are proprietary.

---

<div align="center">
  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>
  <br><br>
  <a href="https://synapselayer.org">Website</a> · <a href="https://synapselayer.org/forge">Forge</a> · <a href="https://synapseforge.abacusai.app/docs">Docs</a> · <a href="https://github.com/SynapseLayer/synapse-layer">GitHub</a> · <a href="https://pypi.org/project/synapse-layer/">PyPI</a>
  <br><br>
  Built by <a href="mailto:founder.synapselayer@proton.me">Ismael Marchi</a>
</div>
