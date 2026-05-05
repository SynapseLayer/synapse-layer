# TRUTH SOURCE — SYNAPSE LAYER (PRIVADO)

> ⚠️ DOCUMENTO INTERNO — NÃO PUBLICAR. Contém métricas reais do sistema.

Última atualização: 2026-05-05 02:30 UTC | Responsável: Ismael Marchi

---

## Estado Real do Sistema

| Métrica | Valor Real | Fonte | Data |
|---------|-----------|-------|------|
| Health endpoint | `status=ok, db=true` | `curl forge.synapselayer.org/api/health` | 2026-05-05 |
| Health version | `4.3.0` | idem | 2026-05-05 |
| MCP tools live | 13 | MCP `tools/list` introspection | 2026-05-05 |
| MCP server version | `2.3.7` | MCP `health_check` tool | 2026-05-05 |
| DB real latency (p50) | ~1157ms | health endpoint `dbRealLatencyMs` | 2026-05-05 |
| DB cache hit | `true` (perceived 0ms) | health endpoint `dbCacheHit` | 2026-05-05 |
| Embeddings ativos | ~265 (de ~267 memórias) | backfill script + DB count (last validated 2026-05-02) | 2026-05-02 |
| Vetores válidos (1536d) | ~265 | pgvector query (last validated 2026-05-02) | 2026-05-02 |
| ForgeMemory total | ~267 | DB count (last validated 2026-05-02) | 2026-05-02 |
| Tenant isolation | `enforced` (v3.5.0) | health endpoint | 2026-05-05 |
| NCI version | `v4.2` | health endpoint | 2026-05-05 |
| Semantic scoring | `active` | health endpoint | 2026-05-05 |
| GC pending expired | `0` | health endpoint | 2026-05-05 |
| 401 on no auth | ✅ confirmed | curl test | 2026-05-05 |
| 401 on invalid token | ✅ confirmed | curl test | 2026-05-05 |
| Smithery listing | `308 redirect → page exists` | HTTP check | 2026-05-05 |
| PyPI install time | 3s | `pip install synapse-layer` in clean venv | 2026-05-05 |
| SDK import | ✅ `from synapse_layer import SynapseA2AClient` | Python test | 2026-05-05 |

---

## PROVEN (com evidência real verificável)

1. **AES-256-GCM encryption at rest** — código auditado em `lib/synapse/crypto.ts`, per-op random IV, 128-bit GCM tag
2. **Tenant isolation** — `WHERE tenantId = $tenantId` em TODA query, fail-closed se tenantId ausente
3. **13 MCP tools live** — introspection confirma: store, recall, search, list, process_text, health_check, slo_report, neural_handover, initialize_context, memory_feedback + aliases
4. **Fail-closed auth** — 401 confirmado para requests sem auth e com token inválido
5. **pgvector HNSW index** — `ForgeMemory_embedding_hnsw_idx` criado (m=16, ef_construction=64)
6. **text-embedding-3-small (1536d)** — OpenAI embeddings gerados antes da encriptação
7. **RecallRouter 5 modes** — auto/temporal/semantic/priority/hybrid implementados
8. **NCI v4.2** — Neural Context Injection ativo, últimas 3 memórias injetadas
9. **Quality Gate shadow mode** — TQ = (0.45·D) + (0.40·A) − (0.15·N), avalia sem bloquear
10. **Stripe integration** — checkout, portal, webhooks funcionais
11. **ConnectToken auth** — SHA-256 hash lookup, raw token NEVER stored
12. **PII redaction pipeline** — sanitização automática antes do store
13. **Structured logging** — synapseLog com zero PII (userId truncado, email hasheado)

---

## HOLD (plausível mas não confirmado externamente)

1. **"Works in 30 seconds"** — install local confirmado em 3s, mas integração E2E com agente externo não validada com usuário real
2. **Quality Gate TQ scores > 0** — fix C4.7 deployed, mas primeiros scores reais ainda não confirmados em volume
3. **HNSW index performance** — existe mas SeqScan usado pelo planner para <300 rows (correto, precisa de >1000 para HNSW kick in)
4. **CBP pipeline** — código existe (`lib/intelligence/`), flag `BETA_CBP_V4=false`, nunca executado em produção
5. **Smithery re-publish** — listing existe mas warm latency >200ms threshold

---

## FORBIDDEN (não vai a público — motivo técnico ou estratégico)

| Item | Motivo |
|------|--------|
| TQ formula weights (0.45/0.40/0.15) | IP proprietária — moat competitivo |
| NCI injection heuristics | Facilita clonagem |
| RecallRouter scoring thresholds | IP proprietária |
| Quality Gate density/alignment/noise formulas | IP proprietária |
| DB real latency (~1157ms p50) | Percepção negativa — cache mascara para 0ms |
| Número exato de memórias/tenants/tokens | Revela escala real |
| withMemory cache strategy (session 120s + query 60s) | Facilita clonagem |
| MetricsSnapshot materialized view strategy | Implementação interna |
| CBP pipeline architecture | Feature flag off, não pronto |
| Encryption key rotation strategy | Segurança operacional |
