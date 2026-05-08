<!-- mcp-name: io.github.SynapseLayer/synapse-layer -->

<p align="center">
  <img src="https://raw.githubusercontent.com/SynapseLayer/synapse-layer/main/docs/assets/synapse-layer-logo-dark.png" width="450" alt="Synapse Layer Logo">
</p>

<h3 align="center">Persistent Memory Layer with AES-256-GCM encryption at rest</h3>

<p align="center">Persistent. Encrypted. 1-line integration. 🧠</p>

<p align="center">
  <a href="https://github.com/SynapseLayer/synapse-layer/actions"><img src="https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/synapse-layer/"><img src="https://img.shields.io/pypi/v/synapse-layer" alt="PyPI"></a>
  <a href="https://registry.modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP_Registry-Official-7c3aed" alt="MCP Registry"></a>
  <a href="https://smithery.ai/server/@synapselayer/synapse-protocol"><img src="https://img.shields.io/badge/Smithery-Listed-0ea5e9" alt="Smithery"></a>
  <a href="https://synapselayer.org/docs"><img src="https://img.shields.io/badge/Docs-v1.1.8-0D9373" alt="Docs"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/tests-496_passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-88%25-brightgreen" alt="Coverage">
</p>

<p align="center">
  <a href="https://synapselayer.org">Website</a> ·
  <a href="https://forge.synapselayer.org">Forge</a> ·
  <a href="https://synapselayer.org/docs">Docs</a> ·
  <a href="https://pypi.org/project/synapse-layer/">PyPI</a> ·
  <a href="https://smithery.ai/servers/synapselayer/synapse-protocol">Smithery</a> ·
  <a href="https://registry.modelcontextprotocol.io">MCP Registry</a>
</p>

---

## ⚡ Quick Start (< 60 seconds)

### Option A: MCP (Zero-Code — Claude, Cursor, Windsurf)

Add to your MCP config and restart. No API keys. No code. Done.

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```

<details>
<summary>📁 Config file locations</summary>

| Client | Path |
|---|---|
| **Claude Desktop** (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Claude Desktop** (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Cursor** | `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |

</details>

**5 tools available instantly:**

| Tool | Description |
|---|---|
| `save_to_synapse` | Store memory with full Cognitive Security pipeline |
| `recall` | Retrieve memories ranked by Trust Quotient™ |
| `search` | Cross-agent memory search with full-text matching |
| `process_text` | Auto-detect decisions, milestones, and alerts |
| `health_check` | System health, version, and capability report |

### Option B: Python SDK

```bash
pip install synapse-layer
```

```python
from synapse_memory import SynapseMemory, SqliteBackend

memory = SynapseMemory(
    agent_id="my-agent",
    backend=SqliteBackend(),  # persistent, zero-config
)

# Store (full security pipeline runs automatically)
result = await memory.store("User prefers dark mode", confidence=0.95)
print(result.trust_quotient)   # 0.89
print(result.sanitized)        # True (PII auto-redacted)
print(result.privacy_applied)  # True (DP noise injected)

# Recall with ranking
recalls = await memory.recall("user preferences")
for r in recalls:
    print(f"{r.content} (TQ: {r.trust_quotient:.2f})")
```

### Option C: `@remember` Decorator (1-Line)

```python
from synapse_memory import SynapseMemory, remember

memory = SynapseMemory(agent_id="my-agent")

@remember(memory)
async def answer(prompt: str) -> str:
    return llm.chat(prompt)  # auto recall + store
```

---

## 🧠 Why Synapse Layer?

AI agents forget everything between sessions. They lose context when switching models. They reprocess the same information every call.

**Synapse Layer is the missing memory primitive.**

| | Without Memory | With Synapse Layer |
|---|---|---|
| **Session state** | Resets every turn | Persistent across sessions |
| **Token usage** | Reprocesses context | Up to 70% reduction via recall |
| **Model switching** | Context lost | Signed handover (GPT-4 ↔ Claude) |
| **Privacy** | Plaintext embeddings | AES-256-GCM + PII redaction + DP noise |
| **Recall quality** | Non-deterministic | Ranked by Trust Quotient™ |

