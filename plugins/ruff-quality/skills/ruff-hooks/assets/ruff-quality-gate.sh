#!/usr/bin/env bash
# ruff-quality gate: Claude Code hook handler for the Python files Claude edits.
# ruff-quality-version: 0.1.0
#
# Usage (from settings.json hook commands, never by hand):
#   bash ruff-quality-gate.sh baseline [OPTIONS]  UserPromptSubmit
#   bash ruff-quality-gate.sh guard [OPTIONS]     PreToolUse  (Write|Edit|NotebookEdit|Bash)
#   bash ruff-quality-gate.sh post [OPTIONS]      PostToolUse (Write|Edit|NotebookEdit|Bash)
#   bash ruff-quality-gate.sh stop [OPTIONS]      Stop
#
# Options:
#   --config-mode recommended|own|defaults   default: own
#       recommended, own  Ruff discovers its configuration natively
#       defaults          Ruff's built-in defaults (--isolated): every
#                         configuration file is ignored
#   --config FILE        pin one configuration file (own mode only)
#   --max-blocks N       Stop: consecutive blocks before the turn may end with a
#                        visible warning (default 5, 1-7; Claude Code itself
#                        overrides a Stop hook after 8 consecutive blocks)
#
# What each event does:
#   baseline  Between turns only the user can change files, so the Ruff
#             configuration and each touched file's suppression count are
#             re-recorded here as the accepted state.
#   guard     Denies, before it happens, an edit that adds a suppression comment
#             (noqa, ruff: noqa/ignore/disable/file-ignore, fmt: off/skip,
#             isort: skip/off) or touches the Ruff configuration, this gate's
#             handler, or its settings; denies Bash commands that do the same.
#   post      For the edited .py/.pyi/.ipynb file: safe fixes (never unsafe,
#             never removing an unused import mid-change), format, lint again,
#             then compare suppressions and configuration with the baseline.
#             Clean -> exit 0 with a confirmation for the user. Anything else ->
#             exit 2, and Claude is told to fix it now.
#   stop      Re-checks every Python file edited this session (read-only), the
#             suppression counts, and the configuration. Anything left -> exit 2,
#             so Claude cannot finish until it is fixed.
#
# Fail-closed: a missing ruff or jq, an unreadable payload, a broken
# configuration, or a crash exits 2 with the reason. Exit 0 means clean, or an
# event that concerns no Python file. Needs bash >= 3.2 and jq >= 1.6. Never
# touches the network.

set -uo pipefail

readonly TAG="ruff-quality"
readonly MAX_REPORT_LINES=80
# Suppression comments counted per file (grep -E, case-insensitive).
readonly SUPP_RE='#[[:space:]]*(noqa|ruff[[:space:]]*:[[:space:]]*(noqa|ignore|disable|file-ignore)|fmt[[:space:]]*:[[:space:]]*(off|skip)|isort[[:space:]]*:[[:space:]]*(skip|off))'

