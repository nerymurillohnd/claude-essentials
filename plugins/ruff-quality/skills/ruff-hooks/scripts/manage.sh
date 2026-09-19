#!/usr/bin/env bash
# ruff-quality hook manager. Deterministic, idempotent, backup-first.
#
# Usage:
#   manage.sh assess                                   read-only report
#   manage.sh show-config --config-mode MODE [--config-path FILE]
#                                                      read-only: the exact configuration a mode uses
#   manage.sh status                                   read-only: where the gate is installed
#   manage.sh preflight --scope SCOPE --config-mode MODE [--config-path FILE]
#   manage.sh install   --scope SCOPE --config-mode MODE [--config-path FILE] [--max-blocks N]
#   manage.sh verify    --scope SCOPE                  re-run the suite against the installed copy
#   manage.sh uninstall --scope SCOPE                  remove only this gate
#
#   SCOPE: project (.claude/settings.json, committed), local
#   (.claude/settings.local.json, this machine only), user (~/.claude/settings.json).
#   MODE: recommended (write the bundled profile where Ruff discovers it),
#   own (the configuration you already have, or --config-path FILE),
#   defaults (Ruff's built-in defaults; every configuration file is ignored).
#   --project-dir DIR overrides the project root (default: $CLAUDE_PROJECT_DIR,
#   then the Git top level, then the current directory).
#
# Exit codes: 0 ok, 1 failed check or error, 2 usage, 3 unsupported surface.
# Needs bash >= 3.2 and jq >= 1.6. Never touches the network.

set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
readonly SKILL_DIR
readonly SRC_HANDLER="${SKILL_DIR}/assets/ruff-quality-gate.sh"
readonly SRC_PROFILE="${SKILL_DIR}/assets/ruff.toml"
readonly TEST_SUITE="${SKILL_DIR}/scripts/test-gate.sh"
readonly HANDLER_NAME="ruff-quality-gate.sh"
readonly EXCLUDE_MARK="# ruff-quality (local scope)"
readonly MIN_RUFF="0.16.0"
readonly CFG_DIR=${CLAUDE_CONFIG_DIR:-${HOME}/.claude}
readonly RUFF_USER_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/ruff"

cmd=${1:-}
[[ $# -gt 0 ]] && shift
scope=""
mode=""
config_path=""
max_blocks=5
project_dir=""
while [[ $# -gt 0 ]]; do
  case $1 in
  --scope | --config-mode | --config-path | --max-blocks | --project-dir)
    [[ $# -ge 2 ]] || {
      printf 'manage.sh: %s needs a value\n' "$1" >&2
      exit 2
    }
    case $1 in
    --scope) scope=$2 ;;
    --config-mode) mode=$2 ;;
    --config-path) config_path=$2 ;;
    --max-blocks) max_blocks=$2 ;;
    --project-dir) project_dir=$2 ;;
    *) ;;
    esac
    shift 2
    ;;
  *)
    printf 'manage.sh: unknown argument: %s\n' "$1" >&2
    exit 2
    ;;
  esac
done

say() { printf '%s\n' "$*"; }
fail() {
  say "FAIL: $*"
  exit 1
}
usage_error() {
  say "manage.sh ${cmd}: $*" >&2
  exit 2
}

bundled_version() { sed -n 's/^# ruff-quality-version: *//p' "$1" 2>/dev/null | head -n 1; }
is_cowork() { [[ -n ${CLAUDE_CODE_IS_COWORK:-} ]]; }
refuse_cowork() {
  if is_cowork; then
    say "UNSUPPORTED: this is a Claude Cowork session. Cowork does not run settings-based hooks, so the gate cannot run here and nothing was changed. Use Claude Code (CLI, Desktop, IDE) to install it."
    exit 3
  fi
}

resolve_root() {
  if [[ -n ${project_dir} ]]; then
    ROOT=$(cd "${project_dir}" 2>/dev/null && pwd -P) || fail "--project-dir does not exist: ${project_dir}"
  elif [[ -n ${CLAUDE_PROJECT_DIR:-} && -d ${CLAUDE_PROJECT_DIR} ]]; then
    ROOT=$(cd "${CLAUDE_PROJECT_DIR}" && pwd -P)
  elif ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
    :
  else
    ROOT=$(pwd -P)
  fi
}

# Sets SETTINGS, HOOK_DIR, HANDLER_DST, CMD_PREFIX for a scope.
scope_paths() {
  case $1 in
  project | local)
    if [[ $1 == project ]]; then SETTINGS="${ROOT}/.claude/settings.json"; else SETTINGS="${ROOT}/.claude/settings.local.json"; fi
    HOOK_DIR="${ROOT}/.claude/hooks"
    # shellcheck disable=SC2016 # expanded by the hook shell at run time, not here
    CMD_PREFIX='bash "$CLAUDE_PROJECT_DIR/.claude/hooks/ruff-quality-gate.sh"'
    ;;
  user)
    SETTINGS="${CFG_DIR}/settings.json"
    HOOK_DIR="${CFG_DIR}/hooks"
    # shellcheck disable=SC2016 # expanded by the hook shell at run time, not here
    if [[ -n ${CLAUDE_CONFIG_DIR:-} ]]; then
      CMD_PREFIX='bash "$CLAUDE_CONFIG_DIR/hooks/ruff-quality-gate.sh"'
    else
      CMD_PREFIX='bash "$HOME/.claude/hooks/ruff-quality-gate.sh"'
    fi
    ;;
  *) return 1 ;;
  esac
  HANDLER_DST="${HOOK_DIR}/${HANDLER_NAME}"
}

