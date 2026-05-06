# DISCLOSURE MATRIX — SYNAPSE LAYER

> Regra de ouro: Público explica o benefício. Privado preserva o mecanismo.
> Atualizado: 2026-05-05 | Responsável: Ismael Marchi

---

## ✅ PODE EXPOR (público)

### Especificações e Documentação
- API specs (endpoints, request/response formats)
- MCP tool names, descriptions, e input schemas
- Fluxo de onboarding (signup → token → store → recall)
- Exemplos de uso (quickstart, cross-agent, Python basic)
- README.md, SKILL.md, agent-card.json, synapse.json
- server-card.json (`.well-known/mcp/server-card.json`)
- smithery.yaml (registry metadata)
- CHANGELOG.md (versões publicadas)

### Arquitetura (nível benefício)
- "AES-256-GCM encryption at rest"
- "Tenant-isolated: 1 user = 1 private mind"
- "pgvector semantic search with HNSW indexing"
- "5 recall modes: auto, temporal, semantic, priority, hybrid"
- "Content sanitization" (formerly PII redaction)
- "Fail-closed auth: invalid token → 401"
- "Neural Context Injection (NCI)" — que existe e injeta contexto

### Demos e Provas
- Health endpoint output (sanitizado)
- MCP tools/list output
- Install time benchmarks
- Store + recall demos

---

## 🔒 NUNCA EXPOR (privado)

### Algoritmos e Heurísticas
- Trust Quotient (TQ) formula e weights (0.45·D + 0.40·A − 0.15·N)
- RecallRouter scoring thresholds e heurísticas de mode detection
- NCI injection logic (quais memórias, quantas, ranking)
- Quality Gate density/alignment/noise formulas
- Semantic similarity threshold value (0.35)
- withMemory cache strategy (session TTL 120s, query TTL 60s)
- MetricsSnapshot materialized view refresh strategy
- bufferIncrement() / batch flush timing

### Infraestrutura Operacional
- DB real latency numbers (p50, p95, p99)
- Cache TTLs e aging strategies
- Rate limit thresholds internos
- Feature flag values e gating criteria
- Circuit breaker thresholds (CBP pipeline)
- Job processor retry/backoff parameters
- keepalive probe timing (30s) e cache TTL (45s)

### Segurança Operacional
- SYNAPSE_ENCRYPTION_KEY e SYNAPSE_HMAC_KEY
- ADMIN_TOKEN e CONNECT_ADMIN_SECRET
- INTERNAL_HEALTH_TOKEN
- Token hash algorithm implementation details
- Encryption key rotation schedule
- GC (garbage collection) policies e thresholds

### Dados de Negócio
- Número exato de usuários, tenants, memórias, tokens
- Revenue metrics e billing internals
- Stripe price IDs e webhook secrets
- userId, tenantId, ou qualquer PII

### Propriedade Intelectual
- Cognitive Blueprint Pipeline (CBP) architecture
- OmniInjectionEngine e CognitiveArbiter designs
- CognitiveDistiller e CognitiveDiffEngine implementations
- Durable job processor architecture
- Qualquer detalhe que facilite clonagem arquitetural

---

## Critério de Decisão

```
SE a informação:
  - explica um BENEFÍCIO para o usuário → PODE EXPOR
  - revela um MECANISMO interno → NUNCA EXPOR
  - contém um NÚMERO operacional → NUNCA EXPOR
  - facilita CLONAGEM do sistema → NUNCA EXPOR
  - contém CREDENCIAIS ou PII → NUNCA EXPOR (crime)
```
