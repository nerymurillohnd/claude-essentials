// @ts-check
// Plugin workflow scripts (plugins/*/workflows/*.js) are written in the dynamic
// workflow dialect: a pure-literal `export const meta`, then a body with a
// top-level `return` and runtime globals (agent, parallel, pipeline, phase, log,
// args, budget, workflow). Biome can't parse that dialect, so biome.json skips
// these files and this suite is their gate: meta shape, body syntax, phase
// titles, and the orchestration logic run against a stub runtime.
//
// `new Function` / AsyncFunction compile these repository files on purpose: they
// are tracked plugin code with the same trust as any script `npm test` runs, and
// no outside input reaches them.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

const GLOBALS = ["agent", "parallel", "pipeline", "phase", "log", "args", "budget", "workflow"];

/** @returns {string[]} Repo-relative paths of every plugin workflow script. */
function workflowFiles() {
  /** @type {string[]} */
  const files = [];
  for (const plugin of readdirSync(join(rootDir, "plugins"), { withFileTypes: true })) {
    if (!plugin.isDirectory()) continue;
    const dir = join("plugins", plugin.name, "workflows");
    let entries;
    try {
      entries = readdirSync(join(rootDir, dir));
    } catch {
      continue;
    }
    for (const name of entries) if (name.endsWith(".js")) files.push(join(dir, name));
  }
  return files;
}

/**
 * Splits a workflow script into its meta literal and its body.
 * @param {string} source
 * @returns {{ metaSource: string, body: string }}
 */
function splitScript(source) {
  const start = source.indexOf("export const meta = ");
  assert.equal(start, 0, "a workflow script must begin with `export const meta = {...}`");
  let depth = 0;
  let index = "export const meta = ".length;
  for (; index < source.length; index++) {
    const char = source[index];
    if (char === "{") depth++;
    if (char === "}" && --depth === 0) break;
  }
  const metaSource = source.slice("export const meta = ".length, index + 1);
  return { metaSource, body: source.slice(index + 1).replace(/^;/, "") };
}

const AsyncFunction =
  /** @type {new (...params: string[]) => (...values: unknown[]) => Promise<unknown>} */ (
    Object.getPrototypeOf(async () => {}).constructor
  );

/**
 * @param {string} body
 * @returns {(...values: unknown[]) => Promise<unknown>}
 */
function compile(body) {
  return new AsyncFunction(...GLOBALS, body);
}

/**
 * A stub of the workflow runtime: `pipeline` and `parallel` keep their
 * documented semantics (a throwing stage or thunk becomes null), and `agent`
 * answers from `respond`.
 * @param {(prompt: string, opts: { label?: string }) => unknown} respond
 */
function stubRuntime(respond) {
  /** @type {string[]} */
  const logs = [];
  /** @type {string[]} */
  const labels = [];
  return {
    logs,
    labels,
    /**
     * @param {string} prompt
     * @param {{ label?: string }} [opts]
     */
    agent: (prompt, opts = {}) => {
      labels.push(opts.label ?? "");
      return Promise.resolve(respond(prompt, opts));
    },
    /** @param {Array<() => Promise<unknown>>} thunks */
    parallel: (thunks) => Promise.all(thunks.map((thunk) => thunk().catch(() => null))),
    /**
     * @param {unknown[]} items
     * @param {...(prev: unknown, item: unknown, index: number) => unknown} stages
     */
    pipeline: (items, ...stages) =>
      Promise.all(
        items.map(async (item, index) => {
          /** @type {unknown} */
          let value = item;
          try {
            for (const stage of stages) value = await stage(value, item, index);
            return value;
          } catch {
            return null;
          }
        }),
      ),
    phase: () => {},
    /** @param {string} message */
    log: (message) => {
      logs.push(message);
    },
  };
}

const files = workflowFiles();

test("plugin workflow scripts are discovered", () => {
  assert.ok(files.length > 0, "expected at least one plugins/*/workflows/*.js script");
});

