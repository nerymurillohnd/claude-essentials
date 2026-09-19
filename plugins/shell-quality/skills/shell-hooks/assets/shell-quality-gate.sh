#!/usr/bin/env bash
# shell-quality gate: Claude Code hook handler for the shell scripts Claude edits.
# shell-quality-version: 0.1.0
#
# Usage (from settings.json hook commands, never by hand):
#   bash shell-quality-gate.sh baseline [OPTIONS]  UserPromptSubmit
#   bash shell-quality-gate.sh guard [OPTIONS]     PreToolUse  (Write|Edit|Bash)
#   bash shell-quality-gate.sh post [OPTIONS]      PostToolUse (Write|Edit|Bash)
#   bash shell-quality-gate.sh stop [OPTIONS]      Stop
#
# Options:
#   --config-mode recommended|own|defaults   default: own
#       recommended, own  ShellCheck finds its rc file and shfmt reads
#                         EditorConfig natively
#       defaults          built-in defaults: shellcheck --norc, and shfmt with
#                         -i 0 (any printer flag makes shfmt ignore EditorConfig)
#   --rcfile FILE        pin one ShellCheck rc file (own mode only)
#   --style-fallback     recommended at user scope: when no .editorconfig governs
#                        a script, format it with the recommended style flags
#                        (-i 2 -ci -bn -s); otherwise EditorConfig decides
#   --max-blocks N       Stop: consecutive blocks before the turn may end with a
#                        visible warning (default 5, 1-7; Claude Code itself
#                        overrides a Stop hook after 8 consecutive blocks)
#
# What each event does:
#   baseline  Between turns only the user changes files, so the shell lint
#             configuration and each touched script's suppression count are
#             re-recorded as the accepted state.
#   guard     Denies, before it happens, an edit that adds a ShellCheck
#             suppression (# shellcheck disable=..., source=/dev/null) or
#             changes .shellcheckrc/shellcheckrc, the shfmt keys of
#             .editorconfig, this gate's handler, or its settings; denies Bash
#             commands that do the same.
#   post      For the edited script (.sh, .bash, .bats, or a sh/bash/dash/ksh
#             shebang): shfmt -w, then ShellCheck, then suppression and
#             configuration checks. Clean -> exit 0 with a confirmation for the
#             user. Anything else -> exit 2, and Claude is told to fix it now.
#   stop      Re-checks every script edited this session (read-only: shfmt -d
#             and ShellCheck), the suppression counts, and the configuration.
#             Anything left -> exit 2, so Claude cannot finish until it is fixed.
#
# Fail-closed: a missing shellcheck, shfmt, or jq, an unreadable payload, a
# broken rc file, or a crash exits 2 with the reason. Exit 0 means clean, or an
# event that concerns no shell script. Needs bash >= 3.2 and jq >= 1.6. Never
# touches the network.

set -uo pipefail

readonly TAG="shell-quality"
readonly MAX_REPORT_LINES=80
# Suppression directives counted per file (grep -E, case-insensitive).
readonly SUPP_RE='#[[:space:]]*shellcheck[[:space:]]+([^#]*[[:space:]])?(disable=[^[:space:]]+|source=/dev/null)'
readonly STYLE_FLAGS="-i 2 -ci -bn -s"
# EditorConfig keys shfmt reads (and section headers) that decide formatting.
readonly EC_KEYS_RE='^[[:space:]]*(\[|root|indent_style|indent_size|shell_variant|language_dialect|binary_next_line|switch_case_indent|case_indent|space_redirects|keep_padding|function_next_line|simplify|minify|ignore)'

event=${1:-}
[[ $# -gt 0 ]] && shift
config_mode=own
rc_file=""
style_fallback=0
max_blocks=5

die() { # fail closed, visible to Claude and the user
  printf '%s: %s\n' "${TAG}" "$1" >&2
  if [[ ${event:-} == guard ]]; then
    printf '%s: the gate cannot check this tool call, so it is denied (fail-closed); every file edit and shell command stays denied until the cause is fixed. Tell the user: they can fix it, or remove the gate in their own terminal with: ! bash <plugin>/skills/shell-hooks/scripts/manage.sh uninstall --scope <scope>\n' "${TAG}" >&2
  else
    printf '%s: the gate could not run, so this change is NOT verified. Fix the cause above (or ask the user), then retry.\n' "${TAG}" >&2
  fi
  exit 2
}

while [[ $# -gt 0 ]]; do
  case $1 in
  --config-mode | --rcfile | --max-blocks)
    [[ $# -ge 2 ]] || die "$1 needs a value"
    case $1 in
    --config-mode) config_mode=$2 ;;
    --rcfile) rc_file=$2 ;;
    *) max_blocks=$2 ;;
    esac
    shift 2
    ;;
  --style-fallback)
    style_fallback=1
    shift
    ;;
  *) die "unknown argument: $1" ;;
  esac
