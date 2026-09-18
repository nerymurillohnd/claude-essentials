#!/usr/bin/env bash
# PreToolUse hook (Bash): records when a Bash command starts, so post-edit.sh can
# lint exactly the files that command changed (Bash edits carry no file_path).
# Idempotent: rewrites one per-session stamp file. See ADR-0002 (amendment).
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="$(cd "${root:-${PWD}}" && pwd -P)"
session_id="$(jq -r '.session_id // empty' <<<"${input}")"
[[ -n "${session_id}" ]] || exit 0

state_dir="${root}/.claude/.cache/hooks"
mkdir -p "${state_dir}"
touch "${state_dir}/bash-stamp-${session_id//[^A-Za-z0-9_-]/_}"
