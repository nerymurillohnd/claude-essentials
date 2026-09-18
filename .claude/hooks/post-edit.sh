#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): runs `biome check --write` on the edited file
# and, for edits under plugins/<name>/ whose current version is already tagged,
# reminds once per session that users only receive changes after a version bump.
# Idempotent: formatting converges; the reminder state is keyed by session.
# See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

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

biome="${root}/node_modules/.bin/biome"
if [[ -x "${biome}" ]]; then
  if ! biome_out="$(cd "${root}" && "${biome}" check --write --no-errors-on-unmatched --reporter=concise "${abs}" 2>&1)"; then
    block_reason="Biome reported issues it could not auto-fix in ${rel}:
${biome_out:0:4000}"
  fi
else
  context="Biome is not installed locally (node_modules missing) — run \`npm install\`."
fi

plugin_reminder() {
  local name rest manifest version state_dir state_file
  [[ "${rel}" == plugins/*/* ]] || return 0
  rest="${rel#plugins/}"
  name="${rest%%/*}"
  manifest="${root}/plugins/${name}/.claude-plugin/plugin.json"
  [[ -f "${manifest}" ]] || return 0
  version="$(jq -r '.version // empty' "${manifest}" 2>/dev/null)" || return 0
  [[ -n "${version}" ]] || return 0
  git -C "${root}" rev-parse -q --verify "refs/tags/${name}--v${version}" >/dev/null 2>&1 || return 0

  state_dir="${root}/.claude/.cache/hooks"
  state_file="${state_dir}/version-reminders.json"
  mkdir -p "${state_dir}"
  if ! jq -e --arg s "${session_id}" --arg n "${name}" \
    '.session == $s and (.plugins | index($n))' "${state_file}" >/dev/null 2>&1; then
    jq -n --arg s "${session_id}" --arg n "${name}" --slurpfile old <(cat "${state_file}" 2>/dev/null || true) '
      ($old[0] // {}) as $o
      | {session: $s, plugins: ((if $o.session == $s then $o.plugins else [] end) + [$n])}
    ' >"${state_file}.tmp" && mv "${state_file}.tmp" "${state_file}"
    printf '%s' "plugins/${name} pins \"version\": \"${version}\" in plugin.json and ${name}--v${version} is already tagged. Claude Code uses that version as the update cache key, so installed users will not receive this change until plugin.json's version is bumped (semver) with a CHANGELOG.md entry and the release is tagged with \`claude plugin tag plugins/${name}\`."
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
