#!/usr/bin/env bash
# shell-quality hook handler. Bash 3.2 compatible. Installs nothing: it only runs
# a shfmt and a ShellCheck that are already installed, in the project or globally.
#
#   shell-gate.sh guard  PreToolUse: asks the user before an edit adds a
#                        ShellCheck suppression or changes .shellcheckrc or the
#                        shfmt keys of .editorconfig.
#   shell-gate.sh post   PostToolUse: on the edited .sh/.bash file, formats with
#                        shfmt, checks with ShellCheck, and hands what is left to
#                        Claude.
#   shell-gate.sh stop   Stop: re-checks every script this session touched and
#                        keeps Claude working up to MAX_BLOCKS times; the next
#                        stop ends with a failure message to the user.
#
# Both tools find their own configuration: ShellCheck the nearest .shellcheckrc,
# then ~/.shellcheckrc, then $XDG_CONFIG_HOME/shellcheckrc, plus SHELLCHECK_OPTS;
# shfmt the .editorconfig files above the script (no style flags are passed).
# Without the tools or jq the hook says so once per session and never blocks.
# CLAUDE_PLUGIN_OPTION_ENABLED=false (the plugin's `enabled` option) turns it off.
set -u

readonly TAG="shell-quality"
readonly MAX_BLOCKS=7
readonly MAX_LINES=60
readonly SUPP_RE='#[[:space:]]*shellcheck[[:space:]]+([a-z-]+=[^[:space:]]+[[:space:]]+)*(disable=|source=/dev/null)'
readonly EC_KEYS_RE='^[[:space:]]*(\[|root|indent_style|indent_size|shell_variant|language_dialect|binary_next_line|switch_case_indent|case_indent|space_redirects|keep_padding|function_next_line|block_next_line|simplify|minify|ignore)'
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
    dir="${dir%/}/shell-quality-$(id -u 2>/dev/null || echo 0)"
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
    say_user "${TAG}: jq is not installed, so the shell hook is not running. Install jq (brew install jq, apt install jq, winget install jqlang.jq)."
  fi
  exit 0
fi

field() { jq -r "$1 // empty" <<<"${payload}" 2>/dev/null; }

