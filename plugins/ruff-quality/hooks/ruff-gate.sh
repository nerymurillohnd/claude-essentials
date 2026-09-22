#!/usr/bin/env bash
# ruff-quality hook handler. Bash 3.2 compatible. Installs nothing: it only runs
# a Ruff that is already installed, in the project or globally.
#
#   ruff-gate.sh guard  PreToolUse: asks the user before an edit adds a
#                       suppression comment or changes Ruff configuration.
#   ruff-gate.sh post   PostToolUse: on the edited .py/.pyw/.pyi file, applies
#                       safe fixes, formats, re-checks, and hands what is left
#                       to Claude.
#   ruff-gate.sh stop   Stop: re-checks every file this session touched and keeps
#                       Claude working up to MAX_BLOCKS times; the next stop ends
#                       with a failure message to the user.
#
# Ruff finds its own configuration (nearest ruff.toml, .ruff.toml or
# pyproject.toml [tool.ruff], then the user-level file, then its defaults).
# Without Ruff or jq the hook says so once per session and never blocks.
# CLAUDE_PLUGIN_OPTION_ENABLED=false (the plugin's `enabled` option) turns it off.
set -u

readonly TAG="ruff-quality"
readonly MAX_BLOCKS=7
readonly MAX_LINES=60
readonly SUPP_RE='#[[:space:]]*(noqa|ruff:[[:space:]]*(noqa|ignore|disable|file-ignore)|fmt:[[:space:]]*(off|skip)|isort:[[:space:]]*(skip|off)|yapf:[[:space:]]*disable)'
readonly WRITE_RE='(>|[[:space:]]tee[[:space:]]|sed[[:space:]]+-[a-zA-Z]*i|perl[[:space:]]+-[a-zA-Z]*i|<<)'

event=${1:-}
[[ ${CLAUDE_PLUGIN_OPTION_ENABLED:-true} == false ]] && exit 0
payload=$(cat)

# ------------------------------------------------------------------ state ---

state_dir() {
  local dir
  if [[ -n ${CLAUDE_PLUGIN_DATA:-} ]]; then
    dir="${CLAUDE_PLUGIN_DATA%/}/sessions"
  else
    dir=${TMPDIR:-/tmp}
    dir="${dir%/}/ruff-quality-$(id -u 2>/dev/null || echo 0)"
  fi
  if (umask 077 && mkdir -p "${dir}") 2>/dev/null && [[ -d ${dir} && -w ${dir} ]]; then
    STATE_DIR=${dir}
    find "${dir}" -type f -mtime +7 -exec rm -f {} + 2>/dev/null
    return 0
  fi
  STATE_DIR=""
  return 1
}

# The payload's top-level session_id as a safe file name (never a path).
SESSION=""
session_re='"session_id"[[:space:]]*:[[:space:]]*"([^"]{1,200})"'
if [[ ${payload} =~ ${session_re} ]]; then
  SESSION=$(printf '%s' "${BASH_REMATCH[1]}" | tr -c 'A-Za-z0-9_-' '_')
fi
[[ -n ${SESSION} ]] || SESSION=unknown
state_dir || true

# First call per session and key returns 0; later calls return 1.
first_time() {
  [[ -n ${STATE_DIR} ]] || return 0
  local mark="${STATE_DIR}/${SESSION}.noticed-$1"
  [[ -e ${mark} ]] && return 1
  : >"${mark}" 2>/dev/null
  return 0
}

# ---------------------------------------------------------------- output ---

say_user() { # systemMessage: shown to the user
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg m "$1" '{systemMessage: $m}'
  else
    printf '{"systemMessage":"%s"}\n' "$1"
  fi
}

ask() {
  jq -cn --arg r "${TAG}: $1" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $r}}'
  exit 0
}

if ! command -v jq >/dev/null 2>&1; then
  if [[ ${event} != guard ]] && first_time nojq; then
    say_user "${TAG}: jq is not installed, so the Ruff hook is not running. Install jq (brew install jq, apt install jq, winget install jqlang.jq)."
  fi
  exit 0
fi

field() { jq -r "$1 // empty" <<<"${payload}" 2>/dev/null; }

