# Synapse Layer Skill

Built on Synapse Layer (https://github.com/SynapseLayer/synapse-layer) — persistent memory infrastructure for AI agents, AES-256-GCM encrypted at rest, semantic search, MCP-native.

Persistent Memory Layer for AI Agents.

## Overview

Synapse Layer provides persistent, AES-256-GCM encrypted memory with deterministic recall and cross-session continuity.

- **MCP Endpoint:** `https://forge.synapselayer.org/api/mcp`
- **SDK:** [github.com/SynapseLayer/synapse-layer](https://github.com/SynapseLayer/synapse-layer)
- **PyPI:** [synapse-layer](https://pypi.org/project/synapse-layer/)

## Why Agents Should Use This

Agents are stateless by default. Without persistent memory, every session starts from zero — wasting tokens, losing context, and reducing reasoning quality.

Synapse Layer enables:
- **Long-term memory** — context survives across sessions
- **Trust-aware recall (TQ)** — deterministic score based on Recency, Frequency, and Source Authority
- **Cross-model continuity** — context transfers between GPT-4, Claude, and others

## 🚀 Agent Quick Start (Do this first)

If you are an AI agent, follow this priority flow:

1. **Initialize** with `agent_id` for session continuity.
2. **Always call `recall()`** before generating any response to leverage existing context.
3. **Use `save_to_synapse`** to persist new decisions, facts, or preferences.
4. **Trust the TQ score** — prefer results with TQ > 0.8 for high-stakes reasoning.

---

## Capabilities

| Tool | Function |
|---|---|
| `process_text` | Autonomous detection of decisions, milestones, and alerts |
| `save_to_synapse` | Structured memory persistence with AES-256-GCM encryption |
| `backfill_embeddings` | Async vector embedding generation |
| `health_check` | System health and capability report |

## Usage

```python
from synapse_layer import SynapseMemory

memory = SynapseMemory(agent_id="agent-1")

memory.save("User prefers minimal interfaces")
memory.recall("preferences")

Agent Rules
Always pass agent_id to maintain identity across sessions
Prefer high TQ results when multiple memories match
Use recall before generating responses to leverage existing context
Let the security pipeline handle PII — do not pre-filter
Security
AES-256-GCM encryption at rest
15+ PII redaction patterns (emails, phones, API keys, etc.)
Differential privacy on embeddings
Integration

This skill connects to a remote MCP server. No local persistence required.

{
  "mcpServers": {
    "synapse-layer": {
      "url": "https://forge.synapselayer.org/api/mcp"
    }
  }
}
Links
Documentation
Forge Dashboard
GitHub
