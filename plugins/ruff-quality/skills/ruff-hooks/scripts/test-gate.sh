#!/usr/bin/env bash
# Behavioral test suite for the ruff-quality gate handler.
#
# Usage: test-gate.sh [HANDLER_PATH]
#   HANDLER_PATH defaults to the bundled handler next to this skill. The
#   installer passes the installed copy, so the suite proves what actually runs.
#   RQ_TEST_BASH (or BNV_TEST_BASH, set by the repository's test runner) selects
#   the bash that runs the handler, e.g. /bin/bash for macOS bash 3.2.
#
# Every case runs in a throwaway Git repository with its own TMPDIR,
# XDG_CONFIG_HOME, and CLAUDE_CONFIG_DIR, so nothing on the machine is read or
# changed. Needs bash, jq, git, and ruff >= 0.16 (the suite fails, never skips,
# without them). Exit 0 when every case passes, 1 otherwise.

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
handler=${1:-"${here}/../assets/ruff-quality-gate.sh"}
runner=${RQ_TEST_BASH:-${BNV_TEST_BASH:-bash}}
profile="${here}/../assets/ruff.toml"
pass=0
fail=0
section=""

for tool in jq git ruff; do
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
export TMPDIR="${sandbox}/tmp" XDG_CONFIG_HOME="${sandbox}/xdg" CLAUDE_CONFIG_DIR="${sandbox}/claude-config"
mkdir -p "${TMPDIR}" "${XDG_CONFIG_HOME}" "${CLAUDE_CONFIG_DIR}"
unset RUFF_BIN

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
PL='{}'
run post --max-blocks 9
check "--max-blocks above 7 fails closed" rc_is 2
PL='{}'
run post --config-mode defaults --config /nonexistent.toml
check "--config outside own mode fails closed" rc_is 2
PL='{}'
run post --config "${sandbox}/missing.toml"
check "missing pinned config fails closed" rc_is 2
PL='{}'
run nope
check "unknown event fails closed" rc_is 2
PL=''
run post
check "empty payload fails closed" rc_is 2
PL='not json'
run post
check "invalid JSON fails closed" rc_is 2
check "invalid JSON explains itself" err_has "not valid JSON"

# --- post: the per-edit pipeline --------------------------------------------------------
section=post
new_repo post
printf 'import sys\nprint( sys.argv )\n' >"${repo}/fixable.py"
file_payload P1 Write "${repo}/fixable.py"
run post --config-mode defaults
check "fixable file exits 0" rc_is 0
check "clean result tells the user" out_has "ruff-quality ✓ fixable.py"
check "formatting was applied" file_has "${repo}/fixable.py" "print(sys.argv)"
check "user is told the file was rewritten" out_has "safe fixes/formatting applied"

printf 'def f():\n    x = 1\n' >"${repo}/unfixable.py"
file_payload P1 Edit "${repo}/unfixable.py"
run post --config-mode defaults
check "remaining finding exits 2" rc_is 2
check "finding reaches Claude on stderr" err_has "F841"
check "Claude is told to stop and fix" err_has "STOP and fix"
check "user sees a failure message" out_has "ruff-quality ✗"

printf 'import os\nimport sys\n\nprint(sys)\n' >"${repo}/newimport.py"
file_payload P1 Write "${repo}/newimport.py"
run post --config-mode defaults
check "an import added before its use survives the edit" file_has "${repo}/newimport.py" "import os"
check "an unused import alone does not stop the edit" rc_is 0

printf 'def f(:\n' >"${repo}/syntax.py"
file_payload P1 Write "${repo}/syntax.py"
run post --config-mode defaults
check "syntax error exits 2" rc_is 2
check "syntax error is reported as a finding" err_has "invalid-syntax"

printf 'x = 1\n' >"${repo}/notes.txt"
file_payload P1 Write "${repo}/notes.txt"
run post --config-mode defaults
check "non-Python file exits 0" rc_is 0
check "non-Python file is silent" quiet

file_payload P1 Write "${repo}/deleted.py"
run post --config-mode defaults
check "vanished file exits 0" rc_is 0

printf 'x=1\n' >"${repo}/UPPER.PY"
file_payload P1 Write "${repo}/UPPER.PY"
run post --config-mode defaults
check "upper-case extension is Python" out_has "UPPER.PY"

mkdir -p "${repo}/with space"
printf 'x=1\n' >"${repo}/with space/s.py"
file_payload P1 Write "${repo}/with space/s.py"
run post --config-mode defaults
check "path with a space works" rc_is 0
check "path with a space is formatted" file_has "${repo}/with space/s.py" "x = 1"

printf 'x=1\n' >"${repo}/relative.py"
file_payload P1 Write relative.py
run post --config-mode defaults
check "relative path resolves against cwd" file_has "${repo}/relative.py" "x = 1"

