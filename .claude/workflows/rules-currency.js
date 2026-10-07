export const meta = {
  name: "rules-currency",
  description:
    "Check every .claude/rules fact against the official Claude Code docs and changelog, then verify each stale claim",
  whenToUse:
    "From /cc-currency when a new Claude Code release is out, or before trusting the rules for a new release",
  phases: [
    {
      title: "Check",
      detail: "one agent per group of rules reads the live docs",
    },
    {
      title: "Verify",
      detail: "one skeptic per group re-reads the cited sources",
    },
  ],
};

// args: { pin: "2.1.292", latest: "2.1.293" } — versions are passed in because the
// script has no shell; /cc-currency reads them first. `pin` is the last reviewed
// release recorded in .claude/rules/claude-code-version.md.
const pin =
  (args && args.pin) ||
  "the last reviewed release in .claude/rules/claude-code-version.md";
const latest =
  (args && args.latest) ||
  "the latest published version (npm view @anthropic-ai/claude-code dist-tags)";

const GROUPS = [
  { key: "plugins", files: ".claude/rules/plugins/*.md" },
  {
    key: "cli-and-catalog",
    files:
      ".claude/rules/claude-cli.md, schemas.md, marketplace-file.md, distribution.md",
  },
  {
    key: "testing-and-release",
    files:
      ".claude/rules/testing/*.md, releasing.md, ci-github.md, tooling-versions.md",
  },
  {
    key: "features-and-identity",
    files:
      ".claude/rules/claude-code-features.md, claude-code-version.md, adrs.md, repo-scripts.md, project-identity.md, local-toolchain.md",
  },
];

const CLAIMS = {
  type: "object",
  properties: {
    claims: {
      type: "array",
      items: {
        type: "object",
        properties: {
          rule: { type: "string", description: "rule file and line" },
          statement: { type: "string", description: "the rule text, quoted" },
          status: {
            type: "string",
            enum: ["current", "stale", "unverifiable"],
          },
          source: {
            type: "string",
            description: "official URL and a literal quote",
          },
          update: {
            type: "string",
            description:
              "the corrected rule text with date and version, or empty",
          },
        },
        required: ["rule", "statement", "status", "source", "update"],
      },
    },
  },
  required: ["claims"],
};

const VERDICTS = {
  type: "object",
  properties: {
    verdicts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          rule: { type: "string" },
          stale: { type: "boolean" },
          reason: { type: "string" },
        },
        required: ["rule", "stale", "reason"],
      },
    },
  },
  required: ["verdicts"],
};

const results = await pipeline(
  GROUPS,
  (group) =>
    agent(
      `Read these Claude Code rule files of the claude-essentials repository with the Read tool: ${group.files}. The rules were last reviewed on Claude Code ${pin}; the latest release is ${latest}. For every factual statement about Claude Code (fields, commands, flags, versions, behaviour), check it against the official sources only: https://code.claude.com/docs/llms.txt, the pages it lists (append .md for raw Markdown, fetch with curl), and every changelog entry newer than ${pin} in https://code.claude.com/docs/en/changelog.md. Never use any other marketplace or plugin collection as a source. Mark a statement stale only with a literal quote from an official source; mark it unverifiable when no official source settles it. Do not edit files.`,
      { label: `check:${group.key}`, phase: "Check", schema: CLAIMS },
    ),
  (checked, group) => {
    const stale = checked
      ? checked.claims.filter((c) => c.status === "stale")
      : [];
    if (stale.length === 0) return { group: group.key, stale: [] };
    return agent(
      `You are a skeptic. For each claim below, fetch the cited official source yourself and try to REFUTE that the rule is stale: the rule may still be true, the quote may be about another surface or version, or the changelog entry may not apply. Mark stale=true only when the source clearly contradicts the rule. Do not edit files.\n\n${JSON.stringify(stale, null, 2)}`,
      { label: `verify:${group.key}`, phase: "Verify", schema: VERDICTS },
    ).then((verdicts) => ({
      group: group.key,
      stale: stale.filter((claim) =>
        (verdicts ? verdicts.verdicts : []).some(
          (v) => v.rule === claim.rule && v.stale,
        ),
      ),
    }));
  },
);

const stale = results.filter(Boolean).flatMap((r) => r.stale);
log(`${stale.length} rule statement(s) confirmed stale`);
return { stale };
