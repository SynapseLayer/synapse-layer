<!-- mcp-name: io.github.SynapseLayer/synapse-layer -->

<p align="center">
  <img src="https://cdn.abacus.ai/images/a39ccc3c-6b85-46d1-aa53-146d5a839b9e.png" width="450" alt="Synapse Layer — Continuous Consciousness Infrastructure"/>
</p>

<h3 align="center">Continuous Consciousness Infrastructure for AI Systems</h3>

<p align="center">Persistent. Secure. 1-line integration. 🧠</p>

<p align="center">
  <a href="https://github.com/SynapseLayer/synapse-layer/actions"><img src="https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/synapse-layer/"><img src="https://img.shields.io/pypi/v/synapse-layer" alt="PyPI"></a>
  <a href="https://registry.modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP_Registry-Official-7c3aed" alt="MCP Registry"></a>
  <a href="https://smithery.ai/servers/synapselayer/synapse-protocol"><img src="https://img.shields.io/badge/Smithery-Listed-0ea5e9" alt="Smithery"></a>
  <a href="https://synapselayer.org/docs"><img src="https://img.shields.io/badge/Docs-v1.1.2-0D9373" alt="Docs"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/tests-481_passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-90%25-brightgreen" alt="Coverage">
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

## ⚡ 1-Line Integration

```python
from synapse_memory import SynapseMemory, remember

memory = SynapseMemory(agent_id="my-agent")

@remember(memory)
async def answer(prompt: str) -> str:
    return llm.chat(prompt)  # auto recall + store
```

That's it. **Encryption, PII redaction, differential privacy, intent validation, and trust scoring** all happen under the hood.

---

## 🚀 Quick Start

### Install

```bash
pip install synapse-layer
```

### Store & Recall

```python
from synapse_memory import SynapseMemory, SqliteBackend

# Zero-config persistent storage
memory = SynapseMemory(
    agent_id="my-agent",
    backend=SqliteBackend(),  # survives restarts
)

# Store a memory (full Cognitive Security pipeline runs automatically)
result = await memory.store(
    content="User prefers dark mode and concise answers",
    confidence=0.95,
)
print(result.trust_quotient)   # 0.89
print(result.sanitized)        # True
print(result.privacy_applied)  # True

# Recall with self-healing
recalls = await memory.recall("user preferences")
for r in recalls:
    print(f"{r.content} (TQ: {r.trust_quotient:.2f})")
```

### Encrypt at Rest

```python
from synapse_memory import SynapseCrypto

# Generate a key (or derive from password)
key = SynapseCrypto.generate_key()
crypto = SynapseCrypto(key)

# AES-256-GCM authenticated encryption
ciphertext = crypto.encrypt("sensitive memory content")
plaintext = crypto.decrypt(ciphertext)

# Or from environment variable
crypto = SynapseCrypto.from_env("SYNAPSE_ENCRYPTION_KEY")
```

### MCP Connection (1-Click Setup)

Add to your MCP config file and you're done. No API keys required.

<details>
<summary><strong>🟣 Claude Desktop</strong></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```
Restart Claude Desktop. Done.
</details>

<details>
<summary><strong>🟢 Cursor</strong></summary>

Edit `.cursor/mcp.json` in your project root (or global `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```
Restart Cursor. The 4 tools appear in the MCP panel.
</details>

<details>
<summary><strong>🔵 Windsurf</strong></summary>

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```
Restart Windsurf.
</details>

<details>
<summary><strong>⚙️ Any MCP Client</strong></summary>

```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```
</details>

**4 tools available:**

| Tool | Description |
|---|---|
| `save_to_synapse` | Structured memory persistence with full security pipeline |
| `recall` | Semantic memory retrieval with TQ ranking |
| `process_text` | Autonomous decision/milestone/alert detection |
| `health_check` | System health, version, capability report |

---

## 🧠 Why Synapse Layer?

AI agents are stateless by design. They forget everything between sessions, lose context when switching models, and reprocess the same information every call.

**Synapse Layer is the missing memory primitive.**

