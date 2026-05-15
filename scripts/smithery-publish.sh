#!/bin/bash
# =============================================================================
# Synapse Layer — Smithery Registry Publish Script v3
# Run this on your LOCAL machine (not VM) to authenticate and publish.
# 
# Prerequisites:
#   - Node.js 20+
#   - Internet access to smithery.ai (Vercel-hosted, needs real browser)
#
# Usage:
#   chmod +x scripts/smithery-publish.sh
#   ./scripts/smithery-publish.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_SCHEMA="${REPO_ROOT}/scripts/smithery-config-schema.json"
SERVER_URL="https://forge.synapselayer.org/api/mcp"
QUALIFIED_NAME="synapselayer/synapse-protocol"
EXPECTED_TOOLS=13

echo "🧠 Synapse Layer — Smithery Publish Pipeline v3"
echo "================================================"
echo ""

# ── Step 0: Pre-flight validation ──────────────────────────────────
echo "📋 Step 0: Pre-flight validation..."

# Check npx
if ! command -v npx &> /dev/null; then
    echo "❌ npx not found. Install Node.js 20+ first."
    exit 1
fi
echo "  ✅ Node.js: $(node --version)"

# Check config schema
if [ ! -f "$CONFIG_SCHEMA" ]; then
    echo "❌ Config schema not found at $CONFIG_SCHEMA"
    exit 1
fi
python3 -c "import json; json.load(open('$CONFIG_SCHEMA'))" 2>/dev/null || {
    echo "❌ Config schema is invalid JSON"
    exit 1
}
echo "  ✅ Config schema valid"

# Check server accessibility
TOOL_COUNT=$(curl -sf -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  python3 -c "import sys,json; print(len(json.loads(sys.stdin.read()).get('result',{}).get('tools',[])))" 2>/dev/null || echo "0")

if [ "$TOOL_COUNT" -lt "$EXPECTED_TOOLS" ]; then
    echo "❌ Server returns $TOOL_COUNT tools (expected $EXPECTED_TOOLS)"
    echo "   Fix the MCP server before publishing."
    exit 1
fi
echo "  ✅ Server returns $TOOL_COUNT tools"

# Snapshot before
echo ""
echo "📸 Current registry state (BEFORE):"
curl -sf "https://registry.smithery.ai/servers/@${QUALIFIED_NAME}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('tools', [])
print(f'  Tools: {len(tools)}')
for t in tools: print(f'    - {t[\"name\"]}')
print(f'  Description: {data.get(\"description\", \"N/A\")[:80]}...')
" 2>/dev/null || echo "  ⚠️ Could not fetch current registry state"
echo ""

# ── Step 1: Authenticate ──────────────────────────────────────────
echo "🔐 Step 1: Authenticating with Smithery..."
echo "   This will open your browser. Log in with your Smithery account."
echo ""
npx @smithery/cli auth login
echo ""

# Verify auth
echo "🔍 Step 2: Verifying authentication..."
npx @smithery/cli auth whoami
echo ""

# ── Step 3: Publish ───────────────────────────────────────────────
echo "🚀 Step 3: Publishing to Smithery Registry..."
npx @smithery/cli mcp publish \
  "$SERVER_URL" \
  -n "$QUALIFIED_NAME" \
  --config-schema "$CONFIG_SCHEMA"
echo ""

# ── Step 4: Wait and verify ──────────────────────────────────────
echo "⏳ Step 4: Waiting 10s for registry propagation..."
sleep 10

echo "🔍 Step 5: Verifying listing..."
curl -sf "https://registry.smithery.ai/servers/@${QUALIFIED_NAME}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
tools = data.get('tools', [])
print(f'  Tools: {len(tools)}')
for t in tools:
    print(f'    ✓ {t[\"name\"]}')
print(f'  Description: {data.get(\"description\", \"N/A\")[:80]}...')
print()
if len(tools) >= $EXPECTED_TOOLS:
    print(f'✅ SUCCESS: All {len(tools)} tools published!')
else:
    print(f'⚠️  Only {len(tools)}/$EXPECTED_TOOLS tools — Smithery may need time to refresh cache.')
    print(f'   Check: https://smithery.ai/servers/{\"$QUALIFIED_NAME\".replace(\"/\", \"/\")}\n')
"

echo ""
echo "📸 Registry state saved. If publishing succeeded, save the SMITHERY_API_KEY"
echo "   as a GitHub secret for automated future publishing:"
echo ""
echo "   npx @smithery/cli auth whoami --full"
echo "   → Copy the API key"
echo "   → Go to github.com/SynapseLayer/synapse-layer/settings/secrets/actions"
echo "   → Add secret: SMITHERY_API_KEY = <your key>"
echo "   → Future publishes: Actions → 'Publish to Smithery Registry' → Run workflow"
echo ""
echo "🎉 Done! Verify at: https://smithery.ai/servers/synapselayer/synapse-protocol"
