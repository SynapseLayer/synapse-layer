#!/usr/bin/env bash
# Synapse Layer — 1-command Smithery installer
# Usage:
#   curl -fsSL https://forge.synapselayer.org/install/smithery | bash
#     (interactive: asks for your client + connect token)
#   bash install-smithery.sh <client> <connect_token>
#     (non-interactive: e.g. bash install-smithery.sh cursor sk_connect_xxx)
#
# Installs @synapselayer/synapselayer into your MCP client config.
set -euo pipefail

LISTING_URL="https://smithery.ai/servers/synapselayer/synapselayer"
SUPPORTED_CLIENTS="claude, cursor, opencode, codex, gemini-cli, cline, windsurf, vscode, roocode, witsy, enconvo, amazon-bedrock, amazonq, librechat, goose"

main() {
  local client="${1:-}"
  local token="${2:-}"

  if [ -z "$client" ]; then
    echo "Synapse Layer — Smithery installer"
    echo "Which client do you use? ($SUPPORTED_CLIENTS)"
    read -r -p "client: " client
  fi
  if [ -z "$token" ]; then
    echo
    echo "Get your free Connect Token at https://forge.synapselayer.org -> Connect"
    while [ -z "$token" ]; do
      read -r -s -p "connect_token (sk_connect_...): " token
      echo
    done
  fi

  echo
  echo "Installing @synapselayer/synapselayer into your $client config..."
  npx -y @smithery/cli@latest install "$LISTING_URL" \
    --client "$client" \
    --config "{\"connect_token\": \"$token\"}"

  echo
  echo "Done. Restart $client and your 13 Synapse Layer MCP tools will be live:"
  echo "  health_check | initialize_context | recall | search | save_to_synapse"
  echo "  process_text | store_memory | save_memory | list_memories"
  echo "  memory_feedback | recall_memory | slo_report"
  echo
  echo "Details: $LISTING_URL"
}

main "$@"