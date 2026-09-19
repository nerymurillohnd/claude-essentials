#!/usr/bin/env bash
# Behavioral tests for verify-completion's hooks: analyze.jq (claim detection,
# record validation) and gate.sh (mark/stop state machine, modes, degraded
# modes, timing). Runs the handler under $BNV_TEST_BASH (set by the repo's
# `npm test` to each bash it finds, including /bin/bash 3.2), else `bash`.
#
# Test data is literal Markdown handed to the hooks, so single-quoted backticks
# and $ are intended; helpers compare what producers print, so a failing
# producer shows up as a failed comparison rather than a masked return code.
# shellcheck disable=SC2016,SC2312

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
gate="${here}/gate.sh"
analyze="${here}/analyze.jq"
hooks_json="${here}/../hooks/hooks.json"
run_bash=${BNV_TEST_BASH:-bash}

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() {
  fail=$((fail + 1))
  printf 'FAIL: %s\n' "$1" >&2
  [[ $# -gt 1 ]] && printf '      %s\n' "$2" >&2
  return 0
}

# ------------------------------------------------------------- helpers ---

# The message goes through stdin, not --arg: Linux caps a single argument at
# 128 KB (MAX_ARG_STRLEN), so a long reply passed as an argument never reaches
# jq there, and a test fed that empty payload passes without testing anything.
payload() { # message [stop_hook_active] [session]
  printf '%s' "$1" | jq -Rs --argjson a "${2:-false}" --arg s "${3:-sess-1}" \
    '{session_id: $s, transcript_path: "/tmp/t.jsonl", cwd: "/tmp", hook_event_name: "Stop", stop_hook_active: $a, last_assistant_message: .}'
}

claims_of() { payload "$1" | jq -c -f "${analyze}" | jq -c '.claims'; }
record_of() { payload "$1" | jq -c -f "${analyze}" | jq -c '.record'; }

expect_claim() {
  local got
  got=$(claims_of "$1")
  if [[ ${got} == "[]" ]]; then bad "claim not detected: $1"; else ok; fi
}

expect_no_claim() {
  local got
  got=$(claims_of "$1")
  if [[ ${got} == "[]" ]]; then ok; else bad "false claim: $1" "${got}"; fi
}

expect_record_ok() { # message verdict
  local got
  got=$(record_of "$1")
  if [[ $(jq -r '.present and (.errors | length == 0)' <<<"${got}") == true &&
  $(jq -r '.verdict' <<<"${got}") == "$2" ]]; then ok; else bad "record should be valid ($2): ${3:-}" "${got}"; fi
}

expect_record_error() { # message error-substring label
  local got
  got=$(record_of "$1")
  if jq -e --arg e "$2" '.present and any(.errors[]; contains($e))' <<<"${got}" >/dev/null; then
    ok
  else
    bad "record error '$2' expected: $3" "${got}"
  fi
}

# Runs gate.sh <cmd> with stdin; sets OUT and RC. Extra env via "VAR=value".
run_gate() { # cmd input [env...]
  local cmd=$1 input=$2
  shift 2
  OUT=$(printf '%s' "${input}" | env CLAUDE_PLUGIN_DATA="${work}/data" "$@" "${run_bash}" "${gate}" "${cmd}")
  RC=$?
}

kind_of_output() { # prints: none | context | warning | invalid
  if [[ -z ${OUT} ]]; then
    echo none
  elif jq -e '.hookSpecificOutput.hookEventName == "Stop" and (.hookSpecificOutput.additionalContext | type == "string")' <<<"${OUT}" >/dev/null 2>&1; then
    echo context
  elif jq -e '.systemMessage | type == "string"' <<<"${OUT}" >/dev/null 2>&1; then
    echo warning
  else
    echo invalid
  fi
}

expect_gate() { # label expected-kind
  local got
  got=$(kind_of_output)
  if [[ ${RC} -eq 0 && ${got} == "$2" ]]; then ok; else bad "$1: expected $2, got ${got} (rc=${RC})" "${OUT}"; fi
}

reset_state() { rm -rf "${work}/data"; }

mark() { run_gate mark "{\"session_id\":\"${1:-sess-1}\",\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{}}" "${@:2}"; }

RECORD='### Verification record

Requirement: add a --dry-run flag to the deploy script

1. Adversarial review: PASS — read the full `git diff` of deploy.sh and re-ran it
2. Outcome: PASS — ran `./deploy.sh --dry-run`; nothing was uploaded, plan printed
3. Counterpart: N/A — no other script or pipeline calls deploy.sh with flags
4. Distrust the green: PASS — no skipped tests; `bats tests/` ran 14 cases, 0 skipped
5. Both directions: PASS — `--dry` (typo) exits 2 with usage; valid flag exits 0
6. Evidence: PASS — commands and trimmed outputs are quoted above in this reply'

record_with() { # sed-like: replace $1 with $2 in RECORD, then append verdict $3
  local r=${RECORD}
  r=${r/"$1"/"$2"}
  printf '%s\n\nVerdict: %s' "${r}" "$3"
}

# --------------------------------------------------- claim detection ---

expect_claim "All tests pass."
expect_claim "I fixed the parser and all the tests now pass."
expect_claim "The feature is done."
expect_claim "Everything is complete and verified."
expect_claim "It's ready to merge."
expect_claim "This is ready for review."
expect_claim "The branch is ready to be merged."
expect_claim "Done."
expect_claim "All done!"
expect_claim "Tests are green."
expect_claim "The bug has been fixed."
expect_claim "I've fixed the race condition."
expect_claim "Successfully deployed to staging."
expect_claim "It now works end to end."
expect_claim "LGTM, ship it."
expect_claim "**Done** — the refactor is complete."
expect_claim "Listo."
expect_claim "¡Listo! El script ya quedó."
expect_claim "Todo está listo para merge."
expect_claim "Las pruebas pasan y está terminado."
expect_claim "El endpoint quedó funcionando."
expect_claim "Arreglé el bug del login."
expect_claim "Todo en verde."
expect_claim "El despliegue terminó con éxito."
expect_claim "La migración está completa."
expect_claim "Funciona correctamente con los datos reales."

expect_no_claim "The feature is not done yet."
expect_no_claim "It isn't ready to merge."
expect_no_claim "I can't say it's done until CI runs."
expect_no_claim "Once the migration runs, if it works, we can continue."
expect_no_claim "Is it ready to merge?"
expect_no_claim "No está listo todavía."
expect_no_claim "Todavía no está terminado: falta el paso 3."
expect_no_claim "¿Está listo para producción?"
expect_no_claim "Cuando esté listo te aviso."
expect_no_claim "Esta lista de archivos incluye todo lo que cambió."
expect_no_claim "I'm working on the parser now."
expect_no_claim "Here is the plan for the refactor."
expect_no_claim "Ready to start when you are."
expect_no_claim "Read the file; it has three functions."
expect_no_claim '> The ticket said: "all tests pass"'
expect_no_claim 'Run `echo done` to see it.'
expect_no_claim 'Example output:
```
All tests pass. Done.
```'
expect_no_claim ""

# -------------------------------------------------- record validation ---

expect_record_ok "$(record_with x x VERIFIED)" VERIFIED "canonical"
expect_record_ok "All tests pass.

$(record_with x x '**VERIFIED**')" VERIFIED "claim + record, bold verdict"
expect_record_ok "$(record_with '1. Adversarial review: PASS' '1. Adversarial review: FAIL' 'NOT VERIFIED')" "NOT VERIFIED" "honest failure"
expect_record_ok "$(record_with '2. Outcome: PASS' '2. Outcome: BLOCKED' 'NOT VERIFIED')" "NOT VERIFIED" "blocked gate"
expect_record_ok '## Registro de verificación

**Requisito:** validar el correo antes de guardarlo en la base de datos

| # | Compuerta | Estado | Evidencia |
| --- | --- | --- | --- |
| 1 | Revisión adversarial | PASS | leí el diff completo de `src/user.ts` y reejecuté las pruebas |
| 2 | Resultado | PASS | `npm test -- user` cubre el guardado con correo válido |
| 3 | Contraparte | PASS | la API rechaza correo vacío con 422 y mensaje claro |
| 4 | Desconfiar del verde | PASS | sin skip ni only; 0 reglas de lint desactivadas |
| 5 | Ambas direcciones | PASS | válido guarda; inválido devuelve 422 y no escribe |
| 6 | Evidencia | PASS | comandos y salidas citados arriba en esta respuesta |

**Veredicto:** VERIFIED' VERIFIED "Spanish table"
expect_record_ok "$(record_with x x VERIFIED)

## Next steps

- 1 file changed; waiting for your approval to commit." VERIFIED "section after record is excluded"

expect_record_error "$(record_with 'Requirement: add a --dry-run flag to the deploy script' '' VERIFIED)" 'missing a "Requirement:"' "no requirement"
expect_record_error "$(record_with 'Requirement: add a --dry-run flag to the deploy script' 'Requirement: fix' VERIFIED)" "too short" "short requirement"
expect_record_error "${RECORD}" "missing a \"Verdict" "no verdict"
expect_record_error "$(record_with '3. Counterpart: N/A — no other script or pipeline calls deploy.sh with flags' '' VERIFIED)" "gate 3 is missing" "missing gate"
expect_record_error "$(record_with '5. Both directions' '5. Dup: PASS — duplicate line for gate five here
5. Both directions' VERIFIED)" "gate 5 appears 2 times" "duplicate gate"
expect_record_error "$(record_with '6. Evidence: PASS — commands and trimmed outputs are quoted above in this reply' '6. Evidence: PASS — ok' VERIFIED)" "gate 6 (PASS) has no evidence" "hollow evidence"
expect_record_error "$(record_with '2. Outcome: PASS' '2. Outcome: FAIL' VERIFIED)" "verdict is VERIFIED but gate 2 is FAIL" "inconsistent verdict"
expect_record_error "$(record_with '4. Distrust the green: PASS' '4. Distrust the green: N/A' VERIFIED)" "gate 4 always applies" "N/A on a mandatory gate"
expect_record_error "$(record_with '1. Adversarial review: PASS' '1. Adversarial review: pass' VERIFIED)" "gate 1 is missing" "lowercase status token"
no_code=$(record_with x x VERIFIED | tr -d '`')
expect_record_error "${no_code}" "re-runnable artifact" "no code evidence"

expect_record_error "All tests pass, the feature is done.

$(record_with '5. Both directions: PASS' '5. Both directions: BLOCKED' 'NOT VERIFIED')" "while its verdict is NOT VERIFIED" "done-claim contradicting NOT VERIFIED"
expect_record_ok "The parser change is not verified yet: gate 5 is blocked.

$(record_with '5. Both directions: PASS' '5. Both directions: BLOCKED' 'NOT VERIFIED')" "NOT VERIFIED" "honest partial report"
got=$(claims_of "$(record_with x x VERIFIED)")
if [[ ${got} == "[]" ]]; then ok; else bad "record lines were read as claims" "${got}"; fi

# Review findings (2026-09-19): forms a model writes in good faith.
expect_claim "I'm done with the refactor."
expect_claim "I am finished."
expect_record_ok "$(record_with '6. Evidence: PASS — commands and trimmed outputs are quoted above in this reply' '6. Evidence: PASS — ran `npm test`, output below
   ```
   # tests 42
   # pass 42
   ## fail 0
   ```' VERIFIED)" VERIFIED "fenced output with # lines inside the record"
expect_record_ok "$(record_with '2. Outcome: PASS — ran `./deploy.sh --dry-run`; nothing was uploaded, plan printed' '2. Outcome: PASS — requirement mapped to evidence:
   1. flag parsed: PASS — `./deploy.sh --dry-run` prints the plan
   2. no upload: PASS — no network calls in the dry-run branch' VERIFIED)" VERIFIED "indented numbered sub-list is not a gate"
expect_record_ok "$(record_with '### Verification record' '### 🔍 Final verification record' VERIFIED)" VERIFIED "heading with a short prefix"
expect_record_ok "$(record_with x x VERIFIED)

The Verification record above lists every command I ran." VERIFIED "later prose line mentioning the record"
expect_record_ok "$(record_with 'Requirement: add a --dry-run flag to the deploy script' 'Requirements:
add a --dry-run flag to the deploy script' VERIFIED)" VERIFIED "plural label, text on the next line"
expect_record_ok "$(record_with x x '' | sed '$d')
Verdict — Verified" VERIFIED "verdict with a dash and mixed case"
expect_record_ok "Unit tests are passing and the parser bug is fixed, but the e2e run is blocked.

$(record_with '5. Both directions: PASS' '5. Both directions: BLOCKED' 'NOT VERIFIED')" "NOT VERIFIED" "partial successes in honest prose"
expect_record_error "Everything is ready to merge.

$(record_with '5. Both directions: PASS' '5. Both directions: BLOCKED' 'NOT VERIFIED')" "while its verdict is NOT VERIFIED" "global readiness claim still contradicts"

got=$(record_of "Nothing to see here.")
if [[ $(jq -r '.present' <<<"${got}") == false ]]; then ok; else bad "record detected where there is none" "${got}"; fi

# ---------------------------------------------------- gate: state flow ---

claim=$(payload "All tests pass. The feature is done.")
valid=$(payload "$(record_with x x VERIFIED)")
invalid=$(payload "$(record_with '2. Outcome: PASS' '2. Outcome: FAIL' VERIFIED)")

reset_state
run_gate stop "${claim}"
expect_gate "claim without prior work is ignored" none

mark
expect_gate "mark prints nothing" none
if [[ -e "${work}/data/sessions/sess-1.work" ]]; then ok; else bad "mark did not record work"; fi

run_gate stop "$(payload "Here is what I changed in the parser.")"
expect_gate "no claim after work" none

run_gate stop "${claim}"
expect_gate "claim after work nudges" context
if [[ ${OUT} == *"Verification record"* && ${OUT} == *"never authorizes"* ]]; then ok; else bad "nudge text incomplete" "${OUT}"; fi
# The nudge must be usable without the skill (Cowork, Skill tool denied): it
# carries a template, and that template is itself a valid record once filled.
template=$(jq -r '.hookSpecificOutput.additionalContext' <<<"${OUT}" | sed -n '/^### Verification record/,/^Verdict:/p')
if [[ ${template} == *"1. Adversarial review: PASS"* && ${template} == *"Verdict: VERIFIED"* ]]; then ok; else bad "nudge lacks the record template" "${OUT}"; fi
# shellcheck disable=SC2001 # each <placeholder> separately; a glob would span several
filled=$(sed -e 's/<[^>]*>/checked `npm test` output and the full diff by hand/g' <<<"${template}")
expect_record_ok "${filled}" VERIFIED "template from the nudge, filled in"

run_gate stop "$(payload "All tests pass. The feature is done." true)"
expect_gate "second claim warns the user" warning

run_gate stop "$(payload "All tests pass. The feature is done." true)"
expect_gate "still only a warning, never a loop" warning

mark
run_gate stop "${claim}"
expect_gate "new work resets the nudge" context

run_gate stop "${valid}"
expect_gate "valid record is accepted silently" none
if [[ ! -e "${work}/data/sessions/sess-1.work" ]]; then ok; else bad "valid record did not clear the work marker"; fi

run_gate stop "${claim}"
expect_gate "claim right after a valid record, no new work" none

reset_state
run_gate stop "${invalid}"
expect_gate "invalid record nudges even without work" context
if [[ ${OUT} == *"verdict is VERIFIED but gate 2 is FAIL"* ]]; then ok; else bad "invalid-record nudge lacks the error" "${OUT}"; fi
run_gate stop "${invalid}"
expect_gate "invalid record twice warns" warning

reset_state
mark
run_gate stop "$(payload "$(record_with '5. Both directions: PASS' '5. Both directions: BLOCKED' 'NOT VERIFIED')")"
expect_gate "honest NOT VERIFIED passes" none

# Sessions are independent.
reset_state
mark sess-A
run_gate stop "$(payload "Done." false sess-B)"
expect_gate "other session's work does not count" none
run_gate stop "$(payload "Done." false sess-A)"
expect_gate "own session's work counts" context

# ------------------------------------------------------------- modes ---

reset_state
mark sess-1 CLAUDE_PLUGIN_OPTION_ENFORCEMENT=warn
run_gate stop "${claim}" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=warn
expect_gate "warn mode only warns" warning

reset_state
mark sess-1 CLAUDE_PLUGIN_OPTION_ENFORCEMENT=off
if [[ ! -e "${work}/data/sessions/sess-1.work" ]]; then ok; else bad "off mode still marked work"; fi
run_gate stop "${invalid}" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=OFF
expect_gate "off mode (any case) does nothing" none

reset_state
mark sess-1 CLAUDE_PLUGIN_OPTION_ENFORCEMENT=bogus
run_gate stop "${claim}" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=bogus
expect_gate "unknown mode falls back to enforce" context

# ---------------------------------------------------- degraded modes ---

reset_state
run_gate stop "not json at all"
expect_gate "malformed payload fails open" none
run_gate stop '["an", "array"]'
expect_gate "non-object payload fails open" none
run_gate stop '{"session_id":"sess-1","last_assistant_message":42}'
expect_gate "non-string message fails open" none
run_gate stop ""
expect_gate "empty stdin fails open" none

# No session id: no state, so stop_hook_active decides.
nosess_claim=$(jq -n '{hook_event_name: "Stop", stop_hook_active: false, last_assistant_message: "All tests pass."}')
run_gate stop "${nosess_claim}"
expect_gate "no session id: nudge on first stop" context
run_gate stop "$(jq '.stop_hook_active = true' <<<"${nosess_claim}")"
expect_gate "no session id: warn when already continuing" warning

# State directory not writable: treated as work done; stop_hook_active decides.
reset_state
touch "${work}/blocker"
OUT=$(printf '%s' "${claim}" | env CLAUDE_PLUGIN_DATA="${work}/blocker" "${run_bash}" "${gate}" stop)
RC=$?
expect_gate "unwritable state dir still nudges" context

# An escaped "session_id" inside tool_input must not be mistaken for the key.
reset_state
run_gate mark '{"session_id":"real-1","tool_name":"Write","tool_input":{"content":"{\"session_id\":\"fake-9\"}"}}'
if [[ -e "${work}/data/sessions/real-1.work" && ! -e "${work}/data/sessions/fake-9.work" ]]; then ok; else bad "session id taken from tool_input"; fi

# Path traversal in session_id is neutralized.
reset_state
run_gate mark '{"session_id":"../../escape","tool_name":"Edit"}'
if [[ -e "${work}/escape.work" || -e "${work}/data/escape.work" ]]; then bad "session id escaped the state dir"; else ok; fi

# Old state is pruned.
reset_state
mark sess-old
touch -t 202001010000 "${work}/data/sessions/sess-old.work"
run_gate stop "$(payload "Hello." false sess-new)"
if [[ ! -e "${work}/data/sessions/sess-old.work" ]]; then ok; else bad "stale state not pruned"; fi

# Without jq: fail open, tell the user once per session.
nojq="${work}/nojq-bin"
mkdir -p "${nojq}"
for tool in cat tr find rm mkdir id dirname env; do
  src=$(command -v "${tool}") && ln -s "${src}" "${nojq}/${tool}"
done
reset_state
bash_abs=$(command -v "${run_bash}")
OUT=$(printf '%s' "${claim}" | env PATH="${nojq}" CLAUDE_PLUGIN_DATA="${work}/data" "${bash_abs}" "${gate}" stop)
RC=$?
expect_gate "missing jq warns" warning
if [[ ${OUT} == *"jq was not found"* ]]; then ok; else bad "missing-jq message" "${OUT}"; fi
OUT=$(printf '%s' "${claim}" | env PATH="${nojq}" CLAUDE_PLUGIN_DATA="${work}/data" "${bash_abs}" "${gate}" stop)
RC=$?
expect_gate "missing jq warns only once" none
OUT=$(printf '%s' '{"session_id":"sess-1","tool_name":"Edit"}' | env PATH="${nojq}" CLAUDE_PLUGIN_DATA="${work}/data" "${bash_abs}" "${gate}" mark)
RC=$?
expect_gate "mark works without jq" none

run_gate bogus "{}" 2>/dev/null
expect_gate "unknown subcommand exits 0 silently on stdout" none

# ----------------------------------------------------- hooks.json ---

# Shell form with the quoted placeholder: exec form (`args`) needs Claude Code
# 2.1.139+, and an older version would run a bare `bash` that reads the hook
# payload, Claude's reply included, from stdin as a script.
if jq -e '[.hooks[][].hooks[]] | length == 2 and all(has("args") | not) and all(.command | test("^bash \"\\$\\{CLAUDE_PLUGIN_ROOT\\}/scripts/gate\\.sh\" (mark|stop)$"))' "${hooks_json}" >/dev/null &&
  jq -e '.hooks.Stop[0].hooks[0].command | endswith(" stop")' "${hooks_json}" >/dev/null; then ok; else bad "hooks.json wiring"; fi

if command -v node >/dev/null 2>&1; then
  matcher=$(jq -r '.hooks.PostToolUse[0].matcher' "${hooks_json}")
  verdicts=$(node -e '
    const re = new RegExp(process.argv[1]);
    const marks = ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Agent", "mcp__github__create_pull_request", "ReadMcpResourceToolX"];
    const skips = ["Read", "Glob", "Grep", "WebFetch", "WebSearch", "TodoWrite", "Skill", "ToolSearch", "AskUserQuestion", "TaskList"];
    const wrong = [...marks.filter((t) => !re.test(t)), ...skips.filter((t) => re.test(t))];
    process.stdout.write(wrong.join(","));
  ' "${matcher}")
  if [[ -z ${verdicts} ]]; then ok; else bad "PostToolUse matcher misclassifies: ${verdicts}"; fi
fi

# ---------------------------------------------------------- timing ---
# The hook timeout is 10 s and a timed-out Stop hook just lets the turn end, so
# the budget here is 3 s for 250 KB replies built to be as slow as possible.

timed_stop() { # label line-format expected-kind
  local big start elapsed
  reset_state
  mark
  big=$(awk -v f="$2" 'BEGIN { for (i = 0; i < 6000; i++) printf f "\n", i }')
  local input
  input=$(payload "${big}")
  # Guard against a vacuous pass: the payload must really carry the long reply.
  if [[ ${#input} -gt ${#big} ]]; then ok; else bad "$1: payload was not built (${#input} bytes for a ${#big}-byte reply)"; fi
  start=$(date +%s)
  run_gate stop "${input}"
  elapsed=$(($(date +%s) - start))
  expect_gate "$1" "$3"
  if [[ ${elapsed} -le 3 ]]; then ok; else bad "$1 took ${elapsed}s"; fi
}

timed_stop "long reply, no claims" "Line %d of a long report about the parser." none
timed_stop "long reply, a claim on every line" "Step %d is done and the tests are green." context
timed_stop "long reply, near-miss claims on every line" "Step %d is not done; is it ready to merge?" none

reset_state
mark
prose=$(awk 'BEGIN { for (i = 0; i < 250; i++) printf "Paragraph %d about the parser.\n", i }')
run_gate stop "$(payload "${prose}
All tests pass.")"
expect_gate "claim at the end of a long reply" context

printf '%d passed, %d failed\n' "${pass}" "${fail}"
[[ ${fail} -eq 0 ]]