need_scope() {
  case ${scope} in
  project | local | user) scope_paths "${scope}" ;;
  *) usage_error "--scope must be project, local, or user" ;;
  esac
}

need_mode() {
  case ${mode} in
  recommended | defaults)
    [[ -z ${config_path} ]] || usage_error "--config-path is only valid with --config-mode own"
    ;;
  own) ;;
  *) usage_error "--config-mode must be recommended, own, or defaults" ;;
  esac
  case ${max_blocks} in
  [1-7]) ;;
  *) usage_error "--max-blocks must be a number from 1 to 7" ;;
  esac
}

# Where the recommended profile goes for the chosen scope.
profile_target() {
  if [[ ${scope} == user ]]; then say "${RUFF_USER_DIR}/ruff.toml"; else say "${ROOT}/ruff.toml"; fi
}

# Ruff configuration files that already govern a directory level.
existing_configs_in() { # existing_configs_in DIR
  local d=$1 f
  for f in .ruff.toml ruff.toml; do
    [[ -f ${d}/${f} ]] && say "${d}/${f}"
  done
  if [[ -f ${d}/pyproject.toml ]] && grep -q '^\[tool\.ruff' "${d}/pyproject.toml" 2>/dev/null; then
    say "${d}/pyproject.toml"
  fi
  return 0
}