cwd=$(field '.cwd')
[[ -d ${cwd} ]] || cwd=${PWD}
tool=$(field '.tool_name')
file=$(field '.tool_input.file_path')
[[ -n ${file} && ${file} != /* ]] && file="${cwd%/}/${file}"

is_python() { case $1 in *.py | *.pyw | *.pyi) return 0 ;; *) return 1 ;; esac }
count_supp() { # how many suppression markers a text carries
  local found n
  found=$(grep -oiE "${SUPP_RE}" <<<"$1") || found=""
  n=0
  [[ -n ${found} ]] && n=$(wc -l <<<"${found}")
  printf '%d' "${n}"
}
ruff_section() { # the [tool.ruff*] tables of a pyproject.toml text
  awk '/^[[:space:]]*\[/{ on = ($0 ~ /^[[:space:]]*\[+tool\.ruff(\]|\.)/) } on' <<<"$1"
}
rel() { case $1 in "${cwd%/}"/*) printf '%s' "${1#"${cwd%/}"/}" ;; *) printf '%s' "$1" ;; esac }

# ------------------------------------------------------------------ guard ---

do_guard() {
  if [[ ${tool} == Bash ]]; then
    local cmd
    cmd=$(field '.tool_input.command')
    [[ ${cmd} == *--add-noqa* || ${cmd} == *--add-ignore* ]] &&
      ask "Claude wants to run ruff --add-noqa or --add-ignore, which write suppression comments. Allow it only if you want those findings silenced instead of fixed."
    if [[ ${cmd} =~ ${WRITE_RE} ]]; then
      grep -qiE "${SUPP_RE}" <<<"${cmd}" &&
        ask "Claude wants to run a command that writes a Ruff suppression comment. Allow it only if you want that finding silenced instead of fixed."
      [[ ${cmd} =~ (ruff\.toml|pyproject\.toml) ]] &&
        ask "Claude wants to run a command that writes to Ruff configuration (ruff.toml or pyproject.toml). Allow it only if you want this configuration change."
    fi
    exit 0
  fi
  [[ -n ${file} ]] || exit 0
  local new old current where
  where=$(rel "${file}")
  new=$(field '[.tool_input.content, .tool_input.new_string, (.tool_input.edits // [] | .[].new_string)] | map(select(. != null)) | join("\n")')
  old=$(field '[.tool_input.old_string, (.tool_input.edits // [] | .[].old_string)] | map(select(. != null)) | join("\n")')
  current=""
  [[ -f ${file} ]] && current=$(cat "${file}" 2>/dev/null)
  [[ ${tool} == Write ]] && old=${current}
  case ${file##*/} in
  ruff.toml | .ruff.toml)
    ask "Claude wants to edit ${where}, a Ruff configuration file. Allow it only if you want this configuration change."
    ;;
  pyproject.toml)
    local section after
    section=$(ruff_section "${current}")
    if [[ ${tool} == Write ]]; then
      after=$(ruff_section "${new}")
      [[ ${section} == "${after}" ]] ||
        ask "Claude wants to change the [tool.ruff] tables of ${where}. Allow it only if you want this Ruff configuration change."
    elif [[ ${new}${old} == *tool.ruff* ]] || { [[ -n ${old} && -n ${section} ]] && [[ ${section} == *"${old}"* ]]; }; then
      ask "Claude wants to change the [tool.ruff] tables of ${where}. Allow it only if you want this Ruff configuration change."
    fi
    ;;
  *)
    is_python "${file}" || exit 0
    local added removed
    added=$(count_supp "${new}")
    removed=$(count_supp "${old}")
    ((added > removed)) &&
      ask "Claude wants to add a suppression comment (noqa, ruff: noqa, fmt: off/skip, yapf: disable or isort: skip) to ${where}. Allow it only if you want that finding silenced instead of fixed."
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------- ruff ---

