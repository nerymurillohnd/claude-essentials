export const meta = {
  name: "review-pr-deep",
  description:
    "Review a claude-essentials pull request along four dimensions in parallel and adversarially verify every finding",
  whenToUse:
    "For large or risky pull requests (new plugins, hooks, MCP servers, release changes); /review-pr covers the rest",
  phases: [
    { title: "Review", detail: "one reviewer per dimension" },
    {
      title: "Verify",
      detail: "one skeptic per dimension tries to refute each finding",
    },
  ],
};

// args: { target: "12" } — a pull request number or a branch name; the current branch when empty.
const target = (args && args.target) || "the current branch against main";

const DIMENSIONS = [
  {
    key: "release",
    prompt:
      "release discipline: one single-step bump per changed plugin made by scripts/bump_version.py, a matching dated CHANGELOG section with user-facing notes, an empty [Unreleased], exactly one semver: label equal to the highest bump, a Conventional Commit title with the plugin as scope, catalog notes for marketplace.json changes (docs/releasing.md, scripts/check_pr.py)",
  },
  {
    key: "quality",
    prompt:
      "the quality bar in docs/quality-bar.md and docs/authoring.md, judged from the point of view of a stranger who installs the plugin: clear skill descriptions with triggers, instructions that work without the maintainer's setup, README sections, examples",
  },
  {
    key: "security",
    prompt:
      "security and portability per docs/security-review.md: what every hook, MCP or LSP server, bin/ executable, monitor or mod runs on the user's machine, whether the README Permissions section states it, secrets, network calls, writes outside ${CLAUDE_PLUGIN_DATA}, absolute or home paths, ../, personal data, files outside plugins/<name>/",
  },
  {
    key: "docs",
    prompt:
      "documentation drift: README, CHANGELOG, docs/, .claude/rules and CLAUDE.md still describe what the change does, and generated README blocks were regenerated with scripts/sync_readmes.py rather than edited",
  },
];

const FINDINGS = {
  type: "object",
  properties: {
    findings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          location: { type: "string", description: "file:line" },
          severity: { type: "string", enum: ["blocker", "major", "minor"] },
          finding: { type: "string" },
          evidence: {
            type: "string",
            description: "quoted line and why it is wrong",
          },
          fix: { type: "string" },
        },
        required: ["location", "severity", "finding", "evidence", "fix"],
      },
    },
  },
  required: ["findings"],
};

const VERDICTS = {
  type: "object",
  properties: {
    verdicts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          location: { type: "string" },
          real: { type: "boolean" },
          reason: { type: "string" },
        },
        required: ["location", "real", "reason"],
      },
    },
  },
  required: ["verdicts"],
};

const results = await pipeline(
  DIMENSIONS,
  (dimension) =>
    agent(
      `Review ${target} in the claude-essentials repository for ${dimension.prompt}. Get the diff with gh pr diff <number> and gh pr view <number> --json title,labels,files for a pull request, or git diff main...<branch>. Read files with the Read tool, never edit, commit, push or comment. Report only findings you can cite with file:line and a quoted line.`,
      { label: `review:${dimension.key}`, phase: "Review", schema: FINDINGS },
    ),
  (found, dimension) => {
    if (!found || found.findings.length === 0)
      return { dimension: dimension.key, findings: [] };
    return agent(
      `You are a skeptic. For each finding below about ${target}, open the cited lines and the rule it relies on and try to REFUTE it. Mark real=true only when the problem holds against the actual diff and the repository's documented rules; default to false when unsure. Do not edit anything.\n\n${JSON.stringify(found.findings, null, 2)}`,
      { label: `verify:${dimension.key}`, phase: "Verify", schema: VERDICTS },
    ).then((checked) => ({
      dimension: dimension.key,
      findings: found.findings.filter((finding) =>
        (checked ? checked.verdicts : []).some(
          (v) => v.location === finding.location && v.real,
        ),
      ),
    }));
  },
);

const findings = results
  .filter(Boolean)
  .flatMap((r) => r.findings.map((f) => ({ dimension: r.dimension, ...f })));
const order = { blocker: 0, major: 1, minor: 2 };
findings.sort((a, b) => order[a.severity] - order[b.severity]);
const verdict = findings.some((f) => f.severity === "blocker")
  ? "blocked"
  : findings.length
    ? "changes needed"
    : "ready";
log(`verdict: ${verdict}, ${findings.length} verified finding(s)`);
return { verdict, findings };
