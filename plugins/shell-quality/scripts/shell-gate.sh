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
#   shell-gate.sh stop   Stop: re-formats and re-checks every script this session
#                        touched and keeps Claude working while the findings change,
#                        up to MAX_BLOCKS times; then it tells the user what still
#                        fails and forgets those scripts until they are edited again.
#
# Both tools find their own configuration: ShellCheck the nearest .shellcheckrc,
# then ~/.shellcheckrc, then $XDG_CONFIG_HOME/shellcheckrc, plus SHELLCHECK_OPTS;
# shfmt the .editorconfig files above the script (no style flags are passed).
# Without the tools or jq the hook says so once per session and never blocks.
# CLAUDE_PLUGIN_OPTION_ENABLED false, 0, no or off (the plugin's `enabled` option) turns it off.
set -u

readonly TAG="shell-quality"
readonly MAX_BLOCKS=7
readonly MAX_LINES=60
readonly MAX_REPORT=8000 # Claude Code keeps at most 10,000 characters of additionalContext
readonly SUPP_RE='#[[:space:]]*shellcheck[[:space:]]+([a-z-]+=[^[:space:]]+[[:space:]]+)*(disable=|source=/dev/null)'
readonly EC_KEYS_RE='^[[:space:]]*(\[|root|indent_style|indent_size|shell_variant|language_dialect|binary_next_line|switch_case_indent|case_indent|space_redirects|keep_padding|function_next_line|block_next_line|simplify|minify|ignore)'
readonly WRITE_RE='(>|[[:space:]]tee[[:space:]]|sed[[:space:]]+-[a-zA-Z]*i|perl[[:space:]]+-[a-zA-Z]*i|<<)'

event=${1:-}
# How Claude Code writes a boolean option into the environment is not documented, so every
# common spelling of "off" counts.
case $(printf '%s' "${CLAUDE_PLUGIN_OPTION_ENABLED:-true}" | tr '[:upper:]' '[:lower:]') in
false | 0 | no | off) exit 0 ;;
*) ;;
esac
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
  # A fallback directory someone else created (or a symlink to one) is never trusted.
  if (umask 077 && mkdir -p "${dir}") 2>/dev/null && [[ -d ${dir} && ! -L ${dir} && -O ${dir} && -w ${dir} ]]; then
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

