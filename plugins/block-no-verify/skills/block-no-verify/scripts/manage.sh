#!/usr/bin/env bash
# block-no-verify policy manager. Deterministic, idempotent, backup-first.
#
# Usage:
#   manage.sh assess                              read-only report
#   manage.sh status                              read-only: where it is installed
#   manage.sh preflight --scope SCOPE             read-only checks before install
#   manage.sh install   --scope SCOPE             copy handler + merge one group
#   manage.sh verify    --scope SCOPE             run the test suite on the installed copy
#   manage.sh uninstall --scope SCOPE             remove only this policy
#
#   SCOPE: project (.claude/settings.json, shared), local
#   (.claude/settings.local.json, this machine), user (~/.claude/settings.json).
#   --project-dir DIR overrides the project root (default: $CLAUDE_PROJECT_DIR,
#   then the Git top level, then the current directory).
#
# Exit codes: 0 ok, 1 failed check or error, 2 usage, 3 unsupported surface.
# Needs bash >= 3.2 and jq >= 1.6. Never touches the network.

set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
readonly SKILL_DIR
readonly SRC_HANDLER="${SKILL_DIR}/assets/block-no-verify.sh"
readonly FRAGMENT="${SKILL_DIR}/assets/settings-fragment.json"
readonly TEST_SUITE="${SKILL_DIR}/scripts/test-handler.sh"
readonly HANDLER_NAME="block-no-verify.sh"
readonly EXCLUDE_MARK="# block-no-verify (local scope)"
# Claude Code reads user settings from CLAUDE_CONFIG_DIR when it is set.
readonly CFG_DIR=${CLAUDE_CONFIG_DIR:-${HOME}/.claude}

cmd=${1:-}
[[ $# -gt 0 ]] && shift
scope=""
project_dir=""
while [[ $# -gt 0 ]]; do
  case $1 in
  --scope)
    scope=${2:-}
    shift 2 || true
    ;;
  --scope=*)
    scope=${1#--scope=}
    shift
    ;;
  --project-dir)
    project_dir=${2:-}
    shift 2 || true
    ;;
  --project-dir=*)
    project_dir=${1#--project-dir=}
    shift
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

bundled_version() {
  sed -n 's/^# block-no-verify-version: *//p' "$1" 2>/dev/null | head -n 1
}

is_cowork() { [[ -n ${CLAUDE_CODE_IS_COWORK:-} ]]; }

refuse_cowork() {
  if is_cowork; then
    say "UNSUPPORTED: this is a Claude Cowork session. Cowork runs in a sandbox that does not load settings-based hooks, so this policy cannot protect anything here and nothing was changed. Use Claude Code (CLI, Desktop, IDE) to install it."
    exit 3
  fi
}

resolve_root() {
  if [[ -n ${project_dir} ]]; then
    ROOT=$(cd "${project_dir}" 2>/dev/null && pwd) || fail "--project-dir does not exist: ${project_dir}"
  elif [[ -n ${CLAUDE_PROJECT_DIR:-} && -d ${CLAUDE_PROJECT_DIR} ]]; then
    ROOT=${CLAUDE_PROJECT_DIR}
  elif ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
    :
  else
    ROOT=$(pwd)
  fi
}

# Sets SETTINGS, HOOK_DIR, HANDLER_DST, COMMAND for a scope.
scope_paths() {
  case $1 in
  project | local)
    if [[ $1 == project ]]; then SETTINGS="${ROOT}/.claude/settings.json"; else SETTINGS="${ROOT}/.claude/settings.local.json"; fi
    HOOK_DIR="${ROOT}/.claude/hooks"
    # shellcheck disable=SC2016 # expanded by the hook shell at run time, not here
    COMMAND='bash "$CLAUDE_PROJECT_DIR/.claude/hooks/block-no-verify.sh"'
    ;;
  user)
    SETTINGS="${CFG_DIR}/settings.json"
    HOOK_DIR="${CFG_DIR}/hooks"
    # shellcheck disable=SC2016 # expanded by the hook shell at run time, not here
    if [[ -n ${CLAUDE_CONFIG_DIR:-} ]]; then
      COMMAND='bash "$CLAUDE_CONFIG_DIR/hooks/block-no-verify.sh"'
    else
      COMMAND='bash "$HOME/.claude/hooks/block-no-verify.sh"'
    fi
    ;;
  *) return 1 ;;
  esac
  HANDLER_DST="${HOOK_DIR}/${HANDLER_NAME}"
}

