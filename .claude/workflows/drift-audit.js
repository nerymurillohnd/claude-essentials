export const meta = {
  name: "drift-audit",
  description:
    "Find documentation that no longer matches the claude-essentials code, then verify each finding",
  whenToUse:
    "Before a release or after many doc, script or rule changes; the docs gate covers mechanical drift, this covers meaning",
  phases: [
    { title: "Find", detail: "one reader per documentation area" },
    {
      title: "Verify",
      detail: "one skeptic per area tries to refute each finding",
    },
  ],
};

const AREAS = [
  {
    key: "guides",
    prompt:
      "Compare docs/authoring.md, docs/testing.md, docs/releasing.md, docs/automation.md and CONTRIBUTING.md with the scripts they describe in scripts/ (read the scripts and their --help). Report every sentence that describes a command, flag, step, file or behaviour the code no longer has, or misses one the code has.",
  },
  {
    key: "rules",
    prompt:
      "Compare every file in .claude/rules/ (read each with the Read tool) with the repository: scripts, docs, workflows and configuration. Report every rule statement that the repository contradicts, that names a file, command or value that no longer exists, or whose `paths:` no longer cover the files it is about.",
  },
  {
    key: "claude-md",
    prompt:
      "Compare CLAUDE.md (Commands, Architecture, Where Knowledge Lives, Current state, Definition of done) and README.md with the repository as it is now: git log -20, the scripts, .claude/ (skills, agents, workflows, settings.json) and docs/. Report every statement that is no longer true or that omits something a maintainer needs.",
  },
  {
    key: "automation",
    prompt:
      "Compare the project skills (.claude/skills/*/SKILL.md), the agent (.claude/agents/), the workflows (.claude/workflows/), .claude/settings.json and scripts/claude_hooks.py with docs/automation.md and the ADRs in docs/adr/decisions/ dated 2026-10-04. Report every skill step, hook, permission rule or workflow that the docs describe differently from what the files do.",
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
          file: {
            type: "string",
            description: "document path and line, e.g. docs/testing.md:42",
          },
          claim: {
            type: "string",
            description: "the documented statement, quoted",
          },
          reality: {
            type: "string",
            description: "what the code does, with file:line evidence",
          },
          fix: { type: "string" },
        },
        required: ["file", "claim", "reality", "fix"],
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
          file: { type: "string" },
          confirmed: { type: "boolean" },
          reason: {
            type: "string",
            description: "evidence for or against, with file:line",
          },
        },
        required: ["file", "confirmed", "reason"],
      },
    },
  },
  required: ["verdicts"],
};

const scope =
  args && args.paths
    ? ` Limit yourself to these paths: ${args.paths.join(", ")}.`
    : "";

const results = await pipeline(
  AREAS,
  (area) =>
    agent(
      `${area.prompt}${scope} Read files with the Read tool. Do not edit anything. Only report a finding you can back with a quote from the document and file:line evidence from the code; report nothing rather than a guess.`,
      { label: `find:${area.key}`, phase: "Find", schema: FINDINGS },
    ),
  (found, area) => {
    if (!found || found.findings.length === 0)
      return { area: area.key, confirmed: [] };
    return agent(
      `You are a skeptic. For each finding below, open the cited document and code and try to REFUTE it: the documentation may be right, the code may already match, or the claim may be misquoted. Mark confirmed=true only when the drift is real and the evidence holds; default to false when unsure. Do not edit anything.\n\n${JSON.stringify(found.findings, null, 2)}`,
      { label: `verify:${area.key}`, phase: "Verify", schema: VERDICTS },
    ).then((checked) => ({
      area: area.key,
      confirmed: found.findings.filter((finding) =>
        (checked ? checked.verdicts : []).some(
          (v) => v.file === finding.file && v.confirmed,
        ),
      ),
    }));
  },
);

const confirmed = results
  .filter(Boolean)
  .flatMap((r) => r.confirmed.map((f) => ({ area: r.area, ...f })));
log(`${confirmed.length} confirmed drift finding(s)`);
return { confirmed };
