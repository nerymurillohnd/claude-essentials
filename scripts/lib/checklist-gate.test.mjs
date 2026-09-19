// @ts-check
// Exercises .claude/hooks/lib/checklist.sh and the Stop hook .claude/hooks/checklist-gate.sh
// that maintenance skills use to refuse ending a turn with an incomplete checklist.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

const helper = join(rootDir, ".claude", "hooks", "lib", "checklist.sh");
const gate = join(rootDir, ".claude", "hooks", "checklist-gate.sh");

/** @param {string} project @param {string[]} args */
function checklist(project, ...args) {
  const result = spawnSync(helper, args, {
    encoding: "utf8",
    env: { ...process.env, CLAUDE_PROJECT_DIR: project },
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

/** @param {string} project @param {string} session */
function stop(project, session) {
  const result = spawnSync(gate, [], {
    encoding: "utf8",
    input: JSON.stringify({ hook_event_name: "Stop", session_id: session }),
    env: { ...process.env, CLAUDE_PROJECT_DIR: project },
  });
  return { status: result.status, stderr: result.stderr };
}

/** @param {string} verify */
function project(verify) {
  const dir = mkdtempSync(join(tmpdir(), "checklist-gate-"));
  const template = join(dir, "checklist.json");
  writeFileSync(
    template,
    JSON.stringify({
      skill: "demo-skill",
      items: [
        { id: "a", text: "First step" },
        { id: "b", text: "Verified step", verify },
      ],
    }),
  );
  checklist(dir, "start", template, "demo-plugin", "session-1");
  return dir;
}

/** @param {string} dir */
function state(dir) {
  return JSON.parse(
    readFileSync(
      join(dir, ".claude", "state", "checklists", "demo-skill--demo-plugin.json"),
      "utf8",
    ),
  );
}

test("without an active checklist the gate lets the turn end", () => {
  const dir = mkdtempSync(join(tmpdir(), "checklist-gate-"));
  assert.equal(stop(dir, "session-1").status, 0);
  rmSync(dir, { recursive: true });
});

test("open items block the stop and are listed; another session is never blocked", () => {
  const dir = project("true");
  const blocked = stop(dir, "session-1");
  assert.equal(blocked.status, 2);
  assert.match(blocked.stderr, /- a: First step/);
  assert.match(blocked.stderr, /- b: Verified step/);
  assert.equal(stop(dir, "session-2").status, 0);
  rmSync(dir, { recursive: true });
});

test("a failing verify command reopens its item and blocks", () => {
  const dir = project("echo broken floor; exit 1");
  checklist(dir, "check", "a", "done");
  checklist(dir, "check", "b", "claimed green");
  const blocked = stop(dir, "session-1");
  assert.equal(blocked.status, 2);
  assert.match(blocked.stderr, /b: `echo broken floor; exit 1` failed/);
  assert.equal(state(dir).items[1].state, "open");
  rmSync(dir, { recursive: true });
});

test("a complete, verified checklist lets the turn end and is closed", () => {
  const dir = project("true");
  checklist(dir, "check", "a", "done");
  checklist(dir, "check", "b", "verified");
  assert.equal(stop(dir, "session-1").status, 0);
  assert.equal(state(dir).status, "complete");
  assert.ok(!existsSync(join(dir, ".claude", "state", "checklists", ".active")));
  rmSync(dir, { recursive: true });
});

test("an item waiting on the user lets the turn end so they can answer", () => {
  const dir = project("true");
  checklist(dir, "check", "a", "done");
  checklist(dir, "needs-user", "b", "Approve the 0.1.1 bump?");
  assert.equal(stop(dir, "session-1").status, 0);
  assert.equal(state(dir).status, "in_progress");
  assert.match(checklist(dir, "status"), /\[\?\] b: Verified step — Approve the 0\.1\.1 bump\?/);
  rmSync(dir, { recursive: true });
});

test("verify commands come from the committed template, not the editable state", () => {
  const dir = project("echo still broken; exit 1");
  const statePath = join(dir, ".claude", "state", "checklists", "demo-skill--demo-plugin.json");
  const weakened = state(dir);
  weakened.items[1].verify = "true";
  writeFileSync(statePath, JSON.stringify(weakened));
  checklist(dir, "check", "a", "done");
  checklist(dir, "check", "b", "claimed green");
  assert.equal(stop(dir, "session-1").status, 2);
  rmSync(dir, { recursive: true });
});
