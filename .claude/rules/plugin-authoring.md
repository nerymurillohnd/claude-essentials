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
- Run the plugin's own `test-*.sh` suite and `npm run check` after each change,
  not in a batch before committing.
- Re-run `/plugin-release-review <id>` after every change that touches runtime
  files, the README, or `plugin.json`. One review pass that finds everything
  beats three that find it in pieces.
- A finding is closed only when it is fixed **and** a gate exists that would
  catch it next time (validator rule, test, or a row in the review skill's
  references). Record the gap in `docs/maintenance/`.
- Any change to a skill's `description`, its instructions, or `evals/` re-runs
  `claude plugin eval` in the **same branch**, and the README eval table is
  updated before the PR opens. The same applies to test counts and timings
  quoted in the README or CHANGELOG.
