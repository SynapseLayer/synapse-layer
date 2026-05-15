# P0 SMITHERY DISTRIBUTION — HARD CLOSE REPORT

**Date**: 2026-05-15  
**Mission**: Resolver por que apenas 5/13 tools MCP aparecem na Smithery  
**Status**: CAUSA RAIZ COMPROVADA + CORREÇÃO PRONTA PARA EXECUÇÃO

---

## 1. RESUMO EXECUTIVO

| Item | Antes | Depois |
|------|-------|--------|
| Registry tools | 5 | 13 (pendente re-publish) |
| Server LIVE tools | 13 | 13 (inalterado) |
| smithery.yaml tools | 13 | 13 (inalterado) |
| Description claim | "Security Score: 10/10 (MCP)" | Limpo (pendente re-publish) |
| Publish script | v2 | v3 (com validação pré-flight) |
| GitHub Action | inexistente | criado (workflow_dispatch) |

**O que estava quebrado**: O registry da Smithery cacheia tools no momento do publish. A última publicação foi feita quando o server tinha apenas 5 tools. Desde então, o server foi atualizado para 13 tools, mas o registry nunca foi atualizado.

**O que foi corrigido**: Tudo que podia ser corrigido da VM foi feito. O código está 100% correto. A única ação restante é re-publicar via Smithery CLI.

**Bloqueio residual**: Re-publicação requer `smithery auth login` que abre browser no smithery.ai (Vercel-hosted). Vercel bot protection bloqueia browser headless da VM. **Requer execução na máquina local do fundador.**

---

## 2. DIAGNÓSTICO FORENSE

### 2.1 Matriz de Divergência

| # | Tool | Código (route.ts) | smithery.yaml | Server LIVE | Registry Smithery |
|---|------|-------------------|---------------|-------------|-------------------|
| 1 | recall | ✅ | ✅ | ✅ | ✅ |
| 2 | save_to_synapse | ✅ | ✅ | ✅ | ✅ |
| 3 | process_text | ✅ | ✅ | ✅ | ✅ |
| 4 | search | ✅ | ✅ | ✅ | ✅ |
| 5 | health_check | ✅ | ✅ | ✅ | ✅ |
| 6 | initialize_context | ✅ | ✅ | ✅ | ❌ MISSING |
| 7 | save_memory | ✅ | ✅ | ✅ | ❌ MISSING |
| 8 | store_memory | ✅ | ✅ | ✅ | ❌ MISSING |
| 9 | recall_memory | ✅ | ✅ | ✅ | ❌ MISSING |
| 10 | list_memories | ✅ | ✅ | ✅ | ❌ MISSING |
| 11 | memory_feedback | ✅ | ✅ | ✅ | ❌ MISSING |
| 12 | neural_handover | ✅ | ✅ | ✅ | ❌ MISSING |
| 13 | slo_report | ✅ | ✅ | ✅ | ❌ MISSING |
| 14 | delete_memory | ✅ (feature-flag) | ✅ | ❌ (disabled) | ❌ |

**Nota**: `delete_memory` está feature-flagged (`MCP_TOOL_DELETE_MEMORY_ENABLED`). Quando habilitado, serão 14 tools.

### 2.2 Evidências Coletadas

1. **Server LIVE (forge.synapselayer.org/api/mcp)**
   - `tools/list` retorna **13 tools** ✅
   - Sem auth necessária para `tools/list`
   - Protocol version: `2024-11-05`
   - Server version: `2.4.0`

2. **Registry Smithery (registry.smithery.ai)**
   - Retorna **5 tools** (cacheado de publish anterior)
   - Description contém claim desalinhado: "Security Score: 10/10 (MCP)"
   - Tools schemas são de versão ANTIGA (menos properties que server atual)

3. **Proxy Smithery (synapse-protocol--synapselayer.run.tools)**
   - Retorna `{"error":"invalid_token"}` sem auth
   - Retorna 0 tools em `tools/list` sem config
   - Proxy funcional mas requer `connect_token` para uso real

4. **smithery.yaml (synapse-layer repo)**
   - Declara 13 tools com schemas completos ✅
   - Description limpa (sem claims proibidos) ✅
   - configSchema com `connect_token` required ✅

---

## 3. CAUSA RAIZ

**O registry Smithery é cacheado no momento da publicação.**

Quando `npx @smithery/cli mcp publish` é executado:
1. O CLI se conecta ao serverUrl
2. Chama `tools/list` para descobrir as tools disponíveis
3. Armazena o resultado no registry
4. O registry permanece estático até a próxima publicação

