#!/usr/bin/env bash
# SubagentStop hook (matcher: repo-auditor): records the auditor's own verdict
# for the head it audited, so /pr-delivery can verify it instead of trusting a
# hand-written record. Reads the "HEAD: <sha>" and "VERDICT: PASS|FAIL" lines
# from the subagent's final message (falling back to its transcript) and writes
# .claude/state/audits/<sha>.json. Never blocks; a report without both lines
# records nothing and says so. Idempotent: one file per audited head.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/repo-root.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/repo-root.sh"

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat) || exit 0
agent=$(jq -r '.agent_type // empty' <<<"${input}" 2>/dev/null) || agent=""
[[ ${agent} == repo-auditor ]] || exit 0

# Two different checkouts, on purpose (see lib/repo-root.sh): the auditor runs
# in the session's tree, which is a worktree when it was isolated there, but the
# record is state of the project, so it must outlive that worktree.
tree=$(session_tree "${input}")
root=$(project_dir "${input}")

text=$(jq -r '.last_assistant_message // empty' <<<"${input}")
if ! grep -Eq '^VERDICT: (PASS|FAIL)' <<<"${text}"; then
  transcript=$(jq -r '.agent_transcript_path // empty' <<<"${input}")
  transcript=${transcript/#\~/${HOME}}
  if [[ -f ${transcript} ]]; then
    # Text blocks, plus a SubagentHandback payload: from Claude Code 2.1.271 a
    # handing-back subagent delivers its report as that call's `message`, and
    # `last_assistant_message` then holds only its closing text.
    text=$(jq -r 'select(.type == "assistant") | .message.content[]? |
      if .type == "text" then .text
      elif .type == "tool_use" and .name == "SubagentHandback" then (.input.message // empty)
      else empty end' "${transcript}" 2>/dev/null) || text=""
  fi
fi

head=$(grep -Eo '^HEAD: [0-9a-f]{40}' <<<"${text}" | tail -1 | cut -d' ' -f2) || head=""
verdict=$(grep -Eo '^VERDICT: (PASS|FAIL)' <<<"${text}" | tail -1 | cut -d' ' -f2) || verdict=""

if [[ -z ${head} || -z ${verdict} ]]; then
  jq -cn '{systemMessage: "record-audit: the repo-auditor report has no \"HEAD: <sha>\" and \"VERDICT:\" lines, so no audit was recorded."}'
  exit 0
fi

# A verdict is only about a commit. With a dirty tree the audited content is not
# what `${head}` contains — on a branch with no commits of its own, `${head}` is
# main itself — so record nothing rather than a record pr-delivery would trust.
if ! dirty=$(git -C "${tree}" status --porcelain 2>/dev/null); then
  jq -cn '{systemMessage: "record-audit: git status failed, so the tree could not be checked and no audit was recorded."}'
  exit 0
fi
if [[ -n ${dirty} ]]; then
  jq -cn '{systemMessage: "record-audit: the working tree has uncommitted changes, so the audit does not describe the commit at HEAD. Commit the work and audit again; nothing was recorded."}'
  exit 0
fi

dir="${root}/.claude/state/audits"
mkdir -p "${dir}" || exit 0
jq -n --arg h "${head}" --arg v "${verdict}" '{head: $h, verdict: $v}' >"${dir}/${head}.json" || exit 0
jq -cn --arg m "record-audit: repo-auditor ${verdict} recorded for ${head}" '{systemMessage: $m}'
exit 0
