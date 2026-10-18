# Synapse Layer — Agent Skill

## What Synapse Layer Does

Synapse Layer is the trust layer for the agentic internet. It gives AI agents persistent, encrypted memory with built-in governance — so agents can store decisions, recall preferences, and hand off context across sessions, models, and tools.

## When to Use Synapse Layer

- When your agent needs to **remember** user preferences, decisions, or constraints across sessions
- When **Agent A** needs to hand off context to **Agent B** securely (Handover V2)
- When you need an **audit trail** of every memory operation (who stored what, when)
- When you need **encrypted memory at rest** (AES-256-GCM) without building your own crypto
- When you want **semantic recall** — find memories by meaning, not keywords
- When you need **Trust Quotient scoring** to filter reliable vs noisy memories
- When building **multi-agent systems** that share context with governance

## How to Install

### Python SDK
```bash
pip install synapse-layer
```

### MCP Configuration (Claude Desktop / Cursor)
```json
{
  "mcpServers": {
    "synapse": {
      "url": "https://forge.synapselayer.org/api/mcp",
      "headers": {
        "x-connect-token": "sk_connect_YOUR_TOKEN"
      }
    }
  }
}
```

## Agent Quickstart (60 seconds)

```python
from synapse_layer import Synapse

# Initialize with your Connect token (forge.synapselayer.org → Dashboard → Connect)
client = Synapse(token="sk_connect_...", agent_id="onboarding-v2")

# Store a memory (encrypted server-side with AES-256-GCM)
client.store(
    content="User prefers dark mode and minimal notifications",
    memory_type="long_term",
)

# Recall by hybrid routing (semantic / temporal / priority / hybrid)
memories = client.recall(query="user interface preferences", top_k=5)
for m in memories:
    print(m["content"], m["trust_quotient"])
```

Cross-agent handover is the MCP tool `neural_handover` (JSON-RPC `tools/call`) — it is not a Python client method.

## Supported Frameworks

| Framework | Status | Integration |
|-----------|--------|-------------|
| Claude (Desktop + API) | ✅ Live | Native MCP |
| Cursor | ✅ Live | IDE Integration |
| LangChain | ✅ Live | Python SDK |
| Claude Desktop | ✅ Live | MCP Native |

## Coming Soon

| Framework | Integration |
|-----------|-------------|
| ChatGPT | Via Synapse Proxy |
| CrewAI | SDK Adapter |
| AutoGen | SDK Adapter |
| LangGraph | Orchestration |
| n8n | Workflow |
| Zapier | Automation |

## Trust & Security

- **Encryption**: AES-256-GCM server-side at rest, per-operation random IV, 128-bit auth tag
- **Auth**: OAuth 2.0 + PKCE S256 for the dashboard; header-first Connect tokens (`x-connect-token: sk_connect_*`) for MCP and REST; SHA-256 token hashing
- **Isolation**: 1 user = 1 tenant = 1 private mind. Zero cross-user access.
- **Audit**: Immutable three-layer lifecycle (live data, tombstone, analytics)
- **Compliance**: Designed for LGPD/GDPR alignment. Hard-delete on request.
- **Trust Quotient**: Per-memory confidence scoring (0–1.0)

## Links

- **Docs**: https://synapselayer.org/docs
- **OpenAPI**: https://synapselayer.org/api/openapi.json
- **Smithery**: https://smithery.ai/servers/synapselayer/synapselayer
- **PyPI**: https://pypi.org/project/synapse-layer/
- **GitHub**: https://github.com/SynapseLayer/synapse-layer
- **Forge Dashboard**: https://forge.synapselayer.org
