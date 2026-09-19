// @ts-check
// Exercises .claude/hooks/guard-push.sh against a throwaway clone of
// a local bare "origin": pushing a published branch the remote no longer has is
// denied; new branches, existing branches, deletions, and non-push commands pass.
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { rootDir } from "./plugins.mjs";

const guard = join(rootDir, ".claude", "hooks", "guard-push.sh");

/** @type {string} */
let base = "";
/** @type {string} */
let clone = "";

/** @param {string} cwd @param {string[]} args */
function git(cwd, ...args) {
  return execFileSync("git", args, {
    cwd,
    encoding: "utf8",
    stdio: "pipe",
    env: {
      ...process.env,
      GIT_AUTHOR_NAME: "t",
      GIT_AUTHOR_EMAIL: "t@example.com",
      GIT_COMMITTER_NAME: "t",
      GIT_COMMITTER_EMAIL: "t@example.com",
    },
  });
}

const passingGate = {
  GUARD_PUSH_VERSIONS_CMD: 'echo "Computed label: bump: none"',
  GUARD_PUSH_CHECK_CMD: "true",
};

/**
 * @param {string} command
 * @param {string} [shell]
 * @param {Record<string, string>} [gate]
 */
function run(command, shell = "bash", gate = passingGate) {
  const result = spawnSync(shell, [guard], {
    encoding: "utf8",
    input: JSON.stringify({ tool_name: "Bash", tool_input: { command }, cwd: clone }),
    env: { ...process.env, CLAUDE_PROJECT_DIR: clone, ...gate },
  });
  assert.equal(result.status, 0, result.stderr);
  if (result.stdout.trim() === "") return { decision: "allow", reason: "" };
  const output = JSON.parse(result.stdout).hookSpecificOutput;
  return { decision: output.permissionDecision, reason: output.permissionDecisionReason };
}

/** @param {string} command @param {string} [shell] */
function decide(command, shell = "bash") {
  return run(command, shell).decision;
}

before(() => {
  base = mkdtempSync(join(tmpdir(), "push-guard-"));
  const origin = join(base, "origin.git");
  clone = join(base, "clone");
  git(base, "init", "--quiet", "--bare", "--initial-branch=main", origin);
  git(base, "clone", "--quiet", origin, clone);
  git(clone, "commit", "--quiet", "--allow-empty", "-m", "init");
  git(clone, "push", "--quiet", "origin", "main");
  // A branch that was published and then deleted on the remote, as GitHub does after a merge.
  git(clone, "switch", "--quiet", "-c", "feat/merged");
  git(clone, "commit", "--quiet", "--allow-empty", "-m", "work");
  git(clone, "push", "--quiet", "-u", "origin", "feat/merged");
  git(origin, "update-ref", "-d", "refs/heads/feat/merged");
  // A published branch that still exists, and a local branch never pushed.
  git(clone, "switch", "--quiet", "-c", "feat/open", "main");
  git(clone, "push", "--quiet", "-u", "origin", "feat/open");
  git(clone, "switch", "--quiet", "-c", "feat/new", "main");
  git(clone, "switch", "--quiet", "feat/merged");
});

after(() => rmSync(base, { recursive: true, force: true }));

test("pushing a published branch the remote deleted is denied, in every spelling", () => {
  for (const command of [
    "git push",
    "git push origin",
    "git push origin feat/merged",
    "git push origin HEAD",
    "git push -u origin HEAD:feat/merged",
    "git push --force-with-lease origin +feat/merged",
    "npm run check && git push",
    "git -C . push origin feat/merged",
  ]) {
    assert.equal(decide(command), "deny", command);
  }
});

test("new branches, live branches, deletions, tags, and other commands pass", () => {
  for (const command of [
    "git push -u origin feat/new",
    "git push origin feat/open",
    "git push origin --delete feat/merged",
    "git push origin :feat/merged",
    "git push origin refs/tags/v1",
    "git push --tags",
    "git status && git log --oneline -1",
    "echo push",
  ]) {
    assert.equal(decide(command), "allow", command);
  }
});

test("the guard gives the same answers under /bin/bash", () => {
  assert.equal(decide("git push", "/bin/bash"), "deny");
  assert.equal(decide("git push -u origin feat/new", "/bin/bash"), "allow");
});

test("an unreachable remote fails open", () => {
  git(clone, "remote", "set-url", "origin", join(base, "missing.git"));
  try {
    assert.equal(decide("git push"), "allow");
  } finally {
    git(clone, "remote", "set-url", "origin", join(base, "origin.git"));
  }
});

test("a direct push to main passes when the tree is clean, the change is non-runtime, and check passes", () => {
  assert.equal(run("git push origin main").decision, "allow");
  assert.equal(run("git push origin feat/merged:main").decision, "allow");
});

test("a direct push to main with plugin runtime changes is sent to a pull request", () => {
  const result = run("git push origin main", "bash", {
    ...passingGate,
    GUARD_PUSH_VERSIONS_CMD: 'echo "Computed label: bump: patch"',
  });
  assert.equal(result.decision, "deny");
  assert.match(result.reason, /plugin runtime files \(bump: patch\).*pull request/s);
});

test("a direct push to main is denied when version rules or npm run check fail", () => {
  const versions = run("git push origin main", "bash", {
    ...passingGate,
    GUARD_PUSH_VERSIONS_CMD: "echo 'block-no-verify: runtime change without bump'; exit 1",
  });
  assert.equal(versions.decision, "deny");
  assert.match(versions.reason, /version rules fail.*runtime change without bump/s);
  const check = run("git push origin main", "/bin/bash", {
    ...passingGate,
    GUARD_PUSH_CHECK_CMD: "echo 'biome: 1 error'; exit 1",
  });
  assert.equal(check.decision, "deny");
  assert.match(check.reason, /npm run check fails.*biome: 1 error/s);
});

test("a direct push to main is denied while the tree has uncommitted changes", () => {
  writeFileSync(join(clone, "dirty.txt"), "x");
  try {
    const result = run("git push origin main");
    assert.equal(result.decision, "deny");
    assert.match(result.reason, /uncommitted changes/);
  } finally {
    rmSync(join(clone, "dirty.txt"));
  }
});
