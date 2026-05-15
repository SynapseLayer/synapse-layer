#!/bin/bash
# =============================================================================
# Synapse Layer — Smithery Registry Publish Script v2
# Run this on your LOCAL machine (not VM) to authenticate and publish.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_SCHEMA="${REPO_ROOT}/scripts/smithery-config-schema.json"

echo "🧠 Synapse Layer — Smithery Publish Pipeline v2"
echo "================================================"
echo ""

# 1. Check CLI
if ! command -v npx &> /dev/null; then
    echo "❌ npx not found. Install Node.js 20+ first."
    exit 1
fi
echo "✅ Node.js found: $(node --version)"
echo ""

# 2. Authenticate
echo "🔐 Step 1: Authenticating with Smithery..."
npx @smithery/cli auth login
echo ""

# 3. Verify auth
echo "🔍 Step 2: Verifying authentication..."
npx @smithery/cli auth whoami
echo ""

# 4. Verify config schema exists
if [ ! -f "$CONFIG_SCHEMA" ]; then
    echo "❌ Config schema not found at $CONFIG_SCHEMA"
    exit 1
fi
echo "✅ Config schema found: $CONFIG_SCHEMA"
echo ""

# 5. Publish (update existing listing)
echo "🚀 Step 3: Publishing to Smithery Registry..."
npx @smithery/cli mcp publish \
  https://forge.synapselayer.org/api/mcp \
  -n synapselayer/synapse-protocol \
  --config-schema "$CONFIG_SCHEMA"

echo ""
echo "✅ Published!"
echo ""

# 6. Wait for propagation
echo "⏳ Step 4: Waiting 5s for registry propagation..."
sleep 5

# 7. Verify listing
echo "🔍 Step 5: Verifying listing..."
curl -s "https://registry.smithery.ai/servers/synapselayer/synapse-protocol" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'  Name:  {data.get(\"displayName\")}')
tools = data.get('tools', [])
print(f'  Tools: {len(tools)} registered')
for t in tools:
    print(f'    ✓ {t[\"name\"]}')
print(f'  URL:   {data.get(\"deploymentUrl\")}')
print()
expected = 13
if len(tools) >= expected:
    print(f'✅ All {len(tools)} tools published successfully!')
else:
    print(f'⚠️  Only {len(tools)}/{expected} tools detected — server may need redeployment.')
"

echo ""
echo "🎉 Done! Verify at: https://smithery.ai/servers/synapselayer/synapse-protocol"
