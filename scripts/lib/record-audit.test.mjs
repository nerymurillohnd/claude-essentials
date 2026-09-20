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

/**
 * A throwaway Git repository with one commit, so the hook's clean-tree guard
 * sees the same shape a real project does.
 * @returns {string}
 */
function makeProject() {
  const dir = mkdtempSync(join(tmpdir(), "record-audit-"));
  const git = (/** @type {string[]} */ args) => {
    const result = spawnSync("git", ["-C", dir, ...args], { encoding: "utf8" });
    assert.equal(result.status, 0, `git ${args.join(" ")}: ${result.stderr}`);
  };
  git(["init", "--quiet", "--initial-branch=main"]);
  git(["config", "user.email", "test@example.invalid"]);
  git(["config", "user.name", "Test"]);
  writeFileSync(join(dir, "seed.txt"), "seed\n");
  git(["add", "seed.txt"]);
  git(["commit", "--quiet", "-m", "seed"]);
  return dir;
}

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

/** @param {string} dir @param {string} sha40 */
const recordPath = (dir, sha40) => join(dir, ".claude/state/audits", `${sha40}.json`);

test("records the auditor's verdict for the head it reports", () => {
  const dir = makeProject();
  try {
    const out = run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: `| G1 | PASS | ok |\nHEAD: ${sha}\nVERDICT: PASS\n`,
    });
    const record = JSON.parse(readFileSync(recordPath(dir, sha), "utf8"));
    assert.deepEqual(record, { head: sha, verdict: "PASS" });
    assert.match(out, /PASS recorded/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("falls back to the subagent transcript when the final message lacks the verdict", () => {
  const dir = makeProject();
  try {
    const transcript = join(dir, "agent.jsonl");
    const line = {
      type: "assistant",
      message: { content: [{ type: "text", text: `HEAD: ${sha}\nVERDICT: FAIL` }] },
    };
    writeFileSync(transcript, `${JSON.stringify(line)}\n`);
    // The transcript lives outside the work tree as far as the guard is
    // concerned, so keep the tree clean by ignoring it.
    writeFileSync(join(dir, ".gitignore"), "agent.jsonl\n.claude/\n");
    spawnSync("git", ["-C", dir, "add", ".gitignore"], { encoding: "utf8" });
    spawnSync("git", ["-C", dir, "commit", "--quiet", "-m", "ignore"], { encoding: "utf8" });
    run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: "",
      agent_transcript_path: transcript,
    });
    const record = JSON.parse(readFileSync(recordPath(dir, sha), "utf8"));
    assert.equal(record.verdict, "FAIL");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("reads a SubagentHandback payload, which last_assistant_message does not carry", () => {
  const dir = makeProject();
  try {
    const transcript = join(dir, "agent.jsonl");
    const line = {
      type: "assistant",
      message: {
        content: [
          {
            type: "tool_use",
            name: "SubagentHandback",
            input: { message: `| G1 | PASS |\nHEAD: ${sha}\nVERDICT: PASS` },
          },
        ],
      },
    };
    writeFileSync(transcript, `${JSON.stringify(line)}\n`);
    writeFileSync(join(dir, ".gitignore"), "agent.jsonl\n.claude/\n");
    spawnSync("git", ["-C", dir, "add", ".gitignore"], { encoding: "utf8" });
    spawnSync("git", ["-C", dir, "commit", "--quiet", "-m", "ignore"], { encoding: "utf8" });
    run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: "Done — the full report is above.",
      agent_transcript_path: transcript,
    });
    const record = JSON.parse(readFileSync(recordPath(dir, sha), "utf8"));
    assert.deepEqual(record, { head: sha, verdict: "PASS" });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("records nothing while the working tree is dirty", () => {
  const dir = makeProject();
  try {
    writeFileSync(join(dir, "seed.txt"), "edited, not committed\n");
    const out = run(dir, {
      agent_type: "repo-auditor",
      last_assistant_message: `HEAD: ${sha}\nVERDICT: PASS`,
    });
    assert.match(out, /uncommitted changes/);
    assert.equal(existsSync(recordPath(dir, sha)), false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("checks the worktree Claude is in, not the checkout the session started from", () => {
  const dir = makeProject();
  const worktree = join(dir, "wt");
  const git = (/** @type {string[]} */ args) =>
    spawnSync("git", ["-C", dir, ...args], { encoding: "utf8" });
  try {
    git(["worktree", "add", "--quiet", worktree, "-b", "wt"]);
    // The worktree carries uncommitted work; the main checkout is clean. Before
    // the hook read `cwd`, it checked the clean tree and filed a record anyway.
    writeFileSync(join(worktree, "seed.txt"), "edited in the worktree\n");
    assert.notEqual(
      spawnSync("git", ["-C", worktree, "status", "--porcelain"], { encoding: "utf8" }).stdout,
      "",
      "the worktree must be dirty for this test to mean anything",
    );
    const out = run(dir, {
      agent_type: "repo-auditor",
      cwd: worktree,
      last_assistant_message: `HEAD: ${sha}\nVERDICT: PASS`,
    });
    assert.match(out, /uncommitted changes/);
    assert.equal(existsSync(recordPath(dir, sha)), false);
  } finally {
    spawnSync("git", ["-C", dir, "worktree", "remove", "--force", worktree], { encoding: "utf8" });
    rmSync(dir, { recursive: true, force: true });
  }
});

test("records nothing for other agents or a report without HEAD and VERDICT lines", () => {
  const dir = makeProject();
  try {
    run(dir, { agent_type: "Explore", last_assistant_message: `HEAD: ${sha}\nVERDICT: PASS` });
    assert.equal(existsSync(join(dir, ".claude/state/audits")), false);
    const out = run(dir, { agent_type: "repo-auditor", last_assistant_message: "VERDICT: PASS" });
    assert.match(out, /no audit was recorded/);
    assert.equal(existsSync(recordPath(dir, sha)), false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
