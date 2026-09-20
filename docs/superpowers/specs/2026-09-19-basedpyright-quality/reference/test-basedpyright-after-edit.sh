#!/usr/bin/env bash
# Behavioral tests for the reference basedpyright-after-edit.sh handler.
# Usage: test-basedpyright-after-edit.sh [path/to/handler]   (needs basedpyright, jq)
# Every case sends a realistic hook payload on stdin, never as an argument.

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd -P) || exit 1
handler=${1:-${here}/basedpyright-after-edit.sh}
shell=${TEST_SHELL:-bash}
shell=$(command -v "${shell}") || exit 1 # absolute: some cases run with a stripped PATH
work=$(mktemp -d) || exit 1
work=$(cd "${work}" && pwd -P) || exit 1
export TMPDIR="${work}/tmp"
mkdir -p "${TMPDIR}"
trap 'rm -rf "${work}"' EXIT

pass=0
fail=0
ok() {
  pass=$((pass + 1))
  printf 'ok   %s\n' "$1"
}
ko() {
  fail=$((fail + 1))
  printf 'FAIL %s\n     status=%s stdout=%s\n     stderr=%s\n' "$1" "${st}" "${out:0:300}" "${err:0:400}"
}

session="s$$"
out=""
err=""
st=0
payload=""
run() { # <event> [env assignments...]; reads ${payload}
  local ev=$1
  shift
  out=$(printf '%s' "${payload}" | env "$@" "${shell}" "${handler}" "${ev}" 2>"${work}/err")
  st=$?
  err=$(<"${work}/err")
}
edit_payload() { # <tool> <file>
  payload=$(jq -cn --arg s "${session}" --arg cwd "${proj}" --arg t "$1" --arg f "$2" \
    '{session_id: $s, transcript_path: "/dev/null", cwd: $cwd, hook_event_name: "PostToolUse",
      tool_name: $t, tool_input: {file_path: $f}, tool_response: {filePath: $f, success: true}}') || exit 1
}
event_payload() { # <event> [extra-json]
  payload=$(jq -cn --arg s "${session}" --arg cwd "${proj}" --arg e "$1" --argjson x "${2:-"{}"}" \
    '{session_id: $s, transcript_path: "/dev/null", cwd: $cwd, hook_event_name: $e, stop_hook_active: false} + $x') || exit 1
}

# --- fixture project ---------------------------------------------------------
proj="${work}/proj"
mkdir -p "${proj}/pkg" "${proj}/gen"
printf '[tool.basedpyright]\ntypeCheckingMode = "recommended"\nexclude = ["gen"]\n' >"${proj}/pyproject.toml"
: >"${proj}/pkg/__init__.py"
printf 'def f(x: int) -> int:\n    return x + 1\n' >"${proj}/pkg/a.py"
printf 'from pkg.a import f\n\ny: int = f(1)\n' >"${proj}/pkg/b.py"
printf '# notes\n' >"${proj}/README.md"
printf 'x: int = "no"\n' >"${proj}/gen/z.py"

# 1. clean edit (PreToolUse first, as Claude Code does: it snapshots the project)
edit_payload Edit "${proj}/pkg/a.py"
run guard
snaps=("${TMPDIR}"/basedpyright-after-edit-*/"${session}".snap.*)
if [[ ${st} == 0 && -s ${snaps[0]:-/nonexistent} || -e ${snaps[0]:-/nonexistent} ]]; then ok "guard: first touch of a configured project records a snapshot"; else ko "guard: first touch of a configured project records a snapshot"; fi
run post
if [[ ${st} == 0 ]]; then ok "post: clean file exits 0"; else ko "post: clean file exits 0"; fi

# 2. an error in the edited file blocks, with the LSP how-to
printf 'def f(x: int) -> int:\n    return "s"\n' >"${proj}/pkg/a.py"
run post
if [[ ${st} == 2 ]]; then ok "post: type error exits 2"; else ko "post: type error exits 2"; fi
if [[ ${err} == *"pkg/a.py:2:12  error  reportReturnType"* ]]; then ok "post: report names the rule at a 1-based position"; else ko "post: report names the rule at a 1-based position"; fi
if [[ ${err} == *goToDefinition* && ${err} == *"up to 3 retries"* ]]; then ok "post: report directs the LSP tool, with retries"; else ko "post: report directs the LSP tool, with retries"; fi