done

case ${event} in
baseline | guard | post | stop) ;;
*) die "first argument must be baseline, guard, post, or stop (got: ${event:-nothing})" ;;
esac
case ${config_mode} in
recommended | own | defaults) ;;
*) die "--config-mode must be recommended, own, or defaults" ;;
esac
case ${max_blocks} in
[1-7]) ;;
*) die "--max-blocks must be a number from 1 to 7" ;;
esac
if [[ -n ${rc_file} ]]; then
  [[ ${config_mode} == own ]] || die "--rcfile is only valid with --config-mode own"
  [[ -f ${rc_file} ]] || die "the pinned ShellCheck rc file does not exist: ${rc_file}"
fi
((style_fallback == 0)) || [[ ${config_mode} == recommended ]] || die "--style-fallback is only valid with --config-mode recommended"

command -v jq >/dev/null 2>&1 || die "jq is required (https://jqlang.org/download/)"

payload=$(cat) || die "could not read the hook payload"
[[ -n ${payload} ]] || die "empty hook payload"

# One jq pass: session, cwd, stop_hook_active, tool name, then candidate paths.
fields=$(jq -r '
  def paths_from_diff:
    if type == "array" then .[]
    elif type == "object" then ((.files // .changedFiles // .paths // empty) | if type == "array" then .[] else empty end)
    else empty end
    | if type == "string" then .
      elif type == "object" then (.path // .filePath // .file_path // .file // empty)
      else empty end;
  (.session_id // "" | tostring),
  (.cwd // "" | tostring),
  (.stop_hook_active // false | tostring),
  (.tool_name // "" | tostring),
  ( [ .tool_input.file_path?, .tool_response.filePath?,
      (.tool_response.bashEditDiff? // empty | paths_from_diff) ]
    | map(select(type == "string" and length > 0 and (test("\n") | not)))
    | unique[] )
' <<<"${payload}" 2>/dev/null) || die "hook payload is not valid JSON"

session=""
cwd=""
stop_active=false
tool=""
candidates=()
i=0
while IFS= read -r line; do
  case ${i} in
  0) session=${line} ;;
  1) cwd=${line} ;;
  2) stop_active=${line} ;;
  3) tool=${line} ;;
  *) candidates+=("${line}") ;;
  esac
  i=$((i + 1))
done <<<"${fields}"

[[ -n ${cwd} && -d ${cwd} ]] || cwd=${CLAUDE_PROJECT_DIR:-${PWD}}
session=$(printf '%s' "${session:-nosession}" | tr -c 'A-Za-z0-9._-' '_')
project=${CLAUDE_PROJECT_DIR:-${cwd}}
[[ -d ${project} ]] || project=${cwd}
git_top=$(git -C "${cwd}" rev-parse --show-toplevel 2>/dev/null) || git_top=""
cfg_dir=${CLAUDE_CONFIG_DIR:-${HOME}/.claude}
xdg_rc="${XDG_CONFIG_HOME:-${HOME}/.config}/shellcheckrc"
home_rc="${HOME}/.shellcheckrc"

# --- state -----------------------------------------------------------------------

state_dir="${TMPDIR:-/tmp}"
uid=$(id -u 2>/dev/null) || uid=user
state_dir="${state_dir%/}/shell-quality-gate-${uid}"
files_state="${state_dir}/${session}.files"
supp_state="${state_dir}/${session}.supp"
config_state="${state_dir}/${session}.config"
blocks_state="${state_dir}/${session}.blocks"

ensure_state_dir() {
  if [[ ! -d ${state_dir} ]]; then
    mkdir -p "${state_dir}" 2>/dev/null || die "cannot create state directory ${state_dir}"
    chmod 700 "${state_dir}" 2>/dev/null || true
  fi
  [[ -O ${state_dir} && ! -L ${state_dir} ]] || die "state directory ${state_dir} is not owned by this user"
  find "${state_dir}" -type f -mtime +2 -delete 2>/dev/null || true
}

# --- small helpers -----------------------------------------------------------------

rel() { # rel PATH -> REL (relative to cwd when inside it)
  case $1 in
  "${cwd}"/*) REL=${1#"${cwd}"/} ;;
  *) REL=$1 ;;
  esac
}

is_shell() { # a script ShellCheck and shfmt both support
  local lower first=""
  lower=$(printf '%s' "${1##*/}" | tr '[:upper:]' '[:lower:]')
  case ${lower} in
  *.sh | *.bash | *.bats) return 0 ;;
  *.*) return 1 ;;
  *) ;;
  esac
  [[ -f $1 ]] || return 1
  IFS= read -r first <"$1" 2>/dev/null || true
  case ${first} in
  '#!'*) ;;
  *) return 1 ;;
  esac
  printf '%s' "${first}" | grep -Eq '^#![[:space:]]*(/usr)?(/local)?/bin/(env[[:space:]]+(-S[[:space:]]+)?)?(ba|da|k)?sh([[:space:]]|$)'
}