# jq program fragments shared by every settings query.
readonly JQ_OURS='def ours_hook: ((.command // "") | tostring | test("^bash \"[^\"]*/hooks/ruff-quality-gate[.]sh\"( |$)"));
def ours_group: ((.hooks // []) | length > 0) and all((.hooks // [])[]; ours_hook);
def mixed_group: any((.hooks // [])[]; ours_hook) and (ours_group | not);
def events: ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"];'

# The five groups this gate owns, with the commands for the chosen options.
groups_json() {
  local args="--config-mode ${mode} --max-blocks ${max_blocks}"
  [[ -n ${CONFIG_ARG} ]] && args="${args} --config ${CONFIG_ARG}"
  jq -nc --arg p "${CMD_PREFIX}" --arg a "${args}" '{
    UserPromptSubmit: [
      {hooks: [{type: "command", command: "\($p) baseline \($a)", timeout: 30}]}
    ],
    PreToolUse: [
      {matcher: "Write|Edit|NotebookEdit|Bash", hooks: [{type: "command", command: "\($p) guard \($a)", timeout: 30}]}
    ],
    PostToolUse: [
      {matcher: "Write|Edit|NotebookEdit", hooks: [{type: "command", command: "\($p) post \($a)", timeout: 60, statusMessage: "ruff-quality: fixing, formatting, and linting the edited Python file"}]},
      {matcher: "Bash", hooks: [{type: "command", command: "\($p) post \($a)", timeout: 60}]}
    ],
    Stop: [
      {hooks: [{type: "command", command: "\($p) stop \($a)", timeout: 120, statusMessage: "ruff-quality: Stop gate re-checking edited Python files"}]}
    ]}'
}

# Prints: present|absent|mixed|invalid|missing for a settings file.
settings_state() {
  local f=$1
  [[ -f ${f} ]] || {
    say missing
    return 0
  }
  jq -r "${JQ_OURS}"'
    if type != "object" then "invalid"
    elif ((.hooks // {}) | type) != "object" then "invalid"
    elif any(events[] as $e | (.hooks[$e] // []); type != "array") then "invalid"
    elif any(events[] as $e | (.hooks[$e] // [])[]; mixed_group) then "mixed"
    elif any(events[] as $e | (.hooks[$e] // [])[]; ours_group) then "present"
    else "absent" end' "${f}" 2>/dev/null || say invalid
}

installed_command() { # the installed post command in a settings file, if any
  jq -r "${JQ_OURS}"'[(.hooks.PostToolUse // [])[] | select(ours_group) | .hooks[0].command][0] // empty' "$1" 2>/dev/null
}

version_ge() { # version_ge have want (dotted numbers)
  local IFS=. i
  local -a h w
  read -r -a h <<<"$1"
  read -r -a w <<<"$2"
  for ((i = 0; i < ${#w[@]}; i++)); do
    local hv=${h[i]:-0} wv=${w[i]:-0}
    hv=${hv%%[!0-9]*}
    wv=${wv%%[!0-9]*}
    ((10#${hv:-0} > 10#${wv:-0})) && return 0
    ((10#${hv:-0} < 10#${wv:-0})) && return 1
  done
  return 0
}

path_bash_version() { bash -c 'printf %s "${BASH_VERSION%%(*}"' 2>/dev/null; }
jq_version() { jq --version 2>/dev/null | sed 's/^jq-//'; }

# The ruff the gate would use for files under ROOT (same order as the handler).
resolve_ruff() {
  local d=${ROOT} c
  RUFF=""
  if [[ -n ${RUFF_BIN:-} && -x ${RUFF_BIN} ]]; then
    RUFF=${RUFF_BIN}
    return 0
  fi
  while [[ -n ${d} ]]; do
    for c in "${d}/.venv/bin/ruff" "${d}/venv/bin/ruff"; do
      if [[ -x ${c} ]]; then
        RUFF=${c}
        return 0
      fi
    done
    [[ ${d} == / ]] && break
    d=$(dirname "${d}")
  done
  if c=$(command -v ruff 2>/dev/null) && [[ -n ${c} ]]; then
    RUFF=${c}
    return 0
  fi
  for c in "${HOME}/.local/bin/ruff" /opt/homebrew/bin/ruff /usr/local/bin/ruff; do
    if [[ -x ${c} ]]; then
      RUFF=${c}
      return 0
    fi
  done
  return 1
}

ruff_version() { "${RUFF}" --version 2>/dev/null | sed -n 's/^ruff \([0-9.]*\).*/\1/p'; }

os_kind() {
  local u
  u=$(uname -s 2>/dev/null) || u=unknown
  case ${u} in
  Darwin) say macos ;;
  Linux)
    if grep -qi microsoft /proc/version 2>/dev/null; then say wsl; else say linux; fi
    ;;
  MINGW* | MSYS* | CYGWIN*) say windows-git-bash ;;
  *) say unknown ;;
  esac
}

managed_settings_file() {
  local os
  os=$(os_kind)
  case ${os} in
  macos) say "/Library/Application Support/ClaudeCode/managed-settings.json" ;;
  linux | wsl) say "/etc/claude-code/managed-settings.json" ;;
  windows-git-bash) say "/c/Program Files/ClaudeCode/managed-settings.json" ;;
  *) say "" ;;
  esac
}

flag_true() { jq -e --arg k "$2" '.[$k] == true' "$1" >/dev/null 2>&1; }

list_hooks() { # list_hooks FILE EVENT
  [[ -f $1 ]] || return 0
  jq -r --arg e "$2" '(.hooks[$e] // [])[]? | "    - \($e) matcher \(.matcher // "*"): " + ([(.hooks // [])[] | (.command // .url // .prompt // .type // "?") | tostring | .[0:110]] | join(" | "))' "$1" 2>/dev/null || say "    (unreadable JSON)"
}

python_files_sample() { # up to N Python files under ROOT, tracked or not ignored
  local n=${1:-20000}
  if git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "${ROOT}" ls-files -co --exclude-standard -- '*.py' '*.pyi' 2>/dev/null | head -n "${n}"
  else
    (cd "${ROOT}" && find . -type f \( -name '*.py' -o -name '*.pyi' \) -not -path '*/.venv/*' -not -path '*/node_modules/*' 2>/dev/null | head -n "${n}")
  fi
}

# Baseline: how many findings each mode would report today on the project.
baseline() { # baseline LABEL ARGS...
  local label=$1 out total
  shift
  out=$(cd "${ROOT}" && "${RUFF}" check --no-cache --force-exclude --statistics --output-format concise "$@" . 2>&1)
  total=$(printf '%s\n' "${out}" | awk '/^ *[0-9]+\t/ || /^ *[0-9]+ +[A-Z]+[0-9]+/ {s += $1} END {print s + 0}')
  say "  ${label}: ${total} finding(s) across the project today"
  printf '%s\n' "${out}" | awk '/^ *[0-9]+[\t ]+[A-Z]+[0-9]+/' | sort -rn | head -n 5 | sed 's/^/      /'
}

# --- assess -------------------------------------------------------------------

cmd_assess() {
  local s st f v n surface="Claude Code" os bv jv rv="missing" mf
  resolve_root
  say "== environment"
  is_cowork && surface="Claude Cowork (UNSUPPORTED: settings hooks do not run here)"
  os=$(os_kind)
  bv=$(path_bash_version) || bv=""
  jv=$(jq_version) || jv=""
  say "surface: ${surface}"
  say "os: ${os}"
  say "bash on PATH: ${bv:-missing}"
  say "jq: ${jv:-missing}"
  if resolve_ruff; then
    rv=$(ruff_version) || rv=unknown
    say "ruff: ${rv} (${RUFF})"
  else
    say "ruff: missing (install: uv tool install ruff, or add ruff to the project's dev dependencies)"
  fi
  say "== project"
  say "project root: ${ROOT}"
  if git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then say "git repository: yes"; else say "git repository: no"; fi
  n=$(python_files_sample | wc -l | tr -d ' ')
  say "python files: ${n}"
  say "== ruff configuration that applies today"
  local project_cfgs user_cfgs
  project_cfgs=$(existing_configs_in "${ROOT}")
  user_cfgs=$(existing_configs_in "${RUFF_USER_DIR}")
  say "project level (${ROOT}): ${project_cfgs:-none}"
  say "user level (${RUFF_USER_DIR}): ${user_cfgs:-none}"
  if [[ -n ${RUFF} ]]; then
    f=$(python_files_sample 1)
    if [[ -n ${f} ]]; then
      v=$(cd "${ROOT}" && "${RUFF}" check --show-settings -- "${f}" 2>/dev/null | sed -n 's/^Settings path: //p' | tr -d '"')
      say "resolved for ${f}: ${v:-Ruff built-in defaults}"
    fi
    if ((n > 0)); then
      say "== baseline (read-only; nothing is fixed)"
      baseline "own (what Ruff resolves today)"
      baseline "recommended (bundled profile)" --config "${SRC_PROFILE}"
      baseline "defaults (--isolated)" --isolated
    fi
  fi
  say "== installed gate"
  for s in project local user; do
    scope_paths "${s}"
    st=$(settings_state "${SETTINGS}")
    say "${s}: ${st} (${SETTINGS})"
  done
  say "== other PostToolUse / Stop hooks (all matching hooks run in parallel)"
  for s in project local user; do
    scope_paths "${s}"
    if [[ -f ${SETTINGS} ]]; then
      say "  ${s}:"
      list_hooks "${SETTINGS}" PostToolUse
      list_hooks "${SETTINGS}" Stop
      if flag_true "${SETTINGS}" disableAllHooks; then say "    WARNING: disableAllHooks is true here"; fi
    fi
  done
  mf=$(managed_settings_file)
  if [[ -n ${mf} && -r ${mf} ]]; then
    if flag_true "${mf}" allowManagedHooksOnly; then say "  WARNING: managed allowManagedHooksOnly is true: user/project/local hooks will not run"; fi
    if flag_true "${mf}" disableAllHooks; then say "  WARNING: managed disableAllHooks is true"; fi
  fi
  say "== verdict"
  if [[ -z ${RUFF} ]]; then
    say "install ruff first: the gate fails closed without it"
  elif ((n == 0)); then
    say "no Python files here yet: project scope would guard future files; user scope covers every project"
  else
    say "ready: choose a scope (project, local, user) and a configuration mode (recommended, own, defaults)"
  fi
}

# --- show-config -----------------------------------------------------------------

cmd_show_config() {
  resolve_root
  need_mode
  case ${mode} in
  recommended)
    say "== recommended: the bundled profile (${SRC_PROFILE})"
    say "project/local scope writes it to ${ROOT}/ruff.toml; user scope writes it to ${RUFF_USER_DIR}/ruff.toml"
    say "(only when no Ruff configuration exists there; an existing one is never overwritten)"
    say "---"
    cat "${SRC_PROFILE}"
    ;;
  own)
    if [[ -n ${config_path} ]]; then
      [[ -f ${config_path} ]] || fail "--config-path does not exist: ${config_path}"
      say "== own: pinned with --config ${config_path} (used for every file, overriding discovery)"
      say "---"
      cat "${config_path}"
    else
      local cfgs f
      cfgs=$(existing_configs_in "${ROOT}")
      [[ -n ${cfgs} ]] || cfgs=$(existing_configs_in "${RUFF_USER_DIR}")
      if [[ -z ${cfgs} ]]; then
        say "== own: no Ruff configuration found at ${ROOT} or ${RUFF_USER_DIR}; Ruff would use its built-in defaults"
        return 0
      fi
      say "== own: Ruff discovers the closest configuration per file; today that is:"
      while IFS= read -r f; do
        say "--- ${f}"
        if [[ ${f} == */pyproject.toml ]]; then
          awk '/^\[tool\.ruff/ {on=1} /^\[/ && !/^\[tool\.ruff/ {on=0} on' "${f}"
        else
          cat "${f}"
        fi
      done <<<"${cfgs}"
    fi
    ;;
  defaults)
    say "== defaults: ruff --isolated ignores every configuration file"
    if resolve_ruff; then
      local tmp settings rules
      tmp=$(mktemp -d) || fail "mktemp failed"
      : >"${tmp}/probe.py"
      settings=$(cd "${tmp}" && "${RUFF}" check --isolated --show-settings -- probe.py 2>/dev/null)
      rm -rf "${tmp}"
      rules=$(printf '%s\n' "${settings}" | awk '/^linter.rules.enabled = \[/ {on=1; next} on && /^\]/ {on=0} on' | grep -c '(' || true)
      local rv
      rv=$(ruff_version) || rv=unknown
      say "ruff ${rv}: ${rules} rules enabled; full list: https://docs.astral.sh/ruff/default-rules/"
      printf '%s\n' "${settings}" | grep -E '^(linter\.line_length|formatter\.line_width|formatter\.indent_style|formatter\.quote_style|linter\.unresolved_target_version) ' | sed 's/^/  /'
    else
      say "ruff is not installed, so its defaults cannot be printed"
    fi
    ;;
  *) ;;
  esac
}

# --- status -------------------------------------------------------------------

cmd_status() {
  local s st ver bundled c
  resolve_root
  bundled=$(bundled_version "${SRC_HANDLER}")
  say "bundled handler version: ${bundled}"
  for s in project local user; do
    scope_paths "${s}"
    st=$(settings_state "${SETTINGS}")
    if [[ -f ${HANDLER_DST} ]]; then ver=$(bundled_version "${HANDLER_DST}"); else ver=missing; fi
    say "${s}: group=${st} handler=${ver} settings=${SETTINGS} handler_path=${HANDLER_DST}"
    if [[ ${st} == present ]]; then
      c=$(installed_command "${SETTINGS}")
      say "  command: ${c}"
      [[ ${ver} == missing ]] && say "  WARNING: the groups point at a missing handler: the hook errors and does NOT gate anything (non-blocking exit). Reinstall or uninstall."
      [[ ${ver} != missing && ${ver} != "${bundled}" ]] && say "  NOTE: installed ${ver}, bundled ${bundled}: reinstall to upgrade"
    fi
  done
  is_cowork && say "surface: Claude Cowork: settings hooks do not run in this session"
  return 0
}

# --- preflight ----------------------------------------------------------------

# Sets CONFIG_ARG (the --config value written into the hook command, or "").
resolve_config_arg() {
  CONFIG_ARG=""
  [[ -n ${config_path} ]] || return 0
  local abs dir=.
  [[ ${config_path} == */* ]] && dir=${config_path%/*}
  dir=$(cd "${dir:-/}" 2>/dev/null && pwd -P) || return 1
  abs="${dir}/${config_path##*/}"
  [[ -f ${abs} ]] || return 1
  case ${abs} in *[\"\$\`\\]*) return 1 ;; *) ;; esac
  if [[ ${scope} != user && ${abs} == "${ROOT}"/* ]]; then
    CONFIG_ARG="\"\$CLAUDE_PROJECT_DIR/${abs#"${ROOT}"/}\""
  elif [[ ${scope} == project ]]; then
    return 2
  else
    CONFIG_ARG="\"${abs}\""
  fi
}

other_scopes_present() { # prints scopes other than the chosen one that have the gate
  local s st saved=${scope}
  for s in project local user; do
    [[ ${s} == "${saved}" ]] && continue
    scope_paths "${s}"
    st=$(settings_state "${SETTINGS}")
    [[ ${st} == present ]] && say "${s}"
  done
  scope_paths "${saved}"
}

cmd_preflight() {
  local problems=0 v st f mf rc others target existing
  refuse_cowork
  resolve_root
  need_scope
  need_mode
  say "scope: ${scope}"
  say "config mode: ${mode}"
  say "settings: ${SETTINGS}"
  say "handler: ${HANDLER_DST}"
  v=$(os_kind)
  say "os: ${v}"
  v=$(path_bash_version) || v=""
  if [[ -z ${v} ]]; then
    say "FAIL bash: not on PATH (Windows needs Git for Windows; without it hooks run in PowerShell)"
    problems=1
  elif version_ge "${v}" 3.2; then say "ok   bash ${v}"; else
    say "FAIL bash ${v} < 3.2"
    problems=1
  fi
  v=$(jq_version) || v=""
  if [[ -z ${v} ]]; then
    say "FAIL jq: not installed (the handler and this installer need it)"
    problems=1
  elif version_ge "${v}" 1.6; then say "ok   jq ${v}"; else
    say "FAIL jq ${v} < 1.6"
    problems=1
  fi
  if resolve_ruff; then
    v=$(ruff_version) || v=""
    if ! version_ge "${v:-0}" "${MIN_RUFF}"; then
      say "FAIL ruff ${v:-unknown} at ${RUFF}: the gate needs ruff >= ${MIN_RUFF} (format --check output formats, 0.16 defaults)"
      problems=1
    else
      say "ok   ruff ${v:-unknown} (${RUFF})"
    fi
  else
    say "FAIL ruff: not found; the gate fails closed without it (install: uv tool install ruff)"
    problems=1
  fi
  v=$(git --version 2>/dev/null | sed -n 's/^git version \([0-9.]*\).*/\1/p') || v=""
  if [[ -z ${v} ]]; then
    say "FAIL git: not on PATH (scopes, backups, and suppression baselines need it)"
    problems=1
  elif version_ge "${v}" 2.18; then
    say "ok   git ${v}"
  else
    say "FAIL git ${v} < 2.18"
    problems=1
  fi
  if [[ ${scope} != user ]] && ! git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    say "FAIL ${ROOT} is not a git repository; use user scope, or run inside the project"
    problems=1
  fi
  resolve_config_arg
  rc=$?
  case ${rc} in
  0) [[ -n ${config_path} ]] && say "ok   pinned config: ${CONFIG_ARG}" ;;
  2)
    say "FAIL project scope is committed: a pinned --config-path must live inside ${ROOT} so teammates have it"
    problems=1
    ;;
  *)
    say "FAIL --config-path must be an existing file whose path has no quotes, \$, backticks, or backslashes: ${config_path}"
    problems=1
    ;;
  esac
  if [[ ${mode} == recommended ]]; then
    target=$(profile_target)
    existing=$(existing_configs_in "$(dirname "${target}")")
    if [[ -n ${existing} ]]; then
      if [[ -f ${target} ]] && cmp -s "${SRC_PROFILE}" "${target}"; then
        say "ok   recommended profile already in place: ${target}"
      else
        say "FAIL a Ruff configuration already exists: ${existing//$'\n'/, }. It is never overwritten. Use --config-mode own to keep it, or merge the recommended profile into it by hand (show-config --config-mode recommended prints it)."
        problems=1
      fi
    else
      say "ok   recommended profile will be written to ${target}"
    fi
  fi
  others=$(other_scopes_present)
  if [[ -n ${others} ]]; then
    say "FAIL the gate is already installed in: ${others//$'\n'/, }. Two copies would fix and format the same file in parallel. Uninstall it there first."
    problems=1
  fi
  st=$(settings_state "${SETTINGS}")
  case ${st} in
  missing) say "ok   settings file absent (will be created)" ;;
  invalid)
    say "FAIL settings file is not a JSON object with array hooks.PostToolUse/Stop; fix it by hand first"
    problems=1
    ;;
  mixed)
    say "FAIL a hand-edited group mixes this handler with other handlers; resolve it by hand first"
    problems=1
    ;;
  present) say "ok   gate already present (install refreshes it in place, no duplicate)" ;;
  *) say "ok   settings file is valid JSON" ;;
  esac
  if [[ -e ${SETTINGS} && ! -w ${SETTINGS} ]]; then
    say "FAIL no write permission for ${SETTINGS}"
    problems=1
  fi
  for f in "${ROOT}/.claude/settings.json" "${ROOT}/.claude/settings.local.json" "${CFG_DIR}/settings.json"; do
    if [[ -f ${f} ]] && flag_true "${f}" disableAllHooks; then
      say "FAIL disableAllHooks is true in ${f}: the gate would never run"
      problems=1
    fi
  done
  mf=$(managed_settings_file)
  if [[ -n ${mf} && -r ${mf} ]] && { flag_true "${mf}" allowManagedHooksOnly || flag_true "${mf}" disableAllHooks; }; then
    say "FAIL managed settings (${mf}) block non-managed hooks: ask your administrator"
    problems=1
  fi
  if ((problems)); then
    say "RESULT: preflight failed; nothing was changed"
    return 1
  fi
  say "RESULT: preflight passed"
}

# --- install / uninstall helpers ------------------------------------------------

backup_dir() {
  local d
  if [[ ${scope} == user ]]; then
    say "${CFG_DIR}/backups/ruff-quality"
    return 0
  fi
  d=$(git -C "${ROOT}" rev-parse --git-common-dir 2>/dev/null) || return 1
  [[ ${d} == /* ]] || d="${ROOT}/${d}"
  say "${d}/ruff-quality-backups"
}

backup_file() { # prints the backup path, or nothing when the file does not exist
  local f=$1 dir stamp b
  [[ -f ${f} ]] || return 0
  dir=$(backup_dir) || return 1
  stamp=$(date -u +%Y%m%dT%H%M%SZ) || return 1
  mkdir -p "${dir}" || return 1
  b="${dir}/$(basename "${f}").${stamp}.$$.bak"
  cp -p "${f}" "${b}" || return 1
  say "${b}"
}

write_json() { # write_json target jq-program [jq args...]; atomic replace
  local target=$1 prog=$2 tmp
  shift 2
  mkdir -p "$(dirname "${target}")" || return 1
  tmp="${target}.ruff-quality.tmp.$$"
  if [[ -f ${target} ]]; then
    jq "$@" "${prog}" "${target}" >"${tmp}" || {
      rm -f "${tmp}"
      return 1
    }
  else
    jq -n "$@" "{} | ${prog}" >"${tmp}" || {
      rm -f "${tmp}"
      return 1
    }
  fi
  jq -e 'type == "object"' "${tmp}" >/dev/null || {
    rm -f "${tmp}"
    return 1
  }
  if [[ -L ${target} ]]; then
    cat "${tmp}" >"${target}" || {
      rm -f "${tmp}"
      return 1
    }
    rm -f "${tmp}"
  else
    mv "${tmp}" "${target}"
  fi
}

exclude_file() { git -C "${ROOT}" rev-parse --git-path info/exclude 2>/dev/null; }

add_local_excludes() { # add_local_excludes REL...
  local ex rel added=0
  ex=$(exclude_file) || return 0
  [[ ${ex} == /* ]] || ex="${ROOT}/${ex}"
  mkdir -p "$(dirname "${ex}")"
  for rel in "$@"; do
    if ! git -C "${ROOT}" check-ignore -q "${rel}" 2>/dev/null && ! git -C "${ROOT}" ls-files --error-unmatch "${rel}" >/dev/null 2>&1; then
      printf '%s\n/%s\n' "${EXCLUDE_MARK}" "${rel}" >>"${ex}"
      say "excluded from git (local only): ${rel} via ${ex}"
      added=1
    fi
  done
  ((added)) || say "git exclusions: already ignored or tracked, nothing added"
}

remove_local_excludes() {
  local ex tmp
  ex=$(exclude_file) || return 0
  [[ ${ex} == /* ]] || ex="${ROOT}/${ex}"
  [[ -f ${ex} ]] && grep -qF "${EXCLUDE_MARK}" "${ex}" || return 0
  tmp="${ex}.tmp.$$"
  awk -v mark="${EXCLUDE_MARK}" '$0 == mark { skip = 1; next } skip { skip = 0; next } { print }' "${ex}" >"${tmp}" && mv "${tmp}" "${ex}"
  say "removed this gate's local exclusions from ${ex}"
}

handler_still_used() {
  local other st
  [[ ${scope} == user ]] && return 1
  if [[ ${scope} == project ]]; then other="${ROOT}/.claude/settings.local.json"; else other="${ROOT}/.claude/settings.json"; fi
  st=$(settings_state "${other}") || st=invalid
  [[ ${st} == present ]]
}

# --- verify -------------------------------------------------------------------

run_verify() {
  local out summary st c f
  [[ -f ${HANDLER_DST} ]] || {
    say "FAIL no installed handler at ${HANDLER_DST}"
    return 1
  }
  st=$(settings_state "${SETTINGS}")
  [[ ${st} == present ]] || {
    say "FAIL ${SETTINGS} has no ruff-quality groups"
    return 1
  }
  if ! out=$(bash "${TEST_SUITE}" "${HANDLER_DST}" 2>&1); then
    printf '%s\n' "${out}" | tail -n 25
    say "FAIL test suite against the installed copy"
    return 1
  fi
  summary=$(printf '%s\n' "${out}" | sed -n '/passed, [0-9]* failed/p')
  say "test suite: ${summary}"
  c=$(installed_command "${SETTINGS}")
  say "installed PostToolUse command: ${c}"
  if resolve_ruff; then
    f=$(python_files_sample 1)
    if [[ -n ${f} ]]; then
      case ${c} in
      *"--config-mode defaults"*) say "config the hook uses: Ruff built-in defaults (--isolated)" ;;
      *"--config "*) say "config the hook uses: pinned (${c##*--config })" ;;
      *)
        f=$(cd "${ROOT}" && "${RUFF}" check --show-settings -- "${f}" 2>/dev/null | sed -n 's/^Settings path: //p' | tr -d '"')
        say "config the hook uses (discovered for this project): ${f:-Ruff built-in defaults}"
        ;;
      esac
    fi
  fi
}

cmd_verify() {
  refuse_cowork
  resolve_root
  need_scope
  run_verify || exit 1
}

# --- install ------------------------------------------------------------------

cmd_install() {
  local settings_backup="" handler_backup="" had_settings=0 had_handler=0 groups target="" wrote_profile=0 ver
  refuse_cowork
  resolve_root
  need_scope
  need_mode
  say "== preflight"
  cmd_preflight || exit 1
  resolve_config_arg || exit 1
  say "== install"
  [[ -f ${SETTINGS} ]] && had_settings=1
  [[ -f ${HANDLER_DST} ]] && had_handler=1
  settings_backup=$(backup_file "${SETTINGS}") || fail "could not back up ${SETTINGS}; nothing changed"
  [[ -n ${settings_backup} ]] && say "settings backup: ${settings_backup}"
  if ((had_handler)); then
    handler_backup=$(backup_file "${HANDLER_DST}") || fail "could not back up ${HANDLER_DST}; nothing changed"
    say "previous handler backup: ${handler_backup}"
  fi

  restore() {
    say "ROLLBACK: restoring the previous state"
    if [[ -n ${settings_backup} ]]; then cp -p "${settings_backup}" "${SETTINGS}"; elif ((! had_settings)); then rm -f "${SETTINGS}"; fi
    if [[ -n ${handler_backup} ]]; then cp -p "${handler_backup}" "${HANDLER_DST}"; elif ((! had_handler)); then rm -f "${HANDLER_DST}"; fi
    ((wrote_profile)) && rm -f "${target}"
    exit 1
  }

  if [[ ${mode} == recommended ]]; then
    target=$(profile_target)
    if [[ ! -f ${target} ]]; then
      mkdir -p "$(dirname "${target}")" || restore
      cp "${SRC_PROFILE}" "${target}" || restore
      wrote_profile=1
      say "recommended profile: wrote ${target} (Ruff discovers it natively; your editor, CI, and manual runs use it too)"
    else
      say "recommended profile: already in place at ${target}"
    fi
  fi

  mkdir -p "${HOOK_DIR}" || restore
  if ! { cp "${SRC_HANDLER}" "${HANDLER_DST}.tmp.$$" && chmod 755 "${HANDLER_DST}.tmp.$$" && mv "${HANDLER_DST}.tmp.$$" "${HANDLER_DST}"; }; then restore; fi
  cmp -s "${SRC_HANDLER}" "${HANDLER_DST}" || restore
  ver=$(bundled_version "${HANDLER_DST}")
  say "handler: ${HANDLER_DST} (byte-identical to the bundled copy, version ${ver})"

  groups=$(groups_json) || restore
  # shellcheck disable=SC2016 # $g, $e, $x are jq variables, not shell expansions
  write_json "${SETTINGS}" "${JQ_OURS}"'
    .hooks = (.hooks // {})
    | reduce events[] as $e (.;
        .hooks[$e] = ([(.hooks[$e] // [])[] | select(ours_group | not)] + $g[$e]))' --argjson g "${groups}" || restore
  say "settings: merged 5 groups into ${SETTINGS}: UserPromptSubmit (baseline), PreToolUse Write|Edit|NotebookEdit|Bash (guard), PostToolUse Write|Edit|NotebookEdit and Bash (post), Stop (gate). Other keys and hooks untouched; whitespace normalized by jq."
  say "== verify"
  run_verify || restore
  if [[ ${scope} == local ]]; then
    if ((wrote_profile)); then add_local_excludes .claude/hooks/ruff-quality-gate.sh .claude/settings.local.json ruff.toml; else add_local_excludes .claude/hooks/ruff-quality-gate.sh .claude/settings.local.json; fi
  fi
  say "== done"
  say "Open /hooks (or restart the session) to confirm the groups are loaded; this script cannot observe live loading."
  [[ ${scope} == project ]] && say "Commit .claude/settings.json and .claude/hooks/ruff-quality-gate.sh together$( ((wrote_profile)) && printf ' with ruff.toml')."
  if [[ -n ${settings_backup} ]]; then
    say "rollback: run manage.sh uninstall --scope ${scope}, or restore ${settings_backup}"
  else
    say "rollback: run manage.sh uninstall --scope ${scope}"
  fi
}

# --- uninstall ----------------------------------------------------------------

cmd_uninstall() {
  local st backup target
  refuse_cowork
  resolve_root
  need_scope
  st=$(settings_state "${SETTINGS}")
  case ${st} in
  invalid) fail "${SETTINGS} is not valid JSON; nothing changed" ;;
  mixed) fail "a hand-edited group mixes this handler with other handlers in ${SETTINGS}; remove it by hand" ;;
  *) ;;
  esac
  if [[ ${st} == present ]]; then
    backup=$(backup_file "${SETTINGS}") || fail "could not back up ${SETTINGS}; nothing changed"
    say "settings backup: ${backup}"
    # shellcheck disable=SC2016 # $e is a jq variable, not a shell expansion
    write_json "${SETTINGS}" "${JQ_OURS}"'
      reduce events[] as $e (.;
        if .hooks[$e] then .hooks[$e] |= map(select(ours_group | not)) | (if (.hooks[$e] | length) == 0 then del(.hooks[$e]) else . end) else . end)
      | if (.hooks | length) == 0 then del(.hooks) else . end' || fail "could not rewrite ${SETTINGS}; restore ${backup}"
    say "removed the ruff-quality groups from ${SETTINGS}; everything else untouched"
    if [[ ${scope} != user ]] && jq -e '. == {}' "${SETTINGS}" >/dev/null 2>&1; then
      rm -f "${SETTINGS}"
      say "deleted the now-empty ${SETTINGS} (backup kept)"
    fi
  else
    say "no ruff-quality groups in ${SETTINGS}"
  fi
  if [[ -f ${HANDLER_DST} ]]; then
    if handler_still_used; then
      say "kept ${HANDLER_DST}: the other project/local scope still uses it"
    else
      rm -f "${HANDLER_DST}"
      rmdir "${HOOK_DIR}" 2>/dev/null || true
      say "deleted ${HANDLER_DST}"
    fi
  fi
  target=$(profile_target)
  if [[ -f ${target} ]]; then
    if cmp -s "${SRC_PROFILE}" "${target}"; then
      say "kept ${target}: it is the recommended profile; it keeps configuring Ruff for your editor and CI. Delete it yourself if you no longer want it."
    else
      say "kept ${target}: it differs from the bundled profile (yours or edited)"
    fi
  fi
  [[ ${scope} == local ]] && remove_local_excludes
  say "Open /hooks (or restart the session) to confirm the groups are gone."
}

command -v jq >/dev/null 2>&1 || {
  say "FAIL jq is required (https://jqlang.org/download/)"
  exit 1
}

case ${cmd} in
assess) cmd_assess ;;
show-config) cmd_show_config ;;
status) cmd_status ;;
preflight) cmd_preflight ;;
install) cmd_install ;;
verify) cmd_verify ;;
uninstall) cmd_uninstall ;;
*)
  sed -n '2,24p' "$0" >&2
  exit 2
  ;;
esac