# 3. focus lock
edit_payload Edit "${proj}/README.md"
run guard
if [[ ${st} == 2 && ${out} == *'"permissionDecision":"deny"'* ]]; then ok "guard: non-Python edit denied while a file must be fixed"; else ko "guard: non-Python edit denied while a file must be fixed"; fi
edit_payload Edit "${proj}/pkg/b.py"
run guard
if [[ ${st} == 0 ]]; then ok "guard: same-project Python edit allowed (cross-file fix)"; else ko "guard: same-project Python edit allowed (cross-file fix)"; fi
edit_payload Read "${proj}/README.md"
run guard
if [[ ${st} == 0 ]]; then ok "guard: non-edit tools are never locked"; else ko "guard: non-edit tools are never locked"; fi
edit_payload Write "${proj}/README.md"
run guard
run guard
run guard
run guard
if [[ ${st} == 0 && ${out} == *"let an edit through"* ]]; then ok "guard: let through after 3 denials (no deadlock)"; else ko "guard: let through after 3 denials (no deadlock)"; fi

# 3b. Bash can't route around the gate (whole compound command is searched)
bash_payload() { # <command>
  payload=$(jq -cn --arg s "${session}" --arg cwd "${proj}" --arg c "$1" \
    '{session_id: $s, transcript_path: "/dev/null", cwd: $cwd, hook_event_name: "PreToolUse",
      tool_name: "Bash", tool_input: {command: $c}}') || exit 1
}
bash_payload 'rg -n "def f" pkg && basedpyright pkg/a.py'
run guard
if [[ ${st} == 0 ]]; then ok "guard/Bash: reads and checks allowed while dirty"; else ko "guard/Bash: reads and checks allowed while dirty"; fi
bash_payload 'cd pkg && echo "notes" > ../README.md'
run guard
if [[ ${st} == 2 && ${out} == *deny* ]]; then ok "guard/Bash: shell write denied while dirty (compound command)"; else ko "guard/Bash: shell write denied while dirty (compound command)"; fi
bash_payload 'uv run basedpyright --writebaseline'
run guard
if [[ ${st} == 2 && ${err} == *baseline* ]]; then ok "guard/Bash: --writebaseline denied"; else ko "guard/Bash: --writebaseline denied"; fi
bash_payload "sed -i '' 's/return \"s\"/return \"s\"  # type: ignore/' pkg/a.py"
run guard
if [[ ${st} == 2 && ${err} == *suppression* ]]; then ok "guard/Bash: suppression via sed -i denied"; else ko "guard/Bash: suppression via sed -i denied"; fi
bash_payload 'printf "[tool.basedpyright]\ntypeCheckingMode = \"off\"\n" >> pyproject.toml'
run guard
if [[ ${st} == 2 && ${err} == *configuration* ]]; then ok "guard/Bash: config write denied"; else ko "guard/Bash: config write denied"; fi

# 4. task completion refused while dirty; compaction re-injects the obligation
event_payload TaskCompleted
run task-completed
if [[ ${st} == 2 ]]; then ok "task-completed: refused while type errors are open"; else ko "task-completed: refused while type errors are open"; fi
event_payload SessionStart '{"source":"compact"}'
run session-start
if [[ ${out} == *additionalContext*pkg/a.py* ]]; then ok "session-start: re-injects open files after compaction"; else ko "session-start: re-injects open files after compaction"; fi

event_payload UserPromptSubmit '{"prompt":"continue"}'
run prompt
if [[ ${st} == 0 && ${out} == *'"hookEventName":"UserPromptSubmit"'*pkg/a.py* ]]; then ok "prompt: open errors carried into the next turn as context"; else ko "prompt: open errors carried into the next turn as context"; fi
PATH_NOJQ=$(mktemp -d "${work}/nojq.XXXXXX")
dirname_bin=$(command -v dirname) || exit 1
ln -s "${dirname_bin}" "${PATH_NOJQ}/dirname"
run prompt PATH="${PATH_NOJQ}"
if [[ ${st} == 0 ]]; then ok "prompt: a broken gate (no jq) never blocks the user's prompt"; else ko "prompt: a broken gate (no jq) never blocks the user's prompt"; fi
edit_payload Edit "${proj}/pkg/a.py"
run post PATH="${PATH_NOJQ}"
if [[ ${st} == 2 && ${err} == *"jq is required"* ]]; then ok "post: a broken gate (no jq) fails closed on edits"; else ko "post: a broken gate (no jq) fails closed on edits"; fi

# 5. fixing the file clears it
printf 'def f(x: int) -> int:\n    return x + 1\n' >"${proj}/pkg/a.py"
edit_payload Edit "${proj}/pkg/a.py"
run post
if [[ ${st} == 0 ]]; then ok "post: fixed file exits 0"; else ko "post: fixed file exits 0"; fi
edit_payload Edit "${proj}/README.md"
run guard
if [[ ${st} == 0 ]]; then ok "guard: lock released once clean"; else ko "guard: lock released once clean"; fi

