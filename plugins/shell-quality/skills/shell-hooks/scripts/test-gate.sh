#!/usr/bin/env bash
# Behavioral test suite for the shell-quality gate handler.
#
# Usage: test-gate.sh [HANDLER_PATH]
#   HANDLER_PATH defaults to the bundled handler next to this skill. The
#   installer passes the installed copy, so the suite proves what actually runs.
#   SQ_TEST_BASH (or BNV_TEST_BASH, set by the repository's test runner) selects
#   the bash that runs the handler, e.g. /bin/bash for macOS bash 3.2.
#
# Every case runs in a throwaway Git repository with its own TMPDIR, HOME-level
# rc paths, and CLAUDE_CONFIG_DIR, so nothing on the machine is read or changed.
# Needs bash, jq, git, shellcheck >= 0.11, and shfmt >= 3.12 (the suite fails,
# never skips, without them). Exit 0 when every case passes, 1 otherwise.
#
# Test fixtures are literal shell scripts handed to the handler as data; they are
# never expanded here, so single-quoted $ is intended.
# shellcheck disable=SC2016

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
handler=${1:-"${here}/../assets/shell-quality-gate.sh"}
runner=${SQ_TEST_BASH:-${BNV_TEST_BASH:-bash}}
profile_rc="${here}/../assets/shellcheckrc"
profile_ec="${here}/../assets/editorconfig-shell"
pass=0
fail=0
section=""

for tool in jq git shellcheck shfmt; do
  command -v "${tool}" >/dev/null 2>&1 || {
    printf 'test-gate: %s is required\n' "${tool}" >&2
    exit 1
  }
