#!/usr/bin/env bash
# Stop hook: when Svelte files changed and that state was not checked yet, run the
# project's own svelte-check and send its errors back to Claude (exit 2 keeps it working).
# svelte-check is the only command it runs, and it runs in every Svelte project, with or
# without SvelteKit. Nothing here runs a
# generator: generating a project's types is the project's own command, behind a permission
# prompt, so a project whose types were never generated is reported, never fixed silently.
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

args=(--output machine --threshold error)
[[ -f tsconfig.json ]] && args+=(--tsconfig ./tsconfig.json)
status=0
output="$("${bin}/svelte-check" "${args[@]}" 2>&1)" || status=$?
[[ "${status}" -eq 0 ]] && exit 0

lines="$(printf '%s\n' "${output}" | grep ' ERROR ' || true)"
# A SvelteKit project extends a TypeScript configuration that SvelteKit generates, and this
# hook runs no generator, so in a project whose types were never generated the configuration
# cannot be read: every error lands in that JSON configuration and not one source file is
# checked. The code is then unchecked, not broken, so Claude is asked to run the project
# check, which generates the types first and goes through a permission prompt.
# The condition is the absence of any error outside a JSON file, because what the generated
# path is called, and whether the message names it at all, follow the SvelteKit major: one
# reports it at tsconfig.json as a file it cannot read under .svelte-kit, the next as a
# missing "$app/tsconfig", generated under node_modules instead. A folder test would also
# refuse to check a synced project that generates its output elsewhere (a custom outDir).
# grep -v, never grep -q: a -q exits on its first match, the SIGPIPE it sends back fails the
# pipeline under pipefail, and the condition would invert.
source_errors="$(printf '%s\n' "${lines}" | grep -v ' ERROR "[^"]*\.json"' || true)"
if [[ -n "${lines}" && -z "${source_errors}" ]]; then
  {
    echo "svelte-development: svelte-check could not read the project TypeScript configuration, so it checked no source file and reported nothing about the Svelte files changed in this session:"
    printf '%s\n' "${lines}" | cut -d ' ' -f 3- | head -c 2000
    echo
    echo "In a SvelteKit project that configuration extends a file SvelteKit generates, and this hook runs no generators. Run the project check yourself (the check script in package.json, which generates the types first), then fix what it reports for the files you changed. Do not edit the configuration or any generated file to satisfy this message."
  } >&2
  exit 2
fi

errors="$(printf '%s\n' "${lines}" | cut -d ' ' -f 3- || true)"
[[ -n "${errors}" ]] || errors="$(printf '%s\n' "${output}" | tail -n 20)"
{
  echo "svelte-development: svelte-check failed after the Svelte changes in this session (it checks the whole project; positions are line:column):"
  printf '%s\n' "${errors}" | head -c 6000
  echo
  echo "Fix the errors your changes caused, confirm the changed .svelte files with the LSP tool diagnostics and findReferences, then run the Svelte autofixer on each changed component. Errors in files you did not touch may predate this session: report them instead of fixing them unasked. An error that names .svelte-kit, \$types or \$app is SvelteKit generated output, not the code: run the project check yourself, which generates it first, instead of editing files to satisfy it."
} >&2
exit 2
