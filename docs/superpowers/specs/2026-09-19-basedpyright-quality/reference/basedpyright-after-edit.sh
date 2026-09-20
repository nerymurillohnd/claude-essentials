#!/usr/bin/env bash
# basedpyright-after-edit: reference Claude Code hook handler (design artifact).
# basedpyright-quality-reference: 2026-09-19 (basedpyright 1.40.1, Claude Code 2.1.278)
#
# Usage (from settings.json hook commands, never by hand):
#   basedpyright-after-edit.sh post    PostToolUse  (Write|Edit|NotebookEdit|Bash)
#   basedpyright-after-edit.sh guard   PreToolUse   (Write|Edit|NotebookEdit|Bash)
#   basedpyright-after-edit.sh stop            Stop and SubagentStop
#   basedpyright-after-edit.sh task-completed  TaskCompleted
#   basedpyright-after-edit.sh prompt          UserPromptSubmit
#   basedpyright-after-edit.sh session-start   SessionStart (matcher: compact|resume)
#
# post   Type-checks every Python file the tool call wrote, with the basedpyright
#        CLI (deterministic and awaited; it never depends on the language server
#        being warm). Clean -> exit 0. Diagnostics -> exit 2: Claude sees the
#        report next to the tool result, the file is marked "must fix", and the
#        report tells Claude how to investigate each finding with the LSP tool.
# guard  Focus lock. While a file is marked "must fix", edits are allowed only to
#        that file and to other Python files of the same project (a fix can live
#        in the module that defines a type). Any other edit is denied until the
#        marked files are clean. After BPAE_MAX_DENIALS consecutive denials the
#        edit is allowed with a warning, so a legitimate cross-cutting fix can't
#        deadlock the session.
# stop   Re-checks every Python file edited this session, then (default) runs a
#        project-scope check of each touched project, because an edit can break
#        a file that imports it. Anything left -> exit 2 and Claude keeps
#        working, up to BPAE_MAX_BLOCKS consecutive blocks. Registered for
#        SubagentStop too, so a subagent can't finish with type errors either.
#        Project scope blocks on every error basedpyright reports, as CI does,
#        so install it only in a project that passes today (or has a baseline).
# task-completed  Refuses to mark a task complete while a file is marked
#        "must fix".
# prompt  A new user turn resets the Stop and focus-lock counters.
# session-start  After compaction or resume, re-injects the files still marked
#        "must fix", so the obligation survives the summary.
#
# Fail-closed: a missing jq or basedpyright, an unreadable payload, a broken
# configuration (exit 3), a checker crash (exit 2), bad arguments (exit 4), a
# kill by signal, or a timeout exits 2 with the reason. Never touches the
# network. Needs bash >= 3.2, jq >= 1.6, basedpyright >= 1.37.0.
#
# Environment knobs:
#   BASEDPYRIGHT_BIN    absolute path to the basedpyright CLI (skips discovery)
#   BPAE_TIMEOUT        seconds per basedpyright run (default 100)
#   BPAE_MAX_BLOCKS     Stop blocks before the turn may end (default 5, 1-7)
#   BPAE_MAX_DENIALS    focus-lock denials before an edit is let through (default 3)
#   BPAE_STOP_SCOPE     auto (default) | files | project
#   BPAE_CONFIG_MODE    own (default) | profile | pinned
#                         own      the project's config, else basedpyright defaults
#                         profile  the project's config, else the file BPAE_CONFIG
#                         pinned   always BPAE_CONFIG, the project's config ignored
#   BPAE_CONFIG         pyrightconfig.json used by profile/pinned (default: the
#                       profile embedded below, materialized idempotently in the
#                       state directory, so this one file is self-contained)
#   BPAE_BASH_SCAN      1 (default) | 0: find .py files a Bash command wrote when
#                       Claude Code didn't report them (bashEditDiff)
#
# Universal: it runs for any edited Python file in any directory, Python project
# or not, inside a repository or not. basedpyright (CLI and language server ship
# together) must be installed in the project's .venv or globally. Configuration:
# the nearest pyrightconfig.json, or pyproject.toml with [tool.basedpyright] /
# [tool.pyright], walking up from the file ("configured"). Without one,
# basedpyright's own defaults apply (typeCheckingMode "recommended", every rule)
# and the file is checked on its own ("unconfigured").
#
# Stop scope "auto": touched files must be clean; in a configured project, the
# project is also re-checked and only diagnostics that were not there when the
# session first touched it block (an edit can break an importer). A project's
# pre-existing debt elsewhere never blocks. "project" = every diagnostic in the
# project blocks (CI parity; install only where the project passes today).
#
# Unconfigured files: reportMissingImports, reportMissingModuleSource, and
# reportMissingTypeStubs describe the Python environment (packages not installed
# where basedpyright looks), not the code, so they are reported but don't block.
# Blocking on them would leave only installing packages or suppressing, and the
# policy allows neither without the user.

