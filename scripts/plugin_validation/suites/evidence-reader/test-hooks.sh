#!/usr/bin/env bash
# Behavioral tests for evidence-reader's report gate (scripts/gate.sh). Runs the
# handler under $BNV_TEST_BASH (set by the repo's `make test-slow` to each bash
# it finds, /bin/bash 3.2 included), else `bash`. It lives in the repository,
# not in the plugin: a plugin ships only what users run.

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plugin="${here}/../../../../plugins/evidence-reader"
gate="${plugin}/scripts/gate.sh"
run_bash=${BNV_TEST_BASH:-bash}
case "${run_bash}" in
/*) ;;
*) run_bash=$(command -v "${run_bash}" || printf '%s' "${run_bash}") ;;
esac
tmp=$(mktemp -d)
trap 'rm -rf "${tmp}"' EXIT
export CLAUDE_PLUGIN_DATA="${tmp}/data"

ok=0
bad=0
pass() {
  ok=$((ok + 1))
  printf 'ok   %s\n' "$1"
}
flunk() {
  bad=$((bad + 1))
  printf 'FAIL %s\n     %s\n' "$1" "$2"
}

complete_report=$(
  cat <<'REPORT'
# Evidence report

**Status:** COMPLETE — read long-report.pdf fully.

**Tier:** TIERS python3=ok poppler=ok exiftool=ok imagemagick=ok heic=sips jq=ok

## Files reviewed

| File | Status | Coverage |
| --- | --- | --- |
| long-report.pdf | fully reviewed | pages 1-20, 21-40, 41-45 of 45 |

## Findings

1. Lot LOT-045 moisture is 4.5%. — `long-report.pdf p45 L2`

## Not verified

- None

## Needs human judgment

- None
REPORT
)

# stop_payload <agent_id> <agent_type> <message> — a realistic SubagentStop payload.
stop_payload() {
  jq -n --arg id "$1" --arg type "$2" --arg msg "$3" '{
    session_id: "s-1", transcript_path: "/tmp/t.jsonl", cwd: "/tmp",
    permission_mode: "default", hook_event_name: "SubagentStop", stop_hook_active: false,
    agent_id: $id, agent_type: $type, agent_transcript_path: "/tmp/sub.jsonl",
    last_assistant_message: $msg, background_tasks: [], session_crons: []}'
}

# run_gate <mode> <payload-file> [env assignments...] — stdout of the hook; sets rc.
run_gate() {
  mode=$1
  file=$2
  shift 2
  out=$(env "$@" "${run_bash}" "${gate}" "${mode}" <"${file}" 2>&1)
  rc=$?
}

# 1. A complete report passes silently.
stop_payload a1 evidence-reader:document-reader "${complete_report}" >"${tmp}/p1.json"
if [ -s "${tmp}/p1.json" ]; then pass "payload built"; else flunk "payload built" "jq produced nothing"; fi
run_gate stop "${tmp}/p1.json"
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "complete report passes"; else flunk "complete report passes" "rc=${rc} out=${out}"; fi

# 2. An incomplete report is blocked, names what is missing, then capped.
stop_payload a2 evidence-reader:tabular-auditor "Total is 97.5." >"${tmp}/p2.json"
run_gate stop "${tmp}/p2.json"
decision=$(printf '%s' "${out}" | jq -r '.decision // empty' 2>/dev/null)
reason=$(printf '%s' "${out}" | jq -r '.reason // empty' 2>/dev/null)
if [ "${decision}" = block ] && printf '%s' "${reason}" | grep -Fq '## Files reviewed'; then
  pass "incomplete report blocked with missing sections"
else
  flunk "incomplete report blocked with missing sections" "out=${out}"
fi
run_gate stop "${tmp}/p2.json"
decision=$(printf '%s' "${out}" | jq -r '.decision // empty' 2>/dev/null)
if [ "${decision}" = block ]; then pass "second retry still blocks"; else flunk "second retry still blocks" "out=${out}"; fi
run_gate stop "${tmp}/p2.json"
message=$(printf '%s' "${out}" | jq -r '.systemMessage // empty' 2>/dev/null)
if printf '%s' "${message}" | grep -Fq 'still INCOMPLETE after 2 retries'; then
  pass "retry cap lets the agent stop, flagged"
else
  flunk "retry cap lets the agent stop, flagged" "out=${out}"
fi
if [ ! -e "${CLAUDE_PLUGIN_DATA}/evidence-reader-gate/a2.retries" ]; then
  pass "retry state cleaned after cap"
else
  flunk "retry state cleaned after cap" "state file left behind"
fi

# 2b. Section names quoted mid-sentence do not satisfy the gate (regression from a live run).
quoted='The report needs **Status:** **Tier:** ## Files reviewed ## Findings ## Not verified ## Needs human judgment, all on one line.'
stop_payload a2b evidence-reader:document-reader "${quoted}" >"${tmp}/p2b.json"
run_gate stop "${tmp}/p2b.json"
if printf '%s' "${out}" | jq -e '.decision == "block"' >/dev/null 2>&1; then
  pass "quoted section names do not pass"
else
  flunk "quoted section names do not pass" "out=${out}"
fi
indented=$(printf '%s\n' "${complete_report}" | sed 's/^/  /')
stop_payload a2c evidence-reader:document-reader "${indented}" >"${tmp}/p2c.json"
run_gate stop "${tmp}/p2c.json"
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "indented report still passes"; else flunk "indented report still passes" "out=${out}"; fi

# 3. warn mode never blocks.
run_gate stop "${tmp}/p2.json" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=warn
if printf '%s' "${out}" | jq -e '.systemMessage and (has("decision") | not)' >/dev/null 2>&1; then
  pass "warn mode warns without blocking"
else
  flunk "warn mode warns without blocking" "out=${out}"
fi

# 4. off mode does nothing.
run_gate stop "${tmp}/p2.json" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=off
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "off mode is silent"; else flunk "off mode is silent" "out=${out}"; fi

# 5. Malformed input fails open.
printf 'not json at all' >"${tmp}/bad.json"
run_gate stop "${tmp}/bad.json"
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "malformed payload fails open"; else flunk "malformed payload fails open" "rc=${rc} out=${out}"; fi
: >"${tmp}/empty.json"
run_gate stop "${tmp}/empty.json"
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "empty payload fails open"; else flunk "empty payload fails open" "rc=${rc} out=${out}"; fi

# 6. Missing jq fails open with a notice (PATH without jq, keeping core utilities).
mkdir -p "${tmp}/nojq"
for tool in cat tr printf grep mkdir rm head; do
  path=$(command -v "${tool}" 2>/dev/null || true)
  case "${path}" in /*) ln -s "${path}" "${tmp}/nojq/${tool}" ;; *) ;; esac
done
run_gate stop "${tmp}/p2.json" PATH="${tmp}/nojq"
if [ "${rc}" -eq 0 ] && printf '%s' "${out}" | grep -Fq 'jq is not installed'; then
  pass "missing jq fails open with a notice"
else
  flunk "missing jq fails open with a notice" "rc=${rc} out=${out}"
fi

# 7. A report handed back through SubagentHandback is the one checked.
jq -n --arg msg "${complete_report}" '{hook_event_name: "PreToolUse", tool_name: "SubagentHandback",
  agent_id: "a7", agent_type: "evidence-reader:image-inspector", tool_input: {message: $msg}}' >"${tmp}/h7.json"
run_gate handback "${tmp}/h7.json"
stop_payload a7 evidence-reader:image-inspector "Done." >"${tmp}/p7.json"
run_gate stop "${tmp}/p7.json"
if [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then pass "handback report is checked instead of closing text"; else flunk "handback report is checked instead of closing text" "out=${out}"; fi

# 8. Another plugin's agent handing back is never stored.
jq -n '{hook_event_name: "PreToolUse", tool_name: "SubagentHandback", agent_id: "x8",
  agent_type: "other-plugin:worker", tool_input: {message: "secret report"}}' >"${tmp}/h8.json"
run_gate handback "${tmp}/h8.json"
if [ ! -e "${CLAUDE_PLUGIN_DATA}/evidence-reader-gate/x8.handback" ]; then
  pass "foreign agent handback not stored"
else
  flunk "foreign agent handback not stored" "state written for a foreign agent"
fi

# 9. Large adversarial report (about 1 MB) stays fast. The report goes to jq through a file:
# Linux caps one argument at 128 KB, so --arg would leave an empty payload on CI.
head -c 1000000 /dev/zero | tr '\0' 'x' >"${tmp}/big.txt"
jq -n --rawfile msg "${tmp}/big.txt" '{session_id: "s-1", transcript_path: "/tmp/t.jsonl",
  cwd: "/tmp", hook_event_name: "SubagentStop", stop_hook_active: false, agent_id: "a9",
  agent_type: "evidence-reader:document-reader", last_assistant_message: $msg}' >"${tmp}/p9.json"
p9_bytes=$(wc -c <"${tmp}/p9.json")
if [ "${p9_bytes}" -gt 1000000 ]; then pass "1 MB payload built"; else flunk "1 MB payload built" "payload too small"; fi
start=$(date +%s)
run_gate stop "${tmp}/p9.json"
elapsed=$(($(date +%s) - start))
if [ "${elapsed}" -le 5 ] && printf '%s' "${out}" | jq -e '.decision == "block"' >/dev/null 2>&1; then
  pass "1 MB report handled in ${elapsed}s"
else
  flunk "1 MB report handled quickly" "elapsed=${elapsed}s out=$(printf '%s' "${out}" | head -c 200 || true)"
fi

# 10. A blocked handback is spent: the next stop checks the new final message, not the old copy.
jq -n --arg msg "Partial notes only." '{hook_event_name: "PreToolUse", tool_name: "SubagentHandback",
  agent_id: "a10", agent_type: "evidence-reader:document-reader", tool_input: {message: $msg}}' >"${tmp}/h10.json"
run_gate handback "${tmp}/h10.json"
stop_payload a10 evidence-reader:document-reader "Partial notes only." >"${tmp}/p10a.json"
run_gate stop "${tmp}/p10a.json"
first=${out}
stop_payload a10 evidence-reader:document-reader "${complete_report}" >"${tmp}/p10b.json"
run_gate stop "${tmp}/p10b.json"
if printf '%s' "${first}" | jq -e '.decision == "block"' >/dev/null 2>&1 && [ "${rc}" -eq 0 ] && [ -z "${out}" ]; then
  pass "fixed report passes after a blocked handback"
else
  flunk "fixed report passes after a blocked handback" "first=${first} then=${out}"
fi

# 11. With no retry state (no agent_id), a repeat stop fails open instead of blocking forever.
jq -n '{hook_event_name: "SubagentStop", stop_hook_active: true, agent_id: "",
  agent_type: "evidence-reader:tabular-auditor", last_assistant_message: "no sections"}' >"${tmp}/p11.json"
run_gate stop "${tmp}/p11.json"
if [ "${rc}" -eq 0 ] && printf '%s' "${out}" | jq -e '(.decision // "") != "block" and (.systemMessage | test("cannot track retries"))' >/dev/null 2>&1; then
  pass "untracked repeat stop fails open"
else
  flunk "untracked repeat stop fails open" "out=${out}"
fi

# 12. Same, when the agent has an id but no state directory can be trusted or created.
jq -n '{hook_event_name: "SubagentStop", stop_hook_active: true, agent_id: "a12",
  agent_type: "evidence-reader:image-inspector", last_assistant_message: "no sections"}' >"${tmp}/p12.json"
run_gate stop "${tmp}/p12.json" CLAUDE_PLUGIN_DATA=/dev/null
if [ "${rc}" -eq 0 ] && printf '%s' "${out}" | jq -e '(.decision // "") != "block" and (.systemMessage | test("cannot track retries"))' >/dev/null 2>&1; then
  pass "repeat stop without a state directory fails open"
else
  flunk "repeat stop without a state directory fails open" "out=${out}"
fi

# 13. A warning built from hostile text is still valid JSON.
jq -n '{hook_event_name: "SubagentStop", stop_hook_active: false, agent_id: "a13",
  agent_type: "evil\u0001\"x\\y", last_assistant_message: "no sections"}' >"${tmp}/p13.json"
run_gate stop "${tmp}/p13.json" CLAUDE_PLUGIN_OPTION_ENFORCEMENT=warn
if printf '%s' "${out}" | jq -e '.systemMessage | test("INCOMPLETE")' >/dev/null 2>&1; then
  pass "warning with control characters is valid JSON"
else
  flunk "warning with control characters is valid JSON" "out=${out}"
fi

printf '\n%d passed, %d failed (hook shell: %s)\n' "${ok}" "${bad}" "${run_bash}"
[ "${bad}" -eq 0 ]