event=${1:-}
[[ $# -gt 0 ]] && shift
config_mode=own
config_file=""
max_blocks=5

die() { # fail closed, visible to Claude and the user
  printf '%s: %s\n' "${TAG}" "$1" >&2
  if [[ ${event:-} == guard ]]; then
    printf '%s: the gate cannot check this tool call, so it is denied (fail-closed); every file edit and shell command stays denied until the cause is fixed. Tell the user: they can fix it, or remove the gate in their own terminal with: ! bash <plugin>/skills/ruff-hooks/scripts/manage.sh uninstall --scope <scope>\n' "${TAG}" >&2
  else
    printf '%s: the gate could not run, so this change is NOT verified. Fix the cause above (or ask the user), then retry.\n' "${TAG}" >&2
  fi
  exit 2
}

while [[ $# -gt 0 ]]; do
  case $1 in
  --config-mode | --config | --max-blocks)
    [[ $# -ge 2 ]] || die "$1 needs a value"
    case $1 in
    --config-mode) config_mode=$2 ;;
    --config) config_file=$2 ;;
    *) max_blocks=$2 ;;
    esac
    shift 2
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
if [[ -n ${config_file} ]]; then
  [[ ${config_mode} == own ]] || die "--config is only valid with --config-mode own"
  [[ -f ${config_file} ]] || die "the pinned Ruff config file does not exist: ${config_file}"
fi

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
  ( [ .tool_input.file_path?, .tool_input.notebook_path?, .tool_response.filePath?,
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
ruff_user_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/ruff"

# --- state -----------------------------------------------------------------------

state_dir="${TMPDIR:-/tmp}"
uid=$(id -u 2>/dev/null) || uid=user
state_dir="${state_dir%/}/ruff-quality-gate-${uid}"
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

is_python() {
  local lower
  lower=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case ${lower} in
  *.py | *.pyi | *.ipynb) return 0 ;;
  *) return 1 ;;
  esac
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

count_supp_text() { # stdin -> number of suppression comments
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
[... ${total} lines in total; run ruff check on the file for the rest]"
  else
    REPORT=$1
  fi
}

emit_system_message() { jq -cn --arg m "$1" '{systemMessage: $m}'; }

deny() { # deny REASON: PreToolUse deny (JSON + exit 2, so profile noise cannot turn it into an allow)
  jq -cn --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}, systemMessage: ("ruff-quality blocked an attempt to weaken the Python quality gate: " + $r)}'
  printf '%s: %s\n' "${TAG}" "$1" >&2
  exit 2
}

# --- ruff resolution: RUFF_BIN, then the nearest venv, then PATH --------------------

find_ruff() { # find_ruff DIR -> RUFF
  local d=$1 c
  RUFF=""
  if [[ -n ${RUFF_BIN:-} ]]; then
    [[ -x ${RUFF_BIN} ]] || die "RUFF_BIN is set but not executable: ${RUFF_BIN}"
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
    d=${d%/*}
    [[ -n ${d} ]] || d=/
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
  die "ruff not found (looked at RUFF_BIN, .venv/bin/ruff and venv/bin/ruff above the file, PATH, ~/.local/bin, /opt/homebrew/bin, /usr/local/bin). Install it (for example 'uv tool install ruff', or add it to the project's dev dependencies) or set RUFF_BIN."
}

config_args=()
case ${config_mode} in
defaults) config_args=(--isolated) ;;
*) [[ -n ${config_file} ]] && config_args=(--config "${config_file}") ;;
esac

run_ruff() { # run_ruff ARGS... -> OUT (stdout+stderr), RC
  OUT=$(cd "${cwd}" 2>/dev/null && "${RUFF}" "$@" 2>&1)
  RC=$?
}

findings_only() { # strip Ruff's summary lines
  grep -v -e '^Found [0-9]* error' -e '^No fixes available' -e 'fixable with the' -e '^All checks passed' -e '^$' || true
}

# --- what counts as the gate's configuration ------------------------------------------

ruff_section() { # the [tool.ruff*] tables of a pyproject.toml read from stdin
  awk '/^[[:space:]]*\[/ { on = ($0 ~ /^[[:space:]]*\[+[[:space:]]*tool\.ruff/) } on'
}

gate_settings() { # this gate's groups and disableAllHooks in a settings file read from stdin
  jq -cS '{d: (.disableAllHooks // false), g: [(.hooks // {}) | to_entries[] | .key as $e | (.value // [])[]? | select(any((.hooks // [])[]?; (.command // "") | tostring | test("ruff-quality-gate[.]sh"))) | {e: $e, h: .}]}' 2>/dev/null || printf 'unparseable\n'
}

config_files() { # every file whose content can change what the gate enforces
  local f listed
  if [[ -n ${git_top} ]]; then
    listed=$(git -C "${git_top}" ls-files -co --exclude-standard -- '*ruff.toml' '*pyproject.toml' 2>/dev/null) || listed=""
    while IFS= read -r f; do
      case ${f##*/} in ruff.toml | .ruff.toml | pyproject.toml) printf '%s\n' "${git_top}/${f}" ;; *) ;; esac
    done <<<"${listed}"
  else
    for f in "${project}/ruff.toml" "${project}/.ruff.toml" "${project}/pyproject.toml"; do
      [[ -f ${f} ]] && printf '%s\n' "${f}"
    done
  fi
  for f in "${ruff_user_dir}/.ruff.toml" "${ruff_user_dir}/ruff.toml" "${ruff_user_dir}/pyproject.toml"; do
    [[ -f ${f} ]] && printf '%s\n' "${f}"
  done
  [[ -n ${config_file} ]] && printf '%s\n' "${config_file}"
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
    pyproject.toml) sum=$(ruff_section <"${f}" | cksum) ;;
    settings.json | settings.local.json) sum=$(gate_settings <"${f}" | cksum) ;;
    *) sum=$(cksum <"${f}") ;;
    esac
    printf '%s %s\n' "${sum}" "${f}"
  done <<<"${files}"
}

record_config_baseline() {
  local fp
  fp=$(fingerprint) || die "cannot fingerprint the Ruff configuration"
  printf '%s\n' "${fp}" >"${config_state}" || die "cannot write ${config_state}"
}