A última publicação foi feita quando o server tinha **apenas 5 tools** (versão antiga, pré-v2.4.0). O server foi atualizado para 13 tools, mas o registry nunca foi re-publicado. **Não há auto-refresh.**

**Prova**: Os schemas das 5 tools no registry diferem dos schemas das mesmas 5 tools no server atual (menos properties, nomes de parâmetros diferentes).

---

## 4. CORREÇÕES EXECUTADAS

### Commit 1: `d7432a0` (main)
```
fix(smithery): publish automation v3 + GitHub Action for registry refresh
```

**Arquivos alterados**:
- `scripts/smithery-publish.sh` → v3 com validação pré-flight, snapshots before/after, gate de 13 tools
- `.github/workflows/smithery-publish.yml` → GitHub Action (workflow_dispatch) para publicação automatizada
- `smithery_p0_evidence.json` → Evidência forense do estado before/after

**Push**: `github.com:SynapseLayer/synapse-layer.git` → `d7432a0`

---

## 5. VALIDAÇÃO TÉCNICA

- [x] 13 tools registradas no código (route.ts)
- [x] 13 tools declaradas no smithery.yaml
- [x] 13 tools retornadas pelo server LIVE
- [x] 5 tools no registry (STALE — requer re-publish)
- [x] Consistência de nomes entre código, yaml e server
- [x] Schema/metadata presente para todas as 13 tools
- [x] config_schema.json válido
- [x] Auth/config preservada
- [x] Claims proibidos ausentes no yaml e código
- [x] "Security Score: 10/10 (MCP)" será removido no re-publish
- [x] Deploy branch correta (main)
- [x] Commit correspondente (`d7432a0`)

---

## 6. VALIDAÇÃO PÚBLICA FINAL

### Estado ANTES
- **Score**: 69/100
- **Uptime**: 100%
- **Tools visíveis**: 5 (recall, save_to_synapse, process_text, search, health_check)
- **Description**: Contém "Security Score: 10/10 (MCP)" (claim desalinhado)

### Estado ESPERADO APÓS re-publish
- **Score**: ≥69/100 (pode aumentar com mais tools)
- **Uptime**: 100% (inalterado)
- **Tools visíveis**: 13 (todas)
- **Description**: Limpa ("Persistent memory infrastructure for AI agents — encrypted, governed, and cross-agent. The OAuth for AI Memory.")

### Bloqueio de Validação
Smithery.ai é hospedado no Vercel. Vercel bot protection (`Code 11`) bloqueia browser headless da VM. Screenshot da página final requer:
- Re-publish da máquina local do fundador
- Screenshot manual após propagação (5-10 segundos)

---

## 7. AÇÃO REQUERIDA DO FUNDADOR

### Publicação Imediata (5 minutos)

Na máquina local, dentro do repo `synapse-layer`:

```bash
# 1. Pull latest
git pull origin main

# 2. Run publish script
chmod +x scripts/smithery-publish.sh
./scripts/smithery-publish.sh
```

O script irá:
1. Validar que o server retorna 13 tools
2. Pedir autenticação via browser (login no Smithery)
3. Publicar para o registry
4. Verificar que 13 tools foram registradas

### Setup de Publicação Automatizada (opcional)

Após a publicação manual:

```bash
# Get your API key
npx @smithery/cli auth whoami --full
# Copy the SMITHERY_API_KEY value
```

1. Ir para: `github.com/SynapseLayer/synapse-layer/settings/secrets/actions`
2. Adicionar secret: `SMITHERY_API_KEY` = `<your key>`
3. Futuras publicações: Actions → "Publish to Smithery Registry" → Run workflow

---

## 8. PRÓXIMAS AÇÕES

### P0 (Bloqueador)
- [ ] **Fundador executa `smithery-publish.sh`** na máquina local → 13/13 tools no registry

### P1 (Pós-publish)
- [ ] Verificar score na Smithery (pode mudar com 13 tools)
- [ ] Habilitar `delete_memory` se desejado (env var `MCP_TOOL_DELETE_MEMORY_ENABLED=true`) → 14 tools
- [ ] Configurar secret `SMITHERY_API_KEY` no GitHub para publicação automática

### P2 (Melhoria contínua)
- [ ] Monitorar Smithery score e uptime
- [ ] Considerar adicionar GitHub Action trigger no push (auto-publish on release)
