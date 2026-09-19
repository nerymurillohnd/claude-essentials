#!/usr/bin/env bash
# Stop hook registered by maintenance skills (ADR-0002 amendment): while this
# session's checklist (lib/checklist.sh) is in progress, Claude can't end the
# turn until every item is done with evidence and every verify command passes.
# Items waiting on the user ("needs_user") let the turn end so the user can
# answer. Exit 2 blocks the stop and shows stderr to Claude; Claude Code lifts
# the block after eight consecutive blocks without progress, so a genuinely
# stuck checklist cannot loop forever.
set -uo pipefail

root=${CLAUDE_PROJECT_DIR:-$(pwd)}
state_dir="${root}/.claude/state/checklists"
active="${state_dir}/.active"

input=$(cat) || input=""
[[ -f ${active} ]] || exit 0
command -v jq >/dev/null 2>&1 || exit 0
file=$(<"${active}")
[[ -f ${file} ]] || exit 0

session=$(printf '%s' "${input}" | jq -r '.session_id // ""' 2>/dev/null) || session=""
owner=$(jq -r '.session_id // ""' "${file}" 2>/dev/null) || owner=""
status=$(jq -r '.status // ""' "${file}" 2>/dev/null) || status=""
# Another session's checklist, or a finished one, never blocks this session.
[[ ${status} == in_progress && -n ${session} && ${session} == "${owner}" ]] || exit 0

open=$(jq -r '.items[] | select(.state == "open" or (.state == "done" and .evidence == "")) | "- \(.id): \(.text)"' "${file}")
waiting=$(jq -r '.items[] | select(.state == "needs_user") | "- \(.id): \(.evidence)"' "${file}")

if [[ -n ${open} ]]; then
  {
    printf 'Checklist %s is not complete. Finish these items (record each with checklist.sh check <id> "<evidence>"), or ask the user and mark it with checklist.sh needs-user:\n%s\n' \
      "${file#"${root}"/}" "${open}"
    [[ -z ${waiting} ]] || printf 'Waiting on the user:\n%s\n' "${waiting}"
  } >&2
  exit 2
fi
if [[ -n ${waiting} ]]; then
  exit 0 # everything else is done; the user must answer before the rest can finish
fi

# Every item is done: run the verify commands before letting the turn end. They
# come from the committed template, never from the editable state file, so a
# verification can't be weakened in place.
failures=""
template=$(jq -r '.template // ""' "${file}") || template=""
source_file="${root}/${template}"
if [[ -z ${template} || ! -f ${source_file} ]]; then
  printf 'Checklist %s has no readable template (%s); restart it with checklist.sh start.\n' \
    "${file#"${root}"/}" "${template:-none}" >&2
  exit 2
fi
verifies=$(jq -r '.items[] | select(.verify != null) | [.id, .verify] | @tsv' "${source_file}") || verifies=""
while IFS=$'\t' read -r id verify; do
  [[ -n ${verify} ]] || continue
  if ! out=$(cd "${root}" && bash -c "${verify}" 2>&1); then
    tail_out=$(printf '%s\n' "${out}" | tail -n 15) || tail_out=""
    failures+="- ${id}: \`${verify}\` failed:"$'\n'"${tail_out}"$'\n'
  fi
done <<<"${verifies}"

if [[ -n ${failures} ]]; then
  printf 'Checklist %s: items are marked done but their verification fails. Fix and re-check them:\n%s' \
    "${file#"${root}"/}" "${failures}" >&2
  jq '(.items[] | select(.verify != null)) |= (.state = "open")' "${file}" >"${file}.tmp.$$" && mv "${file}.tmp.$$" "${file}"
  exit 2
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# shellcheck disable=SC2016 # $at is a jq variable
jq --arg at "${finished}" '.status = "complete" | .completed = $at' "${file}" >"${file}.tmp.$$" &&
  mv "${file}.tmp.$$" "${file}"
rm -f "${active}"
exit 0