printf 'x: int\n' >"${repo}/stub.pyi"
file_payload P1 Write "${repo}/stub.pyi"
run post --config-mode defaults
check ".pyi is handled" rc_is 0

printf 'x=1\n' >"${repo}/viabash.py"
PL=$(jq -nc --arg f "${repo}/viabash.py" --arg c "${repo}" '{session_id: "P1", cwd: $c, tool_name: "Bash", tool_input: {command: "x"}, tool_response: {stdout: "", bashEditDiff: [$f]}}')
run post --config-mode defaults
check "bashEditDiff (array of paths) is processed" file_has "${repo}/viabash.py" "x = 1"
printf 'x=1\n' >"${repo}/viabash2.py"
PL=$(jq -nc --arg c "${repo}" '{session_id: "P1", cwd: $c, tool_name: "Bash", tool_input: {command: "x"}, tool_response: {bashEditDiff: {files: [{filePath: "viabash2.py", hunks: [], created: true}], moreFiles: 0, changedFiles: ["viabash2.py"]}}}')
run post --config-mode defaults
check "bashEditDiff (Claude Code 2.1.278 shape: {files: [{filePath}]}) is processed" file_has "${repo}/viabash2.py" "x = 1"
PL=$(jq -nc --arg c "${repo}" '{session_id: "P1", cwd: $c, tool_name: "Bash", tool_input: {command: "ls"}, tool_response: {stdout: "a"}}')
run post --config-mode defaults
check "Bash without edits is silent" quiet
check "Bash without edits exits 0" rc_is 0

# own mode follows the project's configuration; defaults ignores it.
printf '[lint]\nextend-select = ["T20"]\n' >"${repo}/ruff.toml"
printf 'print(1)\n' >"${repo}/printer.py"
file_payload P1 Write "${repo}/printer.py"
run post --config-mode own
check "own mode uses the project ruff.toml" err_has "T201"
file_payload P2 Write "${repo}/printer.py"
run post --config-mode defaults
check "defaults mode ignores the project ruff.toml" rc_is 0
printf '[lint]\nselect = ["F"]\n' >"${sandbox}/pinned.toml"
file_payload P3 Write "${repo}/printer.py"
run post --config-mode own --config "${sandbox}/pinned.toml"
check "a pinned --config overrides discovery" rc_is 0
rm -f "${repo}/ruff.toml"

printf 'exclude = ["generated.py"]\n' >"${repo}/ruff.toml"
printf 'x=1\n' >"${repo}/generated.py"
file_payload P4 Write "${repo}/generated.py"
run post --config-mode own
check "a file excluded by the config is skipped" out_has "skipped"
check "an excluded file is not formatted" file_has "${repo}/generated.py" "x=1"
rm -f "${repo}/ruff.toml"

mkdir -p "${repo}/.venv/bin"
printf '#!/bin/sh\necho "fake ruff" >&2\nexit 2\n' >"${repo}/.venv/bin/ruff"
chmod +x "${repo}/.venv/bin/ruff"
printf 'x = 1\n' >"${repo}/venv.py"
file_payload P5 Write "${repo}/venv.py"
run post --config-mode defaults
check "the project's .venv ruff is preferred" err_has "fake ruff"
check "a failing ruff fails closed" rc_is 2
rm -rf "${repo}/.venv"

file_payload P5 Write "${repo}/venv.py"
export RUFF_BIN="${sandbox}/not-executable"
run post --config-mode defaults
unset RUFF_BIN
check "a non-executable RUFF_BIN fails closed" rc_is 2

# Without ruff anywhere the gate must fail closed, not pass.
if [[ -x /usr/bin/ruff || -x /bin/ruff || -x /usr/local/bin/ruff || -x /opt/homebrew/bin/ruff ]]; then
  printf '  note: a system-wide ruff exists, so the missing-ruff case cannot be simulated here\n'
else
  file_payload P6 Write "${repo}/venv.py"
  PATH_SAVE=${PATH}
  HOME_SAVE=${HOME}
  jq_path=$(command -v jq)
  PATH="${jq_path%/*}:/usr/bin:/bin"
  export HOME="${sandbox}/nohome"
  run post --config-mode defaults
  PATH=${PATH_SAVE}
  export HOME=${HOME_SAVE}
  check "missing ruff fails closed" rc_is 2
  check "missing ruff explains how to install it" err_has "ruff not found"
fi

