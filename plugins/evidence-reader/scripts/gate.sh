#!/usr/bin/env bash
# gate.sh — evidence-reader report quality gate. Bash 3.2 compatible.
#
#   gate.sh stop      SubagentStop for the three evidence-reader agents: checks that
#                     the returned report carries the evidence-standard sections and,
#                     when it doesn't, sends the agent back to complete it (at most
#                     MAX_RETRIES times per agent run), then lets it stop flagged.
#   gate.sh handback  PreToolUse on SubagentHandback: remembers the report an agent
#                     hands back through that tool, so `stop` checks the real report.
#
# Mode comes from the plugin option `enforcement` (CLAUDE_PLUGIN_OPTION_ENFORCEMENT):
#   block (default) | warn | off.
# Fails open: malformed input, a missing jq or any internal error exits 0 without
# blocking, so the gate can never trap an agent.

set -u

MAX_RETRIES=2
REQUIRED_MARKERS='**Status:**
**Tier:**
## Files reviewed
## Findings
## Not verified
## Needs human judgment'

mode=${1:-}
enforcement=${CLAUDE_PLUGIN_OPTION_ENFORCEMENT:-block}

# state_dir <dir> — resolve a trusted-only report/retry cache directory into
# STATE_DIR (empty if none is trusted). A CLAUDE_PLUGIN_DATA directory is
# always ours; a TMPDIR/tmp fallback is shared with every user, so its name
# carries our uid and a directory someone else created (or a symlink to one)
# is never trusted — the same hardening ruff-quality and shell-quality use
# for the same fallback.
state_dir() {
  dir=$1
  if (umask 077 && mkdir -p "${dir}") 2>/dev/null && [ -d "${dir}" ] && [ ! -L "${dir}" ] && [ -O "${dir}" ] && [ -w "${dir}" ]; then
    STATE_DIR=${dir}
  else
    STATE_DIR=""
  fi
}

emit_system_message() {
  # emit_system_message <text> — visible notice without blocking; works without jq.
  # Quotes, backslashes and control characters would break the JSON string; drop them.
  text=$(printf '%s' "$1" | tr '\n\t' '  ' | tr -d '\042\134\000-\037' || true)
  printf '{"systemMessage":"%s"}\n' "${text}"
}

if [ "${enforcement}" = off ]; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  if [ "${mode}" = stop ]; then
    emit_system_message "evidence-reader: report gate skipped because jq is not installed (install jq to enable it)."
  fi
  exit 0
fi

payload=$(cat 2>/dev/null || true)
if [ -z "${payload}" ] || ! printf '%s' "${payload}" | jq -e 'type == "object"' >/dev/null 2>&1; then
  exit 0
fi

# PreToolUse on SubagentHandback fires for every subagent in the session: leave before
# touching the disk unless the report is one of our own agents'.
if [ "${mode}" = handback ]; then
  handback_type=$(printf '%s' "${payload}" | jq -r '.agent_type // empty' 2>/dev/null || true)
  case "${handback_type}" in
  evidence-reader:document-reader | evidence-reader:tabular-auditor | evidence-reader:image-inspector) ;;
  *) exit 0 ;;
  esac
fi

agent_id=$(printf '%s' "${payload}" | jq -r '.agent_id // empty' 2>/dev/null || true)
safe_id=$(printf '%s' "${agent_id}" | tr -c 'A-Za-z0-9_.-' '_')

if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
  state_dir "${CLAUDE_PLUGIN_DATA%/}/evidence-reader-gate"
else
  uid=$(id -u 2>/dev/null || printf 0)
  state_dir "${TMPDIR:-/tmp}/evidence-reader-gate-${uid}"
fi

case "${mode}" in
handback)
  if [ -n "${safe_id}" ] && [ -n "${STATE_DIR}" ]; then
    printf '%s' "${payload}" | jq -r '.tool_input.message // empty' >"${STATE_DIR}/${safe_id}.handback" 2>/dev/null || true
  fi
  exit 0
  ;;