---

## 🛡️ Security Architecture

Every memory passes through a **non-bypassable 4-layer Cognitive Security Pipeline**:

```
Agent → Sanitize (PII) → Validate Intent → Encrypt (AES-256-GCM) → DP Noise → Vault
```

| Layer | Name | What It Does |
|:---:|---|---|
| 1 | **Semantic Privacy Guard™** | 15+ regex patterns for PII, secrets, credentials |
| 2 | **Intelligent Intent Validation™** | Two-step categorization with self-healing on recall |
| 3 | **AES-256-GCM Encryption** | Authenticated encryption with PBKDF2 key derivation |
| 4 | **Differential Privacy** | Calibrated Gaussian noise on embeddings |

### 🔑 MCP Permissions

| Permission | Required? | Justification |
|---|:---:|---|
| `file_system` | **Local only** | Used exclusively by `SqliteBackend` for local `.synapse/memories.db` persistence. **Remote mode** (`forge.synapselayer.org/api/mcp`) does **not** use the filesystem — all data is stored in PostgreSQL. |
| `network` | ✅ | Required for remote MCP endpoint communication. |

> **Note:** If you use the remote MCP endpoint (recommended), no filesystem access is needed. The `file_system` permission only applies when running the SDK locally with `SqliteBackend`.

---

## 🔌 Framework Integrations

Native adapters — install the extra and import:

| Framework | Install | Import | Status |
|---|---|---|---|
| **LangChain** | `pip install synapse-layer[langchain]` | `from synapse_memory.integrations import SynapseChatMessageHistory` | ✅ Stable |
| **CrewAI** | `pip install synapse-layer[crewai]` | `from synapse_memory.integrations.crewai_memory import SynapseCrewStorage` | ✅ Stable |
| **AutoGen** | `pip install synapse-layer[autogen]` | `from synapse_memory.integrations import SynapseAutoGenMemory` | ✅ Stable |
| **LlamaIndex** | `pip install synapse-layer[llamaindex]` | `from synapse_memory.integrations.llamaindex import SynapseRetriever` | ✅ Stable |
| **Semantic Kernel** | `pip install synapse-layer[semantic-kernel]` | `from synapse_memory.integrations.semantic_kernel import SynapseChatHistory` | ✅ Stable |
| **MCP** | No install needed | `forge.synapselayer.org/api/mcp` | ✅ Live |

### LangChain Example

```python
from synapse_memory.integrations import SynapseChatMessageHistory

history = SynapseChatMessageHistory(agent_id="my-agent", session_id="session-1")
history.add_user_message("I prefer concise answers.")
history.add_ai_message("Got it — I'll keep it brief.")

# Works with RunnableWithMessageHistory:
# chain_with_history = RunnableWithMessageHistory(
#     runnable=your_chain,
#     get_session_history=lambda sid: SynapseChatMessageHistory(agent_id="agent", session_id=sid),
# )
```

### CrewAI Example

```python
from synapse_memory.integrations.crewai_memory import SynapseCrewStorage

storage = SynapseCrewStorage(agent_id="research-crew")
# Use with CrewAI: Memory(storage=storage)
```

See [`examples/`](examples/) for full working examples.

---

## 🔐 Encryption

```python
from synapse_memory import SynapseCrypto

key = SynapseCrypto.generate_key()
crypto = SynapseCrypto(key)

ciphertext = crypto.encrypt("sensitive memory")
plaintext = crypto.decrypt(ciphertext)  # AES-256-GCM

# Or from environment
crypto = SynapseCrypto.from_env("SYNAPSE_ENCRYPTION_KEY")
```

---

## 🏗️ Storage Backends

```python
from synapse_memory import SynapseMemory, SqliteBackend, MemoryBackend

memory = SynapseMemory(agent_id="test")                         # In-memory (default)
memory = SynapseMemory(agent_id="prod", backend=SqliteBackend()) # SQLite (persistent)
memory = SynapseMemory(agent_id="x", backend=MyBackend())        # Custom (implement StorageBackend)
```

