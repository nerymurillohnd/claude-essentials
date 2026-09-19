#!/usr/bin/env bash
# verify-completion hook handler. Bash 3.2 compatible.
#
#   gate.sh mark   PostToolUse: remember that work happened in this session.
#   gate.sh stop   Stop: when the reply that ends the turn presents work as
#                  finished, require a valid Verification record in it.
#
# The Stop gate sends Claude back (additionalContext keeps the turn going) and
# does so again after each round of new work; when a reply comes back with no
# new work and still no valid record, it lets the turn end and warns the user
# (systemMessage) that the claim is unverified. It never traps a session:
# malformed input, a missing jq, or any internal error exits 0.
#
# Mode: CLAUDE_PLUGIN_OPTION_ENFORCEMENT (the plugin's `enforcement` option):
#   enforce (default) nudge, then warn · warn: only warn the user · off: nothing.
set -u

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) || exit 0

# ------------------------------------------------------------------ state ---

# Sets STATE_DIR to a private writable directory, or "" (returns 1).
state_dir() {
  local dir
  if [[ -n ${CLAUDE_PLUGIN_DATA:-} ]]; then
    dir="${CLAUDE_PLUGIN_DATA%/}/sessions"
  else
    dir=${TMPDIR:-/tmp}
    dir="${dir%/}/verify-completion-$(id -u 2>/dev/null || echo 0)"
  fi
  if (umask 077 && mkdir -p "${dir}") 2>/dev/null && [[ -d ${dir} && -w ${dir} ]]; then
    STATE_DIR=${dir}
    return 0
  fi
  STATE_DIR=""
  return 1
}

# Sets SESSION from the payload's top-level "session_id", as a safe file name.
# A JSON-escaped occurrence inside a string value reads \"session_id\" and
# can't match, so the first match is the real key.
session_id() {
  SESSION=""
  local re='"session_id"[[:space:]]*:[[:space:]]*"([^"]{1,200})"'
  if [[ $1 =~ ${re} ]]; then
    SESSION=$(printf '%s' "${BASH_REMATCH[1]}" | tr -c 'A-Za-z0-9_-' '_')
  fi
}

# ---------------------------------------------------------------- output ---

emit_context() {
  jq -n --arg text "$1" \
    '{hookSpecificOutput: {hookEventName: "Stop", additionalContext: $text}}'
}

emit_warning() {
  jq -n --arg text "$1" '{systemMessage: $text}'
}

# Appended to every nudge so Claude can comply even when the skill isn't
# loaded (Cowork, a denied Skill tool). Filled in, it is a valid record.
# shellcheck disable=SC2016 # literal backticks in Markdown sent to Claude, not expansions
TEMPLATE='End the reply with this record; keep the tokens, write the rest in any language, one line per gate with its evidence on that line:

### Verification record

Requirement: <what the user asked for, in their terms>

1. Adversarial review: PASS — <what you re-read and re-ran, e.g. `git diff`>
2. Outcome: PASS — <each part of the request mapped to the evidence for it>
3. Counterpart: N/A — <why nothing consumes it, or PASS and what it rejected>
4. Distrust the green: PASS — <skipped tests, swallowed errors, mocks you checked>
5. Both directions: PASS — <what works, and what fails with which error>
6. Evidence: PASS — <where the commands and outputs are>

Verdict: VERIFIED

Use FAIL or BLOCKED with the exact reason for a gate that did not pass (then "Verdict: NOT VERIFIED"); N/A is allowed only for gates 3 and 5.'

# --------------------------------------------------------------- commands ---

cmd_mark() {
  local input
  input=$(cat) || return 0
  session_id "${input}"
  [[ -n ${SESSION} ]] || return 0
  state_dir || return 0
  : >"${STATE_DIR}/${SESSION}.work" 2>/dev/null
  # New work deserves a new reminder.
  rm -f "${STATE_DIR}/${SESSION}.nudged" 2>/dev/null
  return 0
}

