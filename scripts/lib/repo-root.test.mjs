// @ts-check
// Exercises .claude/hooks/lib/repo-root.sh, which decides whether a hook acts on
// the tree Claude is working in or on the checkout the session started from.
// The two diverge inside a git worktree, and picking the wrong one makes a gate
// inspect a tree nobody is changing.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, realpathSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

// `rootDir` carries a trailing slash; the library prints `pwd -P`, which does not.
const repo = realpathSync(rootDir);
const lib = join(repo, ".claude", "hooks", "lib", "repo-root.sh");

/**
 * Calls one function from the library under bash and returns what it printed.
 * @param {string} fn
 * @param {Record<string, unknown> | null} payload
 * @param {{ projectDir?: string, cwd?: string }} [opts]
 * @returns {string}
 */
function call(fn, payload, opts = {}) {
  const env = { ...process.env };
  if (opts.projectDir === undefined) delete env["CLAUDE_PROJECT_DIR"];
  else env["CLAUDE_PROJECT_DIR"] = opts.projectDir;
  const result = spawnSync(
    "bash",
    ["-c", `source "$1"; ${fn} "$2"`, "bash", lib, payload === null ? "" : JSON.stringify(payload)],
    { encoding: "utf8", env, cwd: opts.cwd ?? repo },
  );
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

test("session_tree follows the hook input's cwd into a worktree", () => {
  const worktree = mkdtempSync(join(tmpdir(), "repo-root-wt-"));
  try {
    assert.equal(
      call("session_tree", { cwd: worktree }, { projectDir: repo }),
      realpathSync(worktree),
      "a gate must read the tree holding the changes, not the session's project directory",
    );
  } finally {
    rmSync(worktree, { recursive: true, force: true });
  }
});

test("session_tree falls back to CLAUDE_PROJECT_DIR when the payload carries no cwd", () => {
  assert.equal(call("session_tree", { tool_name: "Bash" }, { projectDir: repo }), repo);
  assert.equal(call("session_tree", null, { projectDir: repo }), repo);
});

test("project_dir keeps CLAUDE_PROJECT_DIR even when cwd points elsewhere", () => {
  const worktree = mkdtempSync(join(tmpdir(), "repo-root-wt-"));
  try {
    assert.equal(
      call("project_dir", { cwd: worktree }, { projectDir: repo }),
      repo,
      "project state must outlive a worktree that is removed when its agent finishes",
    );
  } finally {
    rmSync(worktree, { recursive: true, force: true });
  }
});

test("project_dir uses the payload's cwd when CLAUDE_PROJECT_DIR is unset", () => {
  const dir = mkdtempSync(join(tmpdir(), "repo-root-wt-"));
  try {
    assert.equal(call("project_dir", { cwd: dir }), realpathSync(dir));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an unusable directory falls back to the current one instead of failing", () => {
  const gone = join(tmpdir(), "repo-root-does-not-exist-9f3a1c");
  assert.equal(call("session_tree", { cwd: gone }, { projectDir: repo, cwd: repo }), repo);
  assert.equal(call("project_dir", null, { cwd: repo }), repo);
});
