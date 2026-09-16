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
SERVER_REF="@synapselayer/synapselayer"
SUPPORTED_CLIENTS="claude, cursor, opencode, codex, gemini-cli, cline, windsurf, vscode, roocode, witsy, enconvo, amazon-bedrock, amazonq, librechat, goose"

trim() { [[ -z "${1:-}" ]] && return 0; printf '%s' "${1//[$'\t\r\n ']}"; }

# When a script is piped through `curl ... | bash`, stdin is the pipe itself,
# already consumed by bash — so `read` would get EOF and abort. Interactive
# prompts must read from the real TTY (/dev/tty) when one is available.
ask() { # ask "<prompt>" <varname> [default]
  local _p="$1" _v="$2" _d="${3:-}"
  if [[ -n "$_d" ]]; then _p+=" [$_d]: "; else _p+=": "; fi
  if [[ -e /dev/tty ]]; then
    read -r -p "$_p" "$_v" < /dev/tty || true
  else
    read -r -p "$_p" "$_v" || true
  fi
  [[ -n "$_d" && -z "${!_v:-}" ]] && printf -v "$_v" "%s" "$_d"
  return 0
}

ask_secret() { # ask_secret "<prompt>" <varname>
  local _p="$1" _v="$2"
  local _val
  if [[ -e /dev/tty ]]; then
    read -r -s -p "$_p" _val < /dev/tty || true
  else
    read -r -s -p "$_p" _val || true
  fi
  printf '\n'
  printf -v "$_v" "%s" "$_val"
  return 0
}

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
    ask "Which client? ($SUPPORTED_CLIENTS)" client "claude"
  fi

  if [ -z "$token" ]; then
    echo
    echo "Get your free Connect Token at https://forge.synapselayer.org -> Connect"
    while [ -z "$token" ]; do
      ask_secret "connect_token (sk_connect_...): " token
      token="$(trim "$token")"
    done
  fi

  if [[ "$token" != sk_connect_* && "$token" != sk_* ]]; then
    echo "Error: connect_token must start with 'sk_connect_'. Got '${token:0:8}…'." >&2
    exit 1
  fi

  echo
  echo "Installing @synapselayer/synapselayer into your $client config"
  echo "  token: ${token:0:12}… (masked)"
  npx -y @smithery/cli@latest install "$SERVER_REF" \
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