abs_path() { # abs_path PATH -> ABS (physical directory, same basename)
  local p=$1 base dir
  case ${p} in
  /*) ;;
  *)
    base=${cwd}
    [[ ${tool} == Bash && -n ${git_top} && -e ${git_top}/${p} ]] && base=${git_top}
    p="${base}/${p}"
    ;;
  esac
  # A directory that does not exist yet (a Write creating it) keeps its lexical path.
  dir=$(cd "${p%/*}" 2>/dev/null && pwd -P) || dir=${p%/*}
  ABS="${dir}/${p##*/}"
}

count_supp_text() { # stdin -> number of suppression directives
  local n
  n=$(grep -Eio "${SUPP_RE}" 2>/dev/null | wc -l | tr -d ' ') || n=0
  printf '%s' "${n:-0}"
}

count_supp_file() { # count_supp_file FILE -> N (0 when the file does not exist)
  if [[ -f $1 ]]; then count_supp_text <"$1"; else printf '0'; fi
}

trim_report() { # trim_report TEXT -> REPORT (bounded)
  local total head_part
  total=$(printf '%s\n' "$1" | wc -l | tr -d ' ')
  if ((total > MAX_REPORT_LINES)); then
    head_part=$(printf '%s\n' "$1" | head -n "${MAX_REPORT_LINES}")
    REPORT="${head_part}
[... ${total} lines in total; run shellcheck on the file for the rest]"
  else
    REPORT=$1
  fi
}

emit_system_message() { jq -cn --arg m "$1" '{systemMessage: $m}'; }

deny() { # deny REASON: PreToolUse deny (JSON + exit 2, so profile noise cannot turn it into an allow)
  jq -cn --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}, systemMessage: ("shell-quality blocked an attempt to weaken the shell quality gate: " + $r)}'
  printf '%s: %s\n' "${TAG}" "$1" >&2
  exit 2
}

# --- tools ---------------------------------------------------------------------------

find_tool() { # find_tool NAME OVERRIDE_VAR -> TOOL
  local name=$1 override=${2:-} c
  TOOL=""
  if [[ -n ${override} ]]; then
    [[ -x ${override} ]] || die "the configured ${name} is not executable: ${override}"
    TOOL=${override}
    return 0
  fi
  if c=$(command -v "${name}" 2>/dev/null) && [[ -n ${c} ]]; then
    TOOL=${c}
    return 0
  fi
  for c in "${HOME}/.local/bin/${name}" "/opt/homebrew/bin/${name}" "/usr/local/bin/${name}" "/usr/bin/${name}"; do
    if [[ -x ${c} ]]; then
      TOOL=${c}
      return 0
    fi
  done
  return 1
}

SC_BIN=""
FMT_BIN=""
resolve_tools() { # SHELLCHECK_BIN / SHFMT_BIN override the lookup
  [[ -n ${SC_BIN} ]] && return 0
  find_tool shellcheck "${SHELLCHECK_BIN:-}" || die "shellcheck not found on PATH or in ~/.local/bin, /opt/homebrew/bin, /usr/local/bin, /usr/bin. Install it (brew install shellcheck, apt install shellcheck, or a release from https://github.com/koalaman/shellcheck/releases), or set SHELLCHECK_BIN."
  SC_BIN=${TOOL}
  find_tool shfmt "${SHFMT_BIN:-}" || die "shfmt not found on PATH or in ~/.local/bin, /opt/homebrew/bin, /usr/local/bin, /usr/bin. Install it (brew install shfmt, or a release from https://github.com/mvdan/sh/releases), or set SHFMT_BIN."
  FMT_BIN=${TOOL}
}

