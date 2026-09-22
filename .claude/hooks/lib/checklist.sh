#!/usr/bin/env bash
# Checklist state for maintenance skills (ADR-0002 amendment). A skill starts a
# checklist from its template, marks items as it works, and checklist-gate.sh (a
# Stop hook the skill registers) refuses to let the turn end until every item is
# done with evidence and each item's verify command passes.
#
# One checklist is active at a time; `start` refuses while another is unfinished.
# Verify commands run from the repository root with $CHECKLIST_SUBJECT set.
#
# Usage (from the repository root, or anywhere with CLAUDE_PROJECT_DIR set):
#   checklist.sh start <template.json> <subject> <session-id>
#   checklist.sh check <item-id> <evidence>     done, with what proves it
#   checklist.sh needs-user <item-id> <question> blocked on a user decision
#   checklist.sh abort <the user's instruction>   only when the user asked to stop
#   checklist.sh status                            print the active checklist
#
# State: .claude/state/checklists/<skill>--<subject>.json (gitignored).
set -euo pipefail

root=${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
state_dir="${root}/.claude/state/checklists"
active="${state_dir}/.active"

die() {
  printf 'checklist: %s\n' "$*" >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || die "jq is required"

current() {
  [[ -f ${active} ]] || die "no active checklist; run: checklist.sh start <template> <subject> <session-id>"
  local file
  file=$(<"${active}")
  [[ -f ${file} ]] || die "active checklist ${file} is missing"
  printf '%s' "${file}"
}

# Each rewrite calls jq directly, with the program as a literal argument, and
# lands through a temporary file so a failed jq never truncates the checklist.
save() { # save <file> <tmp>: move a finished rewrite into place
  mv "$2" "$1"
}

require_item() {
  local file
  file=$(current)
  jq -e --arg id "$1" 'any(.items[]; .id == $id)' "${file}" >/dev/null || die "unknown item: $1"
}

cmd=${1:-}
[[ $# -gt 0 ]] && shift
case ${cmd} in
start)
  [[ $# -eq 3 ]] || die "usage: start <template.json> <subject> <session-id>"
  template=$1 subject=$2 session=$3
  [[ -f ${template} ]] || die "template not found: ${template}"
  [[ -n ${session} ]] || die "a session id is required so the gate only checks this session"
  mkdir -p "${state_dir}"
  skill=$(jq -r '.skill' "${template}")
  file="${state_dir}/${skill}--${subject//[^A-Za-z0-9._-]/_}.json"
  # One active checklist per project: starting another would silently drop the
  # gate on an unfinished one. Restarting the same checklist is fine.
  if [[ -f ${active} ]]; then
    previous=$(<"${active}")
    previous_status=""
    [[ ! -f ${previous} ]] || previous_status=$(jq -r '.status // ""' "${previous}")
    if [[ ${previous} != "${file}" && ${previous_status} == in_progress ]]; then
      die "${previous#"${root}"/} is still in progress; finish it, or run: checklist.sh abort \"<the user's instruction>\""
    fi
  fi
  started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  template_dir=$(dirname "${template}")
  template_dir=$(cd "${template_dir}" && pwd) || die "cannot resolve ${template}"
  template_abs="${template_dir}/${template##*/}"
  jq --arg subject "${subject}" --arg session "${session}" --arg started "${started}" \
    --arg template "${template_abs#"${root}"/}" \
    '{skill, subject: $subject, session_id: $session, started: $started, status: "in_progress", template: $template,
      items: [.items[] | . + {state: "open", evidence: ""}]}' "${template}" >"${file}"
  printf '%s' "${file}" >"${active}"
  count=$(jq '.items | length' "${file}")
  printf 'started %s (%s items)\n' "${file#"${root}"/}" "${count}"
  ;;
check)
  [[ $# -eq 2 && -n $2 ]] || die "usage: check <item-id> <evidence>"
  require_item "$1"
  file=$(current)
  jq --arg id "$1" --arg ev "$2" '(.items[] | select(.id == $id)) |= (.state = "done" | .evidence = $ev)' \
    "${file}" >"${file}.tmp.$$" || die "cannot update ${file#"${root}"/}"
  save "${file}" "${file}.tmp.$$"
  printf 'done: %s\n' "$1"
  ;;
needs-user)
  [[ $# -eq 2 && -n $2 ]] || die "usage: needs-user <item-id> <question>"
  require_item "$1"
  file=$(current)
  jq --arg id "$1" --arg q "$2" '(.items[] | select(.id == $id)) |= (.state = "needs_user" | .evidence = $q)' \
    "${file}" >"${file}.tmp.$$" || die "cannot update ${file#"${root}"/}"
  save "${file}" "${file}.tmp.$$"
  printf 'needs user: %s\n' "$1"
  ;;
abort)
  [[ $# -eq 1 && -n $1 ]] || die "usage: abort <the user's instruction, quoted>"
  file=$(current)
  jq --arg why "$1" '.status = "aborted" | .aborted_because = $why' \
    "${file}" >"${file}.tmp.$$" || die "cannot update ${file#"${root}"/}"
  save "${file}" "${file}.tmp.$$"
  rm -f "${active}"
  printf 'aborted\n'
  ;;
status)
  file=$(current)
  jq -r '"\(.skill) — \(.subject) — \(.status)", (.items[] | "  [\(if .state == "done" then "x" elif .state == "needs_user" then "?" else " " end)] \(.id): \(.text)\(if .evidence != "" then " — " + .evidence else "" end)")' "${file}"
  ;;
*)
  sed -n '2,18p' "$0" >&2
  exit 2
  ;;
esac
