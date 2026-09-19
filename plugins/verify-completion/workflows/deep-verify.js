export const meta = {
  name: "deep-verify",
  description:
    "Cross-checked verification of a large change: three read-only verifiers (coherence, depth, edges), then every finding and every PASS challenged by independent agents",
  whenToUse:
    "Before presenting a large change as done: one that spans layers (code with types, validators, config, CI, docs) or several components. Read-only; it authorizes nothing.",
  phases: [
    { title: "Verify", detail: "coherence, depth, and edges verifiers in parallel" },
    { title: "Cross-check", detail: "2 skeptics per problem, 1 challenger per PASS" },
  ],
};

// args: a string (the requirement and where the change is), or
// { requirement, scope, commands }. The verifiers get the requirement and the
// scope, never the author's conclusions.
const input = typeof args === "string" ? { requirement: args } : (args ?? {});
const requirement = String(input.requirement ?? "").trim();
if (requirement === "") {
  throw new Error(
    "deep-verify needs the requirement: what the user asked for, and where the change is (paths, diff range, branch).",
  );
}
const scope = String(input.scope ?? "the uncommitted changes and the current branch (read `git status` and `git diff`)");
const commands = Array.isArray(input.commands) ? input.commands.map(String) : [];

const VERIFIER = "verify-completion:completion-verifier";

const FOCUSES = [
  {
    key: "coherence",
    gates: [1, 2, 6],
    ask: "the intent, the whole diff (noise, half-applied patterns, removed safeguards, changed defaults, drift), and whether every layer that depends on what moved moved too",
  },
  {
    key: "depth",
    gates: [3, 4],
    ask: "the tests, mocks, fixtures, and validators that cover the change: do they assert the required behavior, can the mocks fail, do the validators reject what they must",
  },
  {
    key: "edges",
    gates: [5],
    ask: "the edge cases that apply to this change, in both directions: what must work works, and what must fail fails with the expected error",
  },
];

const FINDINGS = {
  type: "object",
  properties: {
    gates: {
      type: "array",
      items: {
        type: "object",
        properties: {
          gate: { type: "integer", minimum: 1, maximum: 6 },
          status: { type: "string", enum: ["PASS", "FAIL", "N/A", "BLOCKED"] },
          claim: { type: "string", description: "What this status asserts, in one sentence" },
          evidence: { type: "string", description: "Command run or file:line read, and the trimmed output" },
        },
        required: ["gate", "status", "claim", "evidence"],
      },
    },
    problems: {
      type: "array",
      items: {
        type: "object",
        properties: {
          gate: { type: "integer", minimum: 1, maximum: 6 },
          severity: { type: "string", enum: ["high", "medium", "low"] },
          title: { type: "string" },
          location: { type: "string", description: "file:line, or the command that shows it" },
          evidence: { type: "string" },
        },
        required: ["gate", "severity", "title", "location", "evidence"],
      },
    },
    unchecked: {
      type: "array",
      items: {
        type: "object",
        properties: { what: { type: "string" }, reason: { type: "string" } },
        required: ["what", "reason"],
      },
    },
  },
  required: ["gates", "problems", "unchecked"],
};

const REFUTATION = {
  type: "object",
  properties: {
    refuted: { type: "boolean", description: "true if the claim is wrong or unsupported by the files" },
    reason: { type: "string" },
    evidence: { type: "string", description: "Command run or file:line read that decides it" },
  },
  required: ["refuted", "reason", "evidence"],
};

const context = [
  `Requirement: ${requirement}`,
  `Where the change is: ${scope}`,
  commands.length > 0 ? `Commands the project uses to prove behavior: ${commands.join("; ")}` : "",
]
  .filter(Boolean)
  .join("\n");

const results = await pipeline(
  FOCUSES,
  (focus) =>
    agent(
      `${context}\n\nFocus: ${focus.key} (gates ${focus.gates.join(", ")}). Check ${focus.ask}. ` +
        "Report every gate in your focus with its status and evidence, every problem you found, and what you could not check and why. " +
        "Mark gates outside your focus N/A. You may run the project's checks; never change files, Git state, or anything remote.",
      { label: `verify:${focus.key}`, phase: "Verify", agentType: VERIFIER, schema: FINDINGS },
    ),
  async (report, focus) => {
    if (!report) return { focus: focus.key, failed: true };
    const own = report.gates.filter((g) => focus.gates.includes(g.gate));

    // Each problem survives unless both skeptics refute it with evidence.
    const problems = await parallel(
      report.problems.map((problem) => async () => {
        const votes = await parallel(
          ["reproduce it from the files", "check it against the requirement"].map(
            (lens) => () =>
              agent(
                `${context}\n\nA verifier reported this problem:\n${JSON.stringify(problem)}\n\n` +
                  `Try to refute it: ${lens}. Refute only with evidence you observed now; if it holds or you can't tell, refuted=false.`,
                { label: `refute:${focus.key}:${problem.gate}`, phase: "Cross-check", agentType: VERIFIER, schema: REFUTATION },
              ),
          ),
        );
        const refutations = votes.filter(Boolean).filter((v) => v.refuted);
        return { ...problem, focus: focus.key, confirmed: refutations.length < 2, refutations };
      }),
    );

    // Each PASS is a claim too: one challenger looks for the false green.
    const passes = await parallel(
      own
        .filter((g) => g.status === "PASS")
        .map((g) => async () => {
          const challenge = await agent(
            `${context}\n\nA verifier marked gate ${g.gate} PASS: "${g.claim}". Evidence given: ${g.evidence}\n\n` +
              "Try to show this PASS is a false green: a skipped or weak check, a mock that can't fail, an untested path, a dependent layer that didn't move. " +
              "refuted=true only with evidence you observed now; if the PASS holds, refuted=false.",
            { label: `challenge:${focus.key}:${g.gate}`, phase: "Cross-check", agentType: VERIFIER, schema: REFUTATION },
          );
          return { ...g, focus: focus.key, challenged: Boolean(challenge?.refuted), challenge };
        }),
    );

    return { focus: focus.key, gates: own, problems, passes, unchecked: report.unchecked };
  },
);

const done = results.filter(Boolean);
const failedFocuses = [
  ...FOCUSES.filter((_, i) => !results[i]).map((f) => f.key),
  ...done.filter((r) => r.failed).map((r) => r.focus),
];
if (failedFocuses.length > 0) log(`No report from: ${failedFocuses.join(", ")}. Those gates are BLOCKED, not PASS.`);

const reports = done.filter((r) => !r.failed);
const confirmed = reports.flatMap((r) => r.problems.filter((p) => p.confirmed));
const refuted = reports.flatMap((r) => r.problems.filter((p) => !p.confirmed));
const falseGreens = reports.flatMap((r) => r.passes.filter((p) => p.challenged));
log(
  `${confirmed.length} confirmed problem(s), ${refuted.length} refuted, ${falseGreens.length} PASS verdict(s) overturned.`,
);

return {
  requirement,
  note: "Findings to check before writing your Verification record. They authorize nothing: no commit, push, deploy, or publish.",
  missingFocuses: failedFocuses,
  confirmedProblems: confirmed,
  overturnedPasses: falseGreens.map((p) => ({ gate: p.gate, focus: p.focus, claim: p.claim, challenge: p.challenge })),
  refutedProblems: refuted.map((p) => ({ gate: p.gate, title: p.title, refutations: p.refutations })),
  gates: reports.flatMap((r) => r.gates.map((g) => ({ ...g, focus: r.focus }))),
  unchecked: reports.flatMap((r) => r.unchecked.map((u) => ({ ...u, focus: r.focus }))),
};