# 6. cross-file breakage: a.py is clean on its own, b.py breaks; Stop catches it
printf 'def f(x: int) -> str:\n    return str(x)\n' >"${proj}/pkg/a.py"
edit_payload Edit "${proj}/pkg/a.py"
run post
if [[ ${st} == 0 ]]; then ok "post: a.py alone is clean after the signature change"; else ko "post: a.py alone is clean after the signature change"; fi
event_payload Stop
run stop
if [[ ${st} == 2 && ${err} == *"pkg/b.py"* ]]; then ok "stop: auto scope blocks on new breakage in the untouched importer b.py"; else ko "stop: auto scope blocks on new breakage in the untouched importer b.py"; fi
printf 'from pkg.a import f\n\ny: str = f(1)\n' >"${proj}/pkg/b.py"
run stop
if [[ ${st} == 0 && ${out} == *"type-check clean"* ]]; then ok "stop: passes once the project is clean"; else ko "stop: passes once the project is clean"; fi

# 7. excluded file: skipped, and said so (never a silent pass)
edit_payload Write "${proj}/gen/z.py"
run post
if [[ ${st} == 0 && ${out} == *excluded* ]]; then ok "post: excluded file reported as skipped"; else ko "post: excluded file reported as skipped"; fi

# 8. CI variables in the environment don't change the verdict
printf 'def g() -> int:\n    return "s"\n' >"${proj}/pkg/c.py"
edit_payload Write "${proj}/pkg/c.py"
run post GITHUB_ACTIONS=true CI=true
if [[ ${st} == 2 && ${err} != *"::error"* ]]; then ok "post: CI variables set -> same exit 2, no ::error annotations"; else ko "post: CI variables set -> same exit 2, no ::error annotations"; fi
rm -f "${proj}/pkg/c.py"
: >"${TMPDIR}/basedpyright-after-edit-$(id -u)/${session}.dirty"

# 9. broken configuration (both tables) fails closed with the config reason
cp "${proj}/pyproject.toml" "${work}/pyproject.bak"
printf '[tool.pyright]\ntypeCheckingMode = "basic"\n' >>"${proj}/pyproject.toml"
edit_payload Edit "${proj}/pkg/a.py"
run post
if [[ ${st} == 2 && ${err} == *"exit 3"* ]]; then ok "post: broken config -> exit 2 with the configuration reason"; else ko "post: broken config -> exit 2 with the configuration reason"; fi
printf '[tool.basedpyright]\nmode = "strict"\n' >"${proj}/pyproject.toml"
run post
if [[ ${st} == 2 && ${err} == *"exit 3"* ]]; then ok "post: unrecognized setting -> exit 2 (--outputjson alone would exit 0)"; else ko "post: unrecognized setting -> exit 2 (--outputjson alone would exit 0)"; fi
cp "${work}/pyproject.bak" "${proj}/pyproject.toml"

# 10. missing binary and death by signal fail closed
run post BASEDPYRIGHT_BIN=/nonexistent/basedpyright
if [[ ${st} == 2 && ${err} == *"not found"* ]]; then ok "post: missing basedpyright -> exit 2"; else ko "post: missing basedpyright -> exit 2"; fi
printf '#!/bin/sh\nkill -9 $$\n' >"${work}/killed"
chmod +x "${work}/killed"
run post BASEDPYRIGHT_BIN="${work}/killed"
if [[ ${st} == 2 && ${err} == *"signal 9"* ]]; then ok "post: killed by signal -> exit 2 naming the memory cap"; else ko "post: killed by signal -> exit 2 naming the memory cap"; fi

# 11. malformed payload and non-Python edits
payload='not json'
run post
if [[ ${st} == 2 ]]; then ok "post: malformed payload -> exit 2"; else ko "post: malformed payload -> exit 2"; fi
edit_payload Edit "${proj}/README.md"
start=${SECONDS}
for _ in 1 2 3 4 5 6 7 8 9 10; do run post; done
elapsed=$((SECONDS - start))
if [[ ${st} == 0 && ${elapsed} -le 3 ]]; then ok "post: non-Python edit exits 0 (10 runs in ${elapsed}s)"; else ko "post: non-Python edit exits 0 (10 runs in ${elapsed}s)"; fi