sc_args=()
case ${config_mode} in
defaults) sc_args=(--norc) ;;
*) [[ -n ${rc_file} ]] && sc_args=(--rcfile "${rc_file}") ;;
esac

has_editorconfig() { # has_editorconfig FILE: an .editorconfig above the file
  local d=${1%/*}
  while [[ -n ${d} ]]; do
    [[ -f ${d}/.editorconfig ]] && return 0
    [[ ${d} == / ]] && break
    d=${d%/*}
    [[ -n ${d} ]] || d=/
  done
  return 1
}

shfmt_args_for() { # shfmt_args_for FILE -> SHFMT_ARGS
  SHFMT_ARGS=(--apply-ignore)
  if [[ ${config_mode} == defaults ]]; then
    SHFMT_ARGS+=(-i 0)
  elif ((style_fallback)) && ! has_editorconfig "$1"; then
    # shellcheck disable=SC2206 # STYLE_FLAGS is a fixed list of plain flags, split on purpose
    SHFMT_ARGS+=(${STYLE_FLAGS})
  fi
}

run_tool() { # run_tool BIN ARGS... -> OUT (stdout+stderr), RC
  local bin=$1
  shift
  OUT=$(cd "${cwd}" 2>/dev/null && "${bin}" "$@" 2>&1)
  RC=$?
}

# --- what counts as the gate's configuration ------------------------------------------

editorconfig_view() { # the lines of an .editorconfig (stdin) that decide shfmt formatting
  grep -Ei "${EC_KEYS_RE}" | sed 's/[[:space:]]*$//' || true
}

gate_settings() { # this gate's groups and disableAllHooks in a settings file read from stdin
  jq -cS '{d: (.disableAllHooks // false), g: [(.hooks // {}) | to_entries[] | .key as $e | (.value // [])[]? | select(any((.hooks // [])[]?; (.command // "") | tostring | test("shell-quality-gate[.]sh"))) | {e: $e, h: .}]}' 2>/dev/null || printf 'unparseable\n'
}

config_files() { # every file whose content can change what the gate enforces
  local f listed
  if [[ -n ${git_top} ]]; then
    listed=$(git -C "${git_top}" ls-files -co --exclude-standard -- '*shellcheckrc' '*.editorconfig' 2>/dev/null) || listed=""
    while IFS= read -r f; do
      case ${f##*/} in .shellcheckrc | shellcheckrc | .editorconfig) printf '%s\n' "${git_top}/${f}" ;; *) ;; esac
    done <<<"${listed}"
  else
    for f in "${project}/.shellcheckrc" "${project}/shellcheckrc" "${project}/.editorconfig"; do
      [[ -f ${f} ]] && printf '%s\n' "${f}"
    done
  fi
  for f in "${home_rc}" "${xdg_rc}"; do
    [[ -f ${f} ]] && printf '%s\n' "${f}"
  done
  [[ -n ${rc_file} ]] && printf '%s\n' "${rc_file}"
  for f in "${project}/.claude/settings.json" "${project}/.claude/settings.local.json" "${cfg_dir}/settings.json"; do
    [[ -f ${f} ]] && printf '%s\n' "${f}"
  done
  return 0
}

fingerprint() { # "cksum path" per governing file, sorted
  local f sum files
  files=$(config_files | sort -u)
  while IFS= read -r f; do
    [[ -n ${f} ]] || continue
    case ${f##*/} in
    .editorconfig) sum=$(editorconfig_view <"${f}" | cksum) ;;
    settings.json | settings.local.json) sum=$(gate_settings <"${f}" | cksum) ;;
    *) sum=$(cksum <"${f}") ;;
    esac
    printf '%s %s\n' "${sum}" "${f}"
  done <<<"${files}"
}

record_config_baseline() {
  local fp
  fp=$(fingerprint) || die "cannot fingerprint the shell lint configuration"
  printf '%s\n' "${fp}" >"${config_state}" || die "cannot write ${config_state}"
}

