# Smithery Registry Submission — Synapse Layer

## Submission Manifesto

Use this content for the Smithery listing page, GitHub PR body, or registry form.

---

### Server Name
`@synapselayer/synapse-protocol`

### Display Name
Synapse Layer — Persistent Memory for AI Agents

### One-Liner
Persistent encrypted memory infrastructure for AI agents. Store, recall, and transfer AES-256-GCM encrypted context across models.

### Description

Synapse Layer is the missing memory primitive for AI agents. Every memory passes through a non-bypassable 4-layer Cognitive Security Pipeline:

```
Agent → Sanitize (PII) → Validate Intent → Encrypt (AES-256-GCM) → DP Noise → Vault
```

**Key capabilities:**
- **Persistent cross-session memory** — agents remember across restarts
- **Deterministic recall** — ranked by Trust Quotient scoring
- **AES-256-GCM Encryption** — encrypted at rest with per-operation random IV
- **AES-256-GCM encryption** with PBKDF2 key derivation (600k iterations)
- **Content sanitization** — input validation and sanitization before encryption
- **Differential privacy** — calibrated Gaussian noise on embeddings
- **1-line integration** — `@remember` decorator wraps any function

**4 MCP Tools:**

| Tool | Description |
|---|---|
| `recall` | Deterministic memory retrieval with TQ ranking |
| `save_to_synapse` | Structured persistence through security pipeline |
| `process_text` | Autonomous extraction of decisions/milestones/alerts |
| `health_check` | System health and capability verification |

### Version
`1.1.0`

### MCP Endpoint
```
https://forge.synapselayer.org/api/mcp
```

### Transport
`http-stream`

### Quick MCP Config (Cursor / Claude Desktop / Windsurf)
```json
{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
```

### Repository
https://github.com/SynapseLayer/synapse-layer

### Homepage
https://synapselayer.org

### Documentation
https://synapselayer.org/docs

### PyPI
https://pypi.org/project/synapse-layer/

### License
Apache-2.0

### Author
Ismael Marchi — [@synapselayer](https://x.com/synapselayer)

### Tags
`agent-memory` `persistent-context` `long-term-memory` `mcp-memory` `deterministic-recall` `encrypted-at-rest` `trust-quotient` `aes-256-gcm` `encrypted-at-rest` `continuous-consciousness` `sqlite-backend` `langchain` `crewai` `autogen` `llamaindex` `semantic-kernel`

### Numbers
- 481 tests | 90% coverage
- 5 framework integrations
- 4 MCP tools (real DB calls)
- 2 storage backends + custom protocol
- AES-256-GCM + PBKDF2 (600k iterations)

---

## CLI Publish Command

```bash
npx @anthropic-ai/smithery-cli mcp publish https://forge.synapselayer.org/api/mcp -n @synapselayer/synapse-protocol
```

## Alternative: Submit via GitHub

Open a PR to [smithery-ai/registry](https://github.com/smithery-ai/registry) with the `smithery.yaml` file from this repo.

---

**Status:** Ready for submission ✅