config_drift() { # prints the files that changed since the baseline, empty when none did
  local now before
  [[ -f ${config_state} ]] || return 0
  now=$(fingerprint) || die "cannot fingerprint the Ruff configuration"
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

is_protected_config() { # is_protected_config ABS -> 0 when the path governs the gate
  local f=$1
  case ${f##*/} in
  ruff.toml | .ruff.toml | ruff-quality-gate.sh) return 0 ;;
  *) ;;
  esac
  [[ ${f} == "${ruff_user_dir}"/* ]] && return 0
  [[ -n ${config_file} && ${f} == "${config_file}" ]] && return 0
  return 1
}

guard_file() { # guard_file ABS
  local f=$1 before after new_text n_old n_new
  if is_protected_config "${f}"; then
    rel "${f}"
    deny "Claude may not edit ${REL}: it is part of the Ruff configuration or of this gate. Configuration is the user's decision; ask the user to make the change themselves, and fix the code instead."
  fi
  case ${f##*/} in
  pyproject.toml)
    before=$(ruff_section <"${f}" 2>/dev/null | cksum) || before=""
    after=$(simulate_edit "${f}" | ruff_section | cksum) || after=""
    [[ ${before} == "${after}" ]] || deny "Claude may not change the [tool.ruff] tables of pyproject.toml: configuration is the user's decision. Edit other tables only, and fix the code instead of relaxing Ruff."
    return 0
    ;;
  settings.json | settings.local.json)
    if [[ -f ${f} ]]; then before=$(gate_settings <"${f}"); else before=$(printf '{}' | gate_settings); fi
    after=$(simulate_edit "${f}" | gate_settings) || after=""
    [[ ${before} == "${after}" ]] || deny "Claude may not change or disable the ruff-quality hooks (or set disableAllHooks). Only the user changes them, in their own terminal."
    return 0
    ;;
  *) ;;
  esac
  is_python "${f}" || return 0
  record_supp_baseline "${f}"
  new_text=$(jq -r '.tool_input | (.content // .new_string // .new_source // "")' <<<"${payload}") || new_text=""
  n_new=$(printf '%s' "${new_text}" | count_supp_text)
  if jq -e '.tool_input.content | type == "string"' >/dev/null 2>&1 <<<"${payload}"; then
    n_old=$(count_supp_file "${f}")
  else
    n_old=$(jq -r '.tool_input.old_string // ""' <<<"${payload}" | count_supp_text)
  fi
  if ((n_new > n_old)); then
    rel "${f}"
    deny "this edit to ${REL} adds a Ruff/formatter suppression comment (noqa, ruff: noqa/ignore/disable/file-ignore, fmt: off/skip, isort: skip/off). Silencing a finding is never allowed through this gate; change the code so the rule passes. If the user explicitly wants a suppression, they add it themselves."
  fi
}

guard_bash() {
  local c stripped
  c=$(jq -r '.tool_input.command // ""' <<<"${payload}" | tr '[:upper:]' '[:lower:]') || c=""
  [[ -n ${c} ]] || return 0
  case ${c} in
  *--add-noqa* | *--add-ignore*) deny "ruff --add-noqa/--add-ignore writes suppression comments; that is never allowed through this gate. Fix the findings in the code." ;;
  *disableallhooks*) deny "setting disableAllHooks turns this gate off; only the user may do that." ;;
  *ruff-hooks/scripts/manage.sh*install*)
    deny "reinstalling or uninstalling the ruff-quality gate changes what it enforces; only the user may do that. Ask them to run the command themselves with the ! prefix."
    ;;
  *) ;;
  esac
  # A write construct: redirection (other than to /dev/null or between fds),
  # in-place editors, tee/cp/mv/rm/ln, heredocs, or an inline interpreter.
  stripped=$(printf '%s' "${c}" | sed -E 's/[0-9]*>&[0-9-]//g; s/[0-9]*>>?[[:space:]]*\/dev\/null//g')
  if printf '%s' "${stripped}" | grep -Eq '>|sed[[:space:]]+(-[a-z]*i|--in-place)|perl[[:space:]]+-[a-z]*i|(^|[[:space:];|&(])(tee|cp|mv|rm|ln|truncate|install)[[:space:]]|<<|python[0-9.]*[[:space:]]+-c'; then
    if printf '%s' "${c}" | grep -Eq "${SUPP_RE}"; then
      deny "this command writes a Ruff/formatter suppression comment. Silencing a finding is never allowed through this gate; change the code instead."
    fi
    if printf '%s' "${c}" | grep -Eq 'ruff\.toml|pyproject\.toml|ruff-quality-gate\.sh|settings(\.local)?\.json|\.config/ruff'; then
      deny "this command writes to the Ruff configuration, pyproject.toml, or the Claude Code settings/handler of this gate. Use the Edit tool for non-Ruff pyproject changes; Ruff configuration and hooks are the user's decision."
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