RUFF=""
find_ruff() { # the project's own install above $1, then the global one
  local d=$1 c
  while [[ -n ${d} && ${d} != / ]]; do
    for c in "${d}/.venv/bin/ruff" "${d}/venv/bin/ruff" "${d}/.venv/Scripts/ruff.exe"; do
      [[ -x ${c} ]] && RUFF=${c} && return 0
    done
    d=${d%/*}
  done
  RUFF=$(command -v ruff 2>/dev/null) && return 0
  for c in "${HOME}/.local/bin/ruff" /opt/homebrew/bin/ruff /usr/local/bin/ruff; do
    [[ -x ${c} ]] && RUFF=${c} && return 0
  done
  RUFF=""
  return 1
}

FINDINGS=""
CHANGED=0
# Fix, format and re-check one file. Returns 0 clean, 1 findings, 2 tool break.
correct() {
  local f=$1 before after out rc
  before=$(cksum <"${f}" 2>/dev/null)
  (cd "${cwd}" && "${RUFF}" check --fix --no-unsafe-fixes --unfixable F401 --force-exclude --no-cache --quiet "${f}") >/dev/null 2>&1
  (cd "${cwd}" && "${RUFF}" format --force-exclude --no-cache --quiet "${f}") >/dev/null 2>&1
  out=$(cd "${cwd}" && "${RUFF}" check --no-fix --force-exclude --no-cache --output-format concise "${f}" 2>&1)
  rc=$?
  after=$(cksum <"${f}" 2>/dev/null)
  [[ ${before} == "${after}" ]] || CHANGED=1
  FINDINGS=$(awk -v max="${MAX_LINES}" '!/^Found [0-9]+ error/ && NF { print; if (++n >= max) exit }' <<<"${out}")
  return "${rc}"
}

missing_ruff() {
  first_time noruff &&
    say_user "${TAG}: Ruff is not installed in this project or on PATH, so Python files are not being checked. Install it (uv add --dev ruff, uv tool install ruff, pipx install ruff or brew install ruff)."
  exit 0
}

# ------------------------------------------------------------------- post ---

do_post() {
  [[ -n ${file} && -f ${file} ]] && is_python "${file}" || exit 0
  find_ruff "${file%/*}" || missing_ruff
  [[ -n ${STATE_DIR} ]] && printf '%s\n' "${file}" >>"${STATE_DIR}/${SESSION}.files"
  local r rc
  r=$(rel "${file}")
  correct "${file}"
  rc=$?
  case ${rc} in
  0)
    if ((CHANGED)); then say_user "${TAG} ✓ ${r}: fixed and formatted, no findings left"; else say_user "${TAG} ✓ ${r}: clean"; fi
    ;;
  1)
    jq -cn --arg r "${TAG}: ${r} still fails Ruff after the safe fixes and formatting. Fix each finding in the code; a suppression comment or a configuration change is not a fix and needs the user's confirmation. Findings:
${FINDINGS}" --arg m "${TAG}: ${r} has Ruff findings left; Claude is fixing them" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  *)
    jq -cn --arg r "${TAG}: Ruff could not check ${r} (exit ${rc}). This is a tool or configuration error, not a finding; tell the user what it says:
${FINDINGS}" --arg m "${TAG}: Ruff failed on ${r} (exit ${rc})" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------- stop ---

do_stop() {
  [[ -n ${STATE_DIR} ]] || exit 0
  local list="${STATE_DIR}/${SESSION}.files" blocks_file="${STATE_DIR}/${SESSION}.blocks"
  [[ -s ${list} ]] || exit 0
  local active blocks=0 f r rc report="" bad=0 checked=0 files
  active=$(field '.stop_hook_active')
  [[ ${active} == true && -f ${blocks_file} ]] && blocks=$(cat "${blocks_file}" 2>/dev/null)
  [[ ${blocks} =~ ^[0-9]+$ ]] || blocks=0
  files=$(sort -u "${list}")
  while IFS= read -r f; do
    [[ -f ${f} ]] || continue
    find_ruff "${f%/*}" || continue
    checked=$((checked + 1))
    r=$(rel "${f}")
    correct "${f}"
    rc=$?
    if ((rc != 0)); then
      bad=$((bad + 1))
      report="${report}${r} (exit ${rc}):
${FINDINGS}
"
    fi
  done <<<"${files}"
  if ((bad == 0)); then
    rm -f "${list}" "${blocks_file}"
    ((checked > 0)) && say_user "${TAG} ✓ ${checked} Python file(s) touched this session pass Ruff"
    exit 0
  fi
  if ((blocks >= MAX_BLOCKS)); then
    rm -f "${blocks_file}"
    say_user "${TAG} ✗ gave up after ${MAX_BLOCKS} attempts: ${bad} Python file(s) still fail Ruff.
${report}"
    exit 0
  fi
  blocks=$((blocks + 1))
  printf '%s\n' "${blocks}" >"${blocks_file}"
  jq -cn --arg c "${TAG}: you cannot finish yet (attempt ${blocks} of ${MAX_BLOCKS}). These files you changed still fail Ruff after the safe fixes and formatting. Fix each finding in the code; a suppression comment or a configuration change is not a fix and needs the user's confirmation.
${report}" --arg m "${TAG}: ${bad} Python file(s) still fail Ruff; Claude keeps working (${blocks}/${MAX_BLOCKS})" \
    '{systemMessage: $m, hookSpecificOutput: {hookEventName: "Stop", additionalContext: $c}}'
  exit 0
}

case ${event} in
guard) do_guard ;;
post) do_post ;;
stop) do_stop ;;
*) exit 0 ;;
esac