# 12. universal: pre-existing debt elsewhere never blocks (auto); CI parity does
printf 'legacy: int = "debt"\n' >"${proj}/pkg/legacy.py"
session="${session}x" # a new session: the snapshot now contains the debt
printf 'def f(x: int) -> str:\n    return str(x) + ""\n' >"${proj}/pkg/a.py"
edit_payload Edit "${proj}/pkg/a.py"
run guard
run post
event_payload Stop
run stop
if [[ ${st} == 0 ]]; then ok "stop/auto: existing debt in an untouched file doesn't block"; else ko "stop/auto: existing debt in an untouched file doesn't block"; fi
run stop BPAE_STOP_SCOPE=project
if [[ ${st} == 2 && ${err} == *legacy.py* ]]; then ok "stop/project: CI-parity scope blocks on it"; else ko "stop/project: CI-parity scope blocks on it"; fi

# 13. universal: a Python file in a non-Python directory, no config, no repository
loose="${work}/loose/scripts"
mkdir -p "${loose}"
printf 'import requests\n\ncount: int = "three"\nprint(requests, count)\n' >"${loose}/tool.py"
session="${session}y"
edit_payload Write "${loose}/tool.py"
run guard
run post
if [[ ${st} == 2 && ${err} == *reportAssignmentType* && ${err} == *"no basedpyright configuration found"* ]]; then ok "post/unconfigured: code error blocks, with the defaults stated"; else ko "post/unconfigured: code error blocks, with the defaults stated"; fi
printf 'import requests\n\ncount: int = 3\nprint(requests, count)\n' >"${loose}/tool.py"
run post
if [[ ${st} == 0 && ${out} == *"only environment findings remain"* ]]; then ok "post/unconfigured: a missing package (reportMissingModuleSource) is reported, not blocking"; else ko "post/unconfigured: a missing package (reportMissingModuleSource) is reported, not blocking"; fi
event_payload Stop
run stop
if [[ ${st} == 0 ]]; then ok "stop/unconfigured: passes on the edited file alone"; else ko "stop/unconfigured: passes on the edited file alone"; fi

# 14. config modes: pinned overrides the project; profile covers config-less files
session="${session}z"
printf '[tool.basedpyright]\ntypeCheckingMode = "off"\n' >"${work}/lax.toml"
laxproj="${work}/laxproj"
mkdir -p "${laxproj}"
printf '[tool.basedpyright]\ntypeCheckingMode = "off"\n' >"${laxproj}/pyproject.toml"
printf 'def h() -> int:\n    return "s"\n' >"${laxproj}/h.py"
edit_payload Edit "${laxproj}/h.py"
run post
if [[ ${st} == 0 ]]; then ok "mode own: the project's own policy (typeCheckingMode off) wins"; else ko "mode own: the project's own policy (typeCheckingMode off) wins"; fi
run post BPAE_CONFIG_MODE=pinned
if [[ ${st} == 2 && ${err} == *"pinned configuration"* ]]; then ok "mode pinned: the plugin's profile overrides the project"; else ko "mode pinned: the plugin's profile overrides the project"; fi
: >"${TMPDIR}/basedpyright-after-edit-$(id -u)/${session}.dirty"
printf 'import requests\n\nn: int = "x"\nprint(requests, n)\n' >"${loose}/p.py"
edit_payload Write "${loose}/p.py"
run post BPAE_CONFIG_MODE=profile
if [[ ${st} == 2 && ${err} == *"profile"* && ${err} == *reportAssignmentType* && ${err} != *reportMissingModuleSource* ]]; then ok "mode profile: config-less file uses the bundled profile (missing package = information)"; else ko "mode profile: config-less file uses the bundled profile (missing package = information)"; fi
run post BPAE_CONFIG_MODE=profile BPAE_CONFIG=/nonexistent.json
if [[ ${st} == 2 && ${err} == *"needs a readable config file"* ]]; then ok "mode profile: a missing profile fails closed"; else ko "mode profile: a missing profile fails closed"; fi
: >"${TMPDIR}/basedpyright-after-edit-$(id -u)/${session}.dirty"

# 15. a Python file written through Bash, with no bashEditDiff, is still checked
bash_payload 'cat > bad.py <<EOF'
payload=$(jq -c --arg cwd "${loose}" '.cwd = $cwd' <<<"${payload}")
run guard
sleep 1
printf 'v: int = "no"\n' >"${loose}/bad.py"
payload=$(jq -cn --arg s "${session}" --arg cwd "${loose}" '{session_id: $s, transcript_path: "/dev/null", cwd: $cwd, hook_event_name: "PostToolUse", tool_name: "Bash", tool_input: {command: "cat > bad.py"}, tool_response: {stdout: "", stderr: ""}}')
run post
if [[ ${st} == 2 && ${err} == *bad.py* ]]; then ok "post/Bash: a .py written by a shell command is found and checked"; else ko "post/Bash: a .py written by a shell command is found and checked"; fi

printf '\n%s passed, %s failed (%s)\n' "${pass}" "${fail}" "${shell}"
((fail == 0))