config_drift() { # prints the files that changed since the baseline, empty when none did
  local now before
  [[ -f ${config_state} ]] || return 0
  now=$(fingerprint) || die "cannot fingerprint the shell lint configuration"
  before=$(cat "${config_state}") || die "cannot read ${config_state}"
  [[ ${now} == "${before}" ]] && return 0
  diff <(printf '%s\n' "${before}") <(printf '%s\n' "${now}") | sed -n 's/^[<>] [0-9]* [0-9]* //p' | sort -u
}

supp_baseline() { # supp_baseline FILE -> N recorded for this session, or nothing
  [[ -f ${supp_state} ]] || return 0
  awk -F '\t' -v f="$1" '$2 == f { n = $1 } END { if (n != "") print n }' "${supp_state}"
}

record_supp_baseline() { # record_supp_baseline FILE [committed]: first touch this session only
  local f=$1 n known
  known=$(supp_baseline "${f}")
  [[ -n ${known} ]] && return 0
  # Before an edit (guard) the file on disk is the baseline. After a write the
  # guard never saw (Bash), only the committed version can be trusted.
  if [[ ${2:-} == committed ]]; then
    n=0
    if [[ -n ${git_top} && ${f} == "${git_top}"/* ]]; then
      n=$(git -C "${git_top}" show "HEAD:${f#"${git_top}"/}" 2>/dev/null | count_supp_text)
    fi
  elif [[ -f ${f} ]]; then
    n=$(count_supp_file "${f}")
  elif [[ -n ${git_top} && ${f} == "${git_top}"/* ]]; then
    n=$(git -C "${git_top}" show "HEAD:${f#"${git_top}"/}" 2>/dev/null | count_supp_text)
  else
    n=0
  fi
  printf '%s\t%s\n' "${n}" "${f}" >>"${supp_state}" || die "cannot write ${supp_state}"
}

supp_added() { # supp_added FILE -> prints "now>before" when suppressions grew
  local before now
  before=$(supp_baseline "$1")
  [[ -n ${before} ]] || return 0
  now=$(count_supp_file "$1")
  ((now > before)) && printf '%s>%s' "${now}" "${before}"
  return 0
}

# --- baseline (UserPromptSubmit) ---------------------------------------------------------

do_baseline() {
  local f n sorted tmp
  ensure_state_dir
  record_config_baseline
  rm -f "${blocks_state}"
  if [[ -f ${files_state} ]]; then
    sorted=$(sort -u "${files_state}") || die "cannot read ${files_state}"
    tmp="${supp_state}.tmp.$$"
    : >"${tmp}" || die "cannot write ${tmp}"
    while IFS= read -r f; do
      [[ -n ${f} ]] || continue
      n=$(count_supp_file "${f}")
      printf '%s\t%s\n' "${n}" "${f}" >>"${tmp}"
    done <<<"${sorted}"
    mv "${tmp}" "${supp_state}" || die "cannot write ${supp_state}"
  fi
  exit 0
}

# --- guard (PreToolUse) --------------------------------------------------------------------

simulate_edit() { # simulate_edit FILE -> stdout: the file content after this tool call
  local cur=/dev/null
  [[ -f $1 ]] && cur=$1
  jq -j --rawfile cur "${cur}" '
    .tool_input as $t
    | if ($t.content | type) == "string" then $t.content
      elif ($t.old_string | type) == "string" and ($t.old_string | length) > 0 then
        ($cur | split($t.old_string)) as $p
        | if ($p | length) < 2 then $cur
          elif $t.replace_all == true then $p | join($t.new_string // "")
          else $p[0] + ($t.new_string // "") + ($p[1:] | join($t.old_string)) end
      else $cur end' <<<"${payload}"
}

guard_file() { # guard_file ABS
  local f=$1 before after new_text n_old n_new
  case ${f##*/} in
  .shellcheckrc | shellcheckrc | shell-quality-gate.sh)
    rel "${f}"
    deny "Claude may not edit ${REL}: it is part of the ShellCheck configuration or of this gate. Configuration is the user's decision; ask the user to make the change themselves, and fix the script instead."
    ;;
  .editorconfig)
    if [[ -f ${f} ]]; then before=$(editorconfig_view <"${f}"); else before=""; fi
    after=$(simulate_edit "${f}" | editorconfig_view) || after=""
    [[ ${before} == "${after}" ]] || deny "Claude may not change sections or shfmt keys (indent, shell_variant, binary_next_line, switch_case_indent, space_redirects, function_next_line, simplify, minify, ignore) in .editorconfig: formatting policy is the user's decision."
    return 0
    ;;
  settings.json | settings.local.json)
    if [[ -f ${f} ]]; then before=$(gate_settings <"${f}"); else before=$(printf '{}' | gate_settings); fi
    after=$(simulate_edit "${f}" | gate_settings) || after=""
    [[ ${before} == "${after}" ]] || deny "Claude may not change or disable the shell-quality hooks (or set disableAllHooks). Only the user changes them, in their own terminal."
    return 0
    ;;
  *) ;;
  esac
  [[ ${f} == "${xdg_rc}" || (-n ${rc_file} && ${f} == "${rc_file}") ]] && deny "Claude may not edit the ShellCheck configuration; that is the user's decision."
  # A new file has no shebang on disk yet: decide from the name or the new content.
  if ! is_shell "${f}"; then
    case ${f##*/} in
    *.*) return 0 ;;
    *) jq -r '.tool_input.content // ""' <<<"${payload}" | head -n 1 | grep -Eq '^#![[:space:]]*(/usr)?(/local)?/bin/(env[[:space:]]+(-S[[:space:]]+)?)?(ba|da|k)?sh([[:space:]]|$)' || return 0 ;;
    esac
  fi
  ensure_state_dir
  record_supp_baseline "${f}"
  new_text=$(jq -r '.tool_input | (.content // .new_string // "")' <<<"${payload}") || new_text=""
  n_new=$(printf '%s' "${new_text}" | count_supp_text)
  if jq -e '.tool_input.content | type == "string"' >/dev/null 2>&1 <<<"${payload}"; then
    n_old=$(count_supp_file "${f}")
  else
    n_old=$(jq -r '.tool_input.old_string // ""' <<<"${payload}" | count_supp_text)
  fi
  if ((n_new > n_old)); then
    rel "${f}"
    deny "this edit to ${REL} adds a ShellCheck suppression (# shellcheck disable=... or source=/dev/null). Silencing a finding is never allowed through this gate; change the script so the check passes. If the user explicitly wants a suppression, they add it themselves."
  fi
}