# --- guard: no suppressions, no configuration changes ------------------------------------
section=guard
new_repo guard
printf 'import os\n\nprint(os.sep)\n' >"${repo}/a.py"
printf '[project]\nname = "x"\n\n[tool.ruff]\nline-length = 100\n' >"${repo}/pyproject.toml"
commit_all
prompt_payload G1
run baseline
check "baseline is silent" quiet
edit_payload G1 "${repo}/a.py" 'print(os.sep)' 'print(os.sep)  # noqa: T201'
run guard
check "Edit adding noqa is denied" denied
edit_payload G1 "${repo}/a.py" 'print(os.sep)' 'print(os.sep)  # ruff: ignore[T201]'
run guard
check "Edit adding ruff: ignore is denied" denied
edit_payload G1 "${repo}/a.py" 'import os' '# ruff: noqa\nimport os'
run guard
check "Edit adding ruff: noqa is denied" denied
edit_payload G1 "${repo}/a.py" 'import os' '# fmt: off\nimport os'
run guard
check "Edit adding fmt: off is denied" denied
edit_payload G1 "${repo}/a.py" 'import os' 'import os  # isort: skip'
run guard
check "Edit adding isort: skip is denied" denied
write_payload G1 "${repo}/a.py" "$(printf 'import os  # NOQA\n')"
run guard
check "Write adding an upper-case NOQA is denied" denied
edit_payload G1 "${repo}/a.py" 'print(os.sep)' 'print(os.linesep)'
run guard
check "an ordinary edit is allowed" rc_is 0
check "an allowed edit is silent" quiet
printf 'import os  # noqa: F401\n' >"${repo}/kept.py"
commit_all
edit_payload G1 "${repo}/kept.py" 'import os  # noqa: F401' 'import os  # noqa: F401\nimport sys  # noqa: F401'
run guard
check "adding a second suppression is denied" denied
edit_payload G1 "${repo}/kept.py" 'import os  # noqa: F401' 'import os'
run guard
check "removing a suppression is allowed" rc_is 0
write_payload G1 "${repo}/ruff.toml" 'line-length = 200'
run guard
check "Write to ruff.toml is denied" denied
write_payload G1 "${repo}/sub/.ruff.toml" 'x = 1'
run guard
check "Write to a nested .ruff.toml is denied" denied
edit_payload G1 "${repo}/pyproject.toml" 'line-length = 100' 'line-length = 200'
run guard
check "changing [tool.ruff] in pyproject.toml is denied" denied
edit_payload G1 "${repo}/pyproject.toml" 'name = "x"' 'name = "y"'
run guard
check "changing [project] in pyproject.toml is allowed" rc_is 0
write_payload G1 "${XDG_CONFIG_HOME}/ruff/ruff.toml" 'x = 1'
run guard
check "Write to the user-level Ruff config is denied" denied
write_payload G1 "${repo}/.claude/hooks/ruff-quality-gate.sh" 'exit 0'
run guard
check "Write to the gate's handler is denied" denied
mkdir -p "${repo}/.claude"
jq -n '{hooks: {Stop: [{hooks: [{type: "command", command: "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/ruff-quality-gate.sh\" stop --config-mode own"}]}]}, permissions: {allow: []}}' >"${repo}/.claude/settings.json"
write_payload G1 "${repo}/.claude/settings.json" '{"permissions": {"allow": []}}'
run guard
check "removing the gate from settings is denied" denied
edit_payload G1 "${repo}/.claude/settings.json" '"permissions"' '"disableAllHooks": true, "permissions"'
run guard
check "setting disableAllHooks is denied" denied
edit_payload G1 "${repo}/.claude/settings.json" '"allow": []' '"allow": ["Bash(ls)"]'
run guard
check "an unrelated settings edit is allowed" rc_is 0
bash_payload G1 "sed -i 's/print(os.sep)/print(os.sep)  # noqa/' a.py"
run guard
check "Bash sed writing noqa is denied" denied
bash_payload G1 "echo '# ruff: noqa' >> a.py"
run guard
check "Bash append of ruff: noqa is denied" denied
bash_payload G1 'ruff check --add-noqa .'
run guard
check "ruff --add-noqa is denied" denied
bash_payload G1 "printf 'line-length = 200' > ruff.toml"
run guard
check "Bash write to ruff.toml is denied" denied
bash_payload G1 "jq '.disableAllHooks = true' .claude/settings.json"
run guard
check "Bash mentioning disableAllHooks is denied" denied
bash_payload G1 'bash ~/.claude/plugins/x/skills/ruff-hooks/scripts/manage.sh uninstall --scope user'
run guard
check "Claude running the uninstaller is denied" denied
bash_payload G1 'grep -rn noqa . 2>/dev/null | head'
run guard
check "read-only search for noqa is allowed" rc_is 0
bash_payload G1 'cat pyproject.toml 2>&1'
run guard
check "reading pyproject.toml is allowed" rc_is 0
bash_payload G1 'ruff check --fix a.py'
run guard
check "running ruff is allowed" rc_is 0
bash_payload G1 'bash ~/.claude/plugins/x/skills/ruff-hooks/scripts/manage.sh status'
run guard
check "the read-only status command is allowed" rc_is 0