# check_and_fix FILE SHOWN -> STATUS clean|skipped|findings, FINDINGS, CHANGED 0|1
check_and_fix() {
  local f=$1 shown=$2 before after fmt_rc fmt_out
  STATUS=clean
  FINDINGS=""
  CHANGED=0
  before=$(cksum <"${f}") || die "cannot read ${shown}"
  # F401 is left alone mid-change: an import added one edit before its first
  # use would otherwise be deleted as unused. The Stop gate still checks it.
  run_ruff check --fix --unfixable F401 --force-exclude --no-cache --output-format concise ${config_args[@]+"${config_args[@]}"} -- "${f}"
  case ${RC} in
  0 | 1) ;;
  *) die "ruff check --fix failed on ${shown} (exit ${RC}):
${OUT}" ;;
  esac
  if [[ ${OUT} == *"No Python files found"* ]]; then
    STATUS=skipped
    return 0
  fi
  run_ruff format --force-exclude --no-cache ${config_args[@]+"${config_args[@]}"} -- "${f}"
  fmt_rc=${RC}
  fmt_out=${OUT}
  run_ruff check --force-exclude --no-cache --output-format concise ${config_args[@]+"${config_args[@]}"} -- "${f}"
  # A file that cannot be parsed cannot be formatted; that is a finding
  # (invalid-syntax), not a gate failure. Any other format failure is.
  if ((fmt_rc != 0)) && [[ ${OUT} != *invalid-syntax* ]]; then
    die "ruff format failed on ${shown} (exit ${fmt_rc}):
${fmt_out}"
  fi
  case ${RC} in
  0) ;;
  1)
    FINDINGS=$(printf '%s\n' "${OUT}" | findings_only | grep -v ': F401 ' || true)
    [[ -n ${FINDINGS} ]] && STATUS=findings
    ;;
  *) die "ruff check failed on ${shown} (exit ${RC}):
${OUT}" ;;
  esac
  after=$(cksum <"${f}") || die "cannot read ${shown}"
  [[ ${before} == "${after}" ]] || CHANGED=1
}

