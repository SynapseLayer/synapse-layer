#!/bin/bash
# =============================================================================
# Synapse Layer — Official MCP Registry Publication
# Run on your LOCAL machine with GitHub SSH access.
# =============================================================================
set -e

echo "🧠 Synapse Layer — MCP Registry Publisher"
echo "============================================="
echo ""

# 1. Install mcp-publisher
if ! command -v mcp-publisher &> /dev/null; then
    echo "📦 Installing mcp-publisher..."
    curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/
    echo "✅ mcp-publisher installed: $(mcp-publisher --version 2>&1)"
else
    echo "✅ mcp-publisher found: $(mcp-publisher --version 2>&1)"
fi
echo ""

# 2. Validate server.json
echo "🔍 Step 1: Validating server.json..."
mcp-publisher validate
echo ""

# 3. Authenticate with GitHub
echo "🔐 Step 2: Authenticating with GitHub..."
echo "   Namespace: io.github.SynapseLayer/*"
echo "   This will open a browser for GitHub OAuth."
mcp-publisher login github
echo ""

# 4. Publish to MCP Registry
echo "🚀 Step 3: Publishing to MCP Registry..."
mcp-publisher publish
echo ""

# 5. Verify
echo "🔍 Step 4: Verifying listing..."
sleep 5
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.SynapseLayer/synapse-layer" | python3 -c "
import json, sys
data = json.load(sys.stdin)
servers = data.get('servers', [])
if servers:
    s = servers[0]
    print(f'  \u2705 Server found in registry!')
    print(f'  Name: {s.get(\"name\")}')
    print(f'  Version: {s.get(\"version\")}')
    print(f'  Description: {s.get(\"description\")}')
else:
    print('  \u26a0\ufe0f Server not yet visible (may take a few minutes to propagate)')
"

echo ""
echo "🎉 Done! Synapse Layer is now on the Official MCP Registry."
echo "   Registry: https://registry.modelcontextprotocol.io"
echo "   Server:   io.github.SynapseLayer/synapse-layer"
