<div align="center">

# 🧠 Synapse Layer
**Persistent memory infrastructure for AI agents**

[![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![Python](https://img.shields.io/pypi/pyversions/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![Downloads](https://img.shields.io/pypi/dm/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![MCP Approved](https://img.shields.io/badge/MCP-Approved-blue)](https://mcp-marketplace.io)
[![Security](https://img.shields.io/badge/Security-10.0%2F10-brightgreen)](https://mcp-marketplace.io)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

[Website](https://synapselayer.org) · [Docs](https://synapselayer.org/docs) · [PyPI](https://pypi.org/project/synapse-layer/) · [Forge](https://forge.synapselayer.org)

</div>

---

## What is Synapse Layer?

The **persistent memory layer for AI agents** — the missing piece between stateless LLMs and real continuity of context.

Your AI agents forget everything between sessions. Synapse Layer fixes that.

| Feature | Description |
|---------|-------------|
| 🔐 **Encrypted at rest** | AES-256-GCM with per-operation random IV and HMAC-SHA-256 integrity |
| 🧩 **One-click connect** | Claude Desktop, Cursor, LangChain, n8n |
| 🌐 **Cross-agent memory** | Save in ChatGPT, recall in Claude |
| ⚡ **MCP-native** | Any MCP-compatible agent |
| 🔒 **Header-first auth** | Tokens never in URLs or logs |

---

## Why Synapse Layer?

> Your AI agents forget everything between sessions. Synapse Layer fixes that — in one line.

| Without Synapse Layer | With Synapse Layer |
|---|---|
| Agent forgets context every session | Persistent memory across all sessions |
| Memory locked to one model | Cross-agent: save in ChatGPT, recall in Claude |
| Plaintext stored on servers | AES-256-GCM encrypted at rest — content cleared after encryption |
| Complex integration | `pip install synapse-layer` + 3 lines of code |
| No audit trail | Full memory lifecycle with Truth Quotient™ scoring |

## Install

```bash
pip install synapse-layer
```

## Quick Start

### Local SDK — in-process memory

```python
import asyncio
from synapse_layer import SynapseClient  # canonical public import

async def main():
    memory = SynapseClient(agent_id="my-agent")

    # Save
    await memory.store("User prefers dark mode and concise answers")

    # Recall
    results = await memory.recall("user preferences")
    for r in results:
        print(f"[TQ={r.trust_quotient:.2f}] {r.content}")

asyncio.run(main())
```

### Cloud — Forge API (persistent, cross-agent)

```python
from synapse_memory.client import Synapse

client = Synapse(token="sk_connect_YOUR_TOKEN")
client.remember("User prefers dark mode and concise answers")
results = client.recall("user preferences")
for r in results:
    print(r["content"])
```

Get your token at [synapselayer.org](https://synapselayer.org) → Dashboard → Connect

## MCP Integration (Claude Desktop / Cursor)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse-layer": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://forge.synapselayer.org/mcp",
        "--header",
        "x-connect-token: sk_connect_YOUR_TOKEN"
      ]
    }
  }
}
```

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## API — Header-First Auth

```bash
# Health check
curl -H "x-connect-token: sk_connect_YOUR_TOKEN" \
  https://forge.synapselayer.org/api/connect/health

# Save memory
curl -X POST \
  -H "x-connect-token: sk_connect_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "User is a Python developer"}' \
  https://forge.synapselayer.org/api/v1/capture
```

## Security

| Feature | Implementation |
|---------|---------------|
| Encryption | AES-256-GCM at rest |
| Auth | Header-first (`x-connect-token`) |
| Token exposure | Never in URLs or logs |
| CI protection | `secret-scan.yml` on every commit |
| Encryption | AES-256-GCM at rest with per-operation random IV |
| Security score | 10.0 / 10 (MCP Marketplace) |

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

Apache-2.0 © Synapse Layer — v1.2.0