cmd_stop() {
  local input have_state=0 work=1 already=0
  input=$(cat) || return 0
  session_id "${input}"
  if [[ -n ${SESSION} ]] && state_dir; then
    have_state=1
    find "${STATE_DIR}" -type f -mtime +7 -exec rm -f {} + 2>/dev/null
  fi

  if ! command -v jq >/dev/null 2>&1; then
    if [[ ${have_state} -eq 1 && ! -e "${STATE_DIR}/${SESSION}.nojq" ]]; then
      : >"${STATE_DIR}/${SESSION}.nojq" 2>/dev/null
      printf '%s\n' '{"systemMessage":"verify-completion: jq was not found, so completion claims in this session are not being checked. Install jq 1.6 or later."}'
    fi
    return 0
  fi

  local summary present verdict n_errors n_claims claims errors active
  summary=$(printf '%s' "${input}" | jq -c -f "${here}/analyze.jq" 2>/dev/null) || return 0
  summary=$(printf '%s' "${summary}" | jq -r '
		(.record.present | tostring),
		.record.verdict,
		(.record.errors | length | tostring),
		(.claims | length | tostring),
		(.claims[:3] | map("\"" + . + "\"") | join(", ")),
		(.record.errors | join("; ")),
		(.stop_hook_active | tostring)' 2>/dev/null) || return 0
  {
    IFS= read -r present
    IFS= read -r verdict
    IFS= read -r n_errors
    IFS= read -r n_claims
    IFS= read -r claims
    IFS= read -r errors
    IFS= read -r active
  } <<EOF
${summary}
EOF
  # Empty input makes jq print nothing; anything unexpected fails open.
  [[ ${present} == true || ${present} == false ]] || return 0
  [[ ${n_errors} =~ ^[0-9]+$ && ${n_claims} =~ ^[0-9]+$ ]] || return 0

  if [[ ${have_state} -eq 1 && ! -e "${STATE_DIR}/${SESSION}.work" ]]; then
    work=0
  fi

  local problem
  if [[ ${present} == true ]]; then
    if [[ ${n_errors} == 0 ]]; then
      # A valid record, VERIFIED or NOT VERIFIED, closes this unit of work.
      if [[ ${have_state} -eq 1 ]]; then
        rm -f "${STATE_DIR}/${SESSION}.work" "${STATE_DIR}/${SESSION}.nudged" 2>/dev/null
      fi
      return 0
    fi
    problem=record
  elif [[ ${n_claims} != 0 && ${work} -eq 1 ]]; then
    problem=claim
  else
    return 0
  fi

  if [[ ${MODE} == warn ]]; then
    already=1
  elif [[ ${have_state} -eq 1 ]]; then
    [[ -e "${STATE_DIR}/${SESSION}.nudged" ]] && already=1
  elif [[ ${active} == true ]]; then
    already=1
  fi

  if [[ ${already} -eq 1 ]]; then
    if [[ ${problem} == claim ]]; then
      emit_warning "verify-completion: Claude's last reply presents work as finished (${claims}) without a verification record. Treat that claim as unverified."
    else
      emit_warning "verify-completion: Claude's last reply has an invalid verification record (${errors}). Treat its verdict (${verdict:-none}) as unverified."
    fi
    return 0
  fi

  if [[ ${have_state} -eq 1 ]]; then
    : >"${STATE_DIR}/${SESSION}.nudged" 2>/dev/null
  fi
  if [[ ${problem} == claim ]]; then
    emit_context "verify-completion: this reply presents work as finished (${claims}) but carries no Verification record. Before presenting work as complete, run the verify-completion skill's six gates against the real files, commands, and diffs, and end the reply with its Verification record. If something could not be verified, say so and use \"Verdict: NOT VERIFIED\" with the exact reason. If you did not mean to claim completion, rewrite the reply without that claim. Passing this check never authorizes a commit, push, deploy, or publish.

${TEMPLATE}"
  else
    emit_context "verify-completion: the Verification record in this reply is not valid: ${errors}. Fix the record (see the verify-completion skill's references/record-format.md). Never weaken a gate to make it pass: if a gate cannot be satisfied, use \"Verdict: NOT VERIFIED\" and give the exact reason.

${TEMPLATE}"
  fi
  return 0
}

MODE=$(printf '%s' "${CLAUDE_PLUGIN_OPTION_ENFORCEMENT:-enforce}" | tr '[:upper:]' '[:lower:]')
case ${MODE} in
off) exit 0 ;;
warn) ;;
*) MODE=enforce ;;
esac

case ${1:-} in
mark) cmd_mark ;;
stop) cmd_stop ;;
*)
  printf 'usage: gate.sh mark|stop  (reads a Claude Code hook payload on stdin)\n' >&2
  exit 0
  ;;
esac
exit 0
