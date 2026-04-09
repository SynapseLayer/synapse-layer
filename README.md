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

# Each result includes a Trust Quotient (TQ)
# A deterministic signal of memory reliability — not a black box.
```

That's the entire API. **Encryption, PII redaction, differential privacy, intent validation, and trust scoring** — all happen under the hood. No configuration. No boilerplate. No amnesia.

---

## 🧠 Why Synapse Layer?

AI agents are stateless by design.

They forget everything between sessions, lose context when switching models, and continuously reprocess the same information — increasing cost, latency, and inconsistency.

**This is the missing layer in modern AI systems.**

Synapse Layer introduces persistent, encrypted, cross-model memory with deterministic recall.

Not as a feature — but as **infrastructure**.

---

## 🏢 Real-World Impact

### Used in production

Synapse Layer powers real systems in production:

- 📉 **Up to 70% reduction** in token usage via persistent context recall
- 🔁 **Cross-session and cross-model** memory continuity
- 🔐 **Built-in privacy and compliance** (LGPD/GDPR ready)
- 🧠 **Zero context loss** across 10K+ agent sessions

> *"Synapse Layer eliminated our biggest bottleneck — agents that forget."*

---

## 🔓 Open Core Model

Synapse Layer follows an **Open Core** approach.

- **Community (Apache 2.0)**
  Core SDK, secure memory pipeline, MCP integration, and full local control.

- **Enterprise**
  Advanced memory intelligence, cross-model continuity, and production-grade infrastructure.

The foundation is open. The intelligence layer scales with you.

To enable PRO: `pip install synapse-layer-pro` and set `SYNAPSE_MODE=pro`.

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

## 🛡️ Security Architecture

Every memory passes through a **non-bypassable 4-layer Cognitive Security Pipeline** before persistence:

```
Agent → Sanitize (PII) → Validate Intent → Encrypt (AES-256) → DP Noise → Vault
```

| Layer | Name | What It Does |
|:---:|---|---|
| 1 | **Semantic Privacy Guard™** | 15+ redaction patterns for PII, secrets, and credentials |
| 2 | **Intelligent Intent Validation™** | Autonomous categorization with self-healing on recall |
| 3 | **Differential Privacy** | Calibrated noise on embeddings before storage |
| 4 | **Neural Handover™** | Signed cross-model context transfer with vault-first persistence |

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

## ⚡ Why It Matters

Memory is the missing primitive in AI systems.

Without memory, agents restart every session.
With memory, intelligence compounds over time.

Synapse Layer makes memory:

- **Persistent** — survives across sessions and restarts
- **Secure** — encrypted, redacted, privacy-noised before storage
- **Portable** — moves between models via signed handover
- **Deterministic** — every recall is explainable and hallucination-free

---

## 🎯 Roadmap & Community

| Version | Status | Highlights |
|---|---|---|
| **v1.0.7** | ✅ **Stable** | Auto-Save Engine, Plugin Architecture, MCP Bridge, Smithery listing |
| **v1.1.0** | 🚧 In Progress | LangChain native adapter, CrewAI integration, embedding model selection |
| **v1.2.0** | 📋 Planned | Synapse Forge visual debugger, real-time memory inspector |
| **v2.0.0** | 📋 Planned | Multi-tenant vault, team memory spaces, RBAC |

### Contributing

We welcome contributions! Whether it's bug reports, documentation, new trigger patterns, or framework adapters:

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

## 🧠 The Future of AI Memory

Synapse Layer is not another vector database.

It is the **memory infrastructure layer** for intelligent systems.

As AI agents become autonomous, memory becomes the bottleneck.

We are solving it — at the foundation level.

---

<div align="center">
  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>
  <br><br>
  <a href="https://synapselayer.org">Website</a> · <a href="https://synapselayer.org/forge">Forge</a> · <a href="https://synapselayer.org/docs">Docs</a> · <a href="https://github.com/SynapseLayer/synapse-layer">GitHub</a> · <a href="https://pypi.org/project/synapse-layer/">PyPI</a> · <a href="https://smithery.ai/servers/synapselayer/synapse-protocol">Smithery</a>
  <br><br>
  Built by <a href="https://synapselayer.org">Ismael Marchi</a> · <a href="https://x.com/synapselayer">@synapselayer</a>
</div>
