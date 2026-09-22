#!/usr/bin/env bash
# PreToolUse hook (Bash): before Claude runs `git commit`, runs the staged half
# of the gate over every file the commit could include — staged, modified and
# untracked — and denies the commit when anything fails. The set is wider than
# the index on purpose: at PreToolUse time a chained `git add … && git commit`
# has staged nothing yet.
#
# `make lint-staged` is the one command; what it checks lives in
# scripts/lint/lint_files.py (Ruff format and lint plus basedpyright on the
# Python, ShellCheck and shfmt on the shell, canonical JSON, text bytes).
#
# Fails closed. An unreadable git state, a missing project environment or a
# failing check all deny, because a guard that waves a commit through when it
# cannot check it is worse than no guard. Read-only: it never writes or stages.
# The escape hatch, when the hook itself is broken, is to commit from a terminal
# outside Claude Code. See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/repo-root.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/repo-root.sh"

# Without jq the hook can neither read its input nor express a decision, so it
# steps aside — the same choice every other hook here makes, and CI still holds.
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
command_text="$(jq -r '.tool_input.command // empty' <<<"${input}")"
# `git commit` as a command, optionally with global options such as -C <dir>.
[[ "${command_text}" =~ (^|[;&|[:space:]])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+commit([[:space:]]|$) ]] || exit 0

# The tree holding the files this commit would include: the worktree when Claude
# is in one, not the checkout the session started from. See lib/repo-root.sh.
root="$(session_tree "${input}")"

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

git -C "${root}" rev-parse --git-dir >/dev/null 2>&1 ||
  deny "Commit refused: ${root} is not a git working tree, so the staged files could not be checked."
git -C "${root}" status --porcelain >/dev/null 2>&1 ||
  deny "Commit refused: git status failed, so the files this commit would include are unknown. Not committing unchecked files."

# Every recipe runs a binary from .venv. Without it `make lint-staged` would
# fail for a reason that has nothing to do with the commit, so say the real one.
[[ -x "${root}/.venv/bin/python" ]] ||
  deny "Commit refused: the project environment is missing (${root}/.venv/bin/python). The gate cannot run, so the commit is not checked. Run \`make setup\`, then commit again."

# The command the gate runs; tests replace it, Claude's command line cannot.
lint_cmd=${GUARD_COMMIT_LINT_CMD:-make -s lint-staged}
if ! out="$(cd "${root}" && bash -c "${lint_cmd}" 2>&1)"; then
  deny "Commit refused: the files this commit could include (staged, modified or untracked) fail \`make lint-staged\`. Fix them — \`make fix\` applies every safe rewrite — then commit again:
${out:0:3000}"
fi
exit 0