stop) ;;
*)
  exit 0
  ;;
esac

agent_type=$(printf '%s' "${payload}" | jq -r '.agent_type // "evidence-reader agent"' 2>/dev/null || true)
report=$(printf '%s' "${payload}" | jq -r '.last_assistant_message // empty' 2>/dev/null || true)
if [ -n "${safe_id}" ] && [ -n "${STATE_DIR}" ] && [ -s "${STATE_DIR}/${safe_id}.handback" ]; then
  report=$(cat "${STATE_DIR}/${safe_id}.handback")
fi

# has_line_starting <marker> — the report has a line that starts with the marker
# (leading spaces allowed). A marker quoted mid-sentence does not count.
has_line_starting() {
  printf '%s\n' "${report}" | awk -v m="$1" '{ sub(/^[ \t]+/, "") } index($0, m) == 1 { found = 1; exit } END { exit found ? 0 : 1 }'
}

missing=""
while IFS= read -r marker; do
  [ -z "${marker}" ] && continue
  if ! has_line_starting "${marker}"; then
    missing="${missing}${missing:+, }${marker}"
  fi
done <<EOF
${REQUIRED_MARKERS}
EOF

cleanup_state() {
  if [ -n "${safe_id}" ] && [ -n "${STATE_DIR}" ]; then
    rm -f "${STATE_DIR}/${safe_id}.retries" "${STATE_DIR}/${safe_id}.handback" 2>/dev/null || true
  fi
}

if [ -z "${missing}" ]; then
  cleanup_state
  exit 0
fi

if [ "${enforcement}" = warn ]; then
  cleanup_state
  emit_system_message "evidence-reader: the report from ${agent_type} is INCOMPLETE (missing: ${missing})."
  exit 0
fi

# Without a place to count retries, a second block could repeat forever: once Claude Code
# says this stop already follows a block (stop_hook_active), let the agent stop, flagged.
stop_hook_active=$(printf '%s' "${payload}" | jq -r '.stop_hook_active // false' 2>/dev/null || true)
if { [ -z "${safe_id}" ] || [ -z "${STATE_DIR}" ]; } && [ "${stop_hook_active}" = true ]; then
  emit_system_message "evidence-reader: the report from ${agent_type} is still INCOMPLETE (missing: ${missing}) and the gate cannot track retries here. Treat it as partial."
  exit 0
fi

retries=0
if [ -n "${safe_id}" ] && [ -n "${STATE_DIR}" ]; then
  if [ -f "${STATE_DIR}/${safe_id}.retries" ]; then
    retries=$(cat "${STATE_DIR}/${safe_id}.retries" 2>/dev/null || printf '0')
  fi
  case "${retries}" in
  '' | *[!0-9]*) retries=0 ;;
  *) ;;
  esac
fi

if [ "${retries}" -ge "${MAX_RETRIES}" ]; then
  cleanup_state
  emit_system_message "evidence-reader: the report from ${agent_type} is still INCOMPLETE after ${MAX_RETRIES} retries (missing: ${missing}). Treat it as partial."
  exit 0
fi

if [ -n "${safe_id}" ] && [ -n "${STATE_DIR}" ]; then
  printf '%s' "$((retries + 1))" >"${STATE_DIR}/${safe_id}.retries" 2>/dev/null || true
  # The blocked report is spent: the next stop checks whatever the agent hands back or
  # writes next, never this copy again.
  rm -f "${STATE_DIR}/${safe_id}.handback" 2>/dev/null || true
fi
reason="Your report is missing required evidence-standard sections: ${missing}. Rewrite it using the template in the evidence-standard skill (assets/report-template.md): Status, Tier, Files reviewed, Findings with receipts, Not verified, Needs human judgment. Write None where a section is empty. Do not invent content to fill a section. Deliver the corrected report the way you delivered the first one: through SubagentHandback if you handed it back, otherwise as your final message."
jq -n --arg reason "${reason}" '{decision: "block", reason: $reason}'
exit 0
