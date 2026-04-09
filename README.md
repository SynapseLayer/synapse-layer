<div align="center">

  <h1>Synapse Layer</h1>

  <p><strong>Persistent, Encrypted Memory Infrastructure for AI Agents</strong></p>

  <p>Plug once. Remember forever. Zero-Knowledge. Zero-Amnesia. 🧠</p>

  <p><i>The missing memory primitive for AI systems.</i></p>

  <br>

  <a href="https://github.com/SynapseLayer/synapse-layer/actions"><img src="https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://smithery.ai/servers/synapselayer/synapse-protocol"><img src="https://smithery.ai/badge/synapselayer/synapse-protocol" alt="Synapse Layer on Smithery"></a>
  <a href="https://synapselayer.org/docs"><img src="https://img.shields.io/badge/Docs-Mintlify-0D9373" alt="Documentation"></a>
  <a href="https://pypi.org/project/synapse-layer/"><img src="https://img.shields.io/pypi/v/synapse-layer" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="SKILL.md"><img src="https://img.shields.io/badge/AI-Agent_Ready-blueviolet" alt="AI Agent Ready"></a>

  <br><br>

  <a href="https://synapselayer.org">Website</a> · <a href="https://synapselayer.org/forge">Forge</a> · <a href="https://synapselayer.org/docs">Docs</a> · <a href="https://pypi.org/project/synapse-layer/">PyPI</a> · <a href="https://smithery.ai/servers/synapselayer/synapse-protocol">Smithery</a>

  <!-- mcp-name: io.github.SynapseLayer/synapse-secure-memory -->

</div>

---

```python
from synapse_layer import SynapseMemory

memory = SynapseMemory(agent_id="agent-1")

await memory.store(
    content="User prefers secure systems",
    confidence=0.95
)

results = await memory.recall("user preferences")

# Each result includes a Trust Quotient (TQ) — a deterministic score based on:
# - Recency (how current the info is)
# - Frequency (how often it was reinforced)
# - Source Authority (how reliable the input source is)
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

## 🎯 Who Is This For

- **AI agent builders** — give your agents persistent context across sessions
- **LLM infrastructure teams** — reduce token waste, increase reasoning consistency
- **Production AI systems** — deterministic recall with zero hallucination risk
- **Privacy-first organizations** — built-in LGPD/GDPR compliance with zero-knowledge architecture

---

## Before vs After

| | Without Memory | With Synapse Layer |
|---|---|---|
| **Session state** | Stateless — resets every turn | Persistent — survives across sessions |
| **Token usage** | Reprocesses context every call | Up to 70% reduction via recall |
| **Model switching** | Context lost between models | Signed handover (GPT-4 ↔ Claude) |
| **Privacy** | Plaintext embeddings | AES-256-GCM + PII redaction + DP noise |
| **Recall quality** | Non-deterministic | Deterministic, explainable, ranked by TQ |

---

## 🏢 Real-World Impact

### Used in production

Synapse Layer powers real systems in production:

- 📉 **Up to 70% reduction** in token usage via persistent context recall
- 🔁 **Cross-session and cross-model** memory continuity
- 🔐 **Built-in privacy and compliance** (LGPD/GDPR ready)
- 🧠 **Zero context loss** across 10K+ agent sessions

> *"Synapse Layer transformed our agents from stochastic parrots into reliable professional partners by giving them an immutable expert memory."*
> — **Ismael Marchi**, Founder @ [GoArqIA](https://goarqia.com)

---

## 🔓 Open Core Model

Synapse Layer follows an **Open Core** approach.

- **Community (Apache 2.0)**
  Core SDK, secure memory pipeline, MCP integration, and full local control.

- **Enterprise**
  Advanced memory intelligence, cross-model continuity, and production-grade infrastructure.

The foundation is open. The intelligence layer scales with you.

Enterprise features (advanced memory intelligence, cross-model continuity) are enabled via commercial license.<br>
Contact: [synapselayer.org](https://synapselayer.org)

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

## 🔗 Using Synapse Layer with LangChain

Synapse Layer integrates natively with LangChain as a chat message history backend.
Every message passes through the full Cognitive Security pipeline — PII redaction,
intent validation, and AES-256 encryption — before persistence.

```bash
pip install synapse-layer langchain-core
```

```python
from synapse_memory.integrations import SynapseChatMessageHistory

# Drop-in replacement for any LangChain message history
history = SynapseChatMessageHistory(agent_id="my-agent")

history.add_user_message("I prefer concise responses.")
history.add_ai_message("Got it — keeping it brief.")

# Retrieve messages in LangChain-compatible format
messages = history.messages
```

Works with `RunnableWithMessageHistory` for LCEL chains:

```python
from langchain_core.runnables.history import RunnableWithMessageHistory

chain_with_history = RunnableWithMessageHistory(
    runnable=your_chain,
    get_session_history=lambda sid: SynapseChatMessageHistory(
        agent_id="your-agent", session_id=sid,
    ),
)
```

> **Note:** This is the OSS adapter. Advanced scoring, enterprise retrieval
> strategies, and PRO heuristics are available under separate license.
> See [synapselayer.org/docs](https://synapselayer.org/docs).

## 🤖 Using Synapse Layer with CrewAI

Synapse Layer plugs into CrewAI as a persistent, encrypted storage backend
for the unified memory system. Every memory passes through PII redaction,
intent validation, and AES-256 encryption automatically.

```bash
pip install synapse-layer[crewai]
```

```python
from synapse_memory.integrations.crewai_memory import SynapseCrewStorage
from crewai.memory.unified_memory import Memory
from crewai import Crew