for (const file of files) {
  const source = readFileSync(join(rootDir, file), "utf8");
  const { metaSource, body } = splitScript(source);

  test(`${file}: meta is a pure literal with name, description, and phases`, () => {
    // Any identifier, call, or interpolation throws here: only literals evaluate.
    const meta = /** @type {Record<string, unknown>} */ (
      new Function(`"use strict"; return (${metaSource});`)()
    );
    assert.equal(typeof meta["name"], "string");
    assert.equal(typeof meta["description"], "string");
    assert.ok(!/[`$]\{/.test(metaSource), "meta must not use template interpolation");
    const phases = /** @type {Array<{ title: string }>} */ (meta["phases"] ?? []);
    const titles = new Set(phases.map((p) => p.title));
    for (const match of body.matchAll(/phase(?:\(|:\s*)"([^"]+)"/g)) {
      assert.ok(titles.has(match[1] ?? ""), `phase "${match[1]}" is not declared in meta.phases`);
    }
  });

  test(`${file}: body compiles with the workflow runtime globals`, () => {
    assert.doesNotThrow(() => compile(body));
    assert.ok(
      !/Date\.now\(\)|Math\.random\(\)|new Date\(\)/.test(body),
      "Date.now/Math.random/new Date break resume",
    );
  });
}

const deepVerify = files.find((file) =>
  file.endsWith("verify-completion/workflows/deep-verify.js"),
);

if (deepVerify) {
  const run = compile(splitScript(readFileSync(join(rootDir, deepVerify), "utf8")).body);

  /**
   * @param {ReturnType<typeof stubRuntime>} rt
   * @param {unknown} input
   */
  const execute = (rt, input) =>
    run(rt.agent, rt.parallel, rt.pipeline, rt.phase, rt.log, input, undefined, undefined);

  const pass = (/** @type {number} */ gate) => ({
    gate,
    status: "PASS",
    claim: `gate ${gate} holds`,
    evidence: "`npm test`",
  });
  const problem = {
    gate: 4,
    severity: "high",
    title: "mock can't fail",
    location: "retry.test.js:5",
    evidence: "client.get always resolves",
  };

  test("deep-verify: requires a requirement", async () => {
    const rt = stubRuntime(() => null);
    await assert.rejects(execute(rt, undefined), /needs the requirement/);
    await assert.rejects(execute(rt, { requirement: "  " }), /needs the requirement/);
  });

  test("deep-verify: a problem survives one refutation, dies on two; a challenged PASS is overturned", async () => {
    const rt = stubRuntime((prompt, opts) => {
      const label = opts.label ?? "";
      if (label === "verify:coherence")
        return { gates: [pass(1), pass(2), pass(6)], problems: [], unchecked: [] };
      if (label === "verify:depth") {
        return {
          gates: [pass(3), { gate: 4, status: "FAIL", claim: "mocks can fail", evidence: "no" }],
          problems: [problem, { ...problem, gate: 3, title: "validator rejects null" }],
          unchecked: [{ what: "network", reason: "offline" }],
        };
      }
      if (label === "verify:edges") return { gates: [pass(5)], problems: [], unchecked: [] };
      if (label.startsWith("refute:depth:4")) {
        // Only one of the two skeptics refutes the mock problem: it survives.
        return { refuted: prompt.includes("reproduce"), reason: "r", evidence: "e" };
      }
      if (label.startsWith("refute:depth:3"))
        return { refuted: true, reason: "validator does reject null", evidence: "e" };
      if (label === "challenge:edges:5")
        return { refuted: true, reason: "boundary untested", evidence: "e" };
      if (label.startsWith("challenge:")) return { refuted: false, reason: "holds", evidence: "e" };
      throw new Error(`unexpected agent ${label}`);
    });
    const result = /** @type {any} */ (
      await execute(rt, { requirement: "retry throws the last error after 3 attempts" })
    );
    assert.deepEqual(
      result.confirmedProblems.map((/** @type {any} */ p) => p.title),
      ["mock can't fail"],
    );
    assert.deepEqual(
      result.refutedProblems.map((/** @type {any} */ p) => p.title),
      ["validator rejects null"],
    );
    assert.deepEqual(
      result.overturnedPasses.map((/** @type {any} */ p) => p.gate),
      [5],
    );
    assert.deepEqual(result.missingFocuses, []);
    assert.equal(result.unchecked.length, 1);
    // Only PASS verdicts in a verifier's own gates are challenged; FAIL is not.
    assert.ok(!rt.labels.includes("challenge:depth:4"));
    assert.match(result.note, /authorize nothing/);
  });

  test("deep-verify: a verifier that returns nothing is reported, never counted as PASS", async () => {
    const rt = stubRuntime((_prompt, opts) => {
      if (opts.label === "verify:depth") return null;
      if ((opts.label ?? "").startsWith("verify:"))
        return { gates: [], problems: [], unchecked: [] };
      return { refuted: false, reason: "", evidence: "" };
    });
    const result = /** @type {any} */ (await execute(rt, "check the retry change on this branch"));
    assert.deepEqual(result.missingFocuses, ["depth"]);
    assert.ok(rt.logs.some((line) => line.includes("BLOCKED, not PASS")));
  });
}
