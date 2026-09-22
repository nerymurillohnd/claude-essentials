#!/usr/bin/env bash
# Behavioral tests for shell-quality's plugin hook (hooks/shell-gate.sh):
# the guard's questions, the post-edit format/check, the Stop loop and its
# limit, and every degraded mode. Runs the handler under $BNV_TEST_BASH (set by
# the repo's `make test-slow` to each bash it finds, /bin/bash 3.2 included),
# else `bash`. shfmt and ShellCheck come from the repository's .venv, so the
# suite never downloads anything. It lives in the repository, not in the plugin.

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "${here}/../../../.." && pwd)
plugin="${repo}/plugins/shell-quality"
gate="${plugin}/hooks/shell-gate.sh"
hooks_json="${plugin}/hooks/hooks.json"
run_bash=${BNV_TEST_BASH:-bash}
venv_bin="${repo}/.venv/bin"

if [[ ! -x ${venv_bin}/shellcheck || ! -x ${venv_bin}/shfmt ]]; then
  printf "test-gate: shellcheck or shfmt is missing from %s; run \`make setup\`\n" "${venv_bin}" >&2
  exit 2
fi

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
export HOME="${work}/home" XDG_CONFIG_HOME="${work}/home/.config"
mkdir -p "${HOME}" "${XDG_CONFIG_HOME}"
unset SHELLCHECK_OPTS

