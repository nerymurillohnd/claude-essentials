#!/usr/bin/env bash
# Behavioral tests for ruff-quality's plugin hook (scripts/ruff-gate.sh):
# the guard's questions, the post-edit fix/format/check, the Stop loop and its
# limit, and every degraded mode. Runs the handler under $BNV_TEST_BASH (set by
# the repo's `make test-slow` to each bash it finds, /bin/bash 3.2 included),
# else `bash`. Ruff comes from the repository's .venv, so the suite never
# downloads anything. It lives in the repository, not in the plugin.

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "${here}/../../../.." && pwd)
plugin="${repo}/plugins/ruff-quality"
gate="${plugin}/scripts/ruff-gate.sh"
hooks_json="${plugin}/hooks/hooks.json"
run_bash=${BNV_TEST_BASH:-bash}
venv_bin="${repo}/.venv/bin"

if [[ ! -x ${venv_bin}/ruff ]]; then
  printf "test-gate: %s/ruff is missing; run \`make setup\`\n" "${venv_bin}" >&2
  exit 2
fi

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT
export HOME="${work}/home" XDG_CONFIG_HOME="${work}/home/.config"
mkdir -p "${HOME}" "${XDG_CONFIG_HOME}"

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() {
  fail=$((fail + 1))
  printf 'FAIL: %s\n' "$1" >&2
  if [[ $# -gt 1 ]]; then printf '      %s\n' "${2:0:600}" >&2; fi
  return 0
}
check() { # check LABEL CONDITION-RESULT(0/1) [DETAIL]
  if [[ $2 -eq 0 ]]; then ok; else bad "$1" "${3:-}"; fi
}

# ------------------------------------------------------------- helpers ---

proj="${work}/proj"
new_project() {
  rm -rf "${proj}" "${work}/data"
  mkdir -p "${proj}/pkg"
}

INPUT=""
mk_edit() { INPUT=$(jq -cn --arg f "$1" --arg o "$2" --arg n "$3" '{file_path: $f, old_string: $o, new_string: $n}') || INPUT=""; }
mk_write() { INPUT=$(printf '%s' "$2" | jq -Rsc --arg f "$1" '{file_path: $f, content: .}') || INPUT=""; }
mk_bash() { INPUT=$(jq -cn --arg c "$1" '{command: $c}') || INPUT=""; }

OUT=""
RC=0
# fire EVENT TOOL SESSION ACTIVE [ENV...]: send INPUT as a full payload.
# The payload goes through stdin, never one argument (Linux MAX_ARG_STRLEN),
# and a payload jq could not build fails the case instead of passing empty.
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

# Split OUT into the fields a test asserts on.
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
file_is() { # label path expected
  local got
  got=$(cat "$2")
  if [[ ${got} == "$3" ]]; then ok; else bad "$1" "${got}"; fi
}

# --------------------------------------------------------- the wiring ---

jq -e '.hooks.PreToolUse and .hooks.PostToolUse and .hooks.Stop' "${hooks_json}" >/dev/null
check "hooks.json wires PreToolUse, PostToolUse and Stop" $?
ifs=$(jq -r '[.hooks.PostToolUse[].hooks[].if] | join(" ")' "${hooks_json}")
expect_in "PostToolUse covers .py" "${ifs}" 'Edit(//**/*.py)'
expect_in "PostToolUse covers .pyw" "${ifs}" 'Edit(//**/*.pyw)'
expect_in "PostToolUse covers .pyi" "${ifs}" 'Edit(//**/*.pyi)'
if grep -qE '^[[:space:]]*(uvx?|"?[$][{]?UVX?)[[:space:]]' "${gate}"; then
  bad "the handler never runs uv or uvx"
else ok; fi

# ---------------------------------------------------------------- guard ---

new_project
printf 'import os\n' >"${proj}/pkg/a.py"
mk_edit "${proj}/pkg/a.py" 'import os' 'import os  # noqa: F401'
fire guard Edit s1 false
expect_ask "adding noqa asks"
expect_in "the question names the file" "${REASON}" "pkg/a.py"
mk_edit "${proj}/pkg/a.py" 'import os' 'import sys'
fire guard Edit s1 false
expect_silent "a plain edit is not questioned"
mk_edit "${proj}/pkg/a.py" 'import os  # noqa: F401' 'import os  # noqa: F401, E501'
fire guard Edit s1 false
expect_ask "widening a noqa with another code asks"
expect_in "the question names the widened marker" "${REASON}" "# noqa: f401, e501"
mk_edit "${proj}/pkg/a.py" 'import os  # noqa: F401' 'import sys  # noqa: F401'
fire guard Edit s1 false
expect_silent "editing a line that keeps the same noqa is not questioned"
mk_edit "${proj}/pkg/a.py" 'import os  # noqa: F401' 'import os  # noqa'
fire guard Edit s1 false
expect_ask "turning a coded noqa into a bare noqa asks"
mk_edit "${proj}/pkg/a.py" 'import os' '# flake8: noqa
import os'
fire guard Edit s1 false
expect_ask "a file-level flake8: noqa asks"
mk_edit "${proj}/pkg/a.py" 'import os' 'import os  # ruff: ignore[F401]'
fire guard Edit s1 false
parse
expect_in "the question names the marker actually added" "${REASON}" "# ruff: ignore[f401]"
printf 'import os  # noqa: F401\nx = 1\n' >"${proj}/pkg/w.py"
mk_write "${proj}/pkg/w.py" "$(printf 'import os  # noqa: F401\nx = 2')"
fire guard Write s1 false
expect_silent "rewriting a file that keeps its existing noqa is not questioned"
mk_edit "${proj}/pkg/w.py" 'import os  # noqa: F401' 'import os  # noqa: F401
import sys  # noqa: F401'
fire guard Edit s1 false
expect_ask "adding a second copy of an existing noqa asks"
chmod 000 "${proj}/pkg/w.py"
mk_write "${proj}/pkg/w.py" "$(printf 'import os  # noqa: F401\nx = 3')"
fire guard Write s1 false
expect_ask "a file the hook cannot read is compared with nothing, so a marker asks"
chmod 644 "${proj}/pkg/w.py"
INPUT=$(jq -cn --arg f "${proj}/pkg/a.py" '{file_path: $f, edits: [{old_string: "import a  # noqa: F401", new_string: "import a"}, {old_string: "y = 2", new_string: "y = 2  # noqa: F841"}]}') || INPUT=""
fire guard Edit s1 false
expect_ask "a batch that removes one noqa and adds another still asks"
mk_write "${proj}/pkg/b.py" 'x = 1  # fmt: skip'
fire guard Write s1 false
expect_ask "writing a file with fmt: skip asks"
mk_write "${proj}/pkg/b.py" 'x = [1,2]  # yapf: disable'
fire guard Write s1 false
expect_ask "writing a file with yapf: disable asks"
mk_write "${proj}/ruff.toml" 'line-length = 200'
fire guard Write s1 false
expect_ask "writing ruff.toml asks"
mk_edit "${proj}/.ruff.toml" 'a' 'b'
fire guard Edit s1 false
expect_ask "editing .ruff.toml asks"
printf '[project]\nname = "p"\n\n[tool.ruff]\nline-length = 88\n' >"${proj}/pyproject.toml"
mk_edit "${proj}/pyproject.toml" 'line-length = 88' 'line-length = 120'
fire guard Edit s1 false
expect_ask "changing [tool.ruff] in pyproject.toml asks"
mk_edit "${proj}/pyproject.toml" 'name = "p"' 'name = "q"'
fire guard Edit s1 false
expect_silent "changing another pyproject table is not questioned"
printf '[project]\nname = "p"\n\n[tool]\nruff.line-length = 88\n' >"${proj}/pyproject.toml"
mk_edit "${proj}/pyproject.toml" 'ruff.line-length = 88' 'ruff.lint.ignore = ["F401"]'
fire guard Edit s1 false
expect_ask "a dotted ruff key under [tool] asks"
mk_edit "${proj}/pyproject.toml" '[tool]' '[tool]
ruff.lint.select = ["F"]'
fire guard Edit s1 false
expect_ask "adding a dotted ruff key under [tool] asks"
rm -f "${proj}/pyproject.toml"
mk_bash 'sed -i "" "s/x/x  # noqa/" pkg/a.py'
fire guard Bash s1 false
expect_ask "a Bash write of noqa asks"
mk_bash 'ruff check --add-noqa .'
fire guard Bash s1 false
expect_ask "ruff --add-noqa asks"
mk_bash 'ruff check --add-ignore .'
fire guard Bash s1 false
expect_ask "ruff --add-ignore asks"
mk_bash 'echo line-length=1 >> ruff.toml'
fire guard Bash s1 false
expect_ask "a Bash write to ruff.toml asks"
mk_bash 'ls -la'
fire guard Bash s1 false
expect_silent "an ordinary command is not questioned"
mk_bash 'grep -rn "# noqa" src 2>/dev/null'
fire guard Bash s1 false
expect_silent "a stderr redirect is not a write"
mk_bash 'ruff check --statistics . 2>&1 | head; cat pyproject.toml'
fire guard Bash s1 false
expect_silent "reading pyproject.toml after 2>&1 is not a configuration write"
mk_bash 'grep -rn noqa .'
fire guard Bash s1 false
expect_silent "reading noqa without writing is not questioned"

# ----------------------------------------------------------------- post ---

new_project
printf 'x   =  f"abc"\n' >"${proj}/pkg/fixable.py"
mk_edit "${proj}/pkg/fixable.py" '' ''
fire post Edit s2 false
parse
expect_in "a fixable file reports success" "${MESSAGE}" "fixed and formatted"
expect_in "Claude is told to re-read a file the hook rewrote" "${CONTEXT}" "re-read"
file_is "F541 fixed and spacing formatted" "${proj}/pkg/fixable.py" 'x = "abc"'

printf 'import os\n' >"${proj}/pkg/fresh.py"
mk_write "${proj}/pkg/fresh.py" 'import os'
fire post Write s2 false
parse
file_is "F401 is never auto-removed (the import may be used by the next edit)" "${proj}/pkg/fresh.py" "import os"
expect_in "the unused import is reported for Claude instead" "${BLOCK}" "F401"

printf 'print(undefined_name)\n' >"${proj}/pkg/broken.py"
mk_edit "${proj}/pkg/broken.py" '' ''
fire post Edit s2 false
parse
expect_in "an unfixable finding blocks with its code" "${BLOCK}" "F821"
expect_in "the user is told Claude is fixing it" "${MESSAGE}" "Claude is fixing them"

printf 'x = 1\n' >"${proj}/pkg/clean.py"
mk_edit "${proj}/pkg/clean.py" '' ''
fire post Edit s2 false
parse
expect_in "a clean file reports clean" "${MESSAGE}" "clean"

printf 'a_very_long_name = 12345678901234567890\n' >"${proj}/pkg/long.py"
printf 'line-length = 20\n[lint]\nselect = ["E501"]\n' >"${proj}/pkg/ruff.toml"
mk_edit "${proj}/pkg/long.py" '' ''
fire post Edit s2 false
parse
expect_in "the nearest project config is honoured" "${BLOCK}" "E501"
printf 'no-such-setting = 1\n' >"${proj}/pkg/ruff.toml"
fire post Edit s2 false
parse
expect_in "a broken config is a tool break, not a finding" "${BLOCK}" "could not check"
rm -f "${proj}/pkg/ruff.toml"

printf 'body { color: red; }\n' >"${proj}/pkg/style.css"
mk_edit "${proj}/pkg/style.css" '' ''
fire post Edit s2 false
expect_silent "a non-Python file is ignored"
printf 'x=1\n' >"${proj}/pkg/gui.pyw"
mk_edit "${proj}/pkg/gui.pyw" '' ''
fire post Edit s2 false
file_is ".pyw is formatted too" "${proj}/pkg/gui.pyw" "x = 1"

mkdir -p "${proj}/gen"
printf 'extend-exclude = ["gen"]\n' >"${proj}/ruff.toml"
printf 'import os\nprint(undefined_name)\n' >"${proj}/gen/g.py"
mk_edit "${proj}/gen/g.py" '' ''
fire post Edit s2x false
parse
expect_in "an excluded file is reported as not checked" "${MESSAGE}" "excluded"
if [[ ${MESSAGE} == *clean* ]]; then bad "an excluded file is never called clean" "${MESSAGE}"; else ok; fi
INPUT='{}'
fire stop '' s2x false
expect_silent "an excluded file is not re-checked at Stop"
rm -rf "${proj}/ruff.toml" "${proj}/gen"

: >"${proj}/pkg/many.py"
i=0
while ((i < 90)); do
  printf 'print(undefined_%d)\n' "${i}" >>"${proj}/pkg/many.py"
  i=$((i + 1))
done
mk_edit "${proj}/pkg/many.py" '' ''
fire post Edit s2y false
parse
expect_in "a long report says it was cut" "${BLOCK}" "first 60 of 90"

# ----------------------------------------------------------------- stop ---

new_project
printf 'print(undefined_name)\n' >"${proj}/pkg/broken.py"
mk_edit "${proj}/pkg/broken.py" '' ''
fire post Edit s3 false
INPUT='{}'
fire stop '' s3 false
parse
expect_in "Stop keeps Claude working" "${CONTEXT}" "attempt 1 of 7"
expect_in "Stop names the finding" "${CONTEXT}" "F821"
expect_in "the user sees the attempt count" "${MESSAGE}" "(1/7)"
attempt=2
while ((attempt <= 7)); do
  printf 'print(undefined_%d)\n' "${attempt}" >"${proj}/pkg/broken.py" # Claude changed something
  fire stop '' s3 true
  attempt=$((attempt + 1))
done
parse
expect_in "the seventh attempt still continues" "${CONTEXT}" "attempt 7 of 7"
printf 'print(undefined_8)\n' >"${proj}/pkg/broken.py"
fire stop '' s3 true
parse
if [[ -z ${CONTEXT} ]]; then ok; else bad "the eighth stop does not continue" "${OUT}"; fi
expect_in "the eighth stop tells the user it gave up" "${MESSAGE}" "gave up after 7 attempts"
expect_in "the failure names the file" "${MESSAGE}" "pkg/broken.py"
fire stop '' s3 false
expect_silent "after giving up, the next turn does not start again on the same files"

mk_edit "${proj}/pkg/broken.py" '' ''
fire post Edit s3 false
fire stop '' s3 false
parse
expect_in "a new edit re-arms the gate" "${CONTEXT}" "attempt 1 of 7"
fire stop '' s3 true
parse
if [[ -z ${CONTEXT} ]]; then ok; else bad "a retry with no change does not continue" "${OUT}"; fi
expect_in "no progress ends with a message to the user" "${MESSAGE}" "no change"

mk_edit "${proj}/pkg/broken.py" '' ''
fire post Edit s3 false
printf 'print("fixed")\n' >"${proj}/pkg/broken.py"
fire stop '' s3 true
parse
expect_in "clean files end with a success message" "${MESSAGE}" "pass Ruff"
fire stop '' s3 false
expect_silent "after success nothing is left to report"
fire stop '' s-none false
expect_silent "a session that touched no Python stays silent"

for n in 1 2 3 4 5; do
  : >"${proj}/pkg/big${n}.py"
  i=0
  while ((i < 60)); do
    printf 'print(an_undefined_name_that_is_rather_long_%d_%d)\n' "${n}" "${i}" >>"${proj}/pkg/big${n}.py"
    i=$((i + 1))
  done
  mk_edit "${proj}/pkg/big${n}.py" '' ''
  fire post Edit s3b false
done
INPUT='{}'
fire stop '' s3b false
parse
if ((${#CONTEXT} <= 9500)); then ok; else bad "the Stop report stays under Claude Code's 10,000-character cap" "${#CONTEXT} characters"; fi
expect_in "a capped report says how to see the rest" "${CONTEXT}" "ruff check"

# ------------------------------------------------------ trust boundaries ---

new_project
printf 'x = 1\n' >"${proj}/pkg/safe.py"
mkdir -p "${work}/.venv/bin"
printf '#!/bin/sh\n: >"%s/planted-ran"\nexit 0\n' "${work}" >"${work}/.venv/bin/ruff"
chmod +x "${work}/.venv/bin/ruff"
mk_edit "${proj}/pkg/safe.py" '' ''
fire post Edit t1 false
if [[ -e ${work}/planted-ran ]]; then bad "a ruff above the project is never run"; else ok; fi
rm -rf "${work}/.venv" "${work}/planted-ran"

mkdir -p "${work}/tmp" "${work}/elsewhere"
uid=$(id -u)
ln -s "${work}/elsewhere" "${work}/tmp/ruff-quality-${uid}"
fire post Edit t2 false CLAUDE_PLUGIN_DATA= TMPDIR="${work}/tmp"
leaked=$(ls -A "${work}/elsewhere") || leaked="unreadable"
if [[ -z ${leaked} ]]; then ok; else bad "a symlinked state directory is never used" "${leaked}"; fi
rm -rf "${work}/tmp" "${work}/elsewhere"

nl_file="${proj}/pkg/two
lines.py"
printf 'x = 1\n' >"${nl_file}"
mk_edit "${nl_file}" '' ''
fire post Edit t3 false
expect_silent "a path with a newline is ignored"
rm -f "${nl_file}"

printf 'required-version = ">=99"\n' >"${proj}/ruff.toml"
mk_edit "${proj}/pkg/safe.py" '' ''
fire post Edit t4 false
INPUT='{}'
fire stop '' t4 false
parse
if [[ -z ${CONTEXT} ]]; then ok; else bad "a tool break at Stop does not keep Claude working" "${OUT}"; fi
expect_in "a tool break at Stop is reported to the user" "${MESSAGE}" "could not check"
rm -f "${proj}/ruff.toml"

# ------------------------------------------------------- degraded modes ---

new_project
printf 'x=1\n' >"${proj}/pkg/a.py"
link_tools() { # link_tools DIR TOOL...: a PATH holding only these tools
  local dir=$1 t src
  shift
  mkdir -p "${dir}"
  for t in "$@"; do
    src=$(command -v "${t}") && ln -sf "${src}" "${dir}/${t}"
  done
}
link_tools "${work}/minimal" bash jq cat tr id mkdir find rm awk grep wc cksum sort env
mk_edit "${proj}/pkg/a.py" '' ''
fire post Edit s4 false PATH="${work}/minimal"
parse
expect_in "without Ruff the user is told how to install it" "${MESSAGE}" "Ruff is not installed"
expect_in "without Ruff Claude is told too" "${CONTEXT}" "Ruff is not installed"
if [[ ${RC} -eq 0 && -z ${BLOCK} ]]; then ok; else bad "without Ruff nothing is blocked" "${OUT}"; fi
fire post Edit s4 false PATH="${work}/minimal"
expect_silent "the missing-Ruff notice is shown once per session"

link_tools "${work}/nojq" bash cat tr id mkdir find rm
fire post Edit s5 false PATH="${work}/nojq"
if [[ ${RC} -eq 0 && ${OUT} == *"jq is not installed"* ]]; then ok; else bad "without jq the user is told, and nothing breaks" "${OUT}"; fi

fire post Edit s6 false CLAUDE_PLUGIN_OPTION_ENABLED=false
expect_silent "the enabled=false option turns the hook off"
fire post Edit s6 false CLAUDE_PLUGIN_OPTION_ENABLED=False
expect_silent "the enabled option turns the hook off whatever its case"
fire post Edit s6 false CLAUDE_PLUGIN_OPTION_ENABLED=0
expect_silent "the enabled option turns the hook off when written as 0"

OUT=$(printf '{"session_id":"s7","tool_name":"Edit"' | env CLAUDE_PLUGIN_DATA="${work}/data" "${run_bash}" "${gate}" guard 2>/dev/null)
check "a truncated payload never breaks the session" $?
mk_edit "${proj}/pkg/a.py" 'x' 'y'
fire post Edit '../../escape' false
if [[ ! -e ${work}/escape.files && ! -e ${work}/data/escape.files ]]; then ok; else bad "session_id cannot escape the state directory"; fi

printf '%d passed, %d failed\n' "${pass}" "${fail}"
[[ ${fail} -eq 0 ]]