cwd=$(field '.cwd')
[[ -d ${cwd} ]] || cwd=${PWD}
tool=$(field '.tool_name')
file=$(field '.tool_input.file_path')
[[ -n ${file} && ${file} != /* ]] && file="${cwd%/}/${file}"

is_shell() { case $1 in *.sh | *.bash) return 0 ;; *) return 1 ;; esac }
count_supp() { # how many suppression directives a text carries
  local found n
  found=$(grep -oE "${SUPP_RE}" <<<"$1") || found=""
  n=0
  [[ -n ${found} ]] && n=$(wc -l <<<"${found}")
  printf '%d' "${n}"
}
ec_view() { grep -E "${EC_KEYS_RE}" <<<"$1" || true; } # the lines that decide shfmt style
rel() { case $1 in "${cwd%/}"/*) printf '%s' "${1#"${cwd%/}"/}" ;; *) printf '%s' "$1" ;; esac }

# ------------------------------------------------------------------ guard ---

do_guard() {
  if [[ ${tool} == Bash ]]; then
    local cmd
    cmd=$(field '.tool_input.command')
    if [[ ${cmd} =~ ${WRITE_RE} ]]; then
      grep -qE "${SUPP_RE}" <<<"${cmd}" &&
        ask "Claude wants to run a command that writes a ShellCheck suppression. Allow it only if you want that finding silenced instead of fixed."
      [[ ${cmd} =~ (shellcheckrc|\.editorconfig) ]] &&
        ask "Claude wants to run a command that writes to .shellcheckrc or .editorconfig. Allow it only if you want this configuration change."
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
  .shellcheckrc | shellcheckrc)
    ask "Claude wants to edit ${where}, a ShellCheck configuration file. Allow it only if you want this configuration change."
    ;;
  .editorconfig)
    local before after
    before=$(ec_view "${old}")
    after=$(ec_view "${new}")
    [[ ${before} == "${after}" ]] ||
      ask "Claude wants to change sections or shfmt keys (indent, language_dialect, binary_next_line, case_indent, space_redirects, function_next_line, simplify and others) in ${where}. Allow it only if you want this formatting change."
    ;;
  *)
    is_shell "${file}" || exit 0
    local added removed
    added=$(count_supp "${new}")
    removed=$(count_supp "${old}")
    ((added > removed)) &&
      ask "Claude wants to add a ShellCheck suppression (# shellcheck disable=... or source=/dev/null) to ${where}. Allow it only if you want that finding silenced instead of fixed."
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------ tools ---

find_tool() { # find_tool NAME DIR: the project's own install above DIR, then the global one
  local name=$1 d=$2 c
  while [[ -n ${d} && ${d} != / ]]; do
    for c in "${d}/.venv/bin/${name}" "${d}/venv/bin/${name}" "${d}/.venv/Scripts/${name}.exe"; do
      [[ -x ${c} ]] && printf '%s' "${c}" && return 0
    done
    d=${d%/*}
  done
  command -v "${name}" 2>/dev/null && return 0
  for c in "${HOME}/.local/bin/${name}" "/opt/homebrew/bin/${name}" "/usr/local/bin/${name}"; do
    [[ -x ${c} ]] && printf '%s' "${c}" && return 0
  done
  return 1
}

SHFMT=""
SHELLCHECK=""
find_tools() {
  SHFMT=$(find_tool shfmt "$1") || SHFMT=""
  SHELLCHECK=$(find_tool shellcheck "$1") || SHELLCHECK=""
  [[ -n ${SHFMT} && -n ${SHELLCHECK} ]]
}

missing_tools() {
  local which=""
  [[ -n ${SHFMT} ]] || which="shfmt"
  [[ -n ${SHELLCHECK} ]] || which="${which:+${which} and }ShellCheck"
  first_time notools &&
    say_user "${TAG}: ${which} not installed in this project or on PATH, so shell scripts are not being checked. Install them (brew install shellcheck shfmt, apt install shellcheck shfmt, or add shellcheck-py and shfmt-py to the project's dev dependencies)."
  exit 0
}

opts_note() { [[ -n ${SHELLCHECK_OPTS:-} ]] && printf ' (SHELLCHECK_OPTS=%s applies)' "${SHELLCHECK_OPTS}"; }

FINDINGS=""
CHANGED=0
# Format and check one script. Returns 0 clean, 1 findings, 2 cannot be checked, 3 zsh.
correct() {
  local f=$1 before after out rc first
  first=$(head -n 1 "${f}" 2>/dev/null) || first=""
  [[ ${first} == '#!'*zsh* ]] && return 3
  before=$(cksum <"${f}" 2>/dev/null)
  out=$(cd "${cwd}" && "${SHFMT}" -w "${f}" 2>&1)
  rc=$?
  after=$(cksum <"${f}" 2>/dev/null)
  [[ ${before} == "${after}" ]] || CHANGED=1
  if ((rc != 0)); then
    out=${out//"${f}:"/"$(rel "${f}"):"}
    FINDINGS=$(awk -v max="${MAX_LINES}" 'NF { print; if (++n >= max) exit }' <<<"shfmt could not parse the script:
${out}")
    return 1
  fi
  out=$(cd "${f%/*}" && "${SHELLCHECK}" -x -f gcc "${f}" 2>&1)
  rc=$?
  # ShellCheck runs from the script's directory, so `source` resolves as it does at run
  # time, and prints the path it was given; report it relative to the project instead.
  out=${out//"${f}:"/"$(rel "${f}"):"}
  FINDINGS=$(awk -v max="${MAX_LINES}" 'NF { print; if (++n >= max) exit }' <<<"${out}")
  ((rc > 1)) && return 2
  return "${rc}"
}

# ------------------------------------------------------------------- post ---

do_post() {
  [[ -n ${file} && -f ${file} ]] && is_shell "${file}" || exit 0
  find_tools "${file%/*}" || missing_tools
  [[ -n ${STATE_DIR} ]] && printf '%s\n' "${file}" >>"${STATE_DIR}/${SESSION}.files"
  local r rc note
  r=$(rel "${file}")
  note=$(opts_note)
  correct "${file}"
  rc=$?
  case ${rc} in
  0)
    if ((CHANGED)); then say_user "${TAG} ✓ ${r}: formatted, ShellCheck clean${note}"; else say_user "${TAG} ✓ ${r}: clean${note}"; fi
    ;;
  1)
    jq -cn --arg r "${TAG}: ${r} still fails after formatting${note}. Fix each finding in the script (read a code's explanation at https://www.shellcheck.net/wiki/SC<code>); a # shellcheck disable= directive or a configuration change is not a fix and needs the user's confirmation. Findings:
${FINDINGS}" --arg m "${TAG}: ${r} has findings left; Claude is fixing them" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  3)
    say_user "${TAG}: ${r} is a zsh script; ShellCheck does not support zsh, so it was not checked"
    ;;
  *)
    jq -cn --arg r "${TAG}: ShellCheck could not check ${r} (exit ${rc}). This is a tool or configuration error, not a finding; tell the user what it says:
${FINDINGS}" --arg m "${TAG}: ShellCheck failed on ${r} (exit ${rc})" \
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
  local active blocks=0 f r rc report="" bad=0 checked=0 files note
  active=$(field '.stop_hook_active')
  [[ ${active} == true && -f ${blocks_file} ]] && blocks=$(cat "${blocks_file}" 2>/dev/null)
  [[ ${blocks} =~ ^[0-9]+$ ]] || blocks=0
  note=$(opts_note)
  files=$(sort -u "${list}")
  while IFS= read -r f; do
    [[ -f ${f} ]] || continue
    find_tools "${f%/*}" || continue
    correct "${f}"
    rc=$?
    ((rc == 3)) && continue
    checked=$((checked + 1))
    if ((rc != 0)); then
      bad=$((bad + 1))
      r=$(rel "${f}")
      report="${report}${r} (exit ${rc}):
${FINDINGS}
"
    fi
  done <<<"${files}"
  if ((bad == 0)); then
    rm -f "${list}" "${blocks_file}"
    ((checked > 0)) && say_user "${TAG} ✓ ${checked} shell script(s) touched this session pass shfmt and ShellCheck${note}"
    exit 0
  fi
  if ((blocks >= MAX_BLOCKS)); then
    rm -f "${blocks_file}"
    say_user "${TAG} ✗ gave up after ${MAX_BLOCKS} attempts: ${bad} shell script(s) still fail shfmt or ShellCheck${note}.
${report}"
    exit 0
  fi
  blocks=$((blocks + 1))
  printf '%s\n' "${blocks}" >"${blocks_file}"
  jq -cn --arg c "${TAG}: you cannot finish yet (attempt ${blocks} of ${MAX_BLOCKS}). These scripts you changed still fail after formatting${note}. Fix each finding in the script; a # shellcheck disable= directive or a configuration change is not a fix and needs the user's confirmation.
${report}" --arg m "${TAG}: ${bad} shell script(s) still fail; Claude keeps working (${blocks}/${MAX_BLOCKS})" \
    '{systemMessage: $m, hookSpecificOutput: {hookEventName: "Stop", additionalContext: $c}}'
  exit 0
}

case ${event} in
guard) do_guard ;;
post) do_post ;;
stop) do_stop ;;
*) exit 0 ;;
esac
