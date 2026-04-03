<div align="center">

![Synapse Layer Logo](https://img.shields.io/badge/Synapse%20Layer-v1.0.3-6366f1?style=flat-square)

# Synapse Layer

### Zero-Knowledge Memory Layer for AI Agents

**Giving Agents a Past. Giving Models a Soul.** ⚗️

[![PyPI](https://img.shields.io/pypi/v/synapse-layer?style=flat-square&color=6366f1)](https://pypi.org/project/synapse-layer/)
[![License](https://img.shields.io/badge/license-Apache%202.0-000000?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?style=flat-square)](https://www.python.org/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-10b981?style=flat-square)](https://modelcontextprotocol.io)
[![GitHub Stars](https://img.shields.io/github/stars/SynapseLayer/synapse-layer?style=flat-square&color=fbbf24)](https://github.com/SynapseLayer/synapse-layer)
[![Build](https://img.shields.io/badge/build-passing-10b981?style=flat-square)](https://github.com/SynapseLayer/synapse-layer/actions)

🔐 **Semantic Privacy Guard™** | 🧠 **Intelligent Intent Validation™** | 🔌 **MCP Native**

[Website](https://www.synapselayer.org) • [Documentation](https://www.synapselayer.org/docs) • [GitHub Issues](https://github.com/SynapseLayer/synapse-layer/issues) • [Discussions](https://github.com/SynapseLayer/synapse-layer/discussions)

</div>

---

## The Problem

AI agents suffer from **critical memory loss**.

They reset every session. They hallucinate when information conflicts. They can't transfer context between models. They waste **70% more tokens** reprocessing the same information.

**Your agent becomes dumber the longer you use it.**

---

## The Solution

**Synapse Layer** is persistent, encrypted memory infrastructure for AI agents.

```python
from synapse_layer import SynapseMemory
import asyncio

async def main():
    memory = SynapseMemory(agent_id="claude-v1")
    
    # Store user preference (encrypted on your machine)
    await memory.store(
        content="User prefers concise answers in Portuguese",
        confidence=0.95,
        tags=["user-profile", "communication"]
    )
    
    # Recall with semantic search
    results = await memory.recall("user communication", top_k=5)
    
    # Transfer context to GPT-4 with cryptographic proof
    handover = await memory.create_handover(
        target_model="gpt-4",
        session_summary="Analyzed user preferences over 50 messages"
    )
    
    print(f"✓ Handover verified (integrity proof: {handover.signature[:16]}...)")

asyncio.run(main())
```

---

## Why Synapse Layer?

| Feature | Synapse Layer | Mem0 | Zep | pgvector |
|---------|:---:|:---:|:---:|:---:|
| **Client-Side Encryption** | ✅ AES-256-GCM | ❌ Server-side | ❌ Server-side | ❌ None |
| **Zero-Knowledge (You Own Keys)** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Model-to-Model Handover** | ✅ Verified | ❌ No | ⚠️ Basic | ❌ No |
| **Conflict Resolution** | ✅ Trust Quotient™ | ❌ No | ❌ No | ❌ No |
| **MCP Native** | ✅ Full | ❌ No | ⚠️ Partial | ❌ No |
| **Audit Trail** | ✅ Immutable | ⚠️ Basic | ⚠️ Basic | ❌ No |
| **GDPR/LGPD Ready** | ✅ Yes | ⚠️ Partial | ⚠️ Partial | ❌ No |
| **Open Source** | ✅ Apache 2.0 | ❌ Proprietary | ❌ Proprietary | ✅ Open |

---

## Key Features

### 🔐 **Semantic Privacy Guard™**
- **AES-256-GCM encryption on your machine** before transmission
- You own encryption keys — we never have access
- Encrypted blobs stored at rest
- **Result:** Even if our database is breached, your memories remain encrypted

### 🧠 **Intelligent Intent Validation™**
- **Trust Quotient™** scores every memory (confidence, recency, relevance)
- Automatic conflict resolution when information contradicts
- No hallucination. No duplicates. No dead weight.

### 🤝 **Neural Handover™**
- Transfer context between Claude → GPT-4 → LLaMA with cryptographic proof
- HMAC-SHA256 integrity on every transfer
- Prevents tampering, proves origin, validates consistency

### 🔌 **MCP Native**
- Drop-in integration with Claude Desktop
- Full LangChain / LangGraph support
- Works with CrewAI, AutoGen, and any MCP-compatible framework

### 📊 **Audit Everything**
- Immutable log of all memory operations
- HIPAA, GDPR, LGPD compliance ready
- Export audit trail anytime

---

## Installation

```bash
pip install synapse-layer
```

**Requirements:** Python 3.9+  
**Supports:** async/await native

---

## Quick Start

### 1. Store a Memory
```python
from synapse_layer import SynapseMemory

memory = SynapseMemory(agent_id="my-agent")

await memory.store(
    content="User is a software engineer in São Paulo",
    tags=["user-profile"],
    confidence=0.95
)
```

### 2. Recall with Search
```python
results = await memory.recall("user background", top_k=5)

for item in results:
    print(f"{item['content']}")
    print(f"Trust Score: {item['trust_quotient']:.2f}")
    print(f"Recency: {item['recency_score']:.2f}\n")
```

### 3. Create a Handover
```python
handover = await memory.create_handover(
    target_model="gpt-4",
    session_summary="Analyzed user preferences"
)

# Share with another model
print(f"Handover signed (proof: {handover.signature})")
```

---

## MCP Integration (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse-layer": {
      "command": "npx",
      "args": ["@synapse-layer/mcp-server"],
      "env": {
        "SYNAPSE_API_KEY": "sk-your-api-key",
        "SYNAPSE_AGENT_ID": "claude-assistant-v1"
      }
    }
  }
}
```

Claude now has **persistent memory across conversations**.

---

## Use Cases

**🤖 Multi-Agent Orchestration**  
Agents hand off context to each other without losing fidelity or repeating information.

**🏥 Healthcare AI**  
Patient profiles, medication history, treatment preferences — encrypted and fully auditable. HIPAA-ready.

**⚖️ Enterprise Compliance**  
Automatic audit trails. Conflict resolution. Full regulatory compliance (GDPR/LGPD).

**🧠 LLM Continuity**  
Your Claude/GPT-4/LLaMA agent **learns** across sessions. Becomes smarter, not dumber.

---

## Architecture

```
┌──────────────────────────────────┐
│  Your AI Agent                   │
│  (Claude, GPT-4, LLaMA, etc.)   │
└─────────────┬────────────────────┘
              │
              │ store() / recall()
              ▼
┌──────────────────────────────────┐
│  Synapse Layer SDK               │
│  ✓ AES-256-GCM encryption        │
│  ✓ Trust Quotient™ scoring       │
│  ✓ Conflict resolution           │
│  ✓ Neural Handover™ signing      │
└─────────────┬────────────────────┘
              │
              │ HTTPS + mTLS
              ▼
┌──────────────────────────────────┐
│  Memory Vault (Encrypted)        │
│  ✓ PostgreSQL + semantic search  │
│  ✓ AES-256-GCM at rest           │
│  ✓ Immutable audit trail         │
│  ✓ You own the keys              │
└──────────────────────────────────┘
```

---

## Security & Privacy

### Encryption Model
- **On Your Machine:** Plaintext → AES-256-GCM → Encrypted blob
- **In Transit:** HTTPS + TLS 1.3 + mTLS
- **At Rest:** PostgreSQL encrypted with your key
- **Never:** We never see plaintext. Ever.

### Compliance
- ✅ **GDPR** — Data minimization, encryption, right to deletion
- ✅ **LGPD** — Explicit consent, secure data handling
- ✅ **HIPAA** — Encryption + audit trail (with proper key management)

See [SECURITY.md](SECURITY.md) for complete security architecture.

---

## Development

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## FAQ

**Q: How is this different from Mem0 / Zep?**  
A: We encrypt on your machine (you own keys). They encrypt server-side (they own keys). That's the fundamental difference.

**Q: Is my data really encrypted?**  
A: Yes. AES-256-GCM on your machine before transmission. You own the encryption key. We cannot decrypt your data even if we wanted to.

**Q: Is this production-ready?**  
A: Yes. v1.0.3 is stable and production-tested. Used in production systems today.

**Q: Can I self-host?**  
A: The Python SDK is open-source (Apache 2.0). For managed infrastructure, see [synapselayer.org](https://www.synapselayer.org).

**Q: What about the closed-source components (Forge, Handover)?**  
A: The open-source SDK is fully functional. Advanced components (Synapse Forge console, TQ engine internals) are proprietary by design — they fund continued development. Your data remains encrypted with keys you control, regardless.

---

## Benchmarks

**Semantic Search Speed:** 45ms avg (50 memories)  
**Handover Verification:** 12ms avg  
**Encryption Overhead:** < 2% vs unencrypted baseline  
**Conflict Resolution:** < 100ms for 1k contradictory memories  

[See full benchmarks](https://www.synapselayer.org/benchmarks)

---

## Roadmap

- **Phase 1 (April):** Public launch + integrations (LangChain, CrewAI, AutoGen)
- **Phase 2 (May):** Dashboard Web MVP + Synapse Hub (plugin marketplace)
- **Phase 3 (June+):** Decentralized nodes + World Knowledge Cloud

[See full roadmap](https://www.synapselayer.org/roadmap)

---

## Support

- **Docs:** [synapselayer.org/docs](https://www.synapselayer.org/docs)
- **Issues:** [github.com/SynapseLayer/synapse-layer/issues](https://github.com/SynapseLayer/synapse-layer/issues)
- **Discussions:** [github.com/SynapseLayer/synapse-layer/discussions](https://github.com/SynapseLayer/synapse-layer/discussions)
- **Email:** support@synapselayer.org

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

Free for commercial and private use. No vendor lock-in.

---

<div align="center">

### Giving Agents a Past. Giving Models a Soul. ⚗️

**[Website](https://www.synapselayer.org) • [GitHub](https://github.com/SynapseLayer/synapse-layer) • [PyPI](https://pypi.org/project/synapse-layer) • [Docs](https://www.synapselayer.org/docs)**

Built with ❤️ by [Ismael Marchi](https://github.com/ismael-marchi)

[![Synapse Layer — Zero-Knowledge Memory for AI Agents](https://img.shields.io/badge/Synapse%20Layer-Infrastructure%20for%20AI%20Memory-6366f1?style=for-the-badge)](https://www.synapselayer.org)

</div>
