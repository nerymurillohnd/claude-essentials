#!/usr/bin/env bash
# ruff-quality hook handler. Bash 3.2 compatible. Installs nothing: it only runs
# a Ruff that is already installed, in the project or globally.
#
#   ruff-gate.sh guard  PreToolUse: asks the user before an edit adds a
#                       suppression comment or changes Ruff configuration.
#   ruff-gate.sh post   PostToolUse: on the edited .py/.pyw/.pyi file, applies
#                       safe fixes, formats, re-checks, and hands what is left
#                       to Claude.
#   ruff-gate.sh stop   Stop: re-fixes, re-formats and re-checks every file this
#                       session touched and keeps Claude working while the findings
#                       change, up to MAX_BLOCKS times; then it tells the user what
#                       still fails and forgets those files until they are edited again.
#
# Ruff finds its own configuration (nearest ruff.toml, .ruff.toml or
# pyproject.toml [tool.ruff], then the user-level file, then its defaults).
# Without Ruff or jq the hook says so once per session and never blocks.
# CLAUDE_PLUGIN_OPTION_ENABLED false, 0, no or off (the plugin's `enabled` option) turns it off.
set -u

readonly TAG="ruff-quality"
readonly MAX_BLOCKS=7
readonly MAX_LINES=60
readonly MAX_REPORT=8000 # Claude Code keeps at most 10,000 characters of additionalContext
readonly SUPP_RE='#[[:space:]]*(noqa|flake8:[[:space:]]*noqa|ruff:[[:space:]]*(noqa|ignore|disable|file-ignore)|fmt:[[:space:]]*(off|skip)|isort:[[:space:]]*(skip|off)|yapf:[[:space:]]*disable)'
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
    dir="${dir%/}/ruff-quality-$(id -u 2>/dev/null || echo 0)"
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
ruff_section() { # the [tool.ruff*] tables of a pyproject.toml text, and ruff.* keys under [tool]
  awk '/^[[:space:]]*\[/ { on = ($0 ~ /^[[:space:]]*\[+tool\.ruff(\]|\.)/); intool = ($0 ~ /^[[:space:]]*\[tool\][[:space:]]*$/) }
    on || (intool && $0 ~ /^[[:space:]]*ruff([[:space:]]*=|\.)/)' <<<"$1"
}
# A command with its harmless redirects (2>&1, >/dev/null) removed, so they are not taken for
# writes.
write_view() { sed -E 's/[0-9]*>&[0-9]+//g; s/[0-9]*>+[[:space:]]*\/dev\/null//g' <<<"$1"; }
rel() { case $1 in "${cwd%/}"/*) printf '%s' "${1#"${cwd%/}"/}" ;; *) printf '%s' "$1" ;; esac }

# The suppression markers an edit adds, one per line, each from the marker to the end of
# its line, lower-cased. Write compares the new content with the file on disk; Edit compares
# each replacement with its own old_string. A marker whose text changes (a new code, a bare
# `# noqa`, a line-level marker made file-level) counts as added, and removing a marker in one
# replacement never offsets adding one in another.
added_markers() {
  local disk=/dev/null out
  # A file the hook cannot read is compared with nothing, so any marker in the edit asks.
  [[ ${tool} == Write && -f ${file} && -r ${file} ]] && disk=${file}
  if out=$(jq -r --arg re "${SUPP_RE}" --arg tool "${tool}" --rawfile disk "${disk}" '
    def markers: split("\n") | map(select(test($re; "i")) | (match($re; "i").offset) as $o
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
  grep -qiE "${SUPP_RE}" <<<"${payload}" && printf '%s' "a suppression marker (the hook could not compare it with the file)"
  return 0
}

# ------------------------------------------------------------------ guard ---

do_guard() {
  if [[ ${tool} == Bash ]]; then
    local cmd writes
    cmd=$(field '.tool_input.command')
    [[ ${cmd} == *--add-noqa* || ${cmd} == *--add-ignore* ]] &&
      ask "Claude wants to run ruff --add-noqa or --add-ignore, which write suppression comments. Allow it only if you want those findings silenced instead of fixed."
    writes=$(write_view "${cmd}")
    if [[ ${writes} =~ ${WRITE_RE} ]]; then
      grep -qiE "${SUPP_RE}" <<<"${writes}" &&
        ask "Claude wants to run a command that may write a Ruff suppression comment. Allow it only if you want that finding silenced instead of fixed."
      [[ ${writes} =~ (ruff\.toml|pyproject\.toml) ]] &&
        ask "Claude wants to run a command that may write to Ruff configuration (ruff.toml or pyproject.toml). Allow it only if you want this configuration change."
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
    elif [[ ${new}${old} == *tool.ruff* ]] || { [[ -n ${old} && -n ${section} ]] && [[ ${section} == *"${old}"* ]]; } ||
      grep -qE '^[[:space:]]*ruff([[:space:]]*=|\.)' <<<"${new}"; then
      ask "Claude wants to change the [tool.ruff] tables of ${where}. Allow it only if you want this Ruff configuration change."
    fi
    ;;
  *)
    is_python "${file}" || exit 0
    local added
    added=$(added_markers) || added=""
    added=$(awk 'NR > 1 { printf "; " } { printf "%s", $0 }' <<<"${added}")
    [[ -n ${added} ]] &&
      ask "Claude wants to add or widen a suppression in ${where}: ${added}. Allow it only if you want that finding silenced instead of fixed."
    ;;
  esac
  exit 0
}

# ------------------------------------------------------------------- ruff ---

RUFF=""
find_ruff() { # the project's own install between $1 and the project root, then the global one
  local d=$1 root c
  root=${CLAUDE_PROJECT_DIR:-${cwd}}
  root=${root%/}
  # Only inside the project, and only an executable this user owns: a .venv planted in a
  # shared parent directory (/tmp) is never run.
  case "${d}/" in
  "${root}"/*)
    while [[ -n ${d} ]]; do
      for c in "${d}/.venv/bin/ruff" "${d}/venv/bin/ruff" "${d}/.venv/Scripts/ruff.exe"; do
        [[ -x ${c} && -O ${c} ]] && RUFF=${c} && return 0
      done
      [[ ${d} == "${root}" ]] && break
      d=${d%/*}
    done
    ;;
  *) ;;
  esac
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
  local f=$1 before after out rc target
  target=$(rel "${f}") # from the project directory, so reports name the file as Claude does
  before=$(cksum <"${f}" 2>/dev/null)
  (cd "${cwd}" && "${RUFF}" check --fix --no-unsafe-fixes --unfixable F401 --force-exclude --no-cache --quiet -- "${target}") >/dev/null 2>&1
  (cd "${cwd}" && "${RUFF}" format --force-exclude --no-cache --quiet -- "${target}") >/dev/null 2>&1
  out=$(cd "${cwd}" && "${RUFF}" check --no-fix --force-exclude --no-cache --output-format concise -- "${target}" 2>&1)
  rc=$?
  after=$(cksum <"${f}" 2>/dev/null)
  [[ ${before} == "${after}" ]] || CHANGED=1
  FINDINGS=$(trim_findings "${f}" "${out}")
  return "${rc}"
}

# The first MAX_LINES lines of a Ruff report, saying so when there were more.
trim_findings() { # trim_findings FILE TEXT
  local short
  short=$(rel "$1")
  awk -v max="${MAX_LINES}" -v file="${short}" '/^Found [0-9]+ error/ { next }
    NF { total++; if (total <= max) print }
    END { if (total > max) printf "... first %d of %d lines shown; run `ruff check %s` for the rest\n", max, total, file }' <<<"$2"
}

# Whether Ruff would check this file, or the project excludes it.
is_included() {
  local listed rc target
  target=$(rel "$1")
  listed=$(cd "${cwd}" && "${RUFF}" check --force-exclude --no-cache --show-files -- "${target}" 2>/dev/null)
  rc=$?
  ((rc != 0)) || [[ -n ${listed} ]] # a configuration error is reported by the check itself
}

missing_ruff() {
  first_time noruff &&
    tell_both PostToolUse "${TAG}: Ruff is not installed in this project or on PATH, so Python files are not being checked. Install it (uv add --dev ruff, uv tool install ruff, pipx install ruff or brew install ruff); Claude does not install it unasked."
  exit 0
}

# ------------------------------------------------------------------- post ---

do_post() {
  [[ -n ${file} && -f ${file} ]] && is_python "${file}" || exit 0
  [[ ${file} == *$'\n'* ]] && exit 0 # one path per line in the session list
  find_ruff "${file%/*}" || missing_ruff
  local r rc
  r=$(rel "${file}")
  if ! is_included "${file}"; then
    say_user "${TAG}: ${r} is excluded by the project's Ruff configuration, so it was not checked"
    exit 0
  fi
  [[ -n ${STATE_DIR} ]] && printf '%s\n' "${file}" >>"${STATE_DIR}/${SESSION}.files"
  correct "${file}"
  rc=$?
  case ${rc} in
  0)
    if ((CHANGED)); then
      jq -cn --arg m "${TAG} ✓ ${r}: fixed and formatted, no findings left" \
        --arg c "${TAG}: Ruff rewrote ${r} after your edit (safe fixes and formatting); re-read it before editing it again." \
        '{systemMessage: $m, hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
    else
      say_user "${TAG} ✓ ${r}: clean"
    fi
    ;;
  1)
    jq -cn --arg r "${TAG}: ${r} still fails Ruff after the safe fixes and formatting (the hook may have rewritten it; re-read it first). Fix each finding in the code; a suppression comment or a configuration change is not a fix and needs the user's confirmation. Findings:
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
  local last_file="${STATE_DIR}/${SESSION}.last"
  [[ -s ${list} ]] || exit 0
  local active blocks=0 f r rc report="" bad=0 checked=0 files broken="" note="" last="" now
  active=$(field '.stop_hook_active')
  if [[ ${active} == true && -f ${blocks_file} ]]; then
    blocks=$(cat "${blocks_file}" 2>/dev/null)
    [[ -f ${last_file} ]] && last=$(cat "${last_file}" 2>/dev/null)
  fi
  [[ ${blocks} =~ ^[0-9]+$ ]] || blocks=0
  files=$(sort -u "${list}")
  while IFS= read -r f; do
    [[ -f ${f} ]] || continue
    find_ruff "${f%/*}" || continue
    checked=$((checked + 1))
    r=$(rel "${f}")
    correct "${f}"
    rc=$?
    if ((rc == 1)); then
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
  [[ -n ${broken} ]] && note="
${TAG}: Ruff could not check these files (a tool or configuration error, not a finding):
${broken}"
  if ((${#report} > MAX_REPORT)); then
    report="${report:0:MAX_REPORT}
... report cut at ${MAX_REPORT} characters; run \`ruff check\` on the files above for the rest
"
  fi
  if ((bad == 0)); then
    rm -f "${blocks_file}" "${last_file}"
    if [[ -n ${broken} ]]; then
      say_user "${TAG} ✗${note#*"${TAG}:"}"
    else
      rm -f "${list}"
      ((checked > 0)) && say_user "${TAG} ✓ ${checked} Python file(s) touched this session pass Ruff"
    fi
    exit 0
  fi
  # Stop asking when Claude made no change since the last attempt (it asked the user, or it
  # cannot fix what is left) or after MAX_BLOCKS attempts; then forget these files until
  # they are edited again, so the next turn is not pushed back into the same loop.
  now=$(printf '%s' "${report}" | cksum)
  if ((blocks >= MAX_BLOCKS)) || { ((blocks > 0)) && [[ ${now} == "${last}" ]]; }; then
    local why="after ${MAX_BLOCKS} attempts"
    ((blocks < MAX_BLOCKS)) && why="with no change since the last attempt"
    rm -f "${blocks_file}" "${last_file}" "${list}"
    say_user "${TAG} ✗ gave up ${why}: ${bad} Python file(s) still fail Ruff.
${report}${note}"
    exit 0
  fi
  blocks=$((blocks + 1))
  printf '%s\n' "${blocks}" >"${blocks_file}"
  printf '%s\n' "${now}" >"${last_file}"
  jq -cn --arg c "${TAG}: you cannot finish yet (attempt ${blocks} of ${MAX_BLOCKS}). These files you changed still fail Ruff after the safe fixes and formatting. Fix each finding in the code; a suppression comment or a configuration change is not a fix and needs the user's confirmation. If a finding needs the user's decision, ask them and end your turn: when nothing changes between two attempts, the hook stops asking.
${report}" --arg m "${TAG}: ${bad} Python file(s) still fail Ruff; Claude keeps working (${blocks}/${MAX_BLOCKS})${note}" \
    '{systemMessage: $m, hookSpecificOutput: {hookEventName: "Stop", additionalContext: $c}}'
  exit 0
}

case ${event} in
guard) do_guard ;;
post) do_post ;;
stop) do_stop ;;
*) exit 0 ;;
esac