set -uo pipefail

readonly TAG="basedpyright-after-edit"
readonly MAX_ERRORS=25
event=${1:-}

die() {
  # Exit 2 on UserPromptSubmit blocks the prompt and erases it, so a broken gate
  # would lock the user out of the session; SessionStart can't block at all.
  # Those two events report the failure to the user instead and let the prompt
  # through (the edit-time events still fail closed).
  case ${event} in
  prompt | session-start)
    if command -v jq >/dev/null 2>&1; then
      jq -cn --arg m "${TAG}: $1 (the type-check gate is not working; edits will fail closed until this is fixed)" '{systemMessage: $m}'
    else
      printf '%s: %s\n' "${TAG}" "$1" >&2
    fi
    exit 0
    ;;
  *) ;;
  esac
  printf '%s: %s\n' "${TAG}" "$1" >&2
  printf '%s: the type check could not run, so this change is NOT verified. Fix the cause above or ask the user; do not work around the hook.\n' "${TAG}" >&2
  exit 2
}

# On Windows, Claude Code sends native paths (C:\\x\\y); Git Bash needs /c/x/y.
to_posix() { # <path>
  case $1 in
  [A-Za-z]:\\* | [A-Za-z]:/*)
    if command -v cygpath >/dev/null 2>&1; then
      cygpath -u "$1"
    else
      local drive=${1%%:*} rest=${1#?:}
      rest=${rest//\\//}
      drive=$(tr '[:upper:]' '[:lower:]' <<<"${drive}") || return 1
      printf '/%s%s\n' "${drive}" "${rest}"
    fi
    ;;
  *) printf '%s\n' "$1" ;;
  esac
}

case ${event} in post | guard | stop | task-completed | prompt | session-start) ;; *) die "unknown event '${event}'" ;; esac
command -v jq >/dev/null 2>&1 || die "jq is required and was not found on PATH"

timeout_s=${BPAE_TIMEOUT:-100}
max_blocks=${BPAE_MAX_BLOCKS:-5}
max_denials=${BPAE_MAX_DENIALS:-3}
stop_scope=${BPAE_STOP_SCOPE:-auto}
config_mode=${BPAE_CONFIG_MODE:-own}
config_file=${BPAE_CONFIG:-}
bash_scan=${BPAE_BASH_SCAN:-1}
readonly ENV_RULES='reportMissingImports|reportMissingModuleSource|reportMissingTypeStubs'
# The embedded profile: basedpyright's own recommended policy, stated explicitly,
# with "package not installed" findings downgraded to information (reported,
# never failing), since installing packages is the user's decision.
EMBEDDED_PROFILE=""
IFS= read -r -d '' EMBEDDED_PROFILE <<'PROFILE' || true
{
  "typeCheckingMode": "recommended",
  "pythonPlatform": "All",
  "failOnWarnings": true,
  "enableTypeIgnoreComments": false,
  "reportUnnecessaryTypeIgnoreComment": "error",
  "reportIgnoreCommentWithoutRule": "error",
  "reportMissingModuleSource": "information",
  "reportMissingTypeStubs": "information"
}
PROFILE
readonly EMBEDDED_PROFILE

case ${config_mode} in
own) ;;
profile | pinned) [[ -z ${config_file} || -f ${config_file} ]] || die "BPAE_CONFIG_MODE=${config_mode} needs a readable config file; not found: ${config_file}" ;;
*) die "BPAE_CONFIG_MODE must be own, profile, or pinned (got '${config_mode}')" ;;
esac

payload=$(cat) || die "cannot read the hook payload"
[[ -n ${payload} ]] || die "empty hook payload"
parsed=$(jq -r '
  def pyfile: test("\\.(py|pyi|pyw|ipynb)$"; "i");
  (.session_id // "nosession"), (.cwd // ""), (.stop_hook_active // false | tostring), (.tool_name // ""),
  ([ .tool_input.file_path?, .tool_input.notebook_path?, .tool_response.filePath?,
     (.tool_response.bashEditDiff?.files? // [] | .[]?.filePath?) ]
   | map(select(type == "string" and pyfile)) | unique | .[])
' <<<"${payload}" 2>/dev/null) || die "the hook payload is not valid JSON"

session=""
cwd=""
stop_active=""
tool=""
paths=()
n=0
while IFS= read -r line; do
  case ${n} in
  0) session=${line} ;;
  1) cwd=$(to_posix "${line}") ;;
  2) stop_active=${line} ;;
  3) tool=${line} ;;
  *) [[ -n ${line} ]] && paths+=("$(to_posix "${line}")") ;;
  esac
  n=$((n + 1))
done <<<"${parsed}"
session=$(printf '%s' "${session}" | tr -c 'A-Za-z0-9._-' '_')

# --- state -------------------------------------------------------------------
state_dir="${TMPDIR:-/tmp}"
state_dir="${state_dir%/}/basedpyright-after-edit-$(id -u)"
if [[ ! -d ${state_dir} ]]; then
  mkdir -p "${state_dir}" 2>/dev/null || die "cannot create ${state_dir}"
  chmod 700 "${state_dir}" 2>/dev/null || true
fi
case $(uname -s 2>/dev/null) in
MINGW* | MSYS* | CYGWIN*) ;; # ownership bits are emulated on Windows
*) [[ -O ${state_dir} && ! -L ${state_dir} ]] || die "${state_dir} is not owned by this user" ;;
esac
touched="${state_dir}/${session}.touched" # every Python file edited this session
dirty="${state_dir}/${session}.dirty"     # files that must be fixed before other work
denials="${state_dir}/${session}.denials"
blocks="${state_dir}/${session}.blocks"
touch "${touched}" "${dirty}" 2>/dev/null || die "cannot write session state in ${state_dir}"

# Idempotent: rewritten only when the embedded profile changed.
if [[ ${config_mode} != own && -z ${config_file} ]]; then
  config_file="${state_dir}/basedpyright-quality.pyrightconfig.json"
  if [[ $(cat "${config_file}" 2>/dev/null || true) != "${EMBEDDED_PROFILE%$'\n'}" ]]; then
    if ! printf '%s\n' "${EMBEDDED_PROFILE%$'\n'}" >"${config_file}.tmp.$$" || ! mv -f "${config_file}.tmp.$$" "${config_file}"; then
      die "cannot write the embedded profile to ${config_file}"
    fi
  fi
fi

set_add() { grep -qxF -- "$2" "$1" 2>/dev/null || printf '%s\n' "$2" >>"$1"; }
set_del() {
  local tmp="$1.tmp.$$"
  grep -vxF -- "$2" "$1" >"${tmp}" 2>/dev/null
  mv -f "${tmp}" "$1"
}

# --- paths, project root, binary -------------------------------------------

canonical() { # physical path: /var vs /private/var must not defeat `exclude`
  local d
  d=$(cd "$(dirname "$1")" 2>/dev/null && pwd -P) || return 1
  printf '%s/%s\n' "${d}" "$(basename "$1")"
}

project_root() { # nearest basedpyright config, else git root, else the file's dir
  local d=$1 start=$1
  while [[ -n ${d} && ${d} != / ]]; do
    if [[ -f ${d}/pyrightconfig.json ]] || grep -Eq '^\[tool\.(basedpyright|pyright)\]' "${d}/pyproject.toml" 2>/dev/null; then
      printf '%s\n' "${d}"
      return
    fi
    d=$(dirname "${d}")
  done
  d=${start}
  while [[ -n ${d} && ${d} != / ]]; do
    [[ -e ${d}/.git ]] && {
      printf '%s\n' "${d}"
      return
    }
    d=$(dirname "${d}")
  done
  printf '%s\n' "${start}"
}

# Which policy applies to a root: project (its own config), profile or pinned
# (BPAE_CONFIG), or defaults (basedpyright's built-in defaults).
root_kind() { # <root>
  if [[ ${config_mode} == pinned ]]; then
    echo pinned
  elif is_configured "$1"; then
    echo project
  elif [[ ${config_mode} == profile ]]; then
    echo profile
  else
    echo defaults
  fi
}

# The analyzed interpreter for roots without a project config: basedpyright only
# auto-detects ./.venv at its project root, and with -p pointing at a config
# elsewhere it falls back to `python` on PATH [observed], so pass it explicitly.
resolve_python() { # <dir>
  local d=$1 c
  while [[ -n ${d} && ${d} != / ]]; do
    for c in "${d}/.venv/bin/python" "${d}/venv/bin/python" "${d}/.venv/Scripts/python.exe" "${d}/venv/Scripts/python.exe"; do
      [[ -x ${c} ]] && {
        printf '%s\n' "${c}"
        return 0
      }
    done
    d=$(dirname "${d}")
  done
  return 1
}

is_configured() { # <root>
  [[ -f $1/pyrightconfig.json ]] || grep -Eq '^\[tool\.(basedpyright|pyright)\]' "$1/pyproject.toml" 2>/dev/null
}

# Number of diagnostics that block, for RUN_JSON. Configured: the CLI's own
# verdict (exit 1 honours failOnWarnings exactly as CI does). Unconfigured:
# errors and warnings except the environment rules.
blocking() { # <root>
  local kind
  kind=$(root_kind "$1")
  if [[ ${kind} != defaults ]]; then
    ((RUN_STATUS == 1)) && echo 1 || echo 0
  else
    jq --arg env "^(${ENV_RULES})$" '[.generalDiagnostics[] | select((.severity == "error" or .severity == "warning") and ((.rule // "") | test($env) | not))] | length' <<<"${RUN_JSON}"
  fi
}

# Line-insensitive keys (file, rule, first message line) of the errors and
# warnings in RUN_JSON, one per line, sorted: a multiset that survives edits
# shifting line numbers.
diag_keys() {
  jq -r '.generalDiagnostics[] | select(.severity == "error" or .severity == "warning") | "\(.file)\t\(.rule // "syntax")\t\(.message | split("\n") | .[0])"' <<<"${RUN_JSON}" | LC_ALL=C sort
}

snap_path() { # <root>
  local h
  h=$(printf '%s' "$1" | cksum | tr -c '0-9' '_')
  printf '%s/%s.snap.%s\n' "${state_dir}" "${session}" "${h}"
}

resolve_bin() { # project venv first (the version the project pins); never `uv run`
  local d=$1 c
  if [[ -n ${BASEDPYRIGHT_BIN:-} ]]; then
    [[ -x ${BASEDPYRIGHT_BIN} ]] && {
      printf '%s\n' "${BASEDPYRIGHT_BIN}"
      return 0
    }
    return 1
  fi
  while [[ -n ${d} && ${d} != / ]]; do
    for c in "${d}/.venv/bin/basedpyright" "${d}/venv/bin/basedpyright" "${d}/.venv/Scripts/basedpyright.exe" "${d}/venv/Scripts/basedpyright.exe"; do
      [[ -x ${c} ]] && {
        printf '%s\n' "${c}"
        return 0
      }
    done
    d=$(dirname "${d}")
  done
  for c in "$(command -v basedpyright 2>/dev/null)" "${HOME}/.local/bin/basedpyright" "${HOME}/.local/bin/basedpyright.exe" \
    /opt/homebrew/bin/basedpyright /usr/local/bin/basedpyright /home/linuxbrew/.linuxbrew/bin/basedpyright; do
    [[ -n ${c} && -x ${c} ]] && {
      printf '%s\n' "${c}"
      return 0
    }
  done
  return 1
}

# --- one basedpyright run ---------------------------------------------------
# Sets RUN_STATUS, RUN_JSON, RUN_ERR. Globals, not $(...): a failure must be able
# to reach the caller's exit path.
RUN_STATUS=0
RUN_JSON=""
RUN_ERR=""
run_bp() { # <root> [file...]
  local root=$1 bp out err pid waited=0 kind py
  shift
  kind=$(root_kind "${root}")
  local args=(--outputjson --baselinemode discard)
  case ${kind} in
  project | defaults) args+=(-p "${root}") ;;
  *)
    # A config outside the project has no include semantics for it: files only.
    (($# > 0)) || die "internal: a ${kind} run needs file arguments"
    args+=(-p "${config_file}")
    ;;
  esac
  if [[ ${kind} != project ]] && py=$(resolve_python "${root}"); then
    args+=(--pythonpath "${py}")
  fi
  bp=$(resolve_bin "${root}") || die "basedpyright not found (project .venv, PATH, ~/.local/bin, Homebrew). Install it: uv add --dev basedpyright"
  out=$(mktemp "${state_dir}/out.XXXXXX") || die "mktemp failed"
  err=$(mktemp "${state_dir}/err.XXXXXX") || die "mktemp failed"
  # CI detection (is-ci) would switch on annotations and baseline `lock`; discard
  # never writes the committed baseline. No `--`: basedpyright exits 4 on it.
  (
    cd "${root}" || exit 2
    exec env -u CI -u CONTINUOUS_INTEGRATION -u BUILD_NUMBER -u RUN_ID -u GITHUB_ACTIONS \
      -u GITLAB_CI -u BUILDKITE -u CIRCLECI -u TRAVIS -u JENKINS_URL -u TF_BUILD -u TEAMCITY_VERSION \
      NO_COLOR=1 "${bp}" "${args[@]}" "$@"
  ) >"${out}" 2>"${err}" &
  pid=$!
  while kill -0 "${pid}" 2>/dev/null; do
    if ((waited >= timeout_s * 10)); then
      kill -9 "${pid}" 2>/dev/null
      wait "${pid}" 2>/dev/null
      rm -f "${out}" "${err}"
      die "basedpyright did not finish within ${timeout_s}s in ${root} (BPAE_TIMEOUT)"
    fi
    sleep 0.1
    waited=$((waited + 1))
  done
  wait "${pid}"
  RUN_STATUS=$?
  # stdout may carry a leading blank line or a baseline notice before the JSON.
  RUN_JSON=$(sed -n '/^{/,$p' "${out}")
  RUN_ERR=$(head -c 4000 "${err}")
  rm -f "${out}" "${err}"
  # basedpyright 1.40.1 exits 3 on a broken or invalid configuration in text
  # mode, but exits 0 with --outputjson (the error only reaches stderr), after
  # silently falling back to defaults. Restore the real verdict from stderr.
  if ((RUN_STATUS <= 1)) && grep -Eq 'could not be parsed|Config contains unrecognized setting|cannot have both|baseline file cannot be updated' <<<"${RUN_ERR}"; then
    RUN_STATUS=3
  fi
  if ((RUN_STATUS >= 128)); then
    die "basedpyright was killed by signal $((RUN_STATUS - 128)) in ${root}. On Linux/WSL this is usually Claude Code's tool memory cap (CLAUDE_CODE_TOOL_MEMORY_LIMIT), which the kernel enforces without saying so. Ask the user."
  fi
  case ${RUN_STATUS} in
  0 | 1) jq -e '.summary and (.generalDiagnostics | type == "array")' >/dev/null 2>&1 <<<"${RUN_JSON}" ||
    die "basedpyright exited ${RUN_STATUS} but its JSON could not be read. stderr: ${RUN_ERR}" ;;
  2) die "basedpyright crashed (exit 2, fatal error) in ${root}: ${RUN_ERR}" ;;
  3) die "basedpyright could not use the configuration in ${root} (exit 3: unreadable config, an unrecognized setting, or both [tool.pyright] and [tool.basedpyright] in one pyproject.toml). Configuration is the user's decision: report it and stop. ${RUN_ERR}" ;;
  4) die "basedpyright rejected its arguments (exit 4); this is a bug in the hook. ${RUN_ERR}" ;;
  *) die "basedpyright exited ${RUN_STATUS} in ${root}. ${RUN_ERR}" ;;
  esac
}

# Renders RUN_JSON for Claude: errors listed, warnings grouped, syntax first.
render() { # <root>
  jq -r --arg root "$1/" --argjson cap "${MAX_ERRORS}" '
    def rel: sub("^" + ($root | gsub("[.^$*+?()\\[\\]{}|\\\\]"; "\\\\\(.)")); "");
    def pos: "\(.range.start.line + 1):\(.range.start.character + 1)";
    def first_line: .message | split("\n") | .[0];
    [.generalDiagnostics[] | select(.severity == "error" or .severity == "warning")] as $all
    | ($all | map(select(.rule == null)) | map(.file) | unique) as $syntax_files
    | [$all[] | select((.rule == null) or ((.file as $f | $syntax_files | index($f)) | not))] as $shown
    | [$shown[] | select(.severity == "error")] as $errs
    | [$shown[] | select(.severity == "warning")] as $warns
    | "\($errs | length) error(s), \($warns | length) warning(s)",
      ( if ($syntax_files | length) > 0 then "  (files that do not parse show only their syntax errors)" else empty end ),
      ( $errs[:$cap][] | "  \(.file | rel):\(pos)  error  \(.rule // "syntax")  \(first_line)" ),
      ( if ($errs | length) > $cap then "  … \(($errs | length) - $cap) more error(s)" else empty end ),
      ( if ($warns | length) > 0 then
          "  warnings by rule:",
          ( $warns | group_by(.rule) | map({r: .[0].rule, n: length, at: "\(.[0].file | rel):\(.[0] | pos)"})
            | sort_by(-.n)[] | "    \(.n)× \(.r)  (first at \(.at))" )
        else empty end )
  ' <<<"${RUN_JSON}"
}

LSP_HOWTO=""
IFS= read -r -d '' LSP_HOWTO <<'HOWTO' || true
Project type-checking policy (basedpyright gate installed by the user):
  - Positions above are 1-based line:column, the same convention the LSP tool uses. At each one, the LSP tool's `hover` shows the inferred type, `goToDefinition` locates the declaration of the type or symbol named in the message, and `findReferences` / `incomingCalls` list the callers affected by a signature change.
  - A language server that is still indexing can return an error or an empty result; up to 3 retries usually get an answer. When it still fails, Read and Grep give the same facts. This report, produced by the basedpyright CLI, is the verdict; LSP diagnostics are advisory.
  - The policy accepts fixes in code only. `# pyright: ignore`, `# type: ignore`, `cast(Any, ...)`, new `Any` annotations, and configuration or baseline changes are not accepted as fixes; a rule that looks wrong for the project is a question for the user.
  - The check re-runs on every edit of the file. Until it is clean, edits outside this project are denied.
HOWTO
readonly LSP_HOWTO

# Claude Code caps hook text at 10,000 characters and moves the rest to a file
# Claude isn't told to read; keep the report well inside the cap.
budget() { # <text>
  if ((${#1} > 7000)); then
    printf '%s\n  … report truncated at 7000 characters; the full list: basedpyright --outputjson from the project root\n' "${1:0:7000}"
  else
    printf '%s' "$1"
  fi
}

# --- events ------------------------------------------------------------------
case ${event} in
post)
  if ((${#paths[@]} == 0)) && [[ ${tool} == Bash && ${bash_scan} == 1 && -e ${state_dir}/${session}.bashmark && -d ${cwd} ]]; then
    scan=$(find "${cwd}" \( -name .git -o -name .venv -o -name venv -o -name node_modules -o -name __pycache__ -o -name .tox -o -name .mypy_cache -o -name site-packages \) -prune -o \
      -type f \( -name '*.py' -o -name '*.pyi' -o -name '*.pyw' \) -newer "${state_dir}/${session}.bashmark" -print 2>/dev/null) || scan=""
    n=0
    while IFS= read -r found; do
      [[ -n ${found} ]] || continue
      paths+=("${found}")
      n=$((n + 1))
      ((n < 50)) || break
    done <<<"${scan}"
  fi
  ((${#paths[@]} > 0)) || exit 0
  report=""
  notes="" # Claude Code accepts one JSON object on stdout; collect, print once
  failed=0
  for p in "${paths[@]}"; do
    [[ ${p} == /* ]] || p="${cwd}/${p}"
    [[ -f ${p} ]] || continue
    f=$(canonical "${p}") || continue
    root=$(project_root "$(dirname "${f}")")
    set_add "${touched}" "${f}"
    run_bp "${root}" "${f}"
    analyzed=$(jq -r '.summary.filesAnalyzed' <<<"${RUN_JSON}")
    if [[ ${analyzed} == 0 ]]; then
      set_del "${dirty}" "${f}"
      notes+="${TAG}: ${f#"${root}/"} is excluded by the project's configuration; not type-checked. "
      continue
    fi
    nblock=$(blocking "${root}")
    if ((nblock > 0)); then
      failed=1
      set_add "${dirty}" "${f}"
      case $(root_kind "${root}") in
      project) where="project ${root}" ;;
      profile) where="no project configuration; profile ${config_file}" ;;
      pinned) where="pinned configuration ${config_file}" ;;
      *) where="no basedpyright configuration found; basedpyright defaults; environment rules (${ENV_RULES//|/, }) reported but not blocking" ;;
      esac
      report+="basedpyright: ${f#"${root}/"} (${where})"$'\n'"$(render "${root}")"$'\n'
    else
      set_del "${dirty}" "${f}"
      if ((RUN_STATUS == 1)); then
        notes+="${TAG}: ${f#"${root}/"} passes; only environment findings remain (packages not installed where basedpyright looks). "
      fi
    fi
  done
  if ((failed)); then
    : >"${denials}"
    report=$(budget "${report}")
    printf '%s\n%s\n' "${report}" "${LSP_HOWTO}" >&2
    jq -cn --arg m "${notes}${TAG} ✗ type errors in the file Claude just edited; Claude must fix them before other work" '{systemMessage: $m}'
    exit 2
  fi
  [[ -z ${notes} ]] || jq -cn --arg m "${notes% }" '{systemMessage: $m}'
  exit 0
  ;;

guard)
  if [[ ${tool} == Bash ]]; then
    # Bash is the way around a file-tool guard. Unlike the official
    # bash_command_validator example (anchored `^grep`), the whole compound
    # command is searched: `cd x && sed -i ...` must not slip through.
    cmd=$(jq -r '.tool_input.command // empty' <<<"${payload}")
    [[ -n ${cmd} ]] || exit 0
    # Mark the time, so `post` can find .py files this command writes when
    # Claude Code doesn't report them (PostToolUse Edit|Write never fires for
    # Bash writes; bashEditDiff is recorded only in some permission modes).
    : >"${state_dir}/${session}.bashmark" 2>/dev/null || true
    # No \b: word boundaries differ between GNU, BSD, and BusyBox grep.
    b='(^|[^[:alnum:]_-])'
    writes='(^|[^<>&0-9])>{1,2}[^&>]|@B@sed[[:space:]]+(-[a-zA-Z]*i|--in-place)|@B@perl[[:space:]]+-[a-zA-Z]*i|@B@tee([[:space:]]|$)|@B@(cp|mv|rm|ln|truncate|dd)[[:space:]]|<<|@B@python3?[[:space:]]+-c([[:space:]]|$)'
    writes=${writes//@B@/${b}}
    policy=""
    if grep -Eq -- '--writebaseline|--baselinemode[= ]+(auto|lock)|disableAllHooks|enableTypeIgnoreComments' <<<"${cmd}"; then
      policy="it changes the type-checking baseline or disables hooks, which is the user's decision"
    elif grep -Eq -- "${writes}" <<<"${cmd}"; then
      if grep -Eiq '#[[:space:]]*(pyright:[[:space:]]*(ignore|basic|standard|off)|type:[[:space:]]*ignore)' <<<"${cmd}"; then
        policy="it writes a type-checking suppression comment through the shell"
      elif grep -Eq 'pyrightconfig\.json|pyproject\.toml|\.basedpyright/|basedpyright-after-edit\.sh|settings(\.local)?\.json' <<<"${cmd}"; then
        policy="it writes the type-checking configuration, the baseline, the gate, or its settings through the shell"
      elif [[ -s ${dirty} ]]; then
        policy="type errors are open in: $(paste -sd, "${dirty}" || true); until they are clean, shell commands that write files are denied (use the Edit tool on those files)"
      fi
    fi
    [[ -z ${policy} ]] && exit 0
    reason="The basedpyright gate denied this command: ${policy}."
    jq -cn --arg r "${reason}" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
    printf '%s: %s\n' "${TAG}" "${reason}" >&2
    exit 2
  fi
  case ${tool} in Write | Edit | NotebookEdit) ;; *) exit 0 ;; esac
  # First touch of a configured project this session: record its diagnostics
  # before the edit, so Stop can tell new breakage from existing debt. Runs in
  # a subshell: a failure here leaves no snapshot (Stop then checks touched
  # files only) instead of denying the edit.
  if [[ ${stop_scope} == auto ]]; then
    for p in "${paths[@]+"${paths[@]}"}"; do
      [[ ${p} == /* ]] || p="${cwd}/${p}"
      pdir=$(cd "$(dirname "${p}")" 2>/dev/null && pwd -P) || continue
      proot=$(project_root "${pdir}")
      pkind=$(root_kind "${proot}")
      [[ ${pkind} == project ]] || continue
      snap=$(snap_path "${proot}")
      [[ -e ${snap} ]] && continue
      (
        run_bp "${proot}"
        diag_keys >"${snap}.tmp" && mv -f "${snap}.tmp" "${snap}"
      ) 2>/dev/null
      [[ -e ${snap} ]] || : >"${snap}.failed"
    done
  fi
  [[ -s ${dirty} ]] || exit 0
  open_files=$(paste -sd, "${dirty}") || open_files="(unreadable)"
  target=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"${payload}")
  target=$(to_posix "${target}")
  [[ -n ${target} ]] || exit 0
  [[ ${target} == /* ]] || target="${cwd}/${target}"
  t=$(canonical "${target}" 2>/dev/null || printf '%s' "${target}")
  allowed=0
  grep -qxF -- "${t}" "${dirty}" && allowed=1
  if ((! allowed)) && [[ ${t} =~ \.(py|pyi|pyw|ipynb)$ ]]; then
    troot=$(project_root "$(dirname "${t}")")
    while IFS= read -r d; do
      droot=$(project_root "$(dirname "${d}")")
      [[ ${droot} == "${troot}" ]] && allowed=1
    done <"${dirty}"
  fi
  if ((allowed)); then
    : >"${denials}"
    exit 0
  fi
  count=$(($(cat "${denials}" 2>/dev/null || echo 0) + 0 + 1))
  printf '%s\n' "${count}" >"${denials}"
  if ((count > max_denials)); then
    : >"${denials}"
    jq -cn --arg m "${TAG}: focus lock let an edit through after ${max_denials} denials; type errors are still open in: ${open_files}" '{systemMessage: $m}'
    exit 0
  fi
  reason="Type errors are open in: ${open_files}. Until they are clean, the gate allows edits only to those files and to other Python files of the same project; ${t} is outside that set."
  jq -cn --arg r "${reason}" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
  printf '%s: %s\n' "${TAG}" "${reason}" >&2
  exit 2
  ;;

stop)
  [[ -s ${touched} ]] || exit 0
  open_files=$(paste -sd, "${dirty}") || open_files="(unreadable)"
  count=$(($(cat "${blocks}" 2>/dev/null || echo 0) + 0))
  if [[ ${stop_active} == true ]] && ((count >= max_blocks)); then
    : >"${blocks}"
    jq -cn --arg m "${TAG}: ending the turn after ${max_blocks} blocks with type errors still open in: ${open_files}" '{systemMessage: $m}'
    exit 0
  fi
  [[ ${stop_active} == true ]] || count=0
  report=""
  notes_stop=""
  failed=0
  roots=()
  while IFS= read -r f; do
    [[ -f ${f} ]] || {
      set_del "${dirty}" "${f}"
      continue
    }
    r=$(project_root "$(dirname "${f}")")
    seen=0
    for x in "${roots[@]+"${roots[@]}"}"; do [[ ${x} == "${r}" ]] && seen=1; done
    ((seen)) || roots+=("${r}")
  done <"${touched}"
  for r in "${roots[@]+"${roots[@]}"}"; do
    rkind=$(root_kind "${r}")
    if [[ ${stop_scope} == project && ${rkind} == project ]]; then
      run_bp "${r}" # no file arguments: include/exclude/executionEnvironments apply as in CI
      if ((RUN_STATUS == 1)); then
        failed=1
        report+="basedpyright (project scope, CI parity): ${r}"$'\n'"$(render "${r}")"$'\n'
      fi
      continue
    fi
    # Every touched file of this root must be clean.
    files=()
    while IFS= read -r f; do
      [[ -f ${f} ]] || continue
      froot=$(project_root "$(dirname "${f}")")
      [[ ${froot} == "${r}" ]] && files+=("${f}")
    done <"${touched}"
    ((${#files[@]} > 0)) || continue
    run_bp "${r}" "${files[@]}"
    nblock=$(blocking "${r}")
    if ((nblock > 0)); then
      failed=1
      report+="basedpyright (edited files): ${r}"$'\n'"$(render "${r}")"$'\n'
    fi
    # Configured project, auto scope: new diagnostics anywhere else in it.
    snap=$(snap_path "${r}")
    if [[ ${stop_scope} == auto && ${rkind} == project && -e ${snap} ]]; then
      run_bp "${r}"
      now=$(diag_keys)
      touched_list=$(printf '%s\n' "${files[@]}")
      fresh=$(jq -Rn --rawfile before "${snap}" --arg now "${now}" --arg touched "${touched_list}" '
        def counts: split("\n") | map(select(length > 0)) | group_by(.) | map({key: .[0], value: length}) | from_entries;
        ($before | counts) as $b | ($touched | split("\n")) as $t
        | ($now | counts) | to_entries[]
        | select((.key | split("\t")[0]) as $f | ($t | index($f)) | not)
        | select(.value > ($b[.key] // 0)) | .key')
      if [[ -n ${fresh} ]]; then
        failed=1
        report+="basedpyright: new diagnostics in files you did not edit (${r}; they were not there when this session first touched the project, so an edit broke them):"$'\n'
        report+=$(printf '%s\n' "${fresh}" | awk -F '\t' -v root="${r}/" '{ f = $1; sub("^" root, "", f); printf "  %s  %s  %s\n", f, $2, $3 }')$'\n'
      fi
    elif [[ ${stop_scope} == auto && ${rkind} == project ]]; then
      notes_stop="${TAG}: no pre-edit snapshot for ${r}; only the edited files were checked. "
    fi
  done
  if ((failed)); then
    printf '%s\n' "$((count + 1))" >"${blocks}"
    report=$(budget "${report}")
    printf '%s\nFiles you did not edit can appear above: an edit can break code that imports it.\n%s\n' "${report}" "${LSP_HOWTO}" >&2
    exit 2
  fi
  : >"${blocks}"
  : >"${dirty}"
  jq -cn --arg m "${notes_stop}${TAG} ✓ ${#roots[@]} location(s) type-check clean" '{systemMessage: $m}'
  exit 0
  ;;
task-completed)
  [[ -s ${dirty} ]] || exit 0
  open_files=$(paste -sd, "${dirty}") || open_files="(unreadable)"
  printf '%s: a task is not complete while type errors are open in: %s. Each edit of those files re-runs the check.\n' "${TAG}" "${open_files}" >&2
  exit 2
  ;;

prompt)
  # Plain stdout here would be injected into Claude's context: print JSON only.
  : >"${blocks}"
  : >"${denials}"
  [[ -s ${dirty} ]] || exit 0
  open_files=$(paste -sd, "${dirty}") || open_files="(unreadable)"
  jq -cn --arg c "${TAG}: type errors from an earlier turn are still open in: ${open_files}. The gate's focus lock and Stop check still apply to them." \
    '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $c}}'
  exit 0
  ;;

session-start)
  [[ -s ${dirty} ]] || exit 0
  open_files=$(paste -sd, "${dirty}") || open_files="(unreadable)"
  jq -cn --arg c "${TAG}: type errors reported before this context was summarized are still open in: ${open_files}. The gate's focus lock and Stop check still apply to them." \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $c}}'
  exit 0
  ;;

*) die "unknown event '${event}'" ;;
esac