crew = Crew(
    agents=[...],
    tasks=[...],
    memory=Memory(storage=SynapseCrewStorage(agent_id="my-crew")),
)
```

The adapter implements CrewAI's `StorageBackend` protocol — scope management,
category filtering, and async variants all work out of the box.

> **Note:** This is the OSS adapter. Advanced scoring, enterprise retrieval
> strategies, and PRO heuristics are available under separate license.
> See [synapselayer.org/docs](https://synapselayer.org/docs).

## 🧠 Using Synapse Layer with AutoGen

Synapse Layer implements AutoGen's native `Memory` interface (`autogen-core >=0.7`),
giving agents persistent, encrypted memory that survives across conversations.

```bash
pip install synapse-layer[autogen]
```

```python
from synapse_memory.integrations import SynapseAutoGenMemory
from autogen_agentchat.agents import AssistantAgent

memory = SynapseAutoGenMemory(agent_id="my-agent", top_k=5)
agent  = AssistantAgent(
    name="assistant",
    model_client=client,
    memory=[memory],
)
```

The agent automatically calls `memory.update_context()` before each LLM
invocation — relevant memories are injected as system context, no glue code needed.

> **Note:** This is the OSS adapter. Advanced scoring, enterprise retrieval
> strategies, and PRO heuristics are available under separate license.
> See [synapselayer.org/docs](https://synapselayer.org/docs).

## 🔍 Using Synapse Layer with LlamaIndex

Synapse Layer enables LlamaIndex agents to have a sovereign, encrypted
memory that survives across indexes and query engines.  Two adapters
are provided: **SynapseRetriever** (RAG) and **SynapseChatStore** (chat history).

```bash
pip install synapse-layer[llamaindex]
```

**Retriever** — plug into any query engine:

```python
from synapse_memory.integrations.llamaindex import SynapseRetriever

retriever = SynapseRetriever(agent_id="researcher-01", top_k=5)
nodes = retriever.retrieve("What is our deployment strategy?")
```

**Chat Store** — persistent, encrypted chat history:

```python
from synapse_memory.integrations.llamaindex import SynapseChatStore
from llama_index.core.memory import ChatMemoryBuffer

store = SynapseChatStore(agent_id="assistant-01")
memory = ChatMemoryBuffer.from_defaults(chat_store=store, chat_store_key="session-1")
```

Every message passes through the Cognitive Security pipeline — PII
redaction, intent validation, and AES-256 encryption — automatically.

> **Note:** This is the OSS adapter. Advanced scoring, enterprise retrieval
> strategies, and PRO heuristics are available under separate license.
> See [synapselayer.org/docs](https://synapselayer.org/docs).

## 🏢 Using Synapse Layer with Semantic Kernel

Synapse Layer provides the enterprise-grade, zero-knowledge memory
infrastructure for Microsoft Semantic Kernel developers.  Two adapters
are provided: **SynapseChatHistory** (persistent chat state) and
**SynapseMemoryStore** (knowledge retrieval).

```bash
pip install synapse-layer[semantic-kernel]
```

**Chat History** — sovereign, encrypted conversation state:

```python
from synapse_memory.integrations.semantic_kernel import SynapseChatHistory

history = SynapseChatHistory(agent_id="copilot-01")
history.add_user_message("What is our revenue target?")
history.add_assistant_message("The Q4 target is $12.5M.")
```

**Memory Store** — persistent knowledge retrieval:

```python
from synapse_memory.integrations.semantic_kernel import SynapseMemoryStore

store = SynapseMemoryStore(agent_id="enterprise-bot")
# Use with SemanticTextMemory for full RAG capabilities
```

Every message and record passes through the Cognitive Security pipeline —
PII redaction, intent validation, and AES-256 encryption — automatically.

> **Note:** This is the OSS adapter. Advanced scoring, enterprise retrieval
> strategies, and PRO heuristics are available under separate license.
> See [synapselayer.org/docs](https://synapselayer.org/docs).

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

## 🤖 Built for AI Agents

This repository is optimized for autonomous agents, LLM orchestrators, and multi-agent systems.

| File | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Machine-readable agent interface specification |
| [`llms.txt`](llms.txt) | AI crawler format for LLM discovery |
| MCP native protocol | Direct integration via `forge.synapselayer.org/api/mcp` |

Synapse Layer is not just a library you call — it's **infrastructure your agents connect to**.

---

## 🎯 Roadmap & Community

| Version | Status | Highlights |
|---|---|---|
| **v1.0.7** | ✅ **Stable** | Auto-Save Engine, Plugin Architecture, MCP Bridge, Smithery listing |
| **v1.1.0** | 🚧 In Progress | ✅ LangChain native adapter, ✅ CrewAI integration, ✅ AutoGen integration, ✅ LlamaIndex integration, ✅ Semantic Kernel integration, embedding model selection |
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

  ⭐ **[Star Synapse Layer](https://github.com/SynapseLayer/synapse-layer)** — Memory is not optional. Give your agents a past.

  <br><br>

  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>

  <br><br>

  Built by <a href="https://synapselayer.org">Ismael Marchi</a> · <a href="https://x.com/synapselayer">@synapselayer</a>

</div>
