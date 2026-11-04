# PUBLIC_CLAIMS_MATRIX.md
**Synapse Layer — Matriz de Claims Públicos v1.0**

> **Superseded (2026-11-04):** the public contract is [FEATURES.md](../FEATURES.md).
> This file is retained for historical governance; conflicts resolve in favor of FEATURES.md.

Última atualização: 04 de Maio de 2026
Proprietário: Ismael Marchi
Status: APPROVED

## Regra de Ouro
> Público explica o benefício. Privado preserva o moat.

## ALLOWED — Claims Aprovados

### Hero / One-liner
- "RAG retrieves. Synapse remembers."
- "Persistent, encrypted memory infrastructure for AI agents."

### Descrição Principal
- Persistent memory infrastructure for AI agents — encrypted, governed, and cross-agent.
- Memory that survives across sessions, models, and tools.
- State Continuity Layer for autonomous AI systems.

### Benefícios (comprováveis)
- Cross-model handover seguro
- Privacy-first: AES-256-GCM encrypted at rest, com chave por tenant
  (HKDF-SHA256 sobre a chave mestra) e IV aleatório por operação
- Trust-weighted recall com Trust Quotient (TQ)

### Categorias Oficiais
- Memory Infrastructure Layer (principal)
- State Continuity Layer (secundária)
- OAuth for AI Memory (terciária)

## HOLD — Só usar com evidência verificável
- "70% token reduction" → só com dados públicos reais
- "Zero context loss across 10K+ sessions" → só após validação
- "Enterprise-ready" → só após casos reais
- "Self-healing memory" → em desenvolvimento
- "Differential privacy" → not claimed; experimental noise only; API reports `differential_privacy: false`

## FORBIDDEN — Nunca usar publicamente
- Continuous Consciousness / Consciência Sintética
- Giving Models a Soul
- Imortalidade Cognitiva
- GDPR/LGPD compliant (usar: "designed for LGPD/GDPR alignment")
- Detalhes de arquitetura interna (TQ weights, scoring, heuristics, pipeline)
- Métricas sem dados verificáveis

## Copy Aprovada por Canal

| Canal | Copy Aprovada |
|---|---|
| GitHub Org Bio | MCP-native memory infrastructure for autonomous agents. Encrypted server-side persistence (AES-256-GCM) · Trust Quotient™ scoring · human-in-the-loop curation. |
| synapse-layer description | Persistent memory infrastructure for AI agents — encrypted, governed, and cross-agent. |
| synapse-sdk-python description | Python SDK for Synapse Layer — persistent, encrypted, cross-agent memory for AI agents. |
| synapse-layer-skill description | Persistent memory skill for AI agents. Remembers preferences, brand voice and decisions with Trust Quotient scoring. |
| PyPI / npm | Synapse Layer SDK — persistent, encrypted, cross-agent memory for AI agents. |
| MCP | Persistent memory infrastructure for AI agents. Encrypted at rest with a per-tenant key. |

> Evidência e estados (PROVEN / HOLD / FORBIDDEN) na matriz de governança:
> [`docs/governance/PUBLIC_CLAIMS_MATRIX.md`](governance/PUBLIC_CLAIMS_MATRIX.md).
> Em caso de conflito, prevalece a matriz de governança.

## Regras de Governança
1. Toda superfície pública respeita esta matriz.
2. Novo claim → aprovação antes de publicar.
3. Se não está em ALLOWED → é HOLD ou FORBIDDEN.
4. Prioridade: Benefício > Funcionalidade > Como funciona.
5. Forge herda narrativa do domínio principal. Nunca cria claims paralelas.

Aprovado por: Ismael Marchi
Próxima revisão: 18 de Maio de 2026