---

## 🔍 Plugin Architecture

Clean **OSS/PRO separation** via the Strategy pattern:

```python
from synapse_memory import AutoSaveEngine

engine = AutoSaveEngine(database=db, redactor=redact)             # OSS
engine = AutoSaveEngine(database=db, redactor=redact, mode="pro") # PRO (auto-loads synapse-layer-pro)
engine = AutoSaveEngine(database=db, importance_scorer=MyScorer()) # Custom strategies
```

Interfaces: `ImportanceScorer`, `ConflictResolver`, `DedupStrategy`, `RedactionStrategy`

---

## 🏆 Competitive Comparison

| Capability | Synapse Layer | Mem0 | Zep | pgvector |
|---|:---:|:---:|:---:|:---:|
| AES-256-GCM Encryption | ✅ | ❌ | ❌ | ❌ |
| PII Redaction (15+ patterns) | ✅ | ❌ | ❌ | ❌ |
| Differential Privacy | ✅ | ❌ | ❌ | ❌ |
| Intent Validation + Self-Healing | ✅ | ❌ | ❌ | ❌ |
| Cross-Model Handover (JWT) | ✅ | ❌ | partial | ❌ |
| Trust Quotient™ Scoring | ✅ | ❌ | ❌ | ❌ |
| MCP Native (Official Registry) | ✅ | ❌ | ❌ | ❌ |
| Pluggable Storage Backends | ✅ | ❌ | ❌ | ✅ |
| Plugin Architecture | ✅ | ❌ | ❌ | ❌ |
| Zero-Knowledge Architecture | ✅ | ❌ | ❌ | ❌ |

---

## 📊 v1.1.8 Numbers

- **496 tests** | **88% coverage**
- **5 framework integrations** (LangChain, CrewAI, AutoGen, LlamaIndex, Semantic Kernel)
- **5 MCP tools** (real DB, not stubs)
- **2 storage backends** (Memory, SQLite) + custom protocol
- **AES-256-GCM** with PBKDF2 key derivation (600k iterations)

---

## 🌐 Open Core Model

- **Community (Apache 2.0)** — Full SDK, security pipeline, MCP integration, all backends, all integrations.
- **Enterprise** — Advanced TQ calibration, multi-tenant vaults, production infrastructure.

---

## 🛣️ Roadmap

| Version | Status | Highlights |
|---|---|---|
| **v1.1.x** | ✅ **Stable** | SqliteBackend, AES-256-GCM, `@remember`, 5 MCP tools, 5 framework integrations, 496 tests |
| **v1.2.0** | 🚧 Next | Embedding model selection, vector similarity search, batch operations |
| **v2.0.0** | 📋 Planned | Multi-tenant vault, team memory spaces, RBAC |

---

## 🤝 Contributing

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer
pip install -e ".[dev]"
python -m pytest tests/ -q  # 496 tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📎 Connect

- 📦 **PyPI:** [`pip install synapse-layer`](https://pypi.org/project/synapse-layer/)
- 🔌 **MCP:** `forge.synapselayer.org/api/mcp`
- 📖 **Docs:** [synapselayer.org/docs](https://synapselayer.org/docs)
- 📣 **X:** [@synapselayer](https://x.com/synapselayer)
- 🧠 **Forge:** [forge.synapselayer.org](https://forge.synapselayer.org)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Open-core model: SDK, MCP server, and security pipeline are fully open source. Trust Quotient™ weights, Neural Handover™ internals, and Synapse Forge are proprietary.

---

<div align="center">

  ⭐ **[Star Synapse Layer](https://github.com/SynapseLayer/synapse-layer)** — Give your agents a past.

  <br><br>

  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>

  <br><br>

  Built by <a href="https://synapselayer.org">Ismael Marchi</a> · <a href="https://x.com/synapselayer">@synapselayer</a>

</div>
