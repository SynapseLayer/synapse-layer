<div align="center">

  # Synapse Layer — Long-Term Memory for AI Agents

  > **Plug once. Remember forever. Zero-Knowledge. Zero-Amnesia. 🧠**

  <br>

  [![CI](https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml/badge.svg)](https://github.com/SynapseLayer/synapse-layer/actions)
  [![Synapse Layer on Smithery](https://smithery.ai/badge/synapselayer/synapse-protocol)](https://smithery.ai/servers/synapselayer/synapse-protocol)
  [![Documentation](https://img.shields.io/badge/Docs-Mintlify-0D9373)](https://synapselayer.org/docs)

  [Website](https://synapselayer.org) · [Forge](https://synapselayer.org/forge) · [Docs](https://synapselayer.org/docs) · [PyPI](https://pypi.org/project/synapse-layer/) · [Smithery](https://smithery.ai/servers/synapselayer/synapse-protocol)

  <!-- mcp-name: io.github.SynapseLayer/synapse-secure-memory -->

</div>

---

```python
from synapse_layer import SynapseMemory

memory = SynapseMemory(agent_id="my-agent")

# 1. Agents save context automatically
memory.save("User prefers absolute security and neural handover.")

# 2. Recall is deterministic and explainable
info = memory.recall("user focus")
# Result: "User prefers absolute security and neural handover."
```

That's the entire API. **Encryption, PII redaction, differential privacy, intent validation, and trust scoring** — all happen under the hood. No configuration. No boilerplate. No amnesia.

---

## 🚀 Quick Install

**Via Smithery (recommended for MCP agents):**

```bash
npx @smithery/cli install @synapselayer/synapse-protocol
```

**Via PyPI:**

```bash
pip install synapse-layer
```

**Direct MCP connection:**

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```

**4 tools available out of the box:**

| Tool | Description |
|---|---|
| `process_text` | Scans text for decisions, milestones, alerts — saves autonomously |
| `save_to_synapse` | Direct structured memory persistence with full security pipeline |
| `backfill_embeddings` | Async vector embedding generation for stored memories |
| `health_check` | System health, version, capability report |

---

## 🔓 Open Core Model

Synapse Layer follows a transparent **open-core architecture**. The community edition is fully functional. The PRO tier unlocks proprietary intelligence.

| Capability | Community (OSS) | Enterprise (PRO) |
|---|:---:|:---:|
| Memory Storage & Recall | ✅ | ✅ |
| MCP Server (4 tools) | ✅ | ✅ |
| PII/Secret Redaction (15+ patterns) | ✅ | ✅ |
| AES-256-GCM Encryption | ✅ | ✅ |
| Differential Privacy (ε-DP) | ✅ | ✅ |
| Basic Importance Scoring | ✅ | ✅ |
| Hash-Based Deduplication | ✅ | ✅ |
| Auto-Save Trigger Detection | ✅ | ✅ |
| Plugin Architecture | ✅ | ✅ |
| **TQ™ Multi-Factor Scoring** | — | ✅ |
| **Neural Handover™** (JWT cross-model) | — | ✅ |
| **N-Gram Semantic Deduplication** | — | ✅ |
| **Weighted Conflict Resolution** | — | ✅ |
| **Priority Intelligence Layer** | — | ✅ |
| Priority Support & SLA | — | ✅ |

> *"The OSS shows what is possible. The PRO defines how intelligence actually works."*

To enable PRO: `pip install synapse-layer-pro` and set `SYNAPSE_MODE=pro`.

---

## 🧠 Why Synapse Layer?

AI agents are stateless. They forget everything between sessions, waste tokens re-asking questions, and lose critical context when switching models. Existing solutions store plaintext embeddings (security risk), lack cross-model support, or require manual vector DB management.

Synapse Layer solves this with a **deterministic, explainable, hallucination-free** memory engine.

### Trust Quotient™ (TQ) — The Brain

Every memory operation is scored by the **Trust Quotient™**, a multi-factor quality signal built on five pillars:

| Pillar | What It Measures |
|---|---|
| **Recency** | How fresh is the memory? Recent context weighs more. |
| **Frequency** | How often is this pattern confirmed across interactions? |
| **Explicit Signals** | Did the agent or user explicitly mark this as important? |
| **Source Authority** | Was this from a validated source or an inference? |
| **Verification Consensus** | Do multiple independent signals agree on the classification? |

The TQ formula is dynamically calibrated — weights are proprietary and adapt per deployment. What matters is the guarantee:

> **No black box. Every recall is deterministic, explainable, and hallucination-free.**

The full TQ algorithm is available under Enterprise license. The OSS provides baseline linear scoring. See the [Plugin Architecture](#-plugin-architecture) section for extensibility.

---

## 🏢 Real-World Impact

### Case Study: GoArqIA Architecture Platform

[GoArqIA](https://goarqia.com) is an AI-powered architecture platform that uses Synapse Layer as its memory backbone in production.

| Metric | Result |
|---|---|
| **Token consumption** | **70% reduction** via persistent context recall |
| **Compliance** | Full **LGPD/GDPR** compliance with built-in PII redaction |
| **Cross-model transfer** | **Neural Handover™** in production (GPT-4 ↔ Claude) |
| **Memory reliability** | Zero context loss across 10K+ agent sessions |

> *"Synapse Layer eliminated our biggest bottleneck — agents that forget. The security pipeline gave us LGPD compliance without extra engineering."*

---

## 🛠️ Technical Capabilities

### Zero-Leak Security Policy

Every memory passes through a **non-bypassable 4-layer Cognitive Security Pipeline** before persistence:

```
Agent → Sanitize (PII) → Validate Intent → Encrypt (AES-256) → DP Noise → Vault
```

| Seal | Name | Function |
|:---:|---|---|
| 1 | **Semantic Privacy Guard™** | 15+ regex patterns: emails, phones, SSNs, CPFs, CNPJs, API keys, Bearer tokens, AWS keys, private endpoints |
| 2 | **Intelligent Intent Validation™** | Auto-categorization with critical keyword promotion and self-healing on recall |
| 3 | **Differential Privacy** | Calibrated Gaussian noise (ε-bounded) on embeddings before storage |
| 4 | **Neural Handover™** | HMAC-SHA256 signed JWT cross-model transfer with vault-first persistence |

### Autonomous Detection

Synapse Layer doesn’t just store — it **recognizes** what matters:

- 🎯 **Milestones** — deployments, launches, releases, first customers
- 🎯 **Decisions** — pivots, strategy changes, architectural choices
- 🎯 **Alerts** — security incidents, breaches, critical bugs, downtime
- 🎯 **Strategic context** — funding, partnerships, compliance events

All detected autonomously via the [Auto-Save Engine](#auto-save-engine). No manual tagging required.

### Multi-Framework Ready

| Framework | Status |
|---|---|
| Claude Desktop | ✅ Native MCP |
| LangChain | ✅ Via MCP adapter |
| CrewAI | ✅ Via MCP adapter |
| Custom agents | ✅ Python SDK + REST |
| Smithery | ✅ [Listed](https://smithery.ai/servers/synapselayer/synapse-protocol) |

---

## Quick Start (SDK)

```python
from synapse_layer import SynapseMemory
import asyncio

async def main():
    mem = SynapseMemory(agent_id="my-agent")

    # Store — full security pipeline runs automatically
    await mem.store("User prefers dark mode", confidence=0.95)

    # Recall — ranked by Trust Quotient™
    results = await mem.recall("user preferences")
    for r in results:
        print(f"{r.content} (TQ: {r.trust_quotient:.3f})")

asyncio.run(main())
```

That’s it. Encryption, sanitization, differential privacy, intent validation, and trust scoring — all happen automatically.

---

## Auto-Save Engine

The Auto-Save Engine gives agents **autonomous memory** — it decides what’s worth remembering.

```python
from synapse_memory.autosave import AutoSaveEngine, AutoSaveEvent

# Direct save
result = engine.save(AutoSaveEvent(
    content="Launched OFFLY v2.0 to production",
    project="OFFLY",
    type="[MILESTONE]",
    importance=4,
    tags=["launch", "production"],
))

# Auto-detect — the engine decides what’s worth saving
results = engine.process_text("We decided to pivot to enterprise B2B")
```

**Pipeline:** `text → trigger_detect → policy_evaluate → redact → dedup → persist → embed (async)`

- 🔒 PII/secrets **always** redacted before storage
- ⚡ Near-zero latency (embedding=NULL on insert, async backfill)
- 🧠 Autonomous trigger detection (milestones, decisions, alerts)
- 🔁 LRU cache + hash dedup prevents duplicates
- 🏗️ Extensible via plugin architecture

---

## 🔌 Plugin Architecture

Clean **OSS/PRO separation** via the Strategy pattern:

```
┌─────────────────────────────────────────────┐
│              AutoSaveEngine                 │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Importance│ │ Conflict │ │   Dedup    │  │
│  │  Scorer   │ │ Resolver │ │  Strategy  │  │
│  └─────┬────┘ └─────┬────┘ └─────┬──────┘  │
│        │            │            │          │
│   ┌────▼────────────▼────────────▼────┐     │
│   │        Plugin Loader              │     │
│   │   OSS defaults ← PRO override    │     │
│   └───────────────────────────────────┘     │
└─────────────────────────────────────────────┘
```

**Interfaces** (`synapse_memory.plugins`):
- `ImportanceScorer` — Score event significance (0.0–1.0)
- `ConflictResolver` — Resolve competing events
- `DedupStrategy` — Detect duplicate memories
- `RedactionStrategy` — Extensible content redaction

```python
# OSS mode (default)
engine = AutoSaveEngine(database=db, redactor=redact)

# PRO mode — auto-loads synapse-layer-pro if installed
engine = AutoSaveEngine(database=db, redactor=redact, mode="pro")

# Custom strategies — bring your own
engine = AutoSaveEngine(
    database=db, redactor=redact,
    importance_scorer=MyCustomScorer(),
)
```

---

## Competitive Comparison

| Capability | Synapse Layer | Mem0 | Zep | pgvector (raw) |
|---|:---:|:---:|:---:|:---:|
| Client-side AES-256-GCM | ✅ | ❌ | ❌ | ❌ |
| PII/Secret Redaction (15+ patterns) | ✅ | ❌ | ❌ | ❌ |
| Differential Privacy on Embeddings | ✅ | ❌ | ❌ | ❌ |
| Intent Validation Pipeline | ✅ | ❌ | ❌ | ❌ |
| Cross-Model Handover (JWT) | ✅ | ❌ | partial | ❌ |
| Trust Quotient™ Scoring | ✅ | ❌ | ❌ | ❌ |
| Autonomous Memory Detection | ✅ | ❌ | ❌ | ❌ |
| Self-Healing on Recall | ✅ | ❌ | ❌ | ❌ |
| MCP Native | ✅ | ❌ | ❌ | ❌ |
| Plugin Architecture (OSS/PRO) | ✅ | ❌ | ❌ | ❌ |
| Zero-Knowledge Guarantee | ✅ | ❌ | ❌ | ❌ |

---

## 🎯 Roadmap & Community

| Version | Status | Highlights |
|---|---|---|
| **v1.0.7** | ✅ **Stable** | Auto-Save Engine, Plugin Architecture, MCP Bridge, Smithery listing |
| **v1.1.0** | 🚧 In Progress | LangChain native adapter, CrewAI integration, embedding model selection |
| **v1.2.0** | 📋 Planned | Synapse Forge visual debugger, real-time memory inspector |
| **v2.0.0** | 📋 Planned | Multi-tenant vault, team memory spaces, RBAC |

### Contributing

We welcome contributions! Whether it’s bug reports, documentation, new trigger patterns, or framework adapters:

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer
pip install -e .
python -m pytest tests/ -q  # 265 tests, 95% coverage
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Connect

- 📣 Follow updates on [X (Twitter)](https://x.com/synapselayer)
- 🧠 Try the [Forge Dashboard](https://synapselayer.org/forge)
- 📖 Read the [Technical Deep-Dive on dev.to](https://dev.to/synapselayer/beyond-context-windows-a-zero-knowledge-memory-reference-implementation-for-the-mcp-ecosystem-4bcg)
- 📦 Install from [PyPI](https://pypi.org/project/synapse-layer/) or [Smithery](https://smithery.ai/servers/synapselayer/synapse-protocol)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Open-core model: the SDK, MCP server, and security pipeline are fully open source. Trust Quotient™ weights, Neural Handover™ internals, and Synapse Forge are proprietary and available under commercial license.

---

<div align="center">
  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>
  <br><br>
  <a href="https://synapselayer.org">Website</a> · <a href="https://synapselayer.org/forge">Forge</a> · <a href="https://synapselayer.org/docs">Docs</a> · <a href="https://github.com/SynapseLayer/synapse-layer">GitHub</a> · <a href="https://pypi.org/project/synapse-layer/">PyPI</a> · <a href="https://smithery.ai/servers/synapselayer/synapse-protocol">Smithery</a>
  <br><br>
  Built by <a href="https://synapselayer.org">Ismael Marchi</a> · <a href="https://x.com/synapselayer">@synapselayer</a>
</div>
