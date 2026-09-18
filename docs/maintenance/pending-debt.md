# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0006 — The repo marketplace schema rejects `renames: null`

- **Status:** Pending
- **Category:** correctness
- **Evidence:**
  - **Confirmed facts:** In `schemas/marketplace.schema.json`, `renames.additionalProperties` is `{ "type": "string" }`. Ajv rejects `{"renames": {"old": null}}` with `/renames/old must be string` and accepts `{"old": "new"}` (reproduced 2026-09-18). Claude Code documents `null` as the value for a removed plugin ([plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)). [versioning.md](../contributing/versioning.md) tells contributors to use `null` on removal, and `version-check` requires a `renames` entry for every removed plugin.
  - **Inferences:** The first plugin removal will fail `npm run validate` while following the documented procedure.
  - **Open questions:** none.
- **Impact / risk:** Blocks the documented removal flow. The workaround would be a string value, which misstates the removal as a rename.
- **Owner or responsible area:** `schemas/marketplace.schema.json`, `scripts/validate-marketplace.mjs`
- **Next action:** Allow `["string", "null"]` and add a unit test for both values. `schemas/claude-code/marketplace.schema.json` already models this correctly. Planned for phase 1 of the [spec-alignment design](../superpowers/specs/2026-09-18-marketplace-spec-alignment-design.md).
- **Review condition:** Close when the test passes and a removal fixture validates.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)

### DEBT-0007 — The plugin-shape READMEs link to an `evals/` directory the templates don't ship

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `templates/plugin-{bundle,skill-only,agent-only}/README.md` link to `evals/` in their Verification section. No template contains `evals/` (link check run 2026-09-18, PR #6).
  - **Inferences:** A plugin copied from a template ships a broken link until its author adds an eval suite.
  - **Open questions:** The exact grader-file syntax for "skill must not fire" (`tool_used`, `min`/`max`, `arm`) must be verified against [plugin-evals](https://code.claude.com/docs/en/plugin-evals) before scaffolding it.
- **Impact / risk:** A broken link in every new plugin, and the spec's "evals required" rule is not enforced yet.
- **Owner or responsible area:** `templates/`, `scripts/lib/`
- **Next action:** Add a verified `evals/` skeleton (a trigger case and a non-trigger case) to each shape, plus the structural validator. Planned for phase 2 of the [spec-alignment design](../superpowers/specs/2026-09-18-marketplace-spec-alignment-design.md).
- **Review condition:** Close when every shape ships `evals/`, the link resolves, and `npm run validate` enforces the suite shape.
- **Related records:** [PR #6](https://github.com/nerymurillohnd/claude-essentials/pull/6)