guard_bash() {
  local c stripped
  c=$(jq -r '.tool_input.command // ""' <<<"${payload}" | tr '[:upper:]' '[:lower:]') || c=""
  [[ -n ${c} ]] || return 0
  case ${c} in
  *disableallhooks*) deny "setting disableAllHooks turns this gate off; only the user may do that." ;;
  *shell-hooks/scripts/manage.sh*install*)
    deny "reinstalling or uninstalling the shell-quality gate changes what it enforces; only the user may do that. Ask them to run the command themselves with the ! prefix."
    ;;
  *) ;;
  esac
  # A write construct: redirection (other than to /dev/null or between fds),
  # in-place editors, tee/cp/mv/rm/ln, heredocs, or an inline interpreter.
  stripped=$(printf '%s' "${c}" | sed -E 's/[0-9]*>&[0-9-]//g; s/[0-9]*>>?[[:space:]]*\/dev\/null//g')
  if printf '%s' "${stripped}" | grep -Eq '>|sed[[:space:]]+(-[a-z]*i|--in-place)|perl[[:space:]]+-[a-z]*i|(^|[[:space:];|&(])(tee|cp|mv|rm|ln|truncate|install)[[:space:]]|<<|python[0-9.]*[[:space:]]+-c'; then
    if printf '%s' "${c}" | grep -Eq "${SUPP_RE}"; then
      deny "this command writes a ShellCheck suppression. Silencing a finding is never allowed through this gate; change the script instead."
    fi
    if printf '%s' "${c}" | grep -Eq 'shellcheckrc|\.editorconfig|shell-quality-gate\.sh|settings(\.local)?\.json'; then
      deny "this command writes to the ShellCheck or EditorConfig configuration, or to the Claude Code settings/handler of this gate. Configuration and hooks are the user's decision."
    fi
  fi
}

do_guard() {
  local c
  ensure_state_dir
  [[ -f ${config_state} ]] || record_config_baseline
  if [[ ${tool} == Bash ]]; then
    guard_bash
    exit 0
  fi
  for c in ${candidates[@]+"${candidates[@]}"}; do
    abs_path "${c}" || continue
    guard_file "${ABS}"
  done
  exit 0
}

# --- post (PostToolUse) --------------------------------------------------------------------