# --- post and stop catch what slipped past the guard -------------------------------------
section=backstop
prompt_payload G1
run baseline
printf 'import os  # noqa: F401\n' >"${repo}/sneaky.py"
PL=$(jq -nc --arg c "${repo}" --arg f "${repo}/sneaky.py" '{session_id: "G1", cwd: $c, tool_name: "Bash", tool_input: {command: "x"}, tool_response: {bashEditDiff: [$f]}}')
run post --config-mode defaults
check "a suppression written through Bash is caught" rc_is 2
check "the suppression finding is explained" err_has "suppression comments grew"
printf '[project]\nname = "x"\n\n[tool.ruff]\nline-length = 200\n' >"${repo}/pyproject.toml"
printf 'x = 1\n' >"${repo}/a.py"
file_payload G1 Write "${repo}/a.py"
run post --config-mode defaults
check "a configuration change during the turn is caught by post" err_has "configuration"
stop_payload G1 false
run stop --config-mode defaults
check "the Stop gate blocks on configuration drift" rc_is 2
prompt_payload G1
run baseline
printf 'x = 1\n' >"${repo}/sneaky.py"
stop_payload G1 false
run stop --config-mode defaults
check "a change the user made between turns is accepted" rc_is 0

# --- stop ------------------------------------------------------------------------------
section=stop
new_repo stop
stop_payload S0 false
run stop --config-mode defaults
check "no Python edited: Stop is silent" quiet
check "no Python edited: Stop exits 0" rc_is 0
printf 'def f():\n    return 1\n' >"${repo}/ok.py"
file_payload S1 Write "${repo}/ok.py"
run post --config-mode defaults
stop_payload S1 false
run stop --config-mode defaults
check "clean session: Stop exits 0" rc_is 0
check "clean session: user sees confirmation" out_has "Stop gate"
printf 'import os\n' >"${repo}/late.py"
file_payload S2 Write "${repo}/late.py"
run post --config-mode defaults
stop_payload S2 false
run stop --config-mode defaults --max-blocks 2
check "an unused import is caught at Stop" err_has "F401"
check "Stop blocks with exit 2" rc_is 2
check "Stop shows the block count" err_has "block 1 of 2"
stop_payload S2 true
run stop --config-mode defaults --max-blocks 2
check "second consecutive block" err_has "block 2 of 2"
stop_payload S2 true
run stop --config-mode defaults --max-blocks 2
check "after max blocks the turn may end" rc_is 0
check "after max blocks the user is warned" out_has "⚠️"
stop_payload S2 false
run stop --config-mode defaults --max-blocks 2
check "a new turn starts counting again" err_has "block 1 of 2"
printf 'x=1\n' >"${repo}/late.py"
stop_payload S2 true
run stop --config-mode defaults
check "unformatted file is caught at Stop" err_has "not formatted"
printf 'x = 1\n' >"${repo}/late.py"
stop_payload S2 true
run stop --config-mode defaults
check "fixed file lets the turn end" rc_is 0
rm -f "${repo}/late.py"
stop_payload S2 false
run stop --config-mode defaults
check "a deleted file is dropped" rc_is 0

# --- recommended profile -----------------------------------------------------------------
section=profile
new_repo profile
cp "${profile}" "${repo}/ruff.toml"
printf 'def add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n' >"${repo}/good.py"
file_payload R1 Write "${repo}/good.py"
run post --config-mode recommended
check "typed, documented code passes the recommended profile" rc_is 0
printf 'def add(a, b):\n    return a + b\n' >"${repo}/bad.py"
file_payload R1 Write "${repo}/bad.py"
run post --config-mode recommended
check "the recommended profile requires annotations" err_has "ANN"
fmt_warn=$(cd "${repo}" && ruff format --check good.py 2>&1)
check "the recommended profile has no formatter conflicts" test "${fmt_warn}" == "${fmt_warn//warning/}"

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
: >"${repo}/big.py"
for ((i = 0; i < 1500; i++)); do printf 'def f%s(x: int) -> int:\n    """Return x."""\n    return x + %s\n\n\n' "${i}" "${i}" >>"${repo}/big.py"; done
start=$(date +%s)
file_payload T1 Write "${repo}/big.py"
run post --config-mode defaults
end=$(date +%s)
check "a 7,500-line file is processed well inside the 60 s timeout" test $((end - start)) -lt 20
big_cmd=$(head -c 20000 /dev/zero | tr '\0' 'x')
bash_payload T1 "echo ${big_cmd}"
run guard
check "a 20 KB Bash command is guarded" rc_is 0

printf '\n%s passed, %s failed\n' "${pass}" "${fail}"
((fail == 0)) && printf 'PASS\n'
((fail == 0))
