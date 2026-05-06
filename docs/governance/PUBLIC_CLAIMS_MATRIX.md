# PUBLIC CLAIMS MATRIX — SYNAPSE LAYER

> Regra: claim só vai a público se status = PROVEN e evidência existe.
> Atualizado: 2026-05-05 | Responsável: Ismael Marchi

---

## ✅ PROVEN — podem ir a público agora

| # | Claim | Evidência | Onde usar |
|---|-------|-----------|----------|
| 1 | RAG retrieves. Synapse remembers. | Demo real (store+recall via MCP) | Hero, README, socials, everywhere |
| 2 | Persistent memory infrastructure for AI agents | Arquitetura live: store→encrypt→persist→recall | README, landing, docs, everywhere |
| 3 | Encrypted, governed, and cross-agent | AES-256-GCM at rest + tenant isolation + cross-agent recall | README, tagline, everywhere |
| 4 | OAuth for AI Memory | ConnectToken flow implementado (generate→SHA-256→auth) | Category positioning |
| 5 | State Continuity Layer | NCI v4.2 live, session cache, context injection | Technical docs, positioning |
| 6 | AES-256-GCM encryption at rest | `lib/synapse/crypto.ts` — per-op random IV, GCM tag validated | Security docs, comparisons |
| 7 | 13 MCP tools | `tools/list` introspection confirma 13 tools live | Docs, integrations |
| 8 | Tenant-isolated (1 user = 1 private mind) | `WHERE tenantId` em toda query, fail-closed | Security, compliance |
| 9 | Sub-second perceived recall | Cache layer: perceived p50 = 0ms | Performance claims (com "perceived") |
| 10 | Fail-closed security | 401 confirmado para no-auth e invalid-token | Security positioning |
| 11 | ~~PII redaction pipeline~~ | REMOVED (v1.1.5) — replaced by content sanitization | — |
| 12 | LGPD-ready | delete_memory (soft+hard), content sanitization, tenant isolation | Compliance docs |
| 13 | 5 recall modes | auto/temporal/semantic/priority/hybrid — RecallRouter live | Technical docs |
| 14 | pgvector semantic search | HNSW index + text-embedding-3-small (1536d) | Technical docs |
| 15 | pip install synapse-layer (<10s) | Confirmado: 3s em clean venv | Onboarding, README |

---

## ⏸️ HOLD — não usar até validação

| # | Claim | Bloqueador | Prazo estimado |
|---|-------|-----------|----------------|
| 1 | "Works in 30 seconds" | Install ok, mas E2E com agente externo não validado | Bloco B (user test) |
| 2 | Quality Gate TQ scoring live | Fix deployed (C4.7), scores reais pendentes em volume | Monitorar 7 dias |
| 3 | HNSW index accelerates recall | Ativo mas SeqScan usado para <300 rows | Quando >1000 memories |
| 4 | Neural Handover™ production-ready | V2 implementado, 0 sessions em produção | Primeiro uso real |
| 5 | Smithery verified listing | Listing existe, re-publish pendente (latency) | Quando warm <200ms |

---

## 🚫 FORBIDDEN — nunca usar publicamente

| # | Claim | Motivo |
|---|-------|--------|
| 1 | ~~Zero-Knowledge~~ | REMOVED (v1.3.0) — server-side AES-256-GCM, not ZK |
| 2 | Continuous Consciousness Infrastructure | Overclaim — não há "consciência" |
| 3 | Consciência Sintética / Imortalidade Cognitiva | Risco reputacional extremo |
| 4 | Giving Models a Soul | Marketing enganoso |
| 5 | Client-side encryption | Encriptação é server-side (AES-256-GCM at rest) |
| 6 | End-to-end encrypted | Não é E2E — server encripta |
| 7 | Métricas absolutas sem dataset verificável | Misleading (ex: "99.9% accuracy") |
| 8 | Quantum-proof / Quantum-resistant | Sem implementação de PQC |
| 9 | Military-grade encryption | Termo vazio sem certificação |
| 10 | Unhackable / Impenetrable | Impossível de garantir |
| 11 | "The server never sees plaintext" | Server processa plaintext antes de encriptar |
