import assert from "node:assert/strict";
import { test } from "node:test";
import { collectFindings } from "./claude-cli.mjs";

test("collectFindings flattens manifest and content findings", () => {
  const report = {
    success: false,
    strict: true,
    manifest: {
      file: "/r/plugins/demo/.claude-plugin/plugin.json",
      type: "plugin",
      errors: [],
      warnings: [
        {
          path: "kind",
          message: "Unknown field 'kind'. Claude Code ignores it at load time.",
          code: null,
        },
      ],
      notes: [],
    },
    contents: [
      {
        file: "/r/plugins/demo/skills/a/SKILL.md",
        type: "skill",
        errors: [{ path: "name", message: "Bad frontmatter", code: null }],
        warnings: [],
        notes: [],
      },
    ],
  };
  assert.deepEqual(collectFindings(report), [
    {
      severity: "warning",
      file: "/r/plugins/demo/.claude-plugin/plugin.json",
      path: "kind",
      message: "Unknown field 'kind'. Claude Code ignores it at load time.",
    },
    {
      severity: "error",
      file: "/r/plugins/demo/skills/a/SKILL.md",
      path: "name",
      message: "Bad frontmatter",
    },
  ]);
});

test("collectFindings returns [] for a clean report", () => {
  assert.deepEqual(collectFindings({ manifest: { errors: [], warnings: [] }, contents: [] }), []);
});
