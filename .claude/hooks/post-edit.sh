#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): formats and lints the edited file — shfmt +
# ShellCheck for shell scripts, `biome check --write` for everything else — and,
# for edits under plugins/<name>/ that leave runtime files different from the tagged version,
# reminds once per session that users only receive changes after a version bump.
# Idempotent: formatting converges; the reminder state is keyed by session.
# See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/plugin-paths.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/plugin-paths.sh"

command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="$(cd "${root:-${PWD}}" && pwd -P)"
file_path="$(jq -r '.tool_input.file_path // empty' <<<"${input}")"
session_id="$(jq -r '.session_id // empty' <<<"${input}")"
[[ -n "${file_path}" && -f "${file_path}" ]] || exit 0

dir="$(dirname "${file_path}")"
dir="$(cd "${dir}" && pwd -P)"
abs="${dir}/${file_path##*/}"
case "${abs}" in
"${root}"/*) rel="${abs#"${root}"/}" ;;
*) exit 0 ;;
esac
case "/${rel}/" in
*/node_modules/*) exit 0 ;;
*) ;;
esac

context=""
block_reason=""

add_context() { context="${context:+${context}
}$1"; }

# Prints "shell" for .sh files or files with an sh/bash shebang, else "biome".
file_kind() {
  local shebang=""
  if [[ "${abs}" == *.sh ]]; then
    echo shell
    return 0
  fi
  IFS= read -r shebang <"${abs}" || true
  if [[ "${shebang}" =~ ^#!.*[/[:space:]](ba)?sh([[:space:]]|$) ]]; then echo shell; else echo biome; fi
}

lint_shell() {
  local out
  if command -v shfmt >/dev/null 2>&1; then
    shfmt -w "${abs}" >/dev/null 2>&1 || true
  else
    add_context "shfmt is not installed — ${rel} was not formatted (brew install shfmt)."
  fi
  if ! command -v shellcheck >/dev/null 2>&1; then
    add_context "ShellCheck is not installed — ${rel} was not linted (brew install shellcheck)."
    return 0
  fi
  if ! out="$(cd "${dir}" && shellcheck -x -f gcc "${abs}" 2>&1)"; then
    block_reason="ShellCheck reported issues in ${rel} (fix them in code; don't disable checks without a narrow, justified inline directive):
${out:0:4000}"
  fi
}

lint_biome() {
  local out biome="${root}/node_modules/.bin/biome"
  if [[ ! -x "${biome}" ]]; then
    add_context "Biome is not installed locally (node_modules missing) — run \`npm install\`."
    return 0
  fi
  if ! out="$(cd "${root}" && "${biome}" check --write --no-errors-on-unmatched --reporter=concise "${abs}" 2>&1)"; then
    block_reason="Biome reported issues it could not auto-fix in ${rel}:
${out:0:4000}"
  fi
}

kind="$(file_kind)"
if [[ "${kind}" == shell ]]; then
  lint_shell
else
  lint_biome
fi

plugin_reminder() {
  local name rest manifest version runtime state_dir state_file
  [[ "${rel}" == plugins/*/* ]] || return 0
  rest="${rel#plugins/}"
  name="${rest%%/*}"
  manifest="${root}/plugins/${name}/.claude-plugin/plugin.json"
  [[ -f "${manifest}" ]] || return 0
  version="$(jq -r '.version // empty' "${manifest}" 2>/dev/null)" || return 0
  [[ -n "${version}" ]] || return 0
  git -C "${root}" rev-parse -q --verify "refs/tags/${name}--v${version}" >/dev/null 2>&1 || return 0
  runtime="$(plugin_runtime_change "${root}" "${name}" "${name}--v${version}")"
  [[ -n "${runtime}" ]] || return 0

  state_dir="${root}/.claude/.cache/hooks"
  state_file="${state_dir}/version-reminders.json"
  mkdir -p "${state_dir}"
  if ! jq -e --arg s "${session_id}" --arg n "${name}" \
    '.session == $s and (.plugins | index($n))' "${state_file}" >/dev/null 2>&1; then
    jq -n --arg s "${session_id}" --arg n "${name}" --slurpfile old <(cat "${state_file}" 2>/dev/null || true) '
      ($old[0] // {}) as $o
      | {session: $s, plugins: ((if $o.session == $s then $o.plugins else [] end) + [$n])}
    ' >"${state_file}.tmp" && mv "${state_file}.tmp" "${state_file}"
    printf '%s' "plugins/${name} has runtime changes since ${name}--v${version} (first: ${runtime}). Installed users will not receive them until plugin.json's version is bumped (semver, see docs/contributing/versioning.md) with a matching \"## [X.Y.Z] - YYYY-MM-DD\" CHANGELOG.md entry; version-check enforces this in CI and the Tag plugin versions workflow tags the new version on merge. README/docs/LICENSE/CHANGELOG and plugin.json metadata need no bump."
  fi
}

reminder="$(plugin_reminder)"
if [[ -n "${reminder}" ]]; then
  context="${context:+${context}
}${reminder}"
fi

[[ -n "${block_reason}" || -n "${context}" ]] || exit 0

jq -n --arg reason "${block_reason}" --arg ctx "${context}" '
  (if $reason != "" then {decision: "block", reason: $reason} else {} end)
  + (if $ctx != "" then {hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}} else {} end)
'
