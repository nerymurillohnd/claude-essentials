---
paths:
  - "plugins/**/*"
---

# Plugin authoring

Applies while working on any file under `plugins/`. The full procedure is in
`/plugin-design` and `/plugin-release-review`; these are the rules that bite
between their phases.

- The design's non-goals and failure modes (missing dependency, timeout,
  unsupported surface) become the README's **What it does not do** and
  **Limitations**, not an afterthought.
- Run the plugin's suite (`scripts/plugin_validation/suites/<id>/`) and `make check` after each change,
  not in a batch before committing.
- Re-run `/plugin-release-review <id>` after every change that touches runtime
  files, the README, or `plugin.json`. One review pass that finds everything
  beats three that find it in pieces.
- A finding is closed only when it is fixed **and** a gate exists that would
  catch it next time (validator rule, test, or a row in the review skill's
  references). Record the gap in `docs/maintenance/`.
- A skill's `description` opens with the instruction it gives Claude — an
  imperative clause, never a self-introduction — and `when_to_use` carries the
  triggering conditions; the two share one 1,536-character listing budget. Write
  both from the skill's own files (`SKILL.md`, its references, its scripts),
  never from the previous wording, so they state what the skill really does.
  Both are plain YAML scalars, so neither carries quoted trigger phrases nor a
  colon followed by a space; `scripts/plugin_validation/test_frontmatter.py` is
  the gate, because `claude plugin validate --strict` accepts a description that no
  YAML parser can read.
- Any change to a skill's `description`, its instructions, or `evals/` re-runs
  `claude plugin eval` in the **same branch**; its numbers go in the PR body or a
  dated file under `docs/audits/`, never in the README. Test counts and timings
  quoted in the README or CHANGELOG are re-measured the same way.
- In a hook `if`, `Edit(P)` matches the Edit tool only and `Write(P)` the Write
  tool only (measured on 2.1.278, unlike permission rules): give every file
  condition its twin with the same command. H7 in `make validate` enforces it.
- `${CLAUDE_SKILL_DIR}` is filled in only in a skill's own `SKILL.md` and its
  `allowed-tools` rules. A reference or asset file names a script by file name and
  lets `SKILL.md` say where it lives; `scripts/plugin_validation/test_skill_supporting_files.py`
  is the gate.
- Component directories sit flat at the plugin root (`hooks/`, `scripts/`, `skills/`,
  `agents/`, `.claude-plugin/`): `hooks/` holds only `hooks.json`, and its handlers go in
  `scripts/`, never a nested `hooks/scripts/`. H8 enforces it.
