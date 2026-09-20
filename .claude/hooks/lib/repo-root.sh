#!/usr/bin/env bash
# Which checkout a hook should act on.
#
# When Claude works inside a git worktree, the two paths a hook receives stop
# agreeing: `${CLAUDE_PROJECT_DIR}` keeps pointing at the checkout the session
# started from, while the hook input's `cwd` follows Claude into the worktree
# (https://code.claude.com/docs/en/worktrees, "Hook paths don't follow the
# worktree"). Picking the wrong one makes a gate inspect a tree nobody is
# changing, so the two uses get two functions.
#
# Sourced, never executed. Both functions always succeed and always print a
# path: an unusable directory falls back to ${PWD} rather than returning
# non-zero, so callers need no `||` guard (which would disable `set -e` inside
# the function, ShellCheck SC2310).

# _abs <dir>
# The directory's physical path, or ${PWD} when it can't be entered.
_abs() {
  local dir=${1:-} out=""
  out=$(cd "${dir:-${PWD}}" 2>/dev/null && pwd -P) || out=""
  printf '%s' "${out:-${PWD}}"
}

# session_tree <hook-input-json>
# The checkout Claude is working in: what a gate must read, lint, and test,
# because it holds the changes the tool call is about.
session_tree() {
  local input=${1:-} dir=""
  if [[ -n ${input} ]]; then
    dir=$(jq -r '.cwd // empty' <<<"${input}" 2>/dev/null) || dir=""
  fi
  _abs "${dir:-${CLAUDE_PROJECT_DIR:-${PWD}}}"
}

# project_dir <hook-input-json>
# The checkout the session started from: where project-scoped state belongs,
# since a subagent's worktree is removed once it finishes and anything written
# inside it goes with it.
project_dir() {
  local input=${1:-} dir=${CLAUDE_PROJECT_DIR:-}
  if [[ -z ${dir} && -n ${input} ]]; then
    dir=$(jq -r '.cwd // empty' <<<"${input}" 2>/dev/null) || dir=""
  fi
  _abs "${dir}"
}