done
[[ -f ${handler} ]] || {
  printf 'test-gate: handler not found: %s\n' "${handler}" >&2
  exit 1
}
handler_dir=$(cd "${handler%/*}" 2>/dev/null && pwd) || handler_dir=.
[[ ${handler} == */* ]] || handler_dir=$(pwd)
handler="${handler_dir}/${handler##*/}"

sandbox=$(mktemp -d) || exit 1
sandbox=$(cd "${sandbox}" && pwd -P)
trap 'rm -rf "${sandbox}"' EXIT
real_home=${HOME}
export TMPDIR="${sandbox}/tmp" XDG_CONFIG_HOME="${sandbox}/xdg" CLAUDE_CONFIG_DIR="${sandbox}/claude-config" HOME="${sandbox}/home"
mkdir -p "${TMPDIR}" "${XDG_CONFIG_HOME}" "${CLAUDE_CONFIG_DIR}" "${HOME}"
unset SHELLCHECK_OPTS

repo=""
new_repo() { # new_repo NAME: fresh Git repository, becomes the project dir
  repo="${sandbox}/$1"
  mkdir -p "${repo}"
  git -C "${repo}" init -q
  export CLAUDE_PROJECT_DIR="${repo}"
}
commit_all() { git -C "${repo}" add -A && git -C "${repo}" -c user.name=t -c user.email=t@example.com commit -qm fixture; }

OUT=""
ERR=""
RC=0
PL=""
run() { # run EVENT [ARGS...] -> OUT, ERR, RC; the payload is ${PL}
  local ev=$1
  shift
  OUT=$(printf '%s' "${PL}" | (cd "${repo}" && "${runner}" "${handler}" "${ev}" "$@") 2>"${sandbox}/stderr")
  RC=$?
  ERR=$(cat "${sandbox}/stderr")
}

file_payload() { # file_payload SESSION TOOL PATH
  PL=$(jq -nc --arg s "$1" --arg t "$2" --arg f "$3" --arg c "${repo}" \
    '{session_id: $s, cwd: $c, hook_event_name: "PostToolUse", tool_name: $t, tool_input: {file_path: $f}, tool_response: {filePath: $f}}') || built_fail
}
edit_payload() { # edit_payload SESSION PATH OLD NEW
  PL=$(jq -nc --arg s "$1" --arg f "$2" --arg o "$3" --arg n "$4" --arg c "${repo}" \
    '{session_id: $s, cwd: $c, hook_event_name: "PreToolUse", tool_name: "Edit", tool_input: {file_path: $f, old_string: $o, new_string: $n}}') || built_fail
}
write_payload() { # write_payload SESSION PATH CONTENT
  PL=$(jq -nc --arg s "$1" --arg f "$2" --arg b "$3" --arg c "${repo}" \
    '{session_id: $s, cwd: $c, hook_event_name: "PreToolUse", tool_name: "Write", tool_input: {file_path: $f, content: $b}}') || built_fail
}
bash_payload() { # bash_payload SESSION COMMAND
  PL=$(jq -nc --arg s "$1" --arg b "$2" --arg c "${repo}" \
    '{session_id: $s, cwd: $c, hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: {command: $b}}') || built_fail
}
diff_payload() { # diff_payload SESSION PATH: a Bash PostToolUse with Claude Code's bashEditDiff shape
  PL=$(jq -nc --arg s "$1" --arg f "$2" --arg c "${repo}" \
    '{session_id: $s, cwd: $c, hook_event_name: "PostToolUse", tool_name: "Bash", tool_input: {command: "x"}, tool_response: {stdout: "", bashEditDiff: {files: [{filePath: $f, hunks: [], created: true}], moreFiles: 0, changedFiles: [$f]}}}') || built_fail
}
stop_payload() { # stop_payload SESSION ACTIVE
  PL=$(jq -nc --arg s "$1" --argjson a "$2" --arg c "${repo}" '{session_id: $s, cwd: $c, hook_event_name: "Stop", stop_hook_active: $a}') || built_fail
}
prompt_payload() { PL=$(jq -nc --arg s "$1" --arg c "${repo}" '{session_id: $s, cwd: $c, hook_event_name: "UserPromptSubmit", prompt: "go"}') || built_fail; }

built_fail() { # a fixture payload that jq could not build would test nothing
  printf 'test-gate: could not build a fixture payload\n' >&2
  exit 1
}

check() { # check LABEL CONDITION...
  local label=$1
  shift
  if "$@"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL [%s] %s (rc=%s)\n    stdout: %s\n    stderr: %s\n' "${section}" "${label}" "${RC}" "${OUT:0:300}" "${ERR:0:400}"
  fi
}
rc_is() { [[ ${RC} == "$1" ]]; }
out_has() { [[ ${OUT} == *"$1"* ]]; }
err_has() { [[ ${ERR} == *"$1"* ]]; }
quiet() { [[ -z ${OUT} && -z ${ERR} ]]; }
denied() {
  local d
  d=$(jq -r '.hookSpecificOutput.permissionDecision' <<<"${OUT}" 2>/dev/null) || d=""
  [[ ${RC} == 2 && ${d} == deny ]]
}
file_has() { grep -qF -- "$2" "$1"; }

# --- arguments and payloads ----------------------------------------------------------
section=arguments
new_repo args
PL='{}'
run post --config-mode nope
check "bad --config-mode fails closed" rc_is 2
run post --max-blocks 0
check "--max-blocks 0 fails closed" rc_is 2
run post --config-mode defaults --rcfile /nonexistent
check "--rcfile outside own mode fails closed" rc_is 2
run post --rcfile "${sandbox}/missing-rc"
check "missing pinned rc fails closed" rc_is 2
run post --config-mode own --style-fallback
check "--style-fallback outside recommended fails closed" rc_is 2
run nope
check "unknown event fails closed" rc_is 2
PL=''
run post
check "empty payload fails closed" rc_is 2
PL='not json'
run post
check "invalid JSON fails closed" rc_is 2

# --- post ------------------------------------------------------------------------------
section=post
new_repo post
printf '#!/usr/bin/env bash\nif true;then\necho ok\nfi\n' >"${repo}/fmt.sh"
file_payload P1 Write "${repo}/fmt.sh"
run post --config-mode defaults
check "formattable clean script exits 0" rc_is 0
check "clean result tells the user" out_has "shell-quality ✓ fmt.sh"
check "shfmt reformatted it (tabs by default)" file_has "${repo}/fmt.sh" "	echo ok"
check "user is told it was reformatted" out_has "reformatted"

printf '#!/bin/bash\necho $1\n' >"${repo}/warn.sh"
file_payload P1 Edit "${repo}/warn.sh"
run post --config-mode defaults
check "a ShellCheck finding exits 2" rc_is 2
check "the finding reaches Claude on stderr" err_has "SC2086"
check "Claude is told to stop and fix" err_has "STOP and fix"
check "the user sees a failure message" out_has "shell-quality ✗"

printf '#!/bin/bash\nif then\n' >"${repo}/syntax.sh"
file_payload P1 Write "${repo}/syntax.sh"
run post --config-mode defaults
check "a syntax error exits 2" rc_is 2
check "a syntax error is reported as a finding" err_has "SC1073"

printf '#!/usr/bin/env bash\necho "$1"\n' >"${repo}/noext"
file_payload P1 Write "${repo}/noext"
run post --config-mode defaults
check "an extensionless bash script is checked" out_has "noext"
printf '#!/bin/sh\necho "$1"\n' >"${repo}/posix"
file_payload P1 Write "${repo}/posix"
run post --config-mode defaults
check "an extensionless sh script is checked" out_has "posix"
printf '#!/usr/bin/env zsh\necho $1\n' >"${repo}/zshscript"
file_payload P1 Write "${repo}/zshscript"
run post --config-mode defaults
check "a zsh script (unsupported by ShellCheck) is ignored" quiet
printf 'echo $1\n' >"${repo}/README"
file_payload P1 Write "${repo}/README"
run post --config-mode defaults
check "a file without a shell shebang is ignored" quiet
printf '#!/usr/bin/env bats\n@test "x" {\n  run true\n}\n' >"${repo}/t.bats"
file_payload P1 Write "${repo}/t.bats"
run post --config-mode defaults
check ".bats files are handled" rc_is 0
printf 'x=1\n' >"${repo}/notes.txt"
file_payload P1 Write "${repo}/notes.txt"
run post --config-mode defaults
check "a non-shell file is silent" quiet
file_payload P1 Write "${repo}/deleted.sh"
run post --config-mode defaults
check "a vanished file exits 0" rc_is 0
mkdir -p "${repo}/with space"
printf '#!/bin/sh\necho hi\n' >"${repo}/with space/s.sh"
file_payload P1 Write "${repo}/with space/s.sh"
run post --config-mode defaults
check "a path with a space works" rc_is 0
printf '#!/bin/sh\necho hi\n' >"${repo}/viabash.sh"
diff_payload P1 "${repo}/viabash.sh"
run post --config-mode defaults
check "bashEditDiff (Claude Code 2.1.278 shape) is processed" out_has "viabash.sh"
bash_payload P1 ls
run post --config-mode defaults
check "Bash without edits is silent" quiet

# Modes: own follows .shellcheckrc and .editorconfig; defaults ignores both.
printf 'enable=require-variable-braces\n' >"${repo}/.shellcheckrc"
printf '#!/bin/sh\nx=1\necho "$x"\n' >"${repo}/braces.sh"
file_payload P2 Write "${repo}/braces.sh"
run post --config-mode own
check "own mode uses the project .shellcheckrc" err_has "SC2250"
file_payload P3 Write "${repo}/braces.sh"
run post --config-mode defaults
check "defaults mode ignores the project .shellcheckrc" rc_is 0
printf 'disable=SC2086\n' >"${sandbox}/pinned-rc"
file_payload P4 Write "${repo}/warn.sh"
run post --config-mode own --rcfile "${sandbox}/pinned-rc"
check "a pinned --rcfile overrides discovery" rc_is 0
rm -f "${repo}/.shellcheckrc"
printf 'root = true\n[*.sh]\nindent_style = space\nindent_size = 4\n' >"${repo}/.editorconfig"
printf '#!/bin/sh\nif true; then\necho a\nfi\n' >"${repo}/ec.sh"
file_payload P5 Write "${repo}/ec.sh"
run post --config-mode own
check "own mode formats with EditorConfig" file_has "${repo}/ec.sh" "    echo a"
printf '#!/bin/sh\nif true; then\necho a\nfi\n' >"${repo}/ec.sh"
file_payload P6 Write "${repo}/ec.sh"
run post --config-mode defaults
check "defaults mode ignores EditorConfig (tabs)" file_has "${repo}/ec.sh" "	echo a"
rm -f "${repo}/.editorconfig"
printf '#!/bin/sh\ncase "$1" in\na) echo a ;;\n*) echo b ;;\nesac\n' >"${repo}/fallback.sh"
file_payload P7 Write "${repo}/fallback.sh"
run post --config-mode recommended --style-fallback
check "--style-fallback formats ungoverned scripts with the recommended style" file_has "${repo}/fallback.sh" "  a) echo a ;;"

# A configured tool that is not executable fails closed.
file_payload P8 Write "${repo}/fmt.sh"
export SHELLCHECK_BIN="${sandbox}/not-executable"
run post --config-mode defaults
unset SHELLCHECK_BIN
check "a non-executable SHELLCHECK_BIN fails closed" rc_is 2
export SHFMT_BIN="${sandbox}/not-executable"
run post --config-mode defaults
unset SHFMT_BIN
check "a non-executable SHFMT_BIN fails closed" rc_is 2

# Missing tools fail closed.
mkdir -p "${sandbox}/onlyjq"
jq_path=$(command -v jq)
git_path=$(command -v git)
ln -sf "${jq_path}" "${sandbox}/onlyjq/jq"
ln -sf "${git_path}" "${sandbox}/onlyjq/git"
if [[ -x /usr/bin/shellcheck || -x /usr/local/bin/shellcheck || -x /opt/homebrew/bin/shellcheck ]]; then
  printf '  note: a system-wide shellcheck exists, so the missing-tool case cannot be simulated here\n'
else
  file_payload P8 Write "${repo}/fmt.sh"
  PATH_SAVE=${PATH}
  PATH="${sandbox}/onlyjq:/bin"
  run post --config-mode defaults
  PATH=${PATH_SAVE}
  check "a missing shellcheck fails closed" rc_is 2
  check "a missing shellcheck explains how to install it" err_has "shellcheck not found"
fi

# --- guard -----------------------------------------------------------------------------
section=guard
new_repo guard
printf '#!/bin/sh\necho "$1"\n' >"${repo}/a.sh"
printf 'root = true\n\n[*]\nindent_style = space\ncharset = utf-8\n' >"${repo}/.editorconfig"
mkdir -p "${repo}/.claude"
jq -n '{hooks: {Stop: [{hooks: [{type: "command", command: "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/shell-quality-gate.sh\" stop --config-mode own"}]}]}, permissions: {allow: []}}' >"${repo}/.claude/settings.json"
commit_all
prompt_payload G1
run baseline
check "baseline is silent" quiet
edit_payload G1 "${repo}/a.sh" 'echo "$1"' '# shellcheck disable=SC2086
echo $1'
run guard
check "Edit adding shellcheck disable is denied" denied
edit_payload G1 "${repo}/a.sh" 'echo "$1"' '# shellcheck source=/dev/null
. ./x'
run guard
check "Edit adding source=/dev/null is denied" denied
write_payload G1 "${repo}/a.sh" '#!/bin/sh
# shellcheck disable=all
echo $1'
run guard
check "Write adding disable=all is denied" denied
write_payload G1 "${repo}/newscript" '#!/usr/bin/env bash
echo $1 # shellcheck disable=SC2086'
run guard
check "a new extensionless script with a suppression is denied" denied
edit_payload G1 "${repo}/a.sh" 'echo "$1"' 'printf "%s\n" "$1"'
run guard
check "an ordinary edit is allowed" rc_is 0
check "an allowed edit is silent" quiet
edit_payload G1 "${repo}/a.sh" 'echo "$1"' '# shellcheck shell=sh
echo "$1"'
run guard
check "a shell= directive (not a suppression) is allowed" rc_is 0
write_payload G1 "${repo}/.shellcheckrc" 'disable=SC2086'
run guard
check "Write to .shellcheckrc is denied" denied
write_payload G1 "${repo}/sub/shellcheckrc" 'disable=SC2086'
run guard
check "Write to a nested shellcheckrc is denied" denied
write_payload G1 "${XDG_CONFIG_HOME}/shellcheckrc" 'x'
run guard
check "Write to the user-level rc is denied" denied
edit_payload G1 "${repo}/.editorconfig" 'indent_style = space' 'indent_style = tab'
run guard
check "changing indent_style in .editorconfig is denied" denied
edit_payload G1 "${repo}/.editorconfig" 'charset = utf-8' 'charset = utf-8
[*.sh]
ignore = true'
run guard
check "adding a shfmt ignore section to .editorconfig is denied" denied
edit_payload G1 "${repo}/.editorconfig" 'charset = utf-8' 'charset = latin1'
run guard
check "changing a non-shfmt key in .editorconfig is allowed" rc_is 0
write_payload G1 "${repo}/.claude/hooks/shell-quality-gate.sh" 'exit 0'
run guard
check "Write to the gate's handler is denied" denied
write_payload G1 "${repo}/.claude/settings.json" '{"permissions": {"allow": []}}'
run guard
check "removing the gate from settings is denied" denied
edit_payload G1 "${repo}/.claude/settings.json" '"allow": []' '"allow": ["Bash(ls)"]'
run guard
check "an unrelated settings edit is allowed" rc_is 0
bash_payload G1 "sed -i 's/echo/# shellcheck disable=SC2086\necho/' a.sh"
run guard
check "Bash sed writing a disable is denied" denied
bash_payload G1 "echo 'disable=SC2086' >> .shellcheckrc"
run guard
check "Bash append to .shellcheckrc is denied" denied
bash_payload G1 "printf 'ignore = true' >> .editorconfig"
run guard
check "Bash write to .editorconfig is denied" denied
bash_payload G1 'bash ~/.claude/plugins/x/skills/shell-hooks/scripts/manage.sh uninstall --scope user'
run guard
check "Claude running the uninstaller is denied" denied
bash_payload G1 'grep -rn "shellcheck disable" . 2>/dev/null'
run guard
check "a read-only search for disables is allowed" rc_is 0
bash_payload G1 'shellcheck -f gcc a.sh && shfmt -d a.sh'
run guard
check "running the tools is allowed" rc_is 0

# --- backstop -----------------------------------------------------------------------------
section=backstop
prompt_payload G1
run baseline
printf '#!/bin/sh\n# shellcheck disable=SC2086\necho $1\n' >"${repo}/a.sh"
diff_payload G1 "${repo}/a.sh"
run post --config-mode defaults
check "a suppression written through Bash is caught" rc_is 2
check "the suppression finding is explained" err_has "suppressions grew"
printf 'root = true\n\n[*]\nindent_style = tab\ncharset = utf-8\n' >"${repo}/.editorconfig"
printf '#!/bin/sh\necho "$1"\n' >"${repo}/a.sh"
stop_payload G1 false
run stop --config-mode defaults
check "the Stop gate blocks on configuration drift" err_has "configuration"
prompt_payload G1
run baseline
stop_payload G1 false
run stop --config-mode defaults
check "a change the user made between turns is accepted" rc_is 0

# --- stop ------------------------------------------------------------------------------
section=stop
new_repo stop
stop_payload S0 false
run stop --config-mode defaults
check "no scripts edited: Stop is silent" quiet
printf '#!/bin/sh\necho "$1"\n' >"${repo}/ok.sh"
file_payload S1 Write "${repo}/ok.sh"
run post --config-mode defaults
stop_payload S1 false
run stop --config-mode defaults
check "clean session: Stop exits 0" rc_is 0
check "clean session: the user sees confirmation" out_has "Stop gate"
printf '#!/bin/sh\necho "$1"\n' >"${repo}/late.sh"
file_payload S2 Write "${repo}/late.sh"
run post --config-mode defaults
printf '#!/bin/sh\necho $1\n' >"${repo}/late.sh"
stop_payload S2 false
run stop --config-mode defaults --max-blocks 2
check "a finding introduced later is caught at Stop" err_has "SC2086"
check "Stop shows the block count" err_has "block 1 of 2"
stop_payload S2 true
run stop --config-mode defaults --max-blocks 2
check "second consecutive block" err_has "block 2 of 2"
run stop --config-mode defaults --max-blocks 2
check "after max blocks the turn may end" rc_is 0
check "after max blocks the user is warned" out_has "⚠️"
printf '#!/bin/sh\nif true; then\necho "$1"\nfi\n' >"${repo}/late.sh"
stop_payload S2 true
run stop --config-mode defaults
check "an unformatted script is caught at Stop" err_has "not formatted"
printf '#!/bin/sh\nif true; then\n\techo "$1"\nfi\n' >"${repo}/late.sh"
run stop --config-mode defaults
check "a fixed script lets the turn end" rc_is 0

# --- recommended profile -------------------------------------------------------------------
section=profile
new_repo profile
cp "${profile_rc}" "${repo}/.shellcheckrc"
{
  printf 'root = true\n\n'
  cat "${profile_ec}"
} >"${repo}/.editorconfig"
printf '#!/usr/bin/env bash\nmain() {\n  local name=${1:-world}\n  case "${name}" in\n    x) printf "%%s\\n" "x" ;;\n    *) printf "hello %%s\\n" "${name}" ;;\n  esac\n}\nmain "$@"\n' >"${repo}/good.sh"
file_payload R1 Write "${repo}/good.sh"
run post --config-mode recommended
check "idiomatic code passes the recommended profile" rc_is 0
printf '#!/usr/bin/env bash\nname=$1\nif [ "$name" ]; then echo "$name"; fi\n' >"${repo}/bad.sh"
file_payload R1 Write "${repo}/bad.sh"
run post --config-mode recommended
check "the recommended profile enables optional checks (SC2244 nullary)" err_has "SC2244"
check "the recommended profile requires braces (SC2250)" err_has "SC2250"
printf '#!/usr/bin/env bash\nf() {\nif true; then\necho a\nfi\n}\n' >"${repo}/style.sh"
file_payload R2 Write "${repo}/style.sh"
run post --config-mode recommended
check "the recommended style indents with 2 spaces" file_has "${repo}/style.sh" "    echo a"

# --- degraded mode: jq missing, with a realistic full payload -----------------------------
section=degraded
nojq="${sandbox}/nojq-bin"
mkdir -p "${nojq}"
for tool in bash cat tr id git sed grep dirname find mkdir chmod head wc sort awk cksum; do
  tool_path=$(command -v "${tool}") && ln -sf "${tool_path}" "${nojq}/${tool}"
done
PL=$(jq -nc --arg c "${repo}" '{session_id: "D1", transcript_path: "/tmp/t.jsonl", cwd: $c, permission_mode: "default", hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: {command: "ls"}, tool_use_id: "toolu_1"}') || built_fail
PATH_SAVE=${PATH}
PATH=${nojq}
run guard --config-mode defaults
PATH=${PATH_SAVE}
check "without jq the guard denies (fail-closed)" rc_is 2
check "without jq the guard names the cause" err_has "jq is required"
check "without jq the guard says how to get out" err_has "manage.sh uninstall"

# --- performance ---------------------------------------------------------------------------
section=performance
new_repo perf
{
  printf '#!/usr/bin/env bash\n'
  for ((i = 0; i < 1500; i++)); do printf 'f%s() {\n\tprintf "%%s\\n" "%s"\n}\n' "${i}" "${i}"; done
} >"${repo}/big.sh"
start=$(date +%s)
file_payload T1 Write "${repo}/big.sh"
run post --config-mode defaults
end=$(date +%s)
check "a 4,500-line script is processed well inside the 60 s timeout" test $((end - start)) -lt 30
big_cmd=$(head -c 20000 /dev/zero | tr '\0' 'x')
bash_payload T1 "echo ${big_cmd}"
run guard
check "a 20 KB Bash command is guarded" rc_is 0

export HOME=${real_home}
printf '\n%s passed, %s failed\n' "${pass}" "${fail}"
((fail == 0)) && printf 'PASS\n'
((fail == 0))
