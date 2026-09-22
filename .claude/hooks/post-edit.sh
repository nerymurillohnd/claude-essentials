#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|Bash): for plugin files whose runtime content
# differs from the tagged version, reminds once per session that users only
# receive changes after a version bump. It never formats, lints or type-checks:
# that is `make lint-staged` in the commit guard and `make check` (maintainer's
# decision, 2026-09-22).
# Edit/Write: checks tool_input.file_path. Bash: checks every modified or new
# (non-ignored) repo file not older than the stamp bash-stamp.sh wrote when the
# command started, so edits made through shell commands get the same reminder.
# Read-only apart from its own reminder state, which is keyed by session.
# See docs/decisions/adr-0002-project-hooks.md.
set -euo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/plugin-paths.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/plugin-paths.sh"

command -v jq >/dev/null 2>&1 || exit 0

readonly MAX_BASH_FILES=50

input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="$(cd "${root:-${PWD}}" && pwd -P)"
tool_name="$(jq -r '.tool_name // empty' <<<"${input}")"
session_id="$(jq -r '.session_id // empty' <<<"${input}")"
state_dir="${root}/.claude/.cache/hooks"

context=""
# Set by check_file for the file being processed.
rel=""

add_context() { context="${context:+${context}
}$1"; }

plugin_reminder() {
  local name rest manifest version runtime state_file
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

# check_file <path>: adds the plugin version reminder for one file inside the
# project (anything outside it is skipped).
check_file() {
  local path="$1" dir abs reminder
  [[ -f "${path}" ]] || return 0
  dir="$(cd "$(dirname "${path}")" && pwd -P)"
  abs="${dir}/${path##*/}"
  case "${abs}" in
  "${root}"/*) rel="${abs#"${root}"/}" ;;
  *) return 0 ;;
  esac
  reminder="$(plugin_reminder)"
  if [[ -n "${reminder}" ]]; then
    add_context "${reminder}"
  fi
}

# Prints repo files (modified tracked + new non-ignored) not older than $1.
# `! stamp -nt file` keeps same-second changes, since bash 3.2 compares whole seconds.
changed_since_stamp() {
  local stamp="$1" file
  git -C "${root}" ls-files -z --modified --others --exclude-standard 2>/dev/null |
    while IFS= read -r -d '' file; do
      if [[ -f "${root}/${file}" && ! "${stamp}" -nt "${root}/${file}" ]]; then
        printf '%s\n' "${root}/${file}"
      fi
    done
}

if [[ "${tool_name}" == Bash ]]; then
  stamp="${state_dir}/bash-stamp-${session_id//[^A-Za-z0-9_-]/_}"
  [[ -n "${session_id}" && -f "${stamp}" ]] || exit 0
  changed="$(changed_since_stamp "${stamp}" | sort -u)"
  count=0
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    count=$((count + 1))
    if ((count > MAX_BASH_FILES)); then
      add_context "More than ${MAX_BASH_FILES} files changed in this Bash command; only the first ${MAX_BASH_FILES} were checked — run \`make versions\` for the rest."
      break
    fi
    check_file "${path}"
  done <<<"${changed}"
else
  file_path="$(jq -r '.tool_input.file_path // empty' <<<"${input}")"
  [[ -n "${file_path}" ]] || exit 0
  check_file "${file_path}"
fi

[[ -n "${context}" ]] || exit 0

jq -n --arg ctx "${context}" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
