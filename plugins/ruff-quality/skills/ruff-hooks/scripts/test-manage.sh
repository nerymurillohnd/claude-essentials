#!/usr/bin/env bash
# End-to-end suite for manage.sh: every command in a throwaway project, user
# config, and Claude config directory. Nothing on the machine is read or changed.
#
# Usage: test-manage.sh
#   RQ_TEST_BASH (or BNV_TEST_BASH, set by the repository's test runner) selects
#   the bash that runs manage.sh. Needs bash, jq, git, and ruff >= 0.16.
# Exit 0 when every case passes, 1 otherwise.

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
manage="${here}/manage.sh"
profile="${here}/../assets/ruff.toml"
runner=${RQ_TEST_BASH:-${BNV_TEST_BASH:-bash}}
pass=0
fail=0

for tool in jq git ruff; do
  command -v "${tool}" >/dev/null 2>&1 || {
    printf 'test-manage: %s is required\n' "${tool}" >&2
    exit 1
  }
done

sandbox=$(mktemp -d) || exit 1
sandbox=$(cd "${sandbox}" && pwd -P)
trap 'rm -rf "${sandbox}"' EXIT
export TMPDIR="${sandbox}/tmp" XDG_CONFIG_HOME="${sandbox}/xdg" CLAUDE_CONFIG_DIR="${sandbox}/claude-config"
mkdir -p "${TMPDIR}" "${XDG_CONFIG_HOME}" "${CLAUDE_CONFIG_DIR}"
unset CLAUDE_CODE_IS_COWORK

proj="${sandbox}/proj"
mkdir -p "${proj}"
git -C "${proj}" init -q
printf 'import os\nprint( os.sep )\n' >"${proj}/app.py"
export CLAUDE_PROJECT_DIR="${proj}"

OUT=""
RC=0
m() { # m ARGS... -> OUT (stdout+stderr), RC
  OUT=$(cd "${proj}" && "${runner}" "${manage}" "$@" 2>&1)
  RC=$?
}
check() { # check LABEL CONDITION...
  local label=$1
  shift
  if "$@"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL %s (rc=%s)\n%s\n' "${label}" "${RC}" "${OUT:0:1500}"
  fi
}
rc_is() { [[ ${RC} == "$1" ]]; }
has() { [[ ${OUT} == *"$1"* ]]; }
no_shell_errors() { [[ ${OUT} != *"command not found"* && ${OUT} != *"unbound variable"* && ${OUT} != *"syntax error"* ]]; }
groups_in() { jq -r '[.hooks[]? | .[] | select(any(.hooks[]; .command | test("ruff-quality-gate")))] | length' "$1" 2>/dev/null; }

m assess
check "assess exits 0" rc_is 0
check "assess has no shell errors" no_shell_errors
check "assess reports ruff" has "ruff: "
check "assess reports a baseline for each mode" has "defaults (--isolated)"

for mode in recommended own defaults; do
  m show-config --config-mode "${mode}"
  check "show-config ${mode} exits 0" rc_is 0
  check "show-config ${mode} has no shell errors" no_shell_errors
done
m show-config --config-mode recommended
check "show-config recommended prints the whole profile" has "extend-select"

m preflight --scope project --config-mode nope
check "an invalid mode is a usage error" rc_is 2
m install --scope project --config-mode recommended --max-blocks 9
check "an invalid --max-blocks is a usage error" rc_is 2

m install --scope project --config-mode recommended
check "install (project, recommended) exits 0" rc_is 0
check "install has no shell errors" no_shell_errors
check "install ran the suite against the installed copy" has "0 failed"
check "install wrote the recommended profile" cmp -s "${profile}" "${proj}/ruff.toml"
check "install copied the handler" test -x "${proj}/.claude/hooks/ruff-quality-gate.sh"
n=$(groups_in "${proj}/.claude/settings.json")
check "install merged five groups" test "${n}" = 5

m install --scope project --config-mode recommended
n=$(groups_in "${proj}/.claude/settings.json")
check "reinstall is idempotent" test "${n}" = 5

m preflight --scope user --config-mode defaults
check "a second scope is refused" has "already installed in: project"
check "preflight enforces the git minimum" has "ok   git "
check "preflight enforces the ruff minimum in every mode" has "ok   ruff "

m status
check "status exits 0" rc_is 0
check "status shows the installed command" has "post --config-mode recommended --max-blocks 5"

m verify --scope project
check "verify exits 0" rc_is 0

m uninstall --scope project
check "uninstall exits 0" rc_is 0
check "uninstall has no shell errors" no_shell_errors
check "uninstall removed the handler" test ! -e "${proj}/.claude/hooks/ruff-quality-gate.sh"
check "uninstall removed the emptied settings file" test ! -e "${proj}/.claude/settings.json"
check "uninstall kept the profile" test -f "${proj}/ruff.toml"

printf 'line-length = 120\n' >"${proj}/ruff.toml"
m preflight --scope project --config-mode recommended
check "recommended never overwrites an existing configuration" has "already exists"
m install --scope local --config-mode own --config-path "${proj}/ruff.toml"
check "install (local, own, pinned) exits 0" rc_is 0
check "the pinned path is project-relative" has "\"\$CLAUDE_PROJECT_DIR/ruff.toml\""
check "local scope is excluded from git" grep -q 'settings.local.json' "${proj}/.git/info/exclude"
m uninstall --scope local
check "uninstall (local) exits 0" rc_is 0
left=$(grep -c 'ruff-quality' "${proj}/.git/info/exclude" || true)
check "uninstall (local) removed its git exclusions" test "${left}" = 0

m install --scope user --config-mode defaults --max-blocks 3
check "install (user, defaults) exits 0" rc_is 0
check "user scope writes under CLAUDE_CONFIG_DIR" test -x "${CLAUDE_CONFIG_DIR}/hooks/ruff-quality-gate.sh"
m uninstall --scope user
check "uninstall (user) exits 0" rc_is 0

export CLAUDE_CODE_IS_COWORK=1
m install --scope project --config-mode own
unset CLAUDE_CODE_IS_COWORK
check "Cowork is refused with exit 3" rc_is 3

printf '\n%s passed, %s failed\n' "${pass}" "${fail}"
((fail == 0)) && printf 'PASS\n'
((fail == 0))
