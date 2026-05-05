# DISTRIBUTION DRAFT — C3.2
**Status**: INTERNAL REVIEW ONLY — Founder must review before publishing.
**Date**: 2026-05-05
**Author**: Synapse Layer Team

---

## SECTION 1 — X/TWITTER THREAD (5 tweets)

### Tweet 1 (hook)
RAG retrieves. Synapse remembers.

Most AI agents forget everything between sessions.
Synapse Layer fixes that — persistent, encrypted, cross-agent memory.

Here's how it works 🧵

### Tweet 2 (problem)
Your AI agent nails a task today. Tomorrow? Total amnesia.

Different tool? Starts from zero. New session? Context gone.

Every agent rebuilds understanding from scratch. That's not intelligence — it's Groundhog Day for AI.

### Tweet 3 (solution)
Synapse Layer gives agents persistent memory in 3 steps:

1. store() — Save decisions, preferences, context
2. recall() — Semantic search across all stored memory
3. TQ score — Trust Quotient ranks memory by reliability

AES-256-GCM encrypted at rest. Server never sees plaintext.

### Tweet 4 (code)
Get started in 30 seconds:

```bash
pip install synapse-layer
```

```python
from synapse_layer import SynapseA2AClient

async with SynapseA2AClient(api_key="sk_connect_xxx") as client:
    await client.store_memory(
        user_id="agent-001",
        content="User prefers dark mode",
    )
```

Works with Claude, GPT-4, Gemini, Llama via MCP.

### Tweet 5 (CTA)
Try it: forge.synapselayer.org
Docs: forge.synapselayer.org/docs
GitHub: github.com/SynapseLayer
PyPI: pypi.org/project/synapse-layer

Built for agents that need to remember. 🧠

---

## SECTION 2 — LINKEDIN POST

### Persistent Memory for AI Agents — Why It Matters

Every AI agent has the same problem: amnesia.

Switch tools? Context lost. New session? Start over. Different model?
Rebuild everything from scratch. We've normalized this inefficiency.

At Synapse Layer, we built the infrastructure to fix it.

**What we ship today:**
- Store/recall API for any MCP-compatible agent
- AES-256-GCM encryption at rest — server never sees plaintext
- Trust Quotient (TQ) scoring: every memory ranked 0.0–1.0 for reliability
- Cross-agent memory: store in Claude, recall in GPT-4
- 30-second install via pip or MCP config

**What we've proven:**
Our Quality Gate shadow evaluator produces real alignment scores on every
recall. In production, semantic alignment between queries and recalled
memories consistently scores above 0.7 — meaning agents are getting
relevant context, not noise.

**The technical stack:**
MCP-native (JSON-RPC 2.0), pgvector for semantic search, tenant-isolated,
and designed for LGPD/GDPR alignment.

This isn't a wrapper around RAG. RAG retrieves documents.
Synapse remembers decisions, preferences, and context — persistently.

Try it: forge.synapselayer.org

#AI #MCP #AIAgents #Memory #Infrastructure

---

## SECTION 3 — HACKER NEWS (Show HN)

### Title
Show HN: Synapse Layer – Persistent memory infrastructure for AI agents

### Body

Hi HN,

I built Synapse Layer because every AI agent I worked with had the same
problem: total amnesia between sessions.

**The problem:** AI agents forget everything. Switch from Claude to GPT-4?
Start over. New session? Context gone. Ask the same questions again.
We've normalized this, but it's a real productivity killer.

**The solution:** Synapse Layer is a persistent memory layer that works
with any MCP-compatible client. Three operations:

- `store_memory` — Save a memory with semantic content and intent
- `recall_memory` — Semantic search across all stored memories
- Trust Quotient (TQ) — Each memory is scored 0.0–1.0 for reliability

**What's real today:**

- MCP server at forge.synapselayer.org/mcp (13 tools, JSON-RPC 2.0)
- Python SDK on PyPI: `pip install synapse-layer` (v2.3.2)
- AES-256-GCM encryption at rest with per-operation random IV
- pgvector (HNSW index) for semantic search
- Tenant isolation: 1 user = 1 private memory space
- Quality Gate shadow evaluator producing real TQ scores in production
- Works with Claude Desktop, GPT-4 (via proxy), Cursor, Windsurf

**Tech stack:** Next.js 14, PostgreSQL + pgvector, Prisma, TypeScript,
OpenAI embeddings (text-embedding-3-small, 1536d).

**What's NOT real yet:**
- Cognitive Blueprint Pipeline (in shadow/development)
- Active injection (feature-flagged off)
- Smithery registry listing (pending latency optimization)

I'm a solo founder building this from São Paulo. Happy to answer
questions about the architecture, the TQ scoring model, or the
MCP integration.

Live: https://forge.synapselayer.org
GitHub: https://github.com/SynapseLayer/synapse-layer
SDK: https://pypi.org/project/synapse-layer/
Docs: https://forge.synapselayer.org/docs
