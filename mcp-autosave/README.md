<div align="center">
  <h1>Synapse Layer — Auto-Save MCP Bridge</h1>
  <h3>Production-Grade Persistent Memory for AI Agents</h3>
  <p><strong>Zero-latency save • Async embeddings • PII redaction • Deduplication</strong></p>

  [![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
  [![PyPI](https://img.shields.io/pypi/v/synapse-layer)](https://pypi.org/project/synapse-layer/)
  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](../LICENSE)
  [![Security](https://img.shields.io/badge/Security-Strict_Redaction-blueviolet)](#security)
</div>

---

## What This Is

A **production MCP server** that gives any MCP-compatible client (Claude Desktop, LangChain agents, CrewAI, custom agents) persistent memory backed by **Supabase + pgvector**.

Every memory goes through:
1. **Strict PII/secrets redaction** before storage
2. **Instant insert** (embedding=NULL) for ~0 perceived latency
3. **Async embedding generation** via configurable provider
4. **SHA-256 deduplication** to prevent duplicate memories

## Architecture

```
Agent → save_to_synapse() → [Redactor] → INSERT (embedding=NULL) → Supabase
                                                    ↓
                                          embedding_jobs queue
                                                    ↓
Agent → backfill_embeddings() → [OpenAI/Local] → UPDATE embedding → Supabase
```

## Quick Start

### 1. Run the SQL Schema

Execute `schema.sql` in your Supabase SQL Editor:

```bash
# Or via psql:
psql $DATABASE_URL < schema.sql
```

This creates:
- `memories` table with `vector(1536)` column
- `embedding_jobs` async queue table
- HNSW index for similarity search
- RLS policies for project isolation

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Supabase credentials and OpenAI key
```

### 3. Install & Run

```bash
pip install -r requirements.txt
python server.py
```

### 4. Configure Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse-autosave": {
      "command": "python",
      "args": ["/path/to/mcp-autosave/server.py"],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "eyJ...",
        "OPENAI_API_KEY": "sk-...",
        "ALLOWED_PROJECTS": "OFFLY,SYNAPSE_LAYER,GOARQIA,NEXUMI,SAFEZAP_BRASIL",
        "EMBEDDING_PROVIDER": "openai",
        "REDACTION_LEVEL": "strict"
      }
    }
  }
}
```

### 5. Docker

```bash
docker build -t synapse-autosave .
docker run --env-file .env synapse-autosave
```

---

## Tools

### `save_to_synapse`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | string | ✅ | Raw text (PII will be redacted automatically) |
| `project` | string | ✅ | Project identifier |
| `metadata` | string (JSON) | ❌ | Extra fields (see recommended structure below) |

**Example payload:**

```json
{
  "content": "Ismael decided to pivot OFFLY strategy to B2B SaaS with focus on enterprise API",
  "project": "OFFLY",
  "metadata": "{\"type\": \"[AUTO-STRAT]\", \"importance\": 5, \"tags\": [\"pivot\", \"b2b\", \"strategy\"], \"source\": \"chatllm_teams\"}"
}
```

**Response:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "saved",
  "deduplicated": false,
  "redaction": {
    "pii_redacted": false,
    "secrets_filtered": false,
    "redaction_level": "strict"
  }
}
```

**With PII detected:**

```json
{
  "content": "Contact john@acme.com at +55 11 99999-8888 for the API key sk-abc123def456",
  "project": "SYNAPSE_LAYER",
  "metadata": "{\"type\": \"[AUTO-OP]\", \"importance\": 3}"
}
```

```json
{
  "id": "...",
  "status": "saved",
  "redaction": {
    "pii_redacted": true,
    "secrets_filtered": true,
    "redaction_level": "strict"
  }
}
```

Stored content: `"Contact [REDACTED:EMAIL] at [REDACTED:PHONE_BR] for the API key [REDACTED:OPENAI_KEY]"`

### `backfill_embeddings`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | ❌ | Max jobs to process (default 10, max 50) |

**Response:**

```json
{
  "processed": 8,
  "failed": 0,
  "remaining": 42
}
```

### `health_check`

No parameters.

```json
{
  "ok": true,
  "version": "1.0.7",
  "mode": "oss",
  "embedding_provider": "openai",
  "db": "connected",
  "queue": { "pending_embeddings": 42 },
  "projects_allowlist": ["GOARQIA", "NEXUMI", "OFFLY", "SAFEZAP_BRASIL", "SYNAPSE_LAYER"],
  "redaction_level": "strict",
  "rate_limit_per_minute": 60
}
```

---

## Recommended Metadata Structure

```json
{
  "type": "[AUTO-STRAT]",
  "importance": 5,
  "tags": ["strategy", "pivot", "b2b"],
  "source": "chatllm_teams",
  "redaction": {
    "pii_redacted": false,
    "secrets_filtered": false,
    "redaction_level": "strict"
  },
  "source_hash": "a1b2c3...",
  "synapse_version": "1.0.7",
  "synapse_mode": "oss"
}
```

**Valid `type` values (policy helper):**

| Type | Description |
|------|-------------|
| `[AUTO-STRAT]` | Strategic decision/pivot/direction |
| `[AUTO-OP]` | Operational task/action |
| `[AUTO-INSIGHT]` | Learning/insight/observation |
| `[AUTO-DECISION]` | Key decision with rationale |
| `[AUTO-CONTEXT]` | Background context/reference |
| `[MANUAL]` | Manually tagged memory |

**Valid projects:**

| Project | Description |
|---------|-------------|
| `OFFLY` | Offly platform |
| `SYNAPSE_LAYER` | Synapse Layer SDK & infra |
| `GOARQIA` | GoArqia architecture |
| `NEXUMI` | Nexumi project |
| `SAFEZAP_BRASIL` | SafeZap Brasil |

---

## Security

### PII/Secrets Redaction

**Every memory passes through the Semantic Privacy Guard™ before storage.**

Detected and redacted categories:

| Category | Examples |
|----------|----------|
| Email | `user@domain.com` → `[REDACTED:EMAIL]` |
| Phone (BR) | `+55 11 99999-8888` → `[REDACTED:PHONE_BR]` |
| Phone (Intl) | `+1 555-1234` → `[REDACTED:PHONE_INTL]` |
| CPF | `123.456.789-00` → `[REDACTED:CPF]` |
| CNPJ | `12.345.678/0001-00` → `[REDACTED:CNPJ]` |
| SSN | `123-45-6789` → `[REDACTED:SSN]` |
| Credit Card | `4111 1111 1111 1111` → `[REDACTED:CREDIT_CARD]` |
| IP Address | `192.168.1.1` → `[REDACTED:IP_ADDRESS]` |
| API Keys | `sk-abc123...` → `[REDACTED:OPENAI_KEY]` |
| Bearer Tokens | `Bearer eyJ...` → `[REDACTED:BEARER_TOKEN]` |
| AWS Keys | `AKIA...` → `[REDACTED:AWS_KEY]` |
| GitHub Tokens | `ghp_...` → `[REDACTED:GITHUB_TOKEN]` |
| Passwords | `password: ...` → `[REDACTED:PASSWORD_FIELD]` |
| Private URLs | `http://localhost:...` → `[REDACTED:PRIVATE_ENDPOINT]` |
| Connection Strings | `postgres://...` → `[REDACTED:CONNECTION_STRING]` |

### Logging Policy

- ✅ IDs, counters, project names, hashes are logged
- ❌ Raw content is **NEVER** logged
- ❌ Secrets/PII are **NEVER** logged

### Supabase Security

- `SUPABASE_SERVICE_ROLE_KEY` is **server-side only** (never exposed to clients)
- RLS is enabled on all tables
- Project-scoped policies restrict read/write access

### RLS Policies (included in schema.sql)

```sql
-- Users can only access their own project's memories
CREATE POLICY memories_select_own_project ON memories
    FOR SELECT USING (
        project = current_setting('request.jwt.claims', true)::jsonb ->> 'project'
    );

-- Service role has full access (for the MCP server)
CREATE POLICY memories_service_role ON memories
    FOR ALL USING (auth.role() = 'service_role');
```

---

## OSS vs Pro

| Feature | OSS | Pro |
|---------|-----|-----|
| PII Redaction | 15 patterns | 40+ patterns |
| Embedding Providers | OpenAI, Local | + Cohere, Voyage, custom |
| Deduplication | SHA-256 exact | + fuzzy/semantic dedup |
| Rate Limiting | In-memory | Redis-backed distributed |
| Queue | Polling (backfill) | Real-time webhook |
| Metadata Validation | Type enum | Custom schemas per project |
| Encryption at Rest | ❌ | AES-256-GCM |

Set `SYNAPSE_MODE=pro` to unlock extended features (requires `synapse-layer-pro` license).

---

## Deploy

### Railway

```bash
railway login
railway init
railway up
# Set env vars in Railway dashboard
```

### Docker Compose

```yaml
version: '3.8'
services:
  synapse-autosave:
    build: .
    env_file: .env
    restart: unless-stopped
```

### Cron for Backfill

Set up a cron job or scheduled task to periodically process embeddings:

```bash
# Every 5 minutes, process up to 50 pending embeddings
*/5 * * * * cd /path/to/mcp-autosave && python -c "
from server import backfill_embeddings
result = backfill_embeddings(limit=50)
print(result)
"
```

Or use a Supabase Edge Function / pg_cron for fully managed backfill.

---

## File Structure

```
mcp-autosave/
├── server.py          # MCP server (3 tools)
├── redactor.py        # PII/secrets redaction engine
├── schema.sql         # Full database schema + indexes + RLS
├── requirements.txt   # Python dependencies
├── .env.example       # Environment template
├── Dockerfile         # Container image
├── .gitignore
└── README.md          # This file
```

---

<div align="center">
  <strong>Giving Agents a Past. Giving Models a Soul. ⚗️</strong>
  <br><br>
  <a href="https://synapselayer.org">Website</a> · <a href="https://forge.synapselayer.org">Forge</a> · <a href="https://github.com/SynapseLayer/synapse-layer">GitHub</a> · <a href="https://pypi.org/project/synapse-layer/">PyPI</a>
</div>