| | Without Memory | With Synapse Layer |
|---|---|---|
| **Session state** | Resets every turn | Persistent across sessions |
| **Token usage** | Reprocesses context | Up to 70% reduction via recall |
| **Model switching** | Context lost | Signed handover (GPT-4 ↔ Claude) |
| **Privacy** | Plaintext embeddings | AES-256-GCM + PII redaction + DP noise |
| **Recall quality** | Non-deterministic | Deterministic, ranked by Trust Quotient™ |

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

---

## 🔌 Integrations

Native adapters for every major framework:

| Framework | Import | Status |
|---|---|---|
| **LangChain** | `from synapse_memory.integrations import SynapseChatMessageHistory` | ✅ |
| **CrewAI** | `from synapse_memory.integrations.crewai_memory import SynapseCrewStorage` | ✅ |
| **AutoGen** | `from synapse_memory.integrations import SynapseAutoGenMemory` | ✅ |
| **LlamaIndex** | `from synapse_memory.integrations.llamaindex import SynapseRetriever` | ✅ |
| **Semantic Kernel** | `from synapse_memory.integrations.semantic_kernel import SynapseChatHistory` | ✅ |
| **MCP (Claude, etc.)** | Direct connection via `forge.synapselayer.org/api/mcp` | ✅ |

See [full integration docs](https://synapselayer.org/docs) for each framework.

---

## 🏗️ Storage Backends

Pluggable persistence via the `StorageBackend` protocol:

```python
from synapse_memory import SynapseMemory, SqliteBackend, MemoryBackend

# In-memory (default — for testing/demos)
memory = SynapseMemory(agent_id="test")

# SQLite (zero-config local persistence)
memory = SynapseMemory(agent_id="prod", backend=SqliteBackend())

# Custom backend (implement the StorageBackend protocol)
memory = SynapseMemory(agent_id="custom", backend=MyPostgresBackend())
```

---

## 🔍 Plugin Architecture

Clean **OSS/PRO separation** via the Strategy pattern:

```python
from synapse_memory import AutoSaveEngine

# OSS mode (default)
engine = AutoSaveEngine(database=db, redactor=redact)

# PRO mode — auto-loads synapse-layer-pro if installed
engine = AutoSaveEngine(database=db, redactor=redact, mode="pro")

# Custom — bring your own strategies
engine = AutoSaveEngine(database=db, importance_scorer=MyScorer())
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
| Pluggable Storage Backends | ✅ | ❌ | ❌ | ✅ |
| MCP Native | ✅ | ❌ | ❌ | ❌ |
| Plugin Architecture | ✅ | ❌ | ❌ | ❌ |
| Zero-Knowledge Architecture | ✅ | ❌ | ❌ | ❌ |

---

## 📊 v1.1.0 Numbers

- **481 tests** | **90% coverage**
- **5 framework integrations** (LangChain, CrewAI, AutoGen, LlamaIndex, Semantic Kernel)
- **4 MCP tools** (real DB, not stubs)
- **2 storage backends** (Memory, SQLite) + custom protocol
- **AES-256-GCM** with PBKDF2 key derivation (600k iterations)

---

## 🌐 Open Core Model

- **Community (Apache 2.0)** — Full SDK, security pipeline, MCP integration, all backends, all integrations.
- **Enterprise** — Advanced TQ calibration, multi-tenant vaults, production infrastructure.

The foundation is open. The intelligence layer scales with you.

---

## 🛣️ Roadmap

| Version | Status | Highlights |
|---|---|---|
| **v1.1.0** | ✅ **Stable** | SqliteBackend, AES-256-GCM crypto, `@remember` wrapper, real MCP tools, 481 tests |
| **v1.2.0** | 🚧 Next | Embedding model selection, vector similarity search, batch operations |
| **v2.0.0** | 📋 Planned | Multi-tenant vault, team memory spaces, RBAC |

---

## 🤝 Contributing

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer
pip install -e ".[dev]"
python -m pytest tests/ -q  # 481 tests
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
