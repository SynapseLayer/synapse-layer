<!-- mcp-name: io.github.SynapseLayer/synapse-layer -->
<div align="center">

# 🧠 Synapse Layer

### RAG retrieves. Synapse remembers.

**Persistent memory infrastructure for AI agents — AES-256-GCM encrypted at rest, semantic search, MCP-native.**

Synapse Layer is open-source persistent memory infrastructure for AI agents and assistants. Memories are encrypted at rest with AES-256-GCM, indexed via pgvector HNSW for semantic recall, and exposed through MCP JSON-RPC for native integration with Claude, GPT, Gemini, and any MCP-compatible client. Apache 2.0 licensed.

**Status and limits:** see [FEATURES.md](FEATURES.md) — the public contract for what is shipped, gated, experimental or roadmap.

[![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![Python](https://img.shields.io/pypi/pyversions/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![Downloads](https://img.shields.io/pypi/dm/synapse-layer)](https://pypi.org/project/synapse-layer/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-6B4FBB)](https://modelcontextprotocol.io)
[![Official MCP Registry](https://img.shields.io/badge/MCP_Registry-Published-00C853)](https://registry.modelcontextprotocol.io)
[![CI](https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml/badge.svg)](https://github.com/SynapseLayer/synapse-layer/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

[Website](https://synapselayer.org) · [Docs](https://forge.synapselayer.org/docs) · [PyPI](https://pypi.org/project/synapse-layer/) · [Forge](https://forge.synapselayer.org)

</div>

---

## ⚡ 30-Second Quickstart

Get your Connect Token at [forge.synapselayer.org](https://forge.synapselayer.org) → Connect, then add the MCP endpoint to your client:

```bash
claude mcp add --transport http synapse-layer \
  https://forge.synapselayer.org/api/mcp \
  --header "x-connect-token: sk_connect_YOUR_TOKEN"
```

For Claude Desktop, Cursor and other clients, use the `npx mcp-remote` block under [MCP Integration](#mcp-integration-one-tested-path-per-client). Smithery's proxy/CLI was retired on 31 Oct 2026; the direct endpoint above is canonical.

Or use the Python SDK:

```python
from synapse_layer import Synapse

s = Synapse(token="sk_connect_YOUR_TOKEN")

s.store("user likes coffee")
print(s.recall("what does user like?"))
```

Get your token at [forge.synapselayer.org](https://forge.synapselayer.org) → Dashboard → Connect

---

## What is Synapse Layer?

The **persistent memory layer for AI agents** — the missing piece between stateless LLMs and real continuity of context.

Your AI agents forget everything between sessions. Synapse Layer fixes that.

| Feature | Description |
|---------|-------------|
| 🔐 **Encrypted at rest** | AES-256-GCM with per-operation random IV and HMAC-SHA-256 integrity |
| 🧩 **One-click connect** | Claude Desktop, Cursor, LangChain, CrewAI, n8n |
| 🌐 **Cross-agent memory** | Save in ChatGPT, recall in Claude |
| ⚡ **MCP-native** | Any MCP-compatible agent |
| 🔒 **Header-first auth** | Tokens never in URLs or logs |
| 🎯 **Trust Quotient** | Trust-weighted recall — confidence, recency and usage combined with semantic relevance |

---

## Why Synapse Layer?

> Your AI agents forget everything between sessions. Synapse Layer fixes that — in one line.

| Without Synapse Layer | With Synapse Layer |
|---|---|
| Agent forgets context every session | Persistent memory across all sessions |
| Memory locked to one model | Cross-agent: save in ChatGPT, recall in Claude |
| No audit trail | Append-only audit events for scope changes and curation decisions |
| Complex integration | `pip install synapse-layer` + 3 lines of code |
| Plaintext stored on servers | AES-256-GCM encrypted at rest |

---

## Use Cases

- **Long-term assistant memory** — persist user preferences, facts, and prior decisions across sessions.
- **Cross-agent continuity** — save context in one agent and recall it in another.
- **Secure memory for MCP clients** — connect Claude Desktop, Cursor, and other MCP-compatible tools to a governed memory layer.
- **Operational memory for teams** — maintain structured context, trust scoring, and searchable recall for production agents.

---

## Install

```bash
pip install synapse-layer
```

## Quick Start

### Python Script

```python
from synapse_layer import Synapse

client = Synapse(token="sk_connect_YOUR_TOKEN")

# Store
client.store("User prefers dark mode and concise answers")

# Recall
results = client.recall("user preferences")
for r in results:
    print(r["content"], r["trust_quotient"])
```

### With Context Manager

```python
from synapse_layer import Synapse

with Synapse(token="sk_connect_YOUR_TOKEN") as client:
    client.store("User prefers dark mode and concise answers")
    results = client.recall("user preferences")
    for r in results:
        print(r["content"])
```

Get your token at [forge.synapselayer.org](https://forge.synapselayer.org) → Dashboard → Connect

---

## 13 MCP Tool Names at a Glance

Synapse Layer registers 13 public tool names (10 operations plus 3 aliases) for persistent memory workflows:

- `recall`
- `save_to_synapse`
- `process_text`
- `search`
- `health_check`
- `initialize_context`
- `save_memory`
- `store_memory`
- `recall_memory`
- `list_memories`
- `memory_feedback`
- `neural_handover`
- `slo_report`

`save_memory`, `store_memory` and `save_to_synapse` are aliases; `recall` and `recall_memory` are aliases. These tools cover memory capture, semantic recall, structured storage, feedback loops, agent handoff, and operational observability.

---

## Deployment Modes

The public package runs the client and local engine. The hosted Forge adds corporate organizations, projects, memberships, curation policies and audit. See [FEATURES.md](FEATURES.md) for what is OSS, hosted, gated or roadmap.

### Python Script Mode
Use the SDK when you want direct Python access to Forge memory from your application.

Best for:
- prototypes and scripts
- Python-native workflows
- fast integration into existing apps

### Cloud / Forge API
Use Forge when you need persistent, cross-session, and cross-agent memory with managed access tokens.

Best for:
- production assistants
- multi-agent systems
- MCP-based integrations
- shared memory across tools and sessions

---

## MCP Integration (one tested path per client)

### Claude Code (CLI)

```bash
claude mcp add --transport http synapse-layer \
  https://forge.synapselayer.org/api/mcp \
  --header "x-connect-token: sk_connect_YOUR_TOKEN"
```

The URL is a **positional argument** — `claude mcp add --transport http <name> <url>` — there is no `--url` flag.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse-layer": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://forge.synapselayer.org/api/mcp",
        "--header",
        "x-connect-token: sk_connect_YOUR_TOKEN"
      ]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root (same JSON block as above).

### Any MCP client

Any host that runs `npx` can use the `mcp-remote` block above unchanged — it bridges local stdio to the remote endpoint.

Config file locations:
- Claude Desktop — macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Claude Desktop — Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Claude Desktop — Linux: `~/.config/Claude/claude_desktop_config.json`

---

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

---

## Security

| Feature | Implementation |
|---------|---------------|
| Encryption | AES-256-GCM at rest with per-operation random IV |
| Integrity | HMAC-SHA-256 on content |
| Auth | Header-first (`x-connect-token`) — tokens never in URLs or logs |
| Privacy | Content sanitization + tenant-scoped encrypted storage |
| Isolation | Personal: 1 user = 1 private mind. Corporate: organization → projects → memberships, with tenant-scoped queries |

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## Related Projects

| Project | Description |
|---------|-------------|
| [synapse-sdk-python](https://github.com/SynapseLayer/synapse-sdk-python) | Python SDK — LangChain, CrewAI, and A2A protocol adapters |
| [synapse-layer-skill](https://github.com/SynapseLayer/synapse-layer-skill) | MCP skill configuration for Claude Desktop, Cursor, Windsurf |
| [synapse-layer-langgraph](https://github.com/SynapseLayer/synapse-layer-langgraph) | LangGraph checkpoint saver with encrypted state persistence |

---

## Governance

- Public features and limits follow [FEATURES.md](FEATURES.md).
- Internal governance follows the [Public Claims Matrix](docs/PUBLIC_CLAIMS_MATRIX.md).
- Architecture details that reveal benefits are public; mechanisms that enable them are private.
- Claim = Reality. If it's not implemented, it's not in the README.

---

## License

Apache-2.0 © Synapse Layer