# check_and_format FILE SHOWN -> STATUS clean|skipped|findings, FINDINGS, CHANGED 0|1
check_and_format() {
  local f=$1 shown=$2 before after fmt_rc fmt_out
  STATUS=clean
  FINDINGS=""
  CHANGED=0
  before=$(cksum <"${f}") || die "cannot read ${shown}"
  shfmt_args_for "${f}"
  run_tool "${FMT_BIN}" "${SHFMT_ARGS[@]}" -w -- "${f}"
  fmt_rc=${RC}
  fmt_out=${OUT}
  run_tool "${SC_BIN}" ${sc_args[@]+"${sc_args[@]}"} -f gcc -- "${f}"
  case ${RC} in
  0) ;;
  1)
    FINDINGS=${OUT}
    STATUS=findings
    ;;
  *) die "shellcheck failed on ${shown} (exit ${RC}):
${OUT}" ;;
  esac
  # A script that cannot be parsed cannot be formatted; ShellCheck reports the
  # parse error as a finding. Any other shfmt failure is a gate failure.
  if ((fmt_rc != 0)); then
    [[ ${STATUS} == findings ]] || die "shfmt failed on ${shown} (exit ${fmt_rc}):
${fmt_out}"
    FINDINGS="${FINDINGS}
${shown}: shfmt could not format it: ${fmt_out}"
  fi
  after=$(cksum <"${f}") || die "cannot read ${shown}"
  [[ ${before} == "${after}" ]] || CHANGED=1
}