tell_both() { # tell_both EVENT TEXT: the user sees it, and Claude gets it as context
  jq -cn --arg e "$1" --arg m "$2" '{systemMessage: $m, hookSpecificOutput: {hookEventName: $e, additionalContext: $m}}'
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
# A command with its harmless redirects (2>&1, >/dev/null) removed, so they are not taken for
# writes.
write_view() { sed -E 's/[0-9]*>&[0-9]+//g; s/[0-9]*>+[[:space:]]*\/dev\/null//g' <<<"$1"; }
ec_view() { grep -E "${EC_KEYS_RE}" <<<"$1" || true; } # the lines that decide shfmt style
rel() { case $1 in "${cwd%/}"/*) printf '%s' "${1#"${cwd%/}"/}" ;; *) printf '%s' "$1" ;; esac }

# The directives an edit adds, one per line, each from `# shellcheck` to the end of its line,
# lower-cased. Write compares the new content with the file on disk; Edit compares each
# replacement with its own old_string. A directive whose text changes (another code,
# `disable=all`) counts as added, and removing one in a replacement never offsets adding one
# in another.
added_markers() {
  local disk=/dev/null out
  # A file the hook cannot read is compared with nothing, so any marker in the edit asks.
  [[ ${tool} == Write && -f ${file} && -r ${file} ]] && disk=${file}
  if out=$(jq -r --arg re "${SUPP_RE}" --arg tool "${tool}" --rawfile disk "${disk}" '
    def markers: split("\n") | map(select(test($re)) | (match($re).offset) as $o
      | .[$o:] | ascii_downcase | gsub("[[:space:]]+"; " ") | sub(" $"; ""));
    def counts: reduce .[] as $m ({}; .[$m] += 1);
    .tool_input
    | if $tool == "Write" then [{n: (.content // ""), o: $disk}]
      else [(.edits // [.])[] | {n: (.new_string // ""), o: (.old_string // "")}] end
    | map((.o | markers | counts) as $old | .n | markers | counts
      | to_entries | map(select(.value > ($old[.key] // 0)) | .key))
    | add // [] | unique | .[]' <<<"${payload}" 2>/dev/null); then
    printf '%s' "${out}"
    return 0
  fi
  # jq could not compare: fail toward asking whenever the payload carries a marker at all.
  grep -qE "${SUPP_RE}" <<<"${payload}" && printf '%s' "a suppression marker (the hook could not compare it with the file)"
  return 0
}

# ------------------------------------------------------------------ guard ---

do_guard() {
  if [[ ${tool} == Bash ]]; then
    local cmd writes
    cmd=$(field '.tool_input.command')
    writes=$(write_view "${cmd}")
    if [[ ${writes} =~ ${WRITE_RE} ]]; then
      grep -qE "${SUPP_RE}" <<<"${writes}" &&
        ask "Claude wants to run a command that may write a ShellCheck suppression. Allow it only if you want that finding silenced instead of fixed."
      [[ ${writes} =~ (shellcheckrc|\.editorconfig) ]] &&
        ask "Claude wants to run a command that may write to .shellcheckrc or .editorconfig. Allow it only if you want this configuration change."
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
      ask "Claude wants to change the sections or shfmt keys of ${where} (indentation, shell_variant, binary_next_line, switch_case_indent, space_redirects and the others shfmt reads, including names newer shfmt releases use). Allow it only if you want this formatting change."
    ;;
  *)
    is_shell "${file}" || exit 0
    local added
    added=$(added_markers) || added=""
    added=$(awk 'NR > 1 { printf "; " } { printf "%s", $0 }' <<<"${added}")
    [[ -n ${added} ]] &&
      ask "Claude wants to add or widen a ShellCheck directive in ${where}: ${added}. Allow it only if you want that finding silenced instead of fixed."
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------ tools ---

find_tool() { # find_tool NAME DIR: the project's own install between DIR and the project root, then the global one
  local name=$1 d=$2 root c
  root=${CLAUDE_PROJECT_DIR:-${cwd}}
  root=${root%/}
  # Only inside the project, and only an executable this user owns: a .venv planted in a
  # shared parent directory (/tmp) is never run.
  case "${d}/" in
  "${root}"/*)
    while [[ -n ${d} ]]; do
      for c in "${d}/.venv/bin/${name}" "${d}/venv/bin/${name}" "${d}/.venv/Scripts/${name}.exe"; do
        [[ -x ${c} && -O ${c} ]] && printf '%s' "${c}" && return 0
      done
      [[ ${d} == "${root}" ]] && break
      d=${d%/*}
    done
    ;;
  *) ;;
  esac
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
    tell_both PostToolUse "${TAG}: ${which} not installed in this project or on PATH, so shell scripts are not being checked. Install them (brew install shellcheck shfmt, apt install shellcheck shfmt, or add shellcheck-py and shfmt-py to the project's dev dependencies); Claude does not install them unasked."
  exit 0
}

opts_note() { [[ -n ${SHELLCHECK_OPTS:-} ]] && printf ' (SHELLCHECK_OPTS=%s applies)' "${SHELLCHECK_OPTS}"; }

FINDINGS=""
CHANGED=0
# First MAX_LINES non-empty lines of a tool's report, with the script's absolute path at
# the start of a line shortened to the project-relative one, saying so when there were more.
# ShellCheck runs from the script's directory so `source` resolves as it does at run time,
# and both tools print the path they were given. awk keeps this linear on long reports.
trim_findings() { # trim_findings FILE TEXT
  local short
  short=$(rel "$1")
  awk -v max="${MAX_LINES}" -v abs="$1:" -v short="${short}:" -v file="${short}" '
    NF { if (index($0, abs) == 1) $0 = short substr($0, length(abs) + 1); total++; if (total <= max) print }
    END { if (total > max) printf "... first %d of %d lines shown; run `shellcheck -x -f gcc` on %s from its directory for the rest\n", max, total, file }' <<<"$2"
}

# Report whether shfmt's output is a parse error, which it prints as FILE:LINE:COL: message.
# Anything else it prints on failure (a file it cannot write, a bad flag) is a tool error.
is_parse_error() { # is_parse_error FILE OUTPUT
  local line
  while IFS= read -r line; do
    [[ ${line} == "$1:"* && ${line#"$1:"} =~ ^[0-9]+:[0-9]+: ]] && return 0
  done <<<"$2"
  return 1
}

# Format and check one script. Returns 0 clean, 1 findings, 2 cannot be checked (a tool or
# configuration error), 3 zsh, 4 shfmt could not parse it (Claude's edit broke the syntax).
correct() {
  local f=$1 before after out rc first
  first=$(head -n 1 "${f}" 2>/dev/null) || first=""
  [[ ${first} == '#!'*zsh* ]] && return 3
  before=$(cksum <"${f}" 2>/dev/null)
  out=$(cd "${cwd}" && "${SHFMT}" -w -- "${f}" 2>&1)
  rc=$?
  after=$(cksum <"${f}" 2>/dev/null)
  [[ ${before} == "${after}" ]] || CHANGED=1
  if ((rc != 0)); then
    if [[ ${out} == *"via EditorConfig"* ]]; then
      # The project's EditorConfig names a dialect the script is not written in: that is
      # configuration for the user to settle, not a defect in the script.
      FINDINGS=$(trim_findings "${f}" "shfmt rejected the script under the dialect the project's .editorconfig sets:
${out}")
      return 2
    fi
    if is_parse_error "${f}" "${out}"; then
      FINDINGS=$(trim_findings "${f}" "${out}")
      return 4
    fi
    FINDINGS=$(trim_findings "${f}" "shfmt failed on the script without reporting a syntax error:
${out}")
    return 2
  fi
  out=$(cd "${f%/*}" && "${SHELLCHECK}" -x -f gcc -- "${f}" 2>&1)
  rc=$?
  FINDINGS=$(trim_findings "${f}" "${out}")
  ((rc > 1)) && return 2
  return "${rc}"
}

# ------------------------------------------------------------------- post ---

do_post() {
  [[ -n ${file} && -f ${file} ]] && is_shell "${file}" || exit 0
  [[ ${file} == *$'\n'* ]] && exit 0 # one path per line in the session list
  find_tools "${file%/*}" || missing_tools
  [[ -n ${STATE_DIR} ]] && printf '%s\n' "${file}" >>"${STATE_DIR}/${SESSION}.files"
  local r rc note
  r=$(rel "${file}")
  note=$(opts_note)
  correct "${file}"
  rc=$?
  case ${rc} in
  0)
    if ((CHANGED)); then
      jq -cn --arg m "${TAG} ✓ ${r}: formatted, ShellCheck clean${note}" \
        --arg c "${TAG}: shfmt rewrote ${r} after your edit; re-read it before editing it again." \
        '{systemMessage: $m, hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
    else
      say_user "${TAG} ✓ ${r}: clean${note}"
    fi
    ;;
  4)
    jq -cn --arg r "${TAG}: shfmt could not parse ${r} after your edit; fix the syntax. Its message:
${FINDINGS}" --arg m "${TAG}: ${r} does not parse; Claude is fixing it" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  1)
    jq -cn --arg r "${TAG}: ${r} still fails ShellCheck after formatting${note} (the hook may have rewritten it; re-read it first). Fix each finding in the script (read a code's explanation at https://www.shellcheck.net/wiki/SC<code>); a # shellcheck disable= directive or a configuration change is not a fix and needs the user's confirmation. Findings:
${FINDINGS}" --arg m "${TAG}: ${r} has findings left; Claude is fixing them" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  3)
    say_user "${TAG}: ${r} is a zsh script; ShellCheck does not support zsh, so it was not checked"
    ;;
  *)
    jq -cn --arg r "${TAG}: ${r} could not be checked (exit ${rc})${note}. This is a tool or configuration error, not a finding in the script; tell the user what it says and do not change the script to work around it:
${FINDINGS}" --arg m "${TAG}: ${r} could not be checked (exit ${rc}); a tool or configuration error" \
      '{decision: "block", reason: $r, systemMessage: $m}'
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------- stop ---

do_stop() {
  [[ -n ${STATE_DIR} ]] || exit 0
  local list="${STATE_DIR}/${SESSION}.files" blocks_file="${STATE_DIR}/${SESSION}.blocks"
  local last_file="${STATE_DIR}/${SESSION}.last"
  [[ -s ${list} ]] || exit 0
  local active blocks=0 f r rc report="" bad=0 checked=0 files note broken="" bnote="" last="" now
  active=$(field '.stop_hook_active')
  if [[ ${active} == true && -f ${blocks_file} ]]; then
    blocks=$(cat "${blocks_file}" 2>/dev/null)
    [[ -f ${last_file} ]] && last=$(cat "${last_file}" 2>/dev/null)
  fi
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
    r=$(rel "${f}")
    if ((rc == 1 || rc == 4)); then
      bad=$((bad + 1))
      report="${report}${FINDINGS}
"
    elif ((rc != 0)); then
      # A tool or configuration error is the user's to fix: reported, never a reason to
      # keep Claude working.
      broken="${broken}${r} (exit ${rc}):
${FINDINGS}
"
    fi
  done <<<"${files}"
  if ((${#broken} > MAX_REPORT)); then
    broken="${broken:0:MAX_REPORT}
... cut at ${MAX_REPORT} characters
"
  fi
  [[ -n ${broken} ]] && bnote="
${TAG}: ShellCheck could not check these scripts (a tool or configuration error, not a finding)${note}:
${broken}"
  if ((${#report} > MAX_REPORT)); then
    report="${report:0:MAX_REPORT}
... report cut at ${MAX_REPORT} characters; run \`shellcheck -x -f gcc\` on the scripts above for the rest
"
  fi
  if ((bad == 0)); then
    rm -f "${blocks_file}" "${last_file}"
    if [[ -n ${broken} ]]; then
      say_user "${TAG} ✗${bnote#*"${TAG}:"}"
    else
      rm -f "${list}"
      ((checked > 0)) && say_user "${TAG} ✓ ${checked} shell script(s) touched this session pass shfmt and ShellCheck${note}"
    fi
    exit 0
  fi
  # Stop asking when Claude made no change since the last attempt (it asked the user, or it
  # cannot fix what is left) or after MAX_BLOCKS attempts; then forget these scripts until
  # they are edited again, so the next turn is not pushed back into the same loop.
  now=$(printf '%s' "${report}" | cksum)
  if ((blocks >= MAX_BLOCKS)) || { ((blocks > 0)) && [[ ${now} == "${last}" ]]; }; then
    local why="after ${MAX_BLOCKS} attempts"
    ((blocks < MAX_BLOCKS)) && why="with no change since the last attempt"
    rm -f "${blocks_file}" "${last_file}" "${list}"
    say_user "${TAG} ✗ gave up ${why}: ${bad} shell script(s) still fail shfmt or ShellCheck${note}.
${report}${bnote}"
    exit 0
  fi
  blocks=$((blocks + 1))
  printf '%s\n' "${blocks}" >"${blocks_file}"
  printf '%s\n' "${now}" >"${last_file}"
  jq -cn --arg c "${TAG}: you cannot finish yet (attempt ${blocks} of ${MAX_BLOCKS}). These scripts you changed still fail after formatting${note}. Fix each finding in the script; a # shellcheck disable= directive or a configuration change is not a fix and needs the user's confirmation. If a finding needs the user's decision, ask them and end your turn: when nothing changes between two attempts, the hook stops asking.
${report}" --arg m "${TAG}: ${bad} shell script(s) still fail; Claude keeps working (${blocks}/${MAX_BLOCKS})${bnote}" \
    '{systemMessage: $m, hookSpecificOutput: {hookEventName: "Stop", additionalContext: $c}}'
  exit 0
}

case ${event} in
guard) do_guard ;;
post) do_post ;;
stop) do_stop ;;
*) exit 0 ;;
esac