need_scope() {
  case ${scope} in
  project | local | user) scope_paths "${scope}" ;;
  *)
    say "manage.sh ${cmd}: --scope must be project, local, or user" >&2
    exit 2
    ;;
  esac
}

# jq program fragments shared by every settings query.
readonly JQ_OURS='def ours_hook: ((.command // "") | tostring | test("^bash \"[^\"]*/hooks/block-no-verify[.]sh\"$"));
def ours_group: ((.hooks // []) | length > 0) and all((.hooks // [])[]; ours_hook);
def mixed_group: any((.hooks // [])[]; ours_hook) and (ours_group | not);'

group_json() {
  jq -c --arg cmd "${COMMAND}" '.hooks[0].command = $cmd' "${FRAGMENT}"
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
    elif ((.hooks // {}) | type) != "object" or ((.hooks.PreToolUse // []) | type) != "array" then "invalid"
    elif any((.hooks.PreToolUse // [])[]; mixed_group) then "mixed"
    elif any((.hooks.PreToolUse // [])[]; ours_group) then "present"
    else "absent" end' "${f}" 2>/dev/null || say invalid
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

os_kind() {
  case $(uname -s 2>/dev/null) in
  Darwin) say macos ;;
  Linux)
    if grep -qi microsoft /proc/version 2>/dev/null; then say wsl; else say linux; fi
    ;;
  MINGW* | MSYS* | CYGWIN*) say windows-git-bash ;;
  *) say unknown ;;
  esac
}

managed_settings_file() {
  case $(os_kind) in
  macos) say "/Library/Application Support/ClaudeCode/managed-settings.json" ;;
  linux | wsl) say "/etc/claude-code/managed-settings.json" ;;
  windows-git-bash) say "/c/Program Files/ClaudeCode/managed-settings.json" ;;
  *) say "" ;;
  esac
}

# Prints each PreToolUse group of a settings file as "matcher -> command(s)".
list_pretool() {
  local f=$1
  [[ -f ${f} ]] || return 0
  jq -r '(.hooks.PreToolUse // [])[]? | "    - matcher \(.matcher // "*"): " + ([(.hooks // [])[] | (.command // .url // .prompt // .type // "?") | tostring | .[0:100]] | join(" | "))' "${f}" 2>/dev/null || say "    (unreadable JSON)"
}

handler_works() { # bypass denied and a clean command allowed
  local d a
  d=$(sample_decision "$1" 'git commit --no-verify -m wip') || d=ERROR
  a=$(sample_decision "$1" 'git status') || a=ERROR
  [[ ${d} == DENY && ${a} == ALLOW ]]
}

flag_true() { # flag_true FILE KEY: the top-level boolean KEY is true
  jq -e --arg k "$2" '.[$k] == true' "$1" >/dev/null 2>&1
}

sample_decision() { # $1 handler, $2 command -> ALLOW|DENY|ERROR
  local out rc
  out=$(jq -nc --arg c "$2" '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:$c}}' | bash "$1" 2>/dev/null)
  rc=$?
  if ((rc == 0)) && [[ -z ${out} ]]; then
    say ALLOW
  elif ((rc == 2)); then
    say DENY
  else
    say "ERROR(${rc})"
  fi
}

# --- assess -------------------------------------------------------------------

cmd_assess() {
  local repo=0 gitdir hooks_path hp_dir f v n=0 protectable=0 s st
  resolve_root
  say "== environment"
  local surface="Claude Code" os bv jv
  is_cowork && surface="Claude Cowork (UNSUPPORTED: settings hooks do not run here)"
  os=$(os_kind) || os=unknown
  bv=$(path_bash_version) || bv=missing
  jv=$(jq_version) || jv=missing
  say "surface: ${surface}"
  say "os: ${os}"
  say "bash on PATH: ${bv:-missing}"
  say "jq: ${jv:-missing}"
  say "== repository"
  say "project root: ${ROOT}"
  if git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    repo=1
    say "git repository: yes"
  else
    say "git repository: no"
  fi
  say "== local verification"
  if ((repo)); then
    hooks_path=$(git -C "${ROOT}" config --get core.hooksPath 2>/dev/null || true)
    say "core.hooksPath: ${hooks_path:-(unset)}"
    [[ -d ${ROOT}/.husky ]] && {
      say "husky: .husky/ present"
      protectable=1
    }
    [[ -f ${ROOT}/.pre-commit-config.yaml ]] && {
      say "pre-commit: .pre-commit-config.yaml present"
      protectable=1
    }
    for f in lefthook.yml .lefthook.yml lefthook.yaml .lefthook.yaml lefthook.json .lefthook.json lefthook.toml .lefthook.toml; do
      if [[ -f ${ROOT}/${f} ]]; then
        say "lefthook: ${f} present"
        protectable=1
      fi
    done
    if [[ -n ${hooks_path} ]]; then
      hp_dir=${hooks_path}
      [[ ${hp_dir} == /* ]] || hp_dir="${ROOT}/${hp_dir}"
    else
      gitdir=$(git -C "${ROOT}" rev-parse --git-path hooks 2>/dev/null || true)
      hp_dir=${gitdir}
      [[ -z ${hp_dir} || ${hp_dir} == /* ]] || hp_dir="${ROOT}/${hp_dir}"
    fi
    if [[ -n ${hp_dir} && -d ${hp_dir} ]]; then
      for f in "${hp_dir}"/*; do
        [[ -f ${f} && -x ${f} && ${f} != *.sample ]] || continue
        say "active git hook: ${f#"${ROOT}"/}"
        n=$((n + 1))
      done
    fi
    ((n > 0)) && protectable=1
    say "== signing"
    for f in commit.gpgsign tag.gpgsign gpg.format; do
      v=$(git -C "${ROOT}" config --get "${f}" 2>/dev/null || true)
      say "${f}: ${v:-(unset)}"
    done
    if git -C "${ROOT}" config --get user.signingkey >/dev/null 2>&1; then say "user.signingkey: set"; else say "user.signingkey: (unset)"; fi
    v=$(git -C "${ROOT}" config --type=bool --get commit.gpgsign 2>/dev/null || true)
    [[ ${v} == true ]] && protectable=1
    v=$(git -C "${ROOT}" config --type=bool --get tag.gpgsign 2>/dev/null || true)
    [[ ${v} == true ]] && protectable=1
  fi
  say "== installed policy"
  for s in project local user; do
    scope_paths "${s}"
    st=$(settings_state "${SETTINGS}") || st=invalid
    say "${s}: ${st} (${SETTINGS})"
  done
  say "== existing PreToolUse hooks (they all run in parallel; the most restrictive decision wins)"
  for s in project local user; do
    scope_paths "${s}"
    if [[ -f ${SETTINGS} ]]; then
      say "  ${s}:"
      list_pretool "${SETTINGS}"
      if flag_true "${SETTINGS}" disableAllHooks; then say "    WARNING: disableAllHooks is true here"; fi
    fi
  done
  f=$(managed_settings_file)
  if [[ -n ${f} && -r ${f} ]]; then
    say "  managed (${f}):"
    list_pretool "${f}"
    if flag_true "${f}" allowManagedHooksOnly; then say "    WARNING: allowManagedHooksOnly is true: user/project/local hooks will not run"; fi
    if flag_true "${f}" disableAllHooks; then say "    WARNING: managed disableAllHooks is true"; fi
  fi
  if [[ -d ${CFG_DIR}/plugins/cache ]]; then
    local found=0 plugin_hooks
    plugin_hooks=$(find "${CFG_DIR}/plugins/cache" -maxdepth 5 -path '*/hooks/hooks.json' -type f 2>/dev/null) || plugin_hooks=""
    while IFS= read -r f; do
      [[ -n ${f} ]] || continue
      if jq -e '(.hooks.PreToolUse // [])[]? | select(((.matcher // "") | tostring | test("Bash|PowerShell|^\\*?$")))' "${f}" >/dev/null 2>&1; then
        ((found)) || say "  installed plugins with PreToolUse shell hooks (active only if the plugin is enabled):"
        found=1
        say "    - ${f#"${HOME}"/.claude/plugins/cache/}"
      fi
    done <<<"${plugin_hooks}"
  fi
  say "== verdict"
  if ((! repo)); then
    say "not a git repository: project and local scope protect nothing here; user scope still covers other repositories"
  elif ((protectable)); then
    say "worth installing: this repository has local hooks and/or required signing that a bypass would skip"
  else
    say "nothing to protect here yet: no local hooks and no required signing were found"
  fi
}

# --- status -------------------------------------------------------------------

cmd_status() {
  local s st ver bundled
  resolve_root
  bundled=$(bundled_version "${SRC_HANDLER}")
  say "bundled handler version: ${bundled}"
  for s in project local user; do
    scope_paths "${s}"
    st=$(settings_state "${SETTINGS}")
    if [[ -f ${HANDLER_DST} ]]; then ver=$(bundled_version "${HANDLER_DST}"); else ver=missing; fi
    say "${s}: group=${st} handler=${ver} settings=${SETTINGS} handler_path=${HANDLER_DST}"
    if [[ ${st} == present && ${ver} == missing ]]; then say "  WARNING: the group points at a missing handler: the hook errors and does NOT block (non-blocking exit). Reinstall or uninstall."; fi
    if [[ ${st} == present && ${ver} != missing && ${ver} != "${bundled}" ]]; then say "  NOTE: installed ${ver}, bundled ${bundled}: reinstall to upgrade"; fi
  done
  is_cowork && say "surface: Claude Cowork: settings hooks do not run in this session"
  return 0
}

# --- preflight ----------------------------------------------------------------

cmd_preflight() {
  local problems=0 v st f mf
  refuse_cowork
  resolve_root
  need_scope
  say "scope: ${scope}"
  say "settings: ${SETTINGS}"
  say "handler: ${HANDLER_DST}"
  v=$(os_kind) || v=unknown
  say "os: ${v}"
  v=$(path_bash_version || true)
  if [[ -z ${v} ]]; then
    say "FAIL bash: not on PATH (Windows needs Git for Windows; without it hooks run in PowerShell)"
    problems=1
  elif version_ge "${v}" 3.2; then
    say "ok   bash ${v}"
  else
    say "FAIL bash ${v} < 3.2"
    problems=1
  fi
  v=$(jq_version || true)
  if [[ -z ${v} ]]; then
    say "FAIL jq: not installed (required by the handler)"
    problems=1
  elif version_ge "${v}" 1.6; then
    say "ok   jq ${v}"
  else
    say "FAIL jq ${v} < 1.6"
    problems=1
  fi
  if [[ ${scope} != user ]] && ! git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    say "FAIL ${ROOT} is not a git repository; project/local scope would protect nothing"
    problems=1
  fi
  st=$(settings_state "${SETTINGS}")
  case ${st} in
  missing) say "ok   settings file absent (will be created)" ;;
  invalid)
    say "FAIL settings file is not a JSON object with an array hooks.PreToolUse; fix it by hand first"
    problems=1
    ;;
  mixed)
    say "FAIL a hand-edited group mixes this handler with other handlers; resolve it by hand first"
    problems=1
    ;;
  present) say "ok   policy already present (install will refresh it in place, no duplicate)" ;;
  *) say "ok   settings file is valid JSON" ;;
  esac
  if [[ -e ${SETTINGS} && ! -w ${SETTINGS} ]] || [[ ! -e ${SETTINGS} && -e $(dirname "${SETTINGS}") && ! -w $(dirname "${SETTINGS}") ]]; then
    say "FAIL no write permission for ${SETTINGS}"
    problems=1
  fi
  for f in "${ROOT}/.claude/settings.json" "${ROOT}/.claude/settings.local.json" "${CFG_DIR}/settings.json"; do
    if [[ -f ${f} ]] && flag_true "${f}" disableAllHooks; then
      say "FAIL disableAllHooks is true in ${f}: the policy would never run"
      problems=1
    fi
  done
  mf=$(managed_settings_file)
  if [[ -n ${mf} && -r ${mf} ]]; then
    if flag_true "${mf}" allowManagedHooksOnly || flag_true "${mf}" disableAllHooks; then
      say "FAIL managed settings (${mf}) block non-managed hooks: ask your administrator to deploy the policy instead"
      problems=1
    fi
  fi
  say "note file-based managed settings only; MDM or server-managed policy can still block non-managed hooks, which /hooks will show"
  if handler_works "${SRC_HANDLER}"; then
    say "ok   handler runs on this machine (bypass denied, clean command allowed)"
  else
    say "FAIL the handler does not run correctly with this machine's bash/jq"
    problems=1
  fi
  if ((problems)); then
    say "RESULT: preflight failed; nothing was changed"
    return 1
  fi
  say "RESULT: preflight passed"
}