do_post() {
  local c f shown count drift added note="" what files=() clean=() changed=() report="" n_findings=0 policy=""
  for c in ${candidates[@]+"${candidates[@]}"}; do
    abs_path "${c}" || continue
    [[ -f ${ABS} ]] || continue
    is_shell "${ABS}" || continue
    files+=("${ABS}")
  done
  ((${#files[@]} > 0)) || exit 0

  resolve_tools
  ensure_state_dir
  [[ -f ${config_state} ]] || record_config_baseline
  for f in "${files[@]}"; do
    printf '%s\n' "${f}" >>"${files_state}" || die "cannot write ${files_state}"
    record_supp_baseline "${f}" committed
  done

  for f in "${files[@]}"; do
    rel "${f}"
    shown=${REL}
    check_and_format "${f}" "${shown}"
    if [[ ${STATUS} == findings ]]; then
      count=$(printf '%s\n' "${FINDINGS}" | grep -c . || true)
      n_findings=$((n_findings + count))
      report="${report}${FINDINGS}"$'\n'
    else
      clean+=("${shown}")
    fi
    ((CHANGED)) && changed+=("${shown}")
    added=$(supp_added "${f}")
    [[ -n ${added} ]] && policy="${policy}${shown}: ShellCheck suppressions grew from ${added#*>} to ${added%>*} this session; remove the new ones and fix the script."$'\n'
  done
  drift=$(config_drift)
  [[ -n ${drift} ]] && policy="${policy}The ShellCheck/EditorConfig configuration or this gate's settings changed during this turn: ${drift//$'\n'/, }. Revert that change; configuration is the user's decision."$'\n'

  if [[ -n ${report}${policy} ]]; then
    ((${#changed[@]})) && note=" The hook reformatted ${changed[*]} with shfmt; re-read before editing again."
    REPORT=""
    [[ -n ${report} ]] && trim_report "${report}"
    what="${n_findings} ShellCheck finding(s)"
    [[ -n ${policy} ]] && what="${what} and a suppression/configuration violation"
    emit_system_message "${TAG} ✗ ${what}; Claude has been told to fix them now."
    {
      printf '%s: STOP and fix this before any other change.%s\n\n' "${TAG}" "${note}"
      [[ -n ${REPORT} ]] && printf '%s\n\n' "${REPORT}"
      [[ -n ${policy} ]] && printf '%s\n' "${policy}"
      printf '%s\n' "Change the script so each check passes; read a code's explanation at https://www.shellcheck.net/wiki/SC<code>. ShellCheck suppressions (# shellcheck disable=..., source=/dev/null) and configuration changes are never accepted by this gate. The Stop gate re-checks these files before the turn can end."
    } >&2
    exit 2
  fi

  local msg="${TAG} ✓ ${clean[*]}: ShellCheck-clean and shfmt-formatted"
  ((${#changed[@]})) && msg="${msg} (reformatted: ${changed[*]})"
  emit_system_message "${msg}"
  exit 0
}

# --- stop ------------------------------------------------------------------------------------

do_stop() {
  local f shown sorted lint fmt added drift files=() report="" n_files=0 blocks=0 bad=()
  [[ -f ${files_state} || -f ${config_state} ]] || exit 0
  ensure_state_dir
  if [[ -f ${files_state} ]]; then
    sorted=$(sort -u "${files_state}") || die "cannot read ${files_state}"
    while IFS= read -r f; do
      [[ -n ${f} && -f ${f} ]] && is_shell "${f}" && files+=("${f}")
    done <<<"${sorted}"
  fi

  # A new turn (not a continuation caused by a Stop hook) starts a new count.
  if [[ ${stop_active} == true && -f ${blocks_state} ]]; then
    blocks=$(cat "${blocks_state}" 2>/dev/null) || blocks=0
    case ${blocks} in '' | *[!0-9]*) blocks=0 ;; *) ;; esac
  fi

  ((${#files[@]} == 0)) || resolve_tools
  for f in ${files[@]+"${files[@]}"}; do
    n_files=$((n_files + 1))
    rel "${f}"
    shown=${REL}
    lint=""
    fmt=""
    run_tool "${SC_BIN}" ${sc_args[@]+"${sc_args[@]}"} -f gcc -- "${f}"
    case ${RC} in
    0) ;;
    1) lint=${OUT} ;;
    *) die "shellcheck failed on ${shown} (exit ${RC}):
${OUT}" ;;
    esac
    shfmt_args_for "${f}"
    run_tool "${FMT_BIN}" "${SHFMT_ARGS[@]}" -d -- "${f}"
    case ${RC} in
    0) ;;
    1) [[ -n ${lint} ]] || fmt="${shown}: not formatted (run: shfmt -w ${shown})" ;;
    *) die "shfmt failed on ${shown} (exit ${RC}):
${OUT}" ;;
    esac
    added=$(supp_added "${f}")
    if [[ -n ${added} ]]; then
      [[ -n ${lint} ]] && lint="${lint}"$'\n'
      lint="${lint}${shown}: ShellCheck suppressions grew from ${added#*>} to ${added%>*} this session; remove the new ones and fix the script"
    fi
    if [[ -n ${lint}${fmt} ]]; then
      bad+=("${shown}")
      [[ -n ${lint} ]] && report="${report}${lint}"$'\n'
      [[ -n ${fmt} ]] && report="${report}${fmt}"$'\n'
    fi
  done
  drift=$(config_drift)
  if [[ -n ${drift} ]]; then
    bad+=("configuration")
    report="${report}The ShellCheck/EditorConfig configuration or this gate's settings changed during this turn: ${drift//$'\n'/, }. Revert that change; configuration is the user's decision."$'\n'
  fi

  if [[ -z ${report} ]]; then
    rm -f "${blocks_state}"
    ((n_files > 0)) && emit_system_message "${TAG} ✓ Stop gate: ${n_files} edited shell script(s) are ShellCheck-clean, formatted, and unsuppressed."
    exit 0
  fi

  blocks=$((blocks + 1))
  trim_report "${report}"
  if ((blocks > max_blocks)); then
    rm -f "${blocks_state}"
    emit_system_message "⚠️ ${TAG}: the turn ended after ${max_blocks} blocked stop attempts with problems still unresolved in: ${bad[*]}. Ask Claude to fix them, or run: shellcheck ${bad[*]}"
    exit 0
  fi
  printf '%s\n' "${blocks}" >"${blocks_state}" || die "cannot write ${blocks_state}"
  emit_system_message "${TAG} ✗ Stop gate (${blocks}/${max_blocks}): unresolved in ${bad[*]}; Claude must fix them before finishing."
  {
    printf '%s: you cannot finish yet (block %s of %s). What you changed this session still fails the shell quality gate:\n\n' "${TAG}" "${blocks}" "${max_blocks}"
    printf '%s\n\n' "${REPORT}"
    printf '%s\n' "Fix it in the script now: \`shfmt -w <file>\` for formatting, then correct each ShellCheck finding by hand (https://www.shellcheck.net/wiki/SC<code>). Suppressions and configuration changes are never accepted. If a finding truly needs the user's decision, say exactly which one and why."
  } >&2
  exit 2
}

case ${event} in
baseline) do_baseline ;;
guard) do_guard ;;
post) do_post ;;
stop) do_stop ;;
*) die "unreachable" ;;
esac
