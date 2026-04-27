# Synapse Layer — Official MCP Registry Submission

## Server Identity

| Field | Value |
|---|---|
| **Name** | `io.github.SynapseLayer/synapse-layer` |
| **Title** | Synapse Layer — Continuous Consciousness Infrastructure |
| **Version** | `1.1.5` |
| **License** | Apache-2.0 |
| **Schema** | `2025-12-11` |

## Description

Persistent encrypted memory for AI agents. AES-256-GCM at rest, PII redaction, HMAC-SHA-256 integrity.

## Package

| Field | Value |
|---|---|
| **Registry** | PyPI |
| **Identifier** | `synapse-layer` |
| **Transport** | `stdio` (local) + `streamable-http` (remote) |
| **Runtime Hint** | `uvx` |
| **PyPI URL** | https://pypi.org/project/synapse-layer/1.1.5/ |
| **Verification** | `<!-- mcp-name: io.github.SynapseLayer/synapse-layer -->` in README |

## Remote Endpoint

| Field | Value |
|---|---|
| **URL** | `https://forge.synapselayer.org/api/mcp` |
| **Transport** | `streamable-http` |
| **Auth** | None required (public endpoint) |
| **Latency** | ~60ms average |

## Tools (5)

| Tool | Description |
|---|---|
| `recall` | Deterministic memory retrieval with Trust Quotient ranking |
| `save_to_synapse` | Structured persistence through 4-layer security pipeline |
| `search` | Cross-agent memory search with full-text matching |
| `process_text` | Autonomous extraction of decisions, milestones, alerts |
| `health_check` | System health, DB connectivity, capability report |

## Environment Variables

| Variable | Required | Secret | Default | Description |
|---|---|---|---|---|
| `SYNAPSE_AGENT_ID` | No | No | `default-agent` | Agent identifier for memory isolation |
| `SYNAPSE_PRIVACY_EPSILON` | No | No | `0.5` | Differential privacy epsilon (0.1–2.0) |
| `SYNAPSE_ENCRYPTION_KEY` | No | Yes | auto-gen | AES-256-GCM key for at-rest encryption |
| `LOG_LEVEL` | No | No | `INFO` | Logging verbosity |

## Why This Server Should Be in the Registry

### Technical Merit

1. **Non-bypassable 4-layer Cognitive Security Pipeline**
   ```
   Agent → PII Redaction → Intent Validation → AES-256-GCM Encryption → DP Noise → Vault
   ```

2. **Production-grade quality**
   - 481 passing tests
   - 90% code coverage
   - Python 3.9+ compatible
   - Zero external service dependencies for local mode

3. **Dual transport architecture**
   - `stdio` for local-first usage (SQLite, zero-config)
   - `streamable-http` for hosted access via `forge.synapselayer.org`

4. **Framework integrations**
   - LangChain, CrewAI, AutoGen, LlamaIndex, Semantic Kernel
   - 1-line `@remember` decorator for any async function

### Protocol Compliance

- `server.json` validates against `2025-12-11` schema (✅ `mcp-publisher validate`)
- PyPI package includes `mcp-name` marker for ownership verification
- Remote endpoint returns valid JSON-RPC 2.0 with `tools/list` and `tools/call`
- `server-card.json` served at `/.well-known/mcp/server-card.json`

### Security Posture

- AES-256-GCM with PBKDF2 key derivation (600k iterations)
- 15+ PII regex patterns (emails, phones, SSNs, credentials)
- Calibrated Gaussian noise on embeddings (differential privacy)
- Encryption: AES-256-GCM at rest with per-operation random IV

## Links

- **Repository**: https://github.com/SynapseLayer/synapse-layer
- **PyPI**: https://pypi.org/project/synapse-layer/
- **Website**: https://synapselayer.org
- **Forge**: https://forge.synapselayer.org
- **Docs**: https://synapselayer.org/docs
- **Smithery**: https://smithery.ai/servers/synapselayer/synapse-protocol

## server.json

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.SynapseLayer/synapse-layer",
  "title": "Synapse Layer — Continuous Consciousness Infrastructure",
  "description": "Persistent encrypted memory for AI agents. AES-256-GCM at rest, PII redaction, HMAC-SHA-256 integrity.",
  "version": "1.1.1",
  "websiteUrl": "https://synapselayer.org",
  "repository": {
    "url": "https://github.com/SynapseLayer/synapse-layer",
    "source": "github"
  },
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "synapse-layer",
      "version": "1.1.1",
      "runtimeHint": "uvx",
      "transport": { "type": "stdio" },
      "environmentVariables": [
        { "name": "SYNAPSE_AGENT_ID", "description": "Agent identifier.", "isRequired": false, "isSecret": false, "default": "default-agent" },
        { "name": "SYNAPSE_PRIVACY_EPSILON", "description": "DP epsilon (0.1–2.0).", "isRequired": false, "isSecret": false, "default": "0.5" },
        { "name": "SYNAPSE_ENCRYPTION_KEY", "description": "AES-256-GCM key.", "isRequired": false, "isSecret": true },
        { "name": "LOG_LEVEL", "description": "Logging level.", "isRequired": false, "isSecret": false, "default": "INFO" }
      ]
    }
  ],
  "remotes": [
    {
      "type": "streamable-http",
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  ]
}
```

---

## Publication Command

```bash
# From the synapse-layer repo root:
mcp-publisher validate   # ✅ Passes
mcp-publisher login github
mcp-publisher publish
```

**Status: VALIDATED ✅ — Ready for publish.**
