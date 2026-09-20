// @ts-check
// Exercises .claude/hooks/record-audit.sh, the SubagentStop hook that records the
// repo-auditor's verdict per audited head for /pr-delivery's audit item.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

const hook = join(rootDir, ".claude", "hooks", "record-audit.sh");
const sha = "a".repeat(40);

/** @param {string} project @param {Record<string, unknown>} payload */
function run(project, payload) {
  const result = spawnSync(hook, [], {
    encoding: "utf8",
    input: JSON.stringify({ hook_event_name: "SubagentStop", ...payload }),
    env: { ...process.env, CLAUDE_PROJECT_DIR: project },
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

test("records the auditor's verdict for the head it reports", () => {
  const dir = mkdtempSync(join(tmpdir(), "record-audit-"));
  try {
    const out = run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: `| G1 | PASS | ok |\nHEAD: ${sha}\nVERDICT: PASS\n`,
    });
    const record = JSON.parse(
      readFileSync(join(dir, ".claude/state/audits", `${sha}.json`), "utf8"),
    );
    assert.deepEqual(record, { head: sha, verdict: "PASS" });
    assert.match(out, /PASS recorded/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("falls back to the subagent transcript when the final message lacks the verdict", () => {
  const dir = mkdtempSync(join(tmpdir(), "record-audit-"));
  try {
    const transcript = join(dir, "agent.jsonl");
    const line = {
      type: "assistant",
      message: { content: [{ type: "text", text: `HEAD: ${sha}\nVERDICT: FAIL` }] },
    };
    writeFileSync(transcript, `${JSON.stringify(line)}\n`);
    run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: "",
      agent_transcript_path: transcript,
    });
    const record = JSON.parse(
      readFileSync(join(dir, ".claude/state/audits", `${sha}.json`), "utf8"),
    );
    assert.equal(record.verdict, "FAIL");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("records nothing for other agents or a report without HEAD and VERDICT lines", () => {
  const dir = mkdtempSync(join(tmpdir(), "record-audit-"));
  try {
    run(dir, { agent_type: "Explore", last_assistant_message: `HEAD: ${sha}\nVERDICT: PASS` });
    assert.equal(existsSync(join(dir, ".claude/state/audits")), false);
    const out = run(dir, { agent_type: "repo-auditor", last_assistant_message: "VERDICT: PASS" });
    assert.match(out, /no audit was recorded/);
    assert.equal(existsSync(join(dir, ".claude/state/audits", `${sha}.json`)), false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
