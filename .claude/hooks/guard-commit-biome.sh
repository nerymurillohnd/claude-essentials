#!/usr/bin/env bash
# PreToolUse hook (Bash): before Claude runs `git commit`, checks every file the
# commit could include with Biome at gate strictness (--error-on-warnings) and
# denies the commit when anything fails. The set is staged + modified + untracked
# (non-ignored) files, because at PreToolUse time a chained `git add … && git
# commit` hasn't staged anything yet. Read-only: never writes or stages files.
# CI remains the authority. See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
command_text="$(jq -r '.tool_input.command // empty' <<<"${input}")"
# `git commit` as a command, optionally with global options such as -C <dir>.
[[ "${command_text}" =~ (^|[;&|[:space:]])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+commit([[:space:]]|$) ]] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="$(cd "${root:-${PWD}}" && pwd -P)"
biome="${root}/node_modules/.bin/biome"
[[ -x "${biome}" ]] || exit 0

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

# Each git listing runs on its own so a failure can't be masked by a pipeline;
# failing closed keeps an unreadable repo state from waving the commit through.
state_dir="${root}/.claude/.cache/hooks"
mkdir -p "${state_dir}"
staged="$(mktemp "${state_dir}/commit-staged.XXXXXX")"
dirty="$(mktemp "${state_dir}/commit-dirty.XXXXXX")"
trap 'rm -f "${staged}" "${dirty}"' EXIT
git -C "${root}" diff --cached --name-only -z --diff-filter=ACMR >"${staged}" 2>/dev/null ||
  deny "Could not list staged files (git diff --cached failed); not committing unchecked files."
git -C "${root}" ls-files --modified --others --exclude-standard -z >"${dirty}" 2>/dev/null ||
  deny "Could not list modified files (git ls-files failed); not committing unchecked files."

files=()
while IFS= read -r -d '' file; do
  if [[ -f "${root}/${file}" ]]; then files+=("${file}"); fi
done <"${staged}"
while IFS= read -r -d '' file; do
  if [[ -f "${root}/${file}" ]]; then files+=("${file}"); fi
done <"${dirty}"
[[ ${#files[@]} -gt 0 ]] || exit 0

if out="$(cd "${root}" && "${biome}" check --error-on-warnings --no-errors-on-unmatched \
  --reporter=concise "${files[@]}" 2>&1)"; then
  exit 0
fi

deny "Biome fails on files this commit could include (staged, modified, or untracked) at gate strictness (--error-on-warnings). Fix them — \`npm run biome:fix\` applies safe fixes — then commit again:
${out:0:6000}"