# --- install / uninstall helpers ------------------------------------------------

# Backups live outside the working tree so they can never be committed:
# <git common dir>/block-no-verify-backups for project/local, and
# ~/.claude/backups/block-no-verify for user scope.
backup_dir() {
  local d
  if [[ ${scope} == user ]]; then
    say "${CFG_DIR}/backups/block-no-verify"
    return 0
  fi
  d=$(git -C "${ROOT}" rev-parse --git-common-dir 2>/dev/null) || return 1
  [[ ${d} == /* ]] || d="${ROOT}/${d}"
  say "${d}/block-no-verify-backups"
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

up_to_date() { # handler byte-identical and exactly one identical group present
  local group
  [[ -f ${HANDLER_DST} && -f ${SETTINGS} ]] || return 1
  cmp -s "${SRC_HANDLER}" "${HANDLER_DST}" || return 1
  group=$(group_json) || return 1
  jq -e --argjson g "${group}" "${JQ_OURS}"' ([(.hooks.PreToolUse // [])[] | select(ours_group)] | length == 1) and any((.hooks.PreToolUse // [])[]; . == $g)' "${SETTINGS}" >/dev/null 2>&1
}

write_json() { # write_json target jq-program [jq args...]; atomic replace
  local target=$1 prog=$2 tmp
  shift 2
  mkdir -p "$(dirname "${target}")" || return 1
  tmp="${target}.block-no-verify.tmp.$$"
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
    # Write through a symlink (dotfile managers) instead of replacing the link.
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

add_local_excludes() {
  local ex rel added=0
  ex=$(exclude_file) || return 0
  [[ ${ex} == /* ]] || ex="${ROOT}/${ex}"
  mkdir -p "$(dirname "${ex}")"
  local project_state
  project_state=$(settings_state "${ROOT}/.claude/settings.json") || project_state=invalid
  for rel in .claude/hooks/block-no-verify.sh .claude/settings.local.json; do
    # The project scope commits the shared handler; never hide it from git.
    [[ ${rel} == *.sh && ${project_state} == present ]] && continue
    if ! git -C "${ROOT}" check-ignore -q "${rel}" 2>/dev/null && ! git -C "${ROOT}" ls-files --error-unmatch "${rel}" >/dev/null 2>&1; then
      printf '%s\n/%s\n' "${EXCLUDE_MARK}" "${rel}" >>"${ex}"
      say "excluded from git (local only): ${rel} via ${ex}"
      added=1
    fi
  done
  ((added)) || say "git exclusions: already ignored or tracked, nothing added"
}

remove_local_excludes() { # $1: "handler" removes only the handler exclusion
  local ex tmp only=${1:-}
  ex=$(exclude_file) || return 0
  [[ ${ex} == /* ]] || ex="${ROOT}/${ex}"
  [[ -f ${ex} ]] && grep -qF "${EXCLUDE_MARK}" "${ex}" || return 0
  tmp="${ex}.tmp.$$"
  awk -v mark="${EXCLUDE_MARK}" -v only="${only}" '
    $0 == mark { held = $0; next }
    held != "" { if (only == "handler" && $0 !~ /block-no-verify\.sh$/) { print held; print } held = ""; next }
    { print }' "${ex}" >"${tmp}" && mv "${tmp}" "${ex}"
  say "removed this policy's ${only:-local} exclusions from ${ex}"
}

handler_still_used() { # another project/local scope still references the shared project handler
  local other
  [[ ${scope} == user ]] && return 1
  if [[ ${scope} == project ]]; then other="${ROOT}/.claude/settings.local.json"; else other="${ROOT}/.claude/settings.json"; fi
  local st
  st=$(settings_state "${other}") || st=invalid
  [[ ${st} == present ]]
}

# --- install ------------------------------------------------------------------

cmd_install() {
  local settings_backup="" handler_backup="" had_settings=0 had_handler=0 group ver
  refuse_cowork
  resolve_root
  need_scope
  say "== preflight"
  cmd_preflight || exit 1
  say "== install"
  if up_to_date; then
    say "already installed and up to date in ${SETTINGS}; nothing changed"
    say "== verify"
    run_verify || exit 1
    print_rollback unchanged
    return 0
  fi
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
    exit 1
  }

  mkdir -p "${HOOK_DIR}" || restore
  if ! { cp "${SRC_HANDLER}" "${HANDLER_DST}.tmp.$$" && chmod 755 "${HANDLER_DST}.tmp.$$" && mv "${HANDLER_DST}.tmp.$$" "${HANDLER_DST}"; }; then restore; fi
  cmp -s "${SRC_HANDLER}" "${HANDLER_DST}" || restore
  ver=$(bundled_version "${HANDLER_DST}") || ver=unknown
  say "handler: ${HANDLER_DST} (byte-identical to the bundled copy, version ${ver})"

  group=$(group_json) || restore
  # shellcheck disable=SC2016 # $x and $g are jq variables, not shell expansions
  write_json "${SETTINGS}" "${JQ_OURS}"'
    .hooks = (.hooks // {})
    | .hooks.PreToolUse = (.hooks.PreToolUse // [])
    | if any(.hooks.PreToolUse[]; ours_group) then
        .hooks.PreToolUse |= (reduce .[] as $x ({out: [], done: false};
          if ($x | ours_group) then
            (if .done then . else {out: (.out + [$g]), done: true} end)
          else .out += [$x] end) | .out)
      else .hooks.PreToolUse += [$g] end' --argjson g "${group}" || restore
  say "settings: merged one PreToolUse group into ${SETTINGS} (other keys and hooks untouched; whitespace normalized by jq)"
  say "== verify"
  run_verify || restore
  # Git exclusions only after verification, so a rollback never leaves them behind.
  [[ ${scope} == local ]] && add_local_excludes
  [[ ${scope} == project ]] && remove_local_excludes handler
  say "== done"
  say "Open /hooks (or restart the session) to confirm the group is loaded; this script cannot observe live loading."
  print_rollback "${settings_backup}"
}

print_rollback() { # $1: backup path | "" (settings file was created) | unchanged (nothing written)
  say "rollback:"
  say "  1. remove the PreToolUse group whose command is: ${COMMAND}"
  say "     from ${SETTINGS} (or run this skill's manage.sh: uninstall --scope ${scope})"
  local note=""
  [[ ${scope} != user ]] && note=" (unless the other project/local scope still uses it)"
  say "  2. delete ${HANDLER_DST}${note}"
  case ${1:-} in
  unchanged) say "  3. this run changed nothing; there is no backup to restore" ;;
  "") say "  3. the settings file did not exist before this install; deleting it restores the previous state" ;;
  *) say "  3. or restore the backup: ${1} (this discards any settings edits made after the install)" ;;
  esac
}

run_verify() {
  local out
  [[ -f ${HANDLER_DST} ]] || {
    say "FAIL no installed handler at ${HANDLER_DST}"
    return 1
  }
  local st summary d
  st=$(settings_state "${SETTINGS}") || st=invalid
  [[ ${st} == present ]] || {
    say "FAIL ${SETTINGS} has no block-no-verify group"
    return 1
  }
  if ! out=$(bash "${TEST_SUITE}" "${HANDLER_DST}" 2>&1); then
    printf '%s\n' "${out}" | tail -n 25
    say "FAIL test suite against the installed copy"
    return 1
  fi
  summary=$(printf '%s\n' "${out}" | sed -n '/passed, [0-9]* failed/p') || summary=""
  say "test suite: ${summary}"
  say "live payloads through the installed handler:"
  for c in 'git commit --no-verify -m wip' 'HUSKY=0 git commit -m wip' 'git commit -m "feat: add x"' 'git status'; do
    d=$(sample_decision "${HANDLER_DST}" "${c}") || d=ERROR
    say "  ${d}  ${c}"
  done
  handler_works "${HANDLER_DST}"
}

cmd_verify() {
  refuse_cowork
  resolve_root
  need_scope
  run_verify || exit 1
}

# --- uninstall ----------------------------------------------------------------

cmd_uninstall() {
  local st backup
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
    write_json "${SETTINGS}" "${JQ_OURS}"'
      .hooks.PreToolUse |= map(select(ours_group | not))
      | if (.hooks.PreToolUse | length) == 0 then del(.hooks.PreToolUse) else . end
      | if (.hooks | length) == 0 then del(.hooks) else . end' || fail "could not rewrite ${SETTINGS}; restore ${backup}"
    say "removed the block-no-verify group from ${SETTINGS}; everything else untouched"
    if [[ ${scope} != user ]] && jq -e '. == {}' "${SETTINGS}" >/dev/null 2>&1; then
      rm -f "${SETTINGS}"
      say "deleted the now-empty ${SETTINGS} (backup kept)"
    fi
  else
    say "no block-no-verify group in ${SETTINGS}"
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
  if [[ ${scope} == local ]]; then
    # Keep the settings.local.json exclusion while that file still exists.
    if [[ -f ${SETTINGS} ]]; then remove_local_excludes handler; else remove_local_excludes; fi
  fi
  say "Open /hooks (or restart the session) to confirm the group is gone."
}

command -v jq >/dev/null 2>&1 || {
  say "FAIL jq is required (https://jqlang.org/download/)"
  exit 1
}

case ${cmd} in
assess) cmd_assess ;;
status) cmd_status ;;
preflight) cmd_preflight ;;
install) cmd_install ;;
verify) cmd_verify ;;
uninstall) cmd_uninstall ;;
*)
  sed -n '2,19p' "$0" >&2
  exit 2
  ;;
esac