pass=0
fail=0
skipped=0
ok() { pass=$((pass + 1)); }
bad() {
  fail=$((fail + 1))
  printf 'FAIL: %s\n' "$1" >&2
  if [[ $# -gt 1 ]]; then printf '      %s\n' "${2:0:600}" >&2; fi
  return 0
}

# ------------------------------------------------------------- helpers ---

proj="${work}/proj"
new_project() {
  rm -rf "${proj}" "${work}/data"
  mkdir -p "${proj}/bin"
}

INPUT=""
mk_edit() { INPUT=$(jq -cn --arg f "$1" --arg o "$2" --arg n "$3" '{file_path: $f, old_string: $o, new_string: $n}') || INPUT=""; }
mk_write() { INPUT=$(printf '%s' "$2" | jq -Rsc --arg f "$1" '{file_path: $f, content: .}') || INPUT=""; }
mk_bash() { INPUT=$(jq -cn --arg c "$1" '{command: $c}') || INPUT=""; }

OUT=""
RC=0
# fire EVENT TOOL SESSION ACTIVE [ENV...]: send INPUT as a full payload through
# stdin; a payload jq could not build fails the case instead of passing empty.
fire() {
  local ev=$1 tool=$2 s=$3 active=$4 p
  shift 4
  p=$(printf '%s' "${INPUT:-{\}}" | jq -c --arg e "${ev}" --arg t "${tool}" --arg s "${s}" --arg c "${proj}" --argjson a "${active}" \
    '{session_id: $s, transcript_path: "/tmp/t.jsonl", cwd: $c, hook_event_name: $e, tool_name: $t, tool_input: ., stop_hook_active: $a}') || p=""
  if [[ -z ${p} ]]; then
    bad "payload for ${ev} was not built"
    OUT=""
    RC=99
    return 0
  fi
  OUT=$(printf '%s' "${p}" | env CLAUDE_PLUGIN_DATA="${work}/data" PATH="${venv_bin}:${PATH}" "$@" "${run_bash}" "${gate}" "${ev}" 2>/dev/null)
  RC=$?
}

DECISION=""
REASON=""
BLOCK=""
CONTEXT=""
MESSAGE=""
parse() {
  DECISION=$(jq -r '.hookSpecificOutput.permissionDecision // empty' <<<"${OUT}" 2>/dev/null) || DECISION=""
  REASON=$(jq -r '.hookSpecificOutput.permissionDecisionReason // empty' <<<"${OUT}" 2>/dev/null) || REASON=""
  BLOCK=$(jq -r 'if .decision == "block" then .reason else empty end' <<<"${OUT}" 2>/dev/null) || BLOCK=""
  CONTEXT=$(jq -r '.hookSpecificOutput.additionalContext // empty' <<<"${OUT}" 2>/dev/null) || CONTEXT=""
  MESSAGE=$(jq -r '.systemMessage // empty' <<<"${OUT}" 2>/dev/null) || MESSAGE=""
}

expect_ask() {
  parse
  if [[ ${RC} -eq 0 && ${DECISION} == ask ]]; then ok; else bad "$1: expected ask" "${OUT}"; fi
}
expect_silent() {
  if [[ ${RC} -eq 0 && -z ${OUT} ]]; then ok; else bad "$1: expected no output" "${OUT}"; fi
}
expect_in() { # label haystack needle
  if [[ $2 == *"$3"* ]]; then ok; else bad "$1: expected '$3'" "$2"; fi
}

# --------------------------------------------------------- the wiring ---

if jq -e '.hooks.PreToolUse and .hooks.PostToolUse and .hooks.Stop' "${hooks_json}" >/dev/null; then ok; else
  bad "hooks.json wires PreToolUse, PostToolUse and Stop"
fi
ifs=$(jq -r '[.hooks.PostToolUse[].hooks[].if] | join(" ")' "${hooks_json}")
expect_in "PostToolUse covers .sh" "${ifs}" 'Edit(//**/*.sh)'
expect_in "PostToolUse covers .bash" "${ifs}" 'Edit(//**/*.bash)'
if grep -qE '(shfmt|SHFMT}")[^|]*[[:space:]]-(i|ci|bn|sr|kp|fn|ln)[[:space:]]' "${gate}"; then
  bad "shfmt gets no style flags, so .editorconfig stays authoritative"
else ok; fi

# ---------------------------------------------------------------- guard ---

new_project
printf "#!/usr/bin/env bash\necho \"\$1\"\n" >"${proj}/bin/a.sh"
mk_edit "${proj}/bin/a.sh" "echo \"\$1\"" "# shellcheck disable=SC2086
echo \$1"
fire guard Edit s1 false
expect_ask "adding a disable directive asks"
expect_in "the question names the script" "${REASON}" "bin/a.sh"
mk_edit "${proj}/bin/a.sh" "echo \"\$1\"" "printf '%s\\n' \"\$1\""
fire guard Edit s1 false
expect_silent "a plain edit is not questioned"
INPUT=$(jq -cn --arg f "${proj}/bin/a.sh" '{file_path: $f, edits: [{old_string: "# shellcheck disable=SC2034\nold=1", new_string: "old=1"}, {old_string: "echo $1", new_string: "# shellcheck disable=SC2086\necho $1"}]}') || INPUT=""
fire guard Edit s1 false
expect_ask "a batch that removes one directive and adds another still asks"
mk_write "${proj}/bin/b.sh" "$(printf '#!/bin/sh\n# shellcheck source=/dev/null\n. ./env\n')"
fire guard Write s1 false
expect_ask "writing source=/dev/null asks"
mk_write "${proj}/.shellcheckrc" 'disable=SC2086'
fire guard Write s1 false
expect_ask "writing .shellcheckrc asks"
printf 'root = true\n\n[*]\ncharset = utf-8\nindent_size = 2\n' >"${proj}/.editorconfig"
mk_edit "${proj}/.editorconfig" 'indent_size = 2' 'indent_size = 4'
fire guard Edit s1 false
expect_ask "changing an shfmt key in .editorconfig asks"
mk_edit "${proj}/.editorconfig" 'charset = utf-8' 'charset = latin1'
fire guard Edit s1 false
expect_silent "changing a key shfmt ignores is not questioned"
mk_bash "sed -i '' 's/^/# shellcheck disable=SC2086\n/' bin/a.sh"
fire guard Bash s1 false
expect_ask "a Bash write of a disable directive asks"
mk_bash 'echo disable=all >> .shellcheckrc'
fire guard Bash s1 false
expect_ask "a Bash write to .shellcheckrc asks"
mk_bash 'shellcheck bin/a.sh'
fire guard Bash s1 false
expect_silent "running ShellCheck is not questioned"

# ----------------------------------------------------------------- post ---

new_project
printf '#!/usr/bin/env bash\nif true; then\n        echo "x"\nfi\n' >"${proj}/bin/fmt.sh"
mk_edit "${proj}/bin/fmt.sh" '' ''
fire post Edit s2 false
parse
expect_in "a misformatted script is formatted and reported clean" "${MESSAGE}" "formatted, ShellCheck clean"
got=$(cat "${proj}/bin/fmt.sh")
expect_in "shfmt rewrote the indentation" "${got}" "$(printf '\techo "x"')"

printf "#!/usr/bin/env bash\necho \$1\n" >"${proj}/bin/unquoted.sh"
mk_edit "${proj}/bin/unquoted.sh" '' ''
fire post Edit s2 false
parse
expect_in "a finding blocks with its code" "${BLOCK}" "SC2086"
expect_in "the finding names the script relative to the project" "${BLOCK}" "
bin/unquoted.sh:2:"
if [[ ${BLOCK} == *"${proj}/bin/unquoted.sh:"* ]]; then
  bad "the finding does not repeat the absolute path" "${BLOCK}"
else ok; fi
expect_in "the user is told Claude is fixing it" "${MESSAGE}" "Claude is fixing them"

fire post Edit s2 false SHELLCHECK_OPTS="-e SC2086"
parse
expect_in "SHELLCHECK_OPTS is respected and named" "${MESSAGE}" "SHELLCHECK_OPTS=-e SC2086 applies"

printf 'disable=SC2086\n' >"${proj}/bin/.shellcheckrc"
fire post Edit s2 false
parse
expect_in "the nearest .shellcheckrc is honoured" "${MESSAGE}" "clean"
rm -f "${proj}/bin/.shellcheckrc"

printf '#!/usr/bin/env bash\nif then fi\n' >"${proj}/bin/broken.sh"
mk_edit "${proj}/bin/broken.sh" '' ''
fire post Edit s2 false
parse
expect_in "a parse error is reported for Claude" "${BLOCK}" "could not parse"

printf "#!/usr/bin/env zsh\necho \$1\n" >"${proj}/bin/z.sh"
mk_edit "${proj}/bin/z.sh" '' ''
fire post Edit s2 false
parse
expect_in "a zsh script is skipped and said so" "${MESSAGE}" "zsh script"

printf 'x = 1\n' >"${proj}/bin/tool.py"
mk_edit "${proj}/bin/tool.py" '' ''
fire post Edit s2 false
expect_silent "a non-shell file is ignored"

# ----------------------------------------------------------------- stop ---

new_project
printf "#!/usr/bin/env bash\necho \$1\n" >"${proj}/bin/unquoted.sh"
mk_edit "${proj}/bin/unquoted.sh" '' ''
fire post Edit s3 false
INPUT='{}'
fire stop '' s3 false
parse
expect_in "Stop keeps Claude working" "${CONTEXT}" "attempt 1 of 7"
expect_in "Stop names the finding" "${CONTEXT}" "SC2086"
expect_in "the user sees the attempt count" "${MESSAGE}" "(1/7)"
attempt=2
while ((attempt <= 7)); do
  fire stop '' s3 true
  attempt=$((attempt + 1))
done
parse
expect_in "the seventh attempt still continues" "${CONTEXT}" "attempt 7 of 7"
fire stop '' s3 true
parse
if [[ -z ${CONTEXT} ]]; then ok; else bad "the eighth stop does not continue" "${OUT}"; fi
expect_in "the eighth stop tells the user it gave up" "${MESSAGE}" "gave up after 7 attempts"
expect_in "the failure names the script" "${MESSAGE}" "bin/unquoted.sh"

fire stop '' s3 false
parse
expect_in "a new turn starts counting again" "${CONTEXT}" "attempt 1 of 7"
printf "#!/usr/bin/env bash\necho \"\$1\"\n" >"${proj}/bin/unquoted.sh"
fire stop '' s3 true
parse
expect_in "clean scripts end with a success message" "${MESSAGE}" "pass shfmt and ShellCheck"
fire stop '' s3 false
expect_silent "after success nothing is left to report"

# ------------------------------------------------------ trust boundaries ---

new_project
printf '#!/usr/bin/env bash\necho ok\n' >"${proj}/bin/safe.sh"
mkdir -p "${work}/.venv/bin"
printf '#!/bin/sh\n: >"%s/planted-ran"\nexit 0\n' "${work}" >"${work}/.venv/bin/shellcheck"
chmod +x "${work}/.venv/bin/shellcheck"
mk_edit "${proj}/bin/safe.sh" '' ''
fire post Edit t1 false
if [[ -e ${work}/planted-ran ]]; then bad "a shellcheck above the project is never run"; else ok; fi
rm -rf "${work}/.venv" "${work}/planted-ran"

mkdir -p "${work}/tmp" "${work}/elsewhere"
uid=$(id -u)
ln -s "${work}/elsewhere" "${work}/tmp/shell-quality-${uid}"
fire post Edit t2 false CLAUDE_PLUGIN_DATA= TMPDIR="${work}/tmp"
leaked=$(ls -A "${work}/elsewhere") || leaked="unreadable"
if [[ -z ${leaked} ]]; then ok; else bad "a symlinked state directory is never used" "${leaked}"; fi
rm -rf "${work}/tmp" "${work}/elsewhere"

nl_file="${proj}/bin/two
lines.sh"
printf '#!/usr/bin/env bash\necho ok\n' >"${nl_file}"
mk_edit "${nl_file}" '' ''
fire post Edit t3 false
expect_silent "a path with a newline is ignored"
rm -f "${nl_file}"

:
mk_edit "${proj}/bin/safe.sh" '' ''
fire post Edit t4 false SHELLCHECK_OPTS="-s zsh"
INPUT='{}'
fire stop '' t4 false SHELLCHECK_OPTS="-s zsh"
parse
if [[ -z ${CONTEXT} ]]; then ok; else bad "a tool break at Stop does not keep Claude working" "${OUT}"; fi
expect_in "a tool break at Stop is reported to the user" "${MESSAGE}" "could not check"
:

# ------------------------------------------------------- degraded modes ---

new_project
printf "#!/usr/bin/env bash\necho \"\$1\"\n" >"${proj}/bin/a.sh"
link_tools() { # link_tools DIR TOOL...: a PATH holding only these tools
  local dir=$1 t src
  shift
  mkdir -p "${dir}"
  for t in "$@"; do
    src=$(command -v "${t}") && ln -sf "${src}" "${dir}/${t}"
  done
}
mk_edit "${proj}/bin/a.sh" '' ''
if [[ -x /opt/homebrew/bin/shellcheck || -x /usr/local/bin/shellcheck || -x /opt/homebrew/bin/shfmt || -x /usr/local/bin/shfmt ]]; then
  skipped=$((skipped + 1))
  printf 'SKIP: missing-tool notice (a shellcheck/shfmt is installed at a fixed fallback path on this machine)\n' >&2
else
  link_tools "${work}/minimal" bash jq cat tr id mkdir find rm awk grep wc cksum sort head env
  fire post Edit s4 false PATH="${work}/minimal"
  parse
  expect_in "without the tools the user is told how to install them" "${MESSAGE}" "not installed"
  if [[ ${RC} -eq 0 && -z ${BLOCK} ]]; then ok; else bad "without the tools nothing is blocked" "${OUT}"; fi
  fire post Edit s4 false PATH="${work}/minimal"
  expect_silent "the missing-tool notice is shown once per session"
fi

link_tools "${work}/nojq" bash cat tr id mkdir find rm
fire post Edit s5 false PATH="${work}/nojq"
if [[ ${RC} -eq 0 && ${OUT} == *"jq is not installed"* ]]; then ok; else bad "without jq the user is told, and nothing breaks" "${OUT}"; fi

fire post Edit s6 false CLAUDE_PLUGIN_OPTION_ENABLED=false
expect_silent "the enabled=false option turns the hook off"

if printf '{"session_id":"s7","tool_name":"Edit"' | env CLAUDE_PLUGIN_DATA="${work}/data" "${run_bash}" "${gate}" guard >/dev/null 2>&1; then
  ok
else bad "a truncated payload never breaks the session"; fi
fire post Edit '../../escape' false
if [[ ! -e ${work}/escape.files && ! -e ${work}/data/escape.files ]]; then ok; else bad "session_id cannot escape the state directory"; fi

printf '%d passed, %d failed, %d skipped\n' "${pass}" "${fail}" "${skipped}"
[[ ${fail} -eq 0 ]]
