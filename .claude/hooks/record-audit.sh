#!/usr/bin/env bash
# SubagentStop hook (matcher: repo-auditor): records the auditor's own verdict
# for the head it audited, so /pr-delivery can verify it instead of trusting a
# hand-written record. Reads the "HEAD: <sha>" and "VERDICT: PASS|FAIL" lines
# from the subagent's final message (falling back to its transcript) and writes
# .claude/state/audits/<sha>.json. Never blocks; a report without both lines
# records nothing and says so. Idempotent: one file per audited head.
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat) || exit 0
agent=$(jq -r '.agent_type // empty' <<<"${input}" 2>/dev/null) || agent=""
[[ ${agent} == repo-auditor ]] || exit 0

root=${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}
root=$(cd "${root:-${PWD}}" && pwd -P) || exit 0

text=$(jq -r '.last_assistant_message // empty' <<<"${input}")
if ! grep -Eq '^VERDICT: (PASS|FAIL)' <<<"${text}"; then
  transcript=$(jq -r '.agent_transcript_path // empty' <<<"${input}")
  transcript=${transcript/#\~/${HOME}}
  if [[ -f ${transcript} ]]; then
    text=$(jq -r 'select(.type == "assistant") | .message.content[]? | select(.type == "text") | .text' "${transcript}" 2>/dev/null) || text=""
  fi
fi

head=$(grep -Eo '^HEAD: [0-9a-f]{40}' <<<"${text}" | tail -1 | cut -d' ' -f2) || head=""
verdict=$(grep -Eo '^VERDICT: (PASS|FAIL)' <<<"${text}" | tail -1 | cut -d' ' -f2) || verdict=""

if [[ -z ${head} || -z ${verdict} ]]; then
  jq -cn '{systemMessage: "record-audit: the repo-auditor report has no \"HEAD: <sha>\" and \"VERDICT:\" lines, so no audit was recorded."}'
  exit 0
fi

dir="${root}/.claude/state/audits"
mkdir -p "${dir}" || exit 0
jq -n --arg h "${head}" --arg v "${verdict}" '{head: $h, verdict: $v}' >"${dir}/${head}.json" || exit 0
jq -cn --arg m "record-audit: repo-auditor ${verdict} recorded for ${head}" '{systemMessage: $m}'
exit 0
