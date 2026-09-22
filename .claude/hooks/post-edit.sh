#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|Bash): formats and lints changed files — shfmt +
# ShellCheck for shell scripts, `make fix-file` for everything else (Ruff and
# basedpyright on maintainer Python, the canonical form on JSON, the byte rules
# on any other text). Both branches apply the gate's own strictness, so a defect
# is reported next to the edit rather than minutes later in an unrelated run.
# Edit/Write: lints tool_input.file_path. Bash: lints every modified or new
# (non-ignored) repo file not older than the stamp bash-stamp.sh wrote when the
# command started, so edits made through shell commands get the same gate.
# For plugin files whose runtime content differs from the tagged version, it
# reminds once per session that users only receive changes after a version bump.
# Idempotent: formatting converges; the reminder state is keyed by session.
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
block_reason=""
# Set by lint_file for the file being processed.
abs=""
rel=""
dir=""

add_context() { context="${context:+${context}
}$1"; }

add_block() { block_reason="${block_reason:+${block_reason}

}$1"; }

# Prints "shell" for .sh files or files with an sh/bash shebang, else "text".
file_kind() {
  local shebang=""
  if [[ "${abs}" == *.sh ]]; then
    echo shell
    return 0
  fi
  IFS= read -r shebang <"${abs}" || true
  if [[ "${shebang}" =~ ^#!.*[/[:space:]](ba)?sh([[:space:]]|$) ]]; then echo shell; else echo text; fi
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
    add_block "ShellCheck reported issues in ${rel} (fix them in code; don't disable checks without a narrow, justified inline directive):
${out:0:4000}"
  fi
}

# Everything that is not shell goes through the pipeline's own single-file writer,
# so the editor, this hook and `make lint` can never disagree about one file.
# A missing project environment is reported, never blocked on: the edit itself is
# fine, and telling the maintainer to run `make setup` is the useful answer.
lint_text() {
  local out
  if [[ ! -x "${root}/.venv/bin/python" ]]; then
    add_context "The project environment is missing (${root}/.venv/bin/python) — ${rel} was not checked. Run \`make setup\`."
    return 0
  fi
  if ! out="$(cd "${root}" && make -s fix-file FILE="${rel}" 2>&1)"; then
    add_block "\`make fix-file FILE=${rel}\` reports what it could not rewrite (fix it in code; never silence it):
${out:0:4000}"
  fi
}

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

# lint_file <path>: lints one file inside the project (anything outside it is
# skipped) and adds the plugin version reminder when relevant.
lint_file() {
  local path="$1" kind reminder
  [[ -f "${path}" ]] || return 0
  dir="$(cd "$(dirname "${path}")" && pwd -P)"
  abs="${dir}/${path##*/}"
  case "${abs}" in
  "${root}"/*) rel="${abs#"${root}"/}" ;;
  *) return 0 ;;
  esac
  kind="$(file_kind)"
  if [[ "${kind}" == shell ]]; then
    lint_shell
  else
    lint_text
  fi
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
      add_context "More than ${MAX_BASH_FILES} files changed in this Bash command; only the first ${MAX_BASH_FILES} were linted — run \`make lint\` for the rest."
      break
    fi
    lint_file "${path}"
  done <<<"${changed}"
else
  file_path="$(jq -r '.tool_input.file_path // empty' <<<"${input}")"
  [[ -n "${file_path}" ]] || exit 0
  lint_file "${file_path}"
fi

[[ -n "${block_reason}" || -n "${context}" ]] || exit 0

jq -n --arg reason "${block_reason}" --arg ctx "${context}" '
  (if $reason != "" then {decision: "block", reason: $reason} else {} end)
  + (if $ctx != "" then {hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}} else {} end)
'
