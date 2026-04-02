<div align="center">
  <h1>Synapse Layer</h1>
  <p><strong>Zero-Knowledge Memory Layer for AI Agents</strong></p>
  <p><em>Giving Agents a Past. Giving Models a Soul.</em></p>

  [![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
  [![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)

  [Website](https://www.synapselayer.org) • [Docs](https://www.synapselayer.org/docs) • [GitHub](https://github.com/SynapseLayer/synapse-layer)
</div>

---

## The Problem
AI agents are stateless by design. They forget everything between sessions or when switching models. This leads to repeated questions, token waste, and poor user experience.

## The Solution
**Synapse Layer** is a persistent, encrypted, cross-model memory infrastructure with cryptographic guarantees.

### Core Capabilities
- **🔐 Zero-Knowledge** — AES-256-GCM client-side encryption (you own the keys)
- **🤝 Neural Handover™** — Secure context transfer between Claude, GPT, Llama, Gemini, etc.
- **⚖️ Trust Quotient™** — Automatic weighted conflict resolution
- **🔌 MCP Native** — Works natively with Claude Desktop, LangChain, CrewAI
- **📦 Open SDK** — Apache 2.0. No vendor lock-in.

**Now available as MCP Skill** on [inference-sh](https://github.com/inference-sh/skills/pull/8)

---

## Quick Start

```bash
pip install synapse-layer
Pythonimport asyncio
from synapse_layer import SynapseMemory

async def main():
    memory = SynapseMemory(agent_id="my-agent")

    await memory.store(
        content="User prefers concise technical answers in Brazilian Portuguese",
        confidence=0.97
    )

    results = await memory.recall("user language preference")
    
    for item in results:
        print(f"→ {item['content']} (TQ: {item['trust_quotient']:.3f})")

asyncio.run(main())

How It Works
Your Agent → Synapse SDK (encrypts locally) → Encrypted Memory Vault → Never sees plaintext.
Security First
See SECURITY.md for full architecture, key management and compliance (GDPR / LGPD ready).
License
Apache License 2.0 — see LICENSE.
Giving Agents a Past. Giving Models a Soul. ⚗️
