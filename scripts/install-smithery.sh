#!/usr/bin/env bash
# Synapse Layer — 1-command Smithery installer
# Usage (all equivalent):
#   curl -fsSL https://forge.synapselayer.org/install/smithery | bash
#     (interactive: asks for your client + connect token)
#   curl -fsSL https://forge.synapselayer.org/install/smithery | bash -s -- sk_connect_xxx
#     (token only — 1 click from the Forge dashboard; asks which client)
#   curl -fsSL https://forge.synapselayer.org/install/smithery | bash -s -- cursor sk_connect_xxx
#     (0 prompts: token + client)
#
# The connect_token is passed as an argv (never in the URL), so it never
# leaks into CDN/proxy logs. It is a per-agent scoped token, not the master key.
# Installs @synapselayer/synapselayer into your MCP client config.
set -euo pipefail

LISTING_URL="https://smithery.ai/servers/synapselayer/synapselayer"
SUPPORTED_CLIENTS="claude, cursor, opencode, codex, gemini-cli, cline, windsurf, vscode, roocode, witsy, enconvo, amazon-bedrock, amazonq, librechat, goose"

trim() { [[ -z "${1:-}" ]] && return 0; printf '%s' "${1//[$'\t\r\n ']}"; }

main() {
  local token="" client=""
  local arg

  for arg in "$@"; do
    if [[ "$arg" == sk_connect_* || "$arg" == sk_* ]]; then
      token="$arg"
    else
      client="$arg"
    fi
  done

  token="$(trim "$token")"

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
    token="$(trim "$token")"
  fi

  if [[ "$token" != sk_connect_* && "$token" != sk_* ]]; then
    echo "Error: connect_token must start with 'sk_connect_'. Got '${token:0:8}…'." >&2
    exit 1
  fi

  echo
  echo "Installing @synapselayer/synapselayer into your $client config"
  echo "  token: ${token:0:12}… (masked)"
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