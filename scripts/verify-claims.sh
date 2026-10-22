#!/usr/bin/env bash
# Synapse Layer — Guarda de afirmações públicas
#
# Falha (exit 1) se voltar a aparecer uma alegação que a matriz de
# governação proíbe. É a rede de segurança do G7: sem ela, a próxima
# actualização volta a publicar "o servidor nunca vê texto claro".
#
# Uso:
#   scripts/verify-claims.sh [caminho-do-repo]     (default: raiz do repo)
#
# Corre também no CI: .github/workflows/claims-guard.yml
#
# A lista de regras vive em docs/governance/PUBLIC_CLAIMS_MATRIX.md.

set -uo pipefail
export LC_ALL=C

REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO" || { echo "ERRO: não foi possível entrar em $REPO"; exit 2; }

# Onde procurar. Por omissão, o repositório inteiro. Repositórios com arquivo
# histórico (versões antigas, já inertes) podem restringir às superfícies vivas:
#   SCAN_PATHS="nextjs_space public" bash scripts/verify-claims.sh
SCAN_PATHS="${SCAN_PATHS:-.}"

FAILED=0
FOUND=0

# ── ficheiros isentos ───────────────────────────────────────────────────────
# Documentos que mencionam as expressões proibidas para as proibirem
# (a matriz, o histórico de mudanças e as auditorias anteriores).
EXCLUDE='((^|/)verify-claims\.sh[: ]|(^|/)\.env[.:]|app/api/v1/capture/route\.ts[: ]|app/api/v1/recall/route\.ts[: ]|\.github/workflows/claims-guard\.yml[: ]|docs/governance/PUBLIC_CLAIMS_MATRIX\.md[: ]|docs/PUBLIC_CLAIMS_MATRIX\.md[: ]|docs/FEATURE_CANONICAL_REGISTRY.*\.md[: ]|CHANGELOG\.md[: ]|docs/releases/.*[: ]|docs/governance/FINAL_SCAN.*\.md[: ]|docs/governance/TRUTH_SOURCE.*\.md[: ]|docs/FEATURE_CANONICAL_REGISTRY_v1\.md[: ]|node_modules/.*$|\.git/.*$|\.pyc$|package-lock\.json[: ]|evidence/.*$|\.venv/.*$|dist/.*$|build/.*$|site/.*$|docs/releases/.*[: ]|docs/archive/.*[: ])'

# As rotas de captura/recall ficam isentas: 'zkMode' é o nome do campo do
# protocolo (renomeá-lo quebra clientes) — um identificador não é uma alegação.
#
# Contexto que indica uma frase correctiva (negação explícita).
# Nota: sem caracteres multibyte dentro de [ ] — o script corre em modo byte (LC_ALL=C),
# e um padrão como [ãa] não funciona aí. O texto literal UTF-8 continua a casar normalmente.
CORRECTIVE='(FORBIDDEN|forbidden|PROIBIDO|proibido|Claim Proibido|removid[oa]|\xef\xb7\x8f|\xe2\x9d\x8c|n[^A-Za-z]{0,2}o[^A-Za-z]{0,3}(usar|usamos|anunciar|afirmar|fazemos|prometemos|somos|processa)|not to be used|instead of|this is[^.]{0,60}not|not[^.]{0,60}(certified|compliant)|processa|processes plaintext|sem prova|prometer|replaced[^.]{0,80}with|sem certifica|no RLS|sem RLS|no database RLS|not a zero-knowledge|not mean zero-knowledge|not end-to-end)'

check() {
  local label="$1" regex="$2" extra_exclude="${3:-}" redact="${4:-}"
  local hits
  hits=$(grep -rIniE "$regex" $SCAN_PATHS \
    --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.next \
    --exclude-dir=coverage --exclude-dir=dist --exclude-dir=__pycache__ \
    --exclude='*.pyc' --exclude='*.lock' --exclude='*.min.js' 2>/dev/null \
    | grep -viE "$EXCLUDE" 2>/dev/null \
    | { [ -n "$extra_exclude" ] && grep -viE "$extra_exclude" 2>/dev/null || cat; } \
    | grep -viE "$CORRECTIVE" 2>/dev/null || true)

  if [ -n "$hits" ]; then
    echo ""
    echo "✗ ${label}"
    if [ "$redact" = "redact" ]; then
      echo "$hits" | sed -E 's/^([^:]+:[0-9]+):.*$/\1/' | sort -u | sed 's/^/    /'
      echo "    (conteudo redigido: pode ser um segredo real - verificar manualmente)"
    else
      echo "$hits" | sed 's/^/    /'
    fi
    FAILED=$((FAILED + 1))
    FOUND=$((FOUND + 1))
  else
    echo "✓ ${label}"
  fi
}

echo "Guarda de afirmações — $(basename "$REPO")"
echo "matriz de governação: docs/governance/PUBLIC_CLAIMS_MATRIX.md"
echo ""

# ── As proibições da matriz ─────────────────────────────────────────────────
check "sem 'zero-knowledge' como alegação" \
  'zero[- ]knowledge|\bZK\b' \
  'docs/governance/.*|synapse_memory/backends/forge_backend\.py:[0-9]+:.*legacy'

check "sem 'o servidor nunca vê texto claro'" \
  '(server never sees plaintext|server NEVER sees plaintext|o servidor nunca vê o texto|o servidor nunca vê texto claro|nunca vê texto claro)'

check "sem 'cifra ponta a ponta'" \
  '(end[- ]to[- ]end encrypt|e2e encrypt(ed|ion)?|cifra ponta a ponta|encriptação ponta a ponta)'

check "sem linguagem de marketing sem prova" \
  '(military[- ]grade|quantum[- ]proof|quantum[- ]resistant|unhackable|impenetrable|unbreakable|Continuous Consciousness|giving models a soul|consciência sintética)'

# ── A arquitectura tem de corresponder ao código ────────────────────────────
check "a KDF do produto é HKDF, não PBKDF2" \
  'PBKDF2' \
  'synapse_memory/crypto/.*'   # utilitário local de senha do SDK — PBKDF2 é correcto aí

check "sem alegações de Row-Level Security" \
  '(Row[- ]Level Security|RLS by|ENABLE ROW LEVEL SECURITY|CREATE POLICY)' \
  'ARCHITECTURE\.md'                # o ARCHITECTURE diz explicitamente que não há RLS

check "sem selos de certificação" \
  '(HIPAA[- ]compliant|SOC ?2[- ]compliant|certified by|GDPR[- ]certified|certificad[oa] (pela|by) )'

check "sem chaves reais em ficheiros versionados" \
  '(832d919b|SYNAPSE_ENCRYPTION_KEY *= *[0-9a-fA-F]{16,})' \
  '' \
  redact

check "sem métricas absolutas sem dataset" \
  '(99\.9% (accuracy|uptime|disponibilidade)|100% (uptime|disponibilidade|seguro))'

# ── Veredito ────────────────────────────────────────────────────────────────
echo ""
if [ "$FOUND" -eq 0 ]; then
  echo "RESULTADO: nenhuma alegação proibida encontrada."
  exit 0
else
  echo "RESULTADO: ${FOUND} categoria(s) com alegações proibidas."
  echo "Consulta a matriz: docs/governance/PUBLIC_CLAIMS_MATRIX.md"
  exit 1
fi
