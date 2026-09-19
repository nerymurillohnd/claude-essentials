#!/usr/bin/env bash
# shell-quality hook manager. Deterministic, idempotent, backup-first.
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
#   MODE: recommended (write the bundled ShellCheck profile and shfmt style where
#   the tools discover them), own (the configuration you already have, or
#   --config-path FILE for a ShellCheck rc file), defaults (built-in defaults:
#   ShellCheck with --norc, shfmt ignoring EditorConfig).
#   --project-dir DIR overrides the project root (default: $CLAUDE_PROJECT_DIR,
#   then the Git top level, then the current directory).
#
# Exit codes: 0 ok, 1 failed check or error, 2 usage, 3 unsupported surface.
# Needs bash >= 3.2 and jq >= 1.6. Never touches the network.

set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
readonly SKILL_DIR
readonly SRC_HANDLER="${SKILL_DIR}/assets/shell-quality-gate.sh"
readonly SRC_RC="${SKILL_DIR}/assets/shellcheckrc"
readonly SRC_EC="${SKILL_DIR}/assets/editorconfig-shell"
readonly EC_BEGIN="# >>> shell-quality recommended shfmt style >>>"
readonly TEST_SUITE="${SKILL_DIR}/scripts/test-gate.sh"
readonly HANDLER_NAME="shell-quality-gate.sh"
readonly EXCLUDE_MARK="# shell-quality (local scope)"
readonly MIN_SHELLCHECK="0.10.0"
readonly MIN_SHELLCHECK_RECOMMENDED="0.11.0"
readonly MIN_SHFMT="3.12.0"
readonly CFG_DIR=${CLAUDE_CONFIG_DIR:-${HOME}/.claude}
readonly XDG_RC="${XDG_CONFIG_HOME:-${HOME}/.config}/shellcheckrc"
readonly HOME_RC="${HOME}/.shellcheckrc"

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

bundled_version() { sed -n 's/^# shell-quality-version: *//p' "$1" 2>/dev/null | head -n 1; }
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
    CMD_PREFIX='bash "$CLAUDE_PROJECT_DIR/.claude/hooks/shell-quality-gate.sh"'
    ;;
  user)
    SETTINGS="${CFG_DIR}/settings.json"
    HOOK_DIR="${CFG_DIR}/hooks"
    # shellcheck disable=SC2016 # expanded by the hook shell at run time, not here
    if [[ -n ${CLAUDE_CONFIG_DIR:-} ]]; then
      CMD_PREFIX='bash "$CLAUDE_CONFIG_DIR/hooks/shell-quality-gate.sh"'
    else
      CMD_PREFIX='bash "$HOME/.claude/hooks/shell-quality-gate.sh"'
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

# Where the recommended ShellCheck profile goes for the chosen scope.
rc_target() {
  if [[ ${scope} == user ]]; then say "${XDG_RC}"; else say "${ROOT}/.shellcheckrc"; fi
}

# ShellCheck rc files that already govern the chosen scope.
existing_rc() {
  local f
  if [[ ${scope} == user ]]; then
    for f in "${HOME_RC}" "${XDG_RC}"; do [[ -f ${f} ]] && say "${f}"; done
  else
    for f in "${ROOT}/.shellcheckrc" "${ROOT}/shellcheckrc"; do [[ -f ${f} ]] && say "${f}"; done
  fi
  return 0
}