do_post() {
  local c f shown count drift added note="" what files=() clean=() changed=() skipped=() report="" n_findings=0 policy=""
  for c in ${candidates[@]+"${candidates[@]}"}; do
    is_python "${c}" || continue
    abs_path "${c}" || continue
    [[ -f ${ABS} ]] || continue
    files+=("${ABS}")
  done
  ((${#files[@]} > 0)) || exit 0

  ensure_state_dir
  [[ -f ${config_state} ]] || record_config_baseline
  for f in "${files[@]}"; do
    printf '%s\n' "${f}" >>"${files_state}" || die "cannot write ${files_state}"
    record_supp_baseline "${f}" committed
  done

  for f in "${files[@]}"; do
    rel "${f}"
    shown=${REL}
    find_ruff "${f%/*}"
    check_and_fix "${f}" "${shown}"
    case ${STATUS} in
    skipped) skipped+=("${shown}") ;;
    clean) clean+=("${shown}") ;;
    *)
      count=$(printf '%s\n' "${FINDINGS}" | grep -c . || true)
      n_findings=$((n_findings + count))
      report="${report}${FINDINGS}"$'\n'
      ;;
    esac
    ((CHANGED)) && changed+=("${shown}")
    added=$(supp_added "${f}")
    [[ -n ${added} ]] && policy="${policy}${shown}: suppression comments grew from ${added#*>} to ${added%>*} this session; remove the new ones and fix the code."$'\n'
  done
  drift=$(config_drift)
  [[ -n ${drift} ]] && policy="${policy}The Ruff configuration or this gate's settings changed during this turn: ${drift//$'\n'/, }. Revert that change; configuration is the user's decision."$'\n'

  if [[ -n ${report}${policy} ]]; then
    ((${#changed[@]})) && note=" The hook rewrote ${changed[*]} (safe fixes/formatting); re-read before editing again."
    REPORT=""
    [[ -n ${report} ]] && trim_report "${report}"
    what="${n_findings} Ruff finding(s)"
    [[ -n ${policy} ]] && what="${what} and a suppression/configuration violation"
    emit_system_message "${TAG} ✗ ${what}; Claude has been told to fix them now."
    {
      printf '%s: STOP and fix this before any other change.%s\n\n' "${TAG}" "${note}"
      [[ -n ${REPORT} ]] && printf '%s\n\n' "${REPORT}"
      [[ -n ${policy} ]] && printf '%s\n' "${policy}"
      printf '%s\n' "Change the code so each rule passes. Suppression comments (noqa, ruff: noqa/ignore/disable/file-ignore, fmt: off/skip, isort: skip/off) and Ruff configuration changes are never accepted by this gate. Run \`ruff rule <CODE>\` to read a rule. The Stop gate re-checks these files before the turn can end."
    } >&2
    exit 2
  fi

  local msg="${TAG} ✓"
  ((${#clean[@]})) && msg="${msg} ${clean[*]}: lint-clean and formatted"
  ((${#changed[@]})) && msg="${msg} (safe fixes/formatting applied to ${changed[*]})"
  ((${#skipped[@]})) && msg="${msg}; skipped, excluded by the Ruff configuration: ${skipped[*]}"
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
      [[ -n ${f} && -f ${f} ]] && is_python "${f}" && files+=("${f}")
    done <<<"${sorted}"
  fi

  # A new turn (not a continuation caused by a Stop hook) starts a new count.
  if [[ ${stop_active} == true && -f ${blocks_state} ]]; then
    blocks=$(cat "${blocks_state}" 2>/dev/null) || blocks=0
    case ${blocks} in '' | *[!0-9]*) blocks=0 ;; *) ;; esac
  fi

  for f in ${files[@]+"${files[@]}"}; do
    n_files=$((n_files + 1))
    rel "${f}"
    shown=${REL}
    find_ruff "${f%/*}"
    lint=""
    fmt=""
    run_ruff check --force-exclude --no-cache --output-format concise ${config_args[@]+"${config_args[@]}"} -- "${f}"
    case ${RC} in
    0) ;;
    1) lint=$(printf '%s\n' "${OUT}" | findings_only) ;;
    *) die "ruff check failed on ${shown} (exit ${RC}):
${OUT}" ;;
    esac
    run_ruff format --check --force-exclude --no-cache --output-format concise ${config_args[@]+"${config_args[@]}"} -- "${f}"
    case ${RC} in
    0) ;;
    1) fmt="${shown}: not formatted (run: ruff format ${shown})" ;;
    *) [[ -n ${lint} ]] || die "ruff format --check failed on ${shown} (exit ${RC}):
${OUT}" ;;
    esac
    added=$(supp_added "${f}")
    if [[ -n ${added} ]]; then
      [[ -n ${lint} ]] && lint="${lint}"$'\n'
      lint="${lint}${shown}: suppression comments grew from ${added#*>} to ${added%>*} this session; remove the new ones and fix the code"
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
    report="${report}The Ruff configuration or this gate's settings changed during this turn: ${drift//$'\n'/, }. Revert that change; configuration is the user's decision."$'\n'
  fi

  if [[ -z ${report} ]]; then
    rm -f "${blocks_state}"
    ((n_files > 0)) && emit_system_message "${TAG} ✓ Stop gate: ${n_files} edited Python file(s) are lint-clean, formatted, and unsuppressed."
    exit 0
  fi

  blocks=$((blocks + 1))
  trim_report "${report}"
  if ((blocks > max_blocks)); then
    rm -f "${blocks_state}"
    emit_system_message "⚠️ ${TAG}: the turn ended after ${max_blocks} blocked stop attempts with problems still unresolved in: ${bad[*]}. Ask Claude to fix them, or run: ruff check ${bad[*]}"
    exit 0
  fi
  printf '%s\n' "${blocks}" >"${blocks_state}" || die "cannot write ${blocks_state}"
  emit_system_message "${TAG} ✗ Stop gate (${blocks}/${max_blocks}): unresolved in ${bad[*]}; Claude must fix them before finishing."
  {
    printf '%s: you cannot finish yet (block %s of %s). What you changed this session still fails the Python quality gate:\n\n' "${TAG}" "${blocks}" "${max_blocks}"
    printf '%s\n\n' "${REPORT}"
    printf '%s\n' "Fix it in the code now: \`ruff check --fix <file>\` for safe fixes and \`ruff format <file>\` for formatting, then correct the rest by hand. Suppression comments and configuration changes are never accepted. If a finding truly needs the user's decision, say exactly which one and why."
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
