#!/usr/bin/env bash
# Stop hook: when Svelte files changed and that state was not checked yet, run the
# project's own svelte-check and send its errors back to Claude (exit 2 keeps it working).
# svelte-check has no single-file mode by design (a renamed prop breaks other files), so
# it checks the whole project; per-file diagnostics come from the language server.
# Silent when there is nothing to check, no git, no installed svelte-check, or the same
# state was already checked: it never downloads or installs anything.
set -euo pipefail

root="${CLAUDE_PROJECT_DIR:-}"
data="${CLAUDE_PLUGIN_DATA:-}"
[[ -n "${root}" && -n "${data}" ]] || exit 0
cd "${root}" 2>/dev/null || exit 0

bin="${root}/node_modules/.bin"
[[ -x "${bin}/svelte-check" ]] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
# Without a first commit every file looks new, so nothing tells this session's changes apart.
git rev-parse --verify --quiet HEAD >/dev/null || exit 0

paths=('*.svelte' '*.svelte.ts' '*.svelte.js')
changes="$(git status --porcelain -- "${paths[@]}" 2>/dev/null || true)"
[[ -n "${changes}" ]] || exit 0

# One check per state of the changed Svelte files: their status, tracked diff and the
# content of new files. A state already checked, clean or not, stays silent, so errors
# that predate the session cannot hold Claude in a loop.
fingerprint="$(
  {
    printf '%s\n' "${changes}"
    git diff HEAD -- "${paths[@]}" 2>/dev/null || true
    git ls-files --others --exclude-standard -z -- "${paths[@]}" 2>/dev/null |
      xargs -0 cat 2>/dev/null || true
  } | cksum
)"
project="$(printf '%s' "${root}" | cksum | cut -d ' ' -f 1)"
stamp="${data}/checked-${project}"
checked=""
[[ -f "${stamp}" ]] && checked="$(cat "${stamp}" || true)"
[[ "${checked}" == "${fingerprint}" ]] && exit 0
mkdir -p "${data}"
printf '%s' "${fingerprint}" >"${stamp}"

# SvelteKit generates the types svelte-check reads; without a sync it reports false errors.
if [[ -x "${bin}/svelte-kit" ]]; then
  "${bin}/svelte-kit" sync >/dev/null 2>&1 || true
fi

args=(--output machine --threshold error)
[[ -f tsconfig.json ]] && args+=(--tsconfig ./tsconfig.json)
status=0
output="$("${bin}/svelte-check" "${args[@]}" 2>&1)" || status=$?
[[ "${status}" -eq 0 ]] && exit 0

errors="$(printf '%s\n' "${output}" | grep ' ERROR ' | cut -d ' ' -f 3- || true)"
[[ -n "${errors}" ]] || errors="$(printf '%s\n' "${output}" | tail -n 20)"
{
  echo "svelte-development: svelte-check failed after the Svelte changes in this session (it checks the whole project; positions are line:column):"
  printf '%s\n' "${errors}" | head -c 6000
  echo
  echo "Fix the errors your changes caused, confirm the changed .svelte files with the LSP tool diagnostics and findReferences, then run the Svelte autofixer on each changed component. Errors in files you did not touch may predate this session: report them instead of fixing them unasked."
} >&2
exit 2
