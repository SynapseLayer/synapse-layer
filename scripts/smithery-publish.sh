#!/bin/bash
# =============================================================================
# Synapse Layer — Smithery Registry Publish Script
# Run this on your LOCAL machine (not VM) to authenticate and publish.
# =============================================================================
set -e

echo "🧠 Synapse Layer — Smithery Publish Pipeline"
echo "============================================="
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

# 4. Publish (update existing listing)
echo "🚀 Step 3: Publishing to Smithery Registry..."
npx @smithery/cli mcp publish \
  https://forge.synapselayer.org/api/mcp \
  -n synapselayer/synapse-protocol \
  --config-schema '{"type":"object","properties":{"agent_id":{"type":"string","description":"Agent identifier for memory isolation. Defaults to default.","default":"default"}},"required":[]}'

echo ""
echo "✅ Published! Check: https://smithery.ai/servers/synapselayer/synapse-protocol"
echo ""

# 5. Verify listing
echo "🔍 Step 4: Verifying listing..."
curl -s "https://registry.smithery.ai/servers/synapselayer/synapse-protocol" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'  Name: {data.get(\"displayName\")}')
print(f'  Tools: {len(data.get(\"tools\", []))} registered')
for t in data.get('tools', []):
    print(f'    - {t[\"name\"]}')
print(f'  URL: {data.get(\"deploymentUrl\")}')
print()
print('✅ Smithery listing verified!')
"

echo ""
echo "🎉 Synapse Layer is now globally discoverable on Smithery!"
echo "   → https://smithery.ai/servers/synapselayer/synapse-protocol"