# Does an .editorconfig already set shfmt style for shell scripts?
ec_has_shell_style() { # ec_has_shell_style FILE
  [[ -f $1 ]] || return 1
  awk '
    /^[[:space:]]*\[/ { shell = ($0 ~ /\[\[(shell|bash|posix|mksh|bats)\]\]/ || $0 ~ /sh|bash|bats/) }
    shell && /^[[:space:]]*(indent_style|indent_size|shell_variant|binary_next_line|switch_case_indent|space_redirects|function_next_line|simplify|minify)[[:space:]]*=/ { found = 1 }
    END { exit !found }' "$1"
}

# Print the ShellCheck rc file that applies to scripts in DIR (discovery order).
discovered_rc() { # discovered_rc DIR
  local d=$1 f
  while [[ -n ${d} ]]; do
    for f in "${d}/.shellcheckrc" "${d}/shellcheckrc"; do
      if [[ -f ${f} ]]; then
        say "${f}"
        return 0
      fi
    done
    [[ ${d} == / ]] && break
    d=$(dirname "${d}")
  done
  for f in "${HOME_RC}" "${XDG_RC}"; do
    if [[ -f ${f} ]]; then
      say "${f}"
      return 0
    fi
  done
  return 0
}

# jq program fragments shared by every settings query.
readonly JQ_OURS='def ours_hook: ((.command // "") | tostring | test("^bash \"[^\"]*/hooks/shell-quality-gate[.]sh\"( |$)"));
def ours_group: ((.hooks // []) | length > 0) and all((.hooks // [])[]; ours_hook);
def mixed_group: any((.hooks // [])[]; ours_hook) and (ours_group | not);
def events: ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"];'

# The five groups this gate owns, with the commands for the chosen options.
groups_json() {
  local args="--config-mode ${mode} --max-blocks ${max_blocks}"
  [[ -n ${CONFIG_ARG} ]] && args="${args} --rcfile ${CONFIG_ARG}"
  [[ ${mode} == recommended && ${scope} == user ]] && args="${args} --style-fallback"
  jq -nc --arg p "${CMD_PREFIX}" --arg a "${args}" '{
    UserPromptSubmit: [
      {hooks: [{type: "command", command: "\($p) baseline \($a)", timeout: 30}]}
    ],
    PreToolUse: [
      {matcher: "Write|Edit|Bash", hooks: [{type: "command", command: "\($p) guard \($a)", timeout: 30}]}
    ],
    PostToolUse: [
      {matcher: "Write|Edit", hooks: [{type: "command", command: "\($p) post \($a)", timeout: 60, statusMessage: "shell-quality: formatting and checking the edited shell script"}]},
      {matcher: "Bash", hooks: [{type: "command", command: "\($p) post \($a)", timeout: 60}]}
    ],
    Stop: [
      {hooks: [{type: "command", command: "\($p) stop \($a)", timeout: 120, statusMessage: "shell-quality: Stop gate re-checking edited shell scripts"}]}
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

# The tools the gate would use (same order as the handler).
find_tool() { # find_tool NAME -> TOOL
  local c
  TOOL=""
  if c=$(command -v "$1" 2>/dev/null) && [[ -n ${c} ]]; then
    TOOL=${c}
    return 0
  fi
  for c in "${HOME}/.local/bin/$1" "/opt/homebrew/bin/$1" "/usr/local/bin/$1" "/usr/bin/$1"; do
    if [[ -x ${c} ]]; then
      TOOL=${c}
      return 0
    fi
  done
  return 1
}

resolve_tools() { # sets SHELLCHECK and SHFMT, or returns 1
  SHELLCHECK=""
  SHFMT=""
  find_tool shellcheck && SHELLCHECK=${TOOL}
  find_tool shfmt && SHFMT=${TOOL}
  [[ -n ${SHELLCHECK} && -n ${SHFMT} ]]
}

shellcheck_version() { "${SHELLCHECK}" --version 2>/dev/null | sed -n 's/^version: *//p'; }
shfmt_version() { "${SHFMT}" --version 2>/dev/null | sed 's/^v//'; }

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

shell_files() { # shell scripts under ROOT (tracked or not ignored): extension or shebang
  local f listed first
  if git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    listed=$(git -C "${ROOT}" ls-files -co --exclude-standard 2>/dev/null) || listed=""
  else
    listed=$(cd "${ROOT}" && find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' 2>/dev/null | sed 's|^\./||' | head -n 20000) || listed=""
  fi
  while IFS= read -r f; do
    [[ -n ${f} ]] || continue
    case ${f##*/} in
    *.sh | *.bash | *.bats) say "${f}" ;;
    *.*) ;;
    *)
      first=""
      [[ -f ${ROOT}/${f} ]] && IFS= read -r first <"${ROOT}/${f}" 2>/dev/null
      printf '%s' "${first}" | grep -Eq '^#![[:space:]]*(/usr)?(/local)?/bin/(env[[:space:]]+(-S[[:space:]]+)?)?(ba|da|k)?sh([[:space:]]|$)' && say "${f}"
      ;;
    esac
  done <<<"${listed}"
  return 0
}

# Baseline: what each mode would report today on the project's scripts.
baseline() { # baseline LABEL SHELLCHECK_ARGS... (reads SCRIPTS)
  local label=$1 out findings unformatted=0 f
  shift
  out=$(cd "${ROOT}" && printf '%s\n' "${SCRIPTS}" | tr '\n' '\0' | xargs -0 "${SHELLCHECK}" "$@" -f gcc -- 2>&1)
  findings=$(printf '%s\n' "${out}" | grep -c ': \(error\|warning\|note\|style\): ' || true)
  say "  ${label}: ${findings} ShellCheck finding(s)"
  printf '%s\n' "${out}" | sed -n 's/.*\[\(SC[0-9]*\)\]$/\1/p' | sort | uniq -c | sort -rn | head -n 5 | sed 's/^/      /'
  while IFS= read -r f; do
    [[ -n ${f} ]] || continue
    (cd "${ROOT}" && "${SHFMT}" ${SHFMT_MODE_ARGS[@]+"${SHFMT_MODE_ARGS[@]}"} -l -- "${f}" >/dev/null 2>&1) || unformatted=$((unformatted + 1))
  done <<<"${SCRIPTS}"
  say "      shfmt: ${unformatted} script(s) not formatted in this mode"
}

# --- assess -------------------------------------------------------------------

cmd_assess() {
  local s st v n surface="Claude Code" os bv jv mf rc
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
  resolve_tools
  if [[ -n ${SHELLCHECK} ]]; then
    v=$(shellcheck_version) || v=unknown
    say "shellcheck: ${v} (${SHELLCHECK})"
  else say "shellcheck: missing (brew install shellcheck, apt install shellcheck)"; fi
  if [[ -n ${SHFMT} ]]; then
    v=$(shfmt_version) || v=unknown
    say "shfmt: ${v} (${SHFMT})"
  else say "shfmt: missing (brew install shfmt, or a release from github.com/mvdan/sh)"; fi
  say "== project"
  say "project root: ${ROOT}"
  if git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then say "git repository: yes"; else say "git repository: no"; fi
  SCRIPTS=$(shell_files)
  n=$(printf '%s' "${SCRIPTS}" | grep -c . || true)
  say "shell scripts: ${n}"
  say "== configuration that applies today"
  rc=$(discovered_rc "${ROOT}")
  say "ShellCheck rc for scripts at the root: ${rc:-none (ShellCheck defaults)}"
  if [[ -f ${ROOT}/.editorconfig ]]; then
    if ec_has_shell_style "${ROOT}/.editorconfig"; then say "EditorConfig: ${ROOT}/.editorconfig sets shfmt style for shell scripts"; else say "EditorConfig: ${ROOT}/.editorconfig exists but sets no shell-specific style (its [*] keys still apply)"; fi
  else
    say "EditorConfig: none at the root (shfmt uses tabs and the dialect from each script)"
  fi
  if [[ -n ${SHELLCHECK} && -n ${SHFMT} ]] && ((n > 0)); then
    say "== baseline (read-only; nothing is changed)"
    SHFMT_MODE_ARGS=()
    baseline "own (what the tools resolve today)"
    baseline "recommended (bundled profile)" --rcfile "${SRC_RC}"
    SHFMT_MODE_ARGS=(-i 0)
    baseline "defaults (--norc; shfmt without EditorConfig)" --norc
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
  if [[ -z ${SHELLCHECK} || -z ${SHFMT} ]]; then
    say "install shellcheck and shfmt first: the gate fails closed without them"
  elif ((n == 0)); then
    say "no shell scripts here yet: project scope would guard future scripts; user scope covers every project"
  else
    say "ready: choose a scope (project, local, user) and a configuration mode (recommended, own, defaults)"
  fi
}

# --- show-config -----------------------------------------------------------------

cmd_show_config() {
  local rc
  resolve_root
  need_mode
  case ${mode} in
  recommended)
    say "== recommended: the bundled ShellCheck profile (${SRC_RC})"
    say "project/local scope writes it to ${ROOT}/.shellcheckrc; user scope writes it to ${XDG_RC}"
    say "(only when no rc file exists there; an existing one is never overwritten)"
    say "---"
    cat "${SRC_RC}"
    say ""
    say "== recommended: the shfmt style (${SRC_EC})"
    say "project/local scope appends this block to ${ROOT}/.editorconfig (created if missing), unless it already sets a shell style;"
    say "user scope passes the same style as flags (-i 2 -ci -bn -s) only to scripts that no .editorconfig governs"
    say "---"
    cat "${SRC_EC}"
    ;;
  own)
    if [[ -n ${config_path} ]]; then
      [[ -f ${config_path} ]] || fail "--config-path does not exist: ${config_path}"
      say "== own: ShellCheck pinned with --rcfile ${config_path} (used for every script, overriding discovery)"
      say "---"
      cat "${config_path}"
    else
      rc=$(discovered_rc "${ROOT}")
      if [[ -n ${rc} ]]; then
        say "== own: ShellCheck uses the closest rc file per script; for the project root that is ${rc}"
        say "---"
        cat "${rc}"
      else
        say "== own: no ShellCheck rc file found at ${ROOT}, ~/.shellcheckrc, or ${XDG_RC}; ShellCheck would use its defaults"
      fi
    fi
    say ""
    if [[ -f ${ROOT}/.editorconfig ]]; then
      say "== own: shfmt reads EditorConfig; these lines of ${ROOT}/.editorconfig decide shell formatting:"
      grep -Ei '^[[:space:]]*(\[|root|indent_style|indent_size|shell_variant|binary_next_line|switch_case_indent|space_redirects|function_next_line|simplify|minify|ignore)' "${ROOT}/.editorconfig" || true
    else
      say "== own: no .editorconfig at the root; shfmt uses tabs and detects the dialect from each script"
    fi
    ;;
  defaults)
    say "== defaults: shellcheck --norc ignores every rc file: default checks only (severity style and above, no optional checks, sourced files not followed)"
    say "== defaults: shfmt -i 0 ignores EditorConfig: tabs, dialect from the extension or shebang, no simplification"
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
  local problems=0 v min st f mf rc others target existing
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
  resolve_tools
  if [[ -z ${SHELLCHECK} ]]; then
    say "FAIL shellcheck: not found; the gate fails closed without it (brew install shellcheck, apt install shellcheck)"
    problems=1
  else
    v=$(shellcheck_version) || v=""
    min=${MIN_SHELLCHECK}
    [[ ${mode} == recommended ]] && min=${MIN_SHELLCHECK_RECOMMENDED}
    if version_ge "${v:-0}" "${min}"; then say "ok   shellcheck ${v} (${SHELLCHECK})"; else
      say "FAIL shellcheck ${v:-unknown} at ${SHELLCHECK}: this mode needs >= ${min}"
      problems=1
    fi
  fi
  if [[ -z ${SHFMT} ]]; then
    say "FAIL shfmt: not found; the gate fails closed without it (brew install shfmt, or a release from github.com/mvdan/sh)"
    problems=1
  else
    v=$(shfmt_version) || v=""
    if version_ge "${v:-0}" "${MIN_SHFMT}"; then say "ok   shfmt ${v} (${SHFMT})"; else
      say "FAIL shfmt ${v:-unknown} at ${SHFMT}: needs >= ${MIN_SHFMT}"
      problems=1
    fi
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
    say "FAIL project scope is committed: a pinned --config-path (ShellCheck rc) must live inside ${ROOT} so teammates have it"
    problems=1
    ;;
  *)
    say "FAIL --config-path must be an existing file whose path has no quotes, \$, backticks, or backslashes: ${config_path}"
    problems=1
    ;;
  esac
  if [[ ${mode} == recommended ]]; then
    target=$(rc_target)
    existing=$(existing_rc)
    if [[ -n ${existing} ]]; then
      if [[ -f ${target} ]] && cmp -s "${SRC_RC}" "${target}"; then
        say "ok   recommended ShellCheck profile already in place: ${target}"
      else
        say "FAIL a ShellCheck rc file already exists: ${existing//$'\n'/, }. It is never overwritten. Use --config-mode own to keep it, or merge the recommended profile into it by hand (show-config --config-mode recommended prints it)."
        problems=1
      fi
    else
      say "ok   recommended ShellCheck profile will be written to ${target}"
    fi
    if [[ ${scope} == user ]]; then
      say "ok   shfmt style: passed as flags to scripts that no .editorconfig governs (no file written)"
    elif grep -qF "${EC_BEGIN}" "${ROOT}/.editorconfig" 2>/dev/null; then
      say "ok   shfmt style block already in ${ROOT}/.editorconfig"
    elif ec_has_shell_style "${ROOT}/.editorconfig"; then
      say "ok   ${ROOT}/.editorconfig already sets a shell style; it is kept and the recommended block is not added"
    else
      say "ok   shfmt style block will be appended to ${ROOT}/.editorconfig (created if missing)"
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
    say "FAIL settings file is not a JSON object with array hook lists; fix it by hand first"
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
    say "${CFG_DIR}/backups/shell-quality"
    return 0
  fi
  d=$(git -C "${ROOT}" rev-parse --git-common-dir 2>/dev/null) || return 1
  [[ ${d} == /* ]] || d="${ROOT}/${d}"
  say "${d}/shell-quality-backups"
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
  tmp="${target}.shell-quality.tmp.$$"
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
    say "FAIL ${SETTINGS} has no shell-quality groups"
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
  case ${c} in
  *"--config-mode defaults"*) say "configuration the hook uses: shellcheck --norc and shfmt -i 0 (built-in defaults)" ;;
  *"--rcfile "*) say "configuration the hook uses: pinned ShellCheck rc ${c##*--rcfile }; shfmt reads EditorConfig" ;;
  *)
    f=$(discovered_rc "${ROOT}")
    local extra=""
    [[ ${c} == *--style-fallback* ]] && extra=", with the recommended style for scripts no .editorconfig governs"
    say "configuration the hook uses: ShellCheck rc ${f:-none (defaults)}; shfmt reads EditorConfig${extra}"
    ;;
  esac
}

cmd_verify() {
  refuse_cowork
  resolve_root
  need_scope
  run_verify || exit 1
}

# --- install ------------------------------------------------------------------

cmd_install() {
  local settings_backup="" handler_backup="" had_settings=0 had_handler=0 groups target="" wrote_profile=0 ver ec="" ec_backup="" had_ec=0 wrote_ec=0
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
    if ((wrote_ec)); then
      if [[ -n ${ec_backup} ]]; then cp -p "${ec_backup}" "${ec}"; elif ((! had_ec)); then rm -f "${ec}"; fi
    fi
    exit 1
  }

  if [[ ${mode} == recommended ]]; then
    target=$(rc_target)
    if [[ ! -f ${target} ]]; then
      mkdir -p "$(dirname "${target}")" || restore
      cp "${SRC_RC}" "${target}" || restore
      wrote_profile=1
      say "recommended ShellCheck profile: wrote ${target} (ShellCheck discovers it natively; your editor, CI, and manual runs use it too)"
    else
      say "recommended ShellCheck profile: already in place at ${target}"
    fi
    if [[ ${scope} != user ]]; then
      ec="${ROOT}/.editorconfig"
      if grep -qF "${EC_BEGIN}" "${ec}" 2>/dev/null; then
        say "shfmt style: block already in ${ec}"
      elif ec_has_shell_style "${ec}"; then
        say "shfmt style: ${ec} already sets a shell style; kept as is"
      else
        [[ -f ${ec} ]] && had_ec=1
        ec_backup=$(backup_file "${ec}") || restore
        {
          [[ -f ${ec} ]] || printf 'root = true\n'
          printf '\n'
          cat "${SRC_EC}"
        } >>"${ec}" || restore
        wrote_ec=1
        say "shfmt style: appended the recommended [[shell]] block to ${ec}"
      fi
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
  say "settings: merged 5 groups into ${SETTINGS}: UserPromptSubmit (baseline), PreToolUse Write|Edit|Bash (guard), PostToolUse Write|Edit and Bash (post), Stop (gate). Other keys and hooks untouched; whitespace normalized by jq."
  say "== verify"
  run_verify || restore
  if [[ ${scope} == local ]]; then
    if ((wrote_profile)); then add_local_excludes .claude/hooks/shell-quality-gate.sh .claude/settings.local.json .shellcheckrc; else add_local_excludes .claude/hooks/shell-quality-gate.sh .claude/settings.local.json; fi
  fi
  say "== done"
  say "Open /hooks (or restart the session) to confirm the groups are loaded; this script cannot observe live loading."
  [[ ${scope} == project ]] && say "Commit .claude/settings.json and .claude/hooks/shell-quality-gate.sh together, with .shellcheckrc and .editorconfig when they were written."
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
    say "removed the shell-quality groups from ${SETTINGS}; everything else untouched"
    if [[ ${scope} != user ]] && jq -e '. == {}' "${SETTINGS}" >/dev/null 2>&1; then
      rm -f "${SETTINGS}"
      say "deleted the now-empty ${SETTINGS} (backup kept)"
    fi
  else
    say "no shell-quality groups in ${SETTINGS}"
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
  target=$(rc_target)
  if [[ -f ${target} ]]; then
    if cmp -s "${SRC_RC}" "${target}"; then
      say "kept ${target}: it is the recommended ShellCheck profile; your editor and CI may rely on it. Delete it yourself if you no longer want it."
    else
      say "kept ${target}: it differs from the bundled profile (yours or edited)"
    fi
  fi
  if [[ ${scope} != user ]] && grep -qF "${EC_BEGIN}" "${ROOT}/.editorconfig" 2>/dev/null; then
    say "kept the recommended [[shell]] block in ${ROOT}/.editorconfig (between the shell-quality markers); remove it yourself if you no longer want it."
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
