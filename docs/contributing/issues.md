# Issues and triage

Issues are for **actionable work**: bugs, feature requests, plugin proposals,
and documentation problems. Everything else has its own place:

| You want to… | Go to |
| --- | --- |
| Ask a question, discuss an idea | [Discussions → Q&A](https://github.com/nerymurillohnd/claude-essentials/discussions/categories/q-a) |
| Report a vulnerability | [Private security advisory](https://github.com/nerymurillohnd/claude-essentials/security/advisories/new) — never a public issue ([SECURITY.md](../../SECURITY.md)) |
| Report a Claude Code bug | [anthropics/claude-code](https://github.com/anthropics/claude-code/issues) |

Blank issues are disabled, so every issue starts from a form:

| Form | Labels applied | Use for |
| --- | --- | --- |
| Bug report | `type: bug`, `status: needs-triage` | A plugin or the catalog doesn't behave as documented |
| Feature request | `type: feature`, `status: needs-triage` | Improving an existing plugin or the marketplace |
| Plugin proposal | `type: plugin-proposal`, `status: needs-triage` | A new plugin, standalone skill, or standalone agent |
| Documentation problem | `type: docs`, `status: needs-triage` | Missing, wrong, or unclear docs |

Bug reports also ask for the **Surface** (Claude Code or Claude Cowork) and
where the plugin was **Installed from**. Only installs from the remote
marketplace are supported, so reproduce there before reporting. Plugin
proposals ask for target surfaces, external requirements, and one request that
should trigger the plugin and one that shouldn't. Those become its eval cases.

Every form and `config.yml` is validated against the vendored GitHub schemas in
`.github/schemas/` by `make validate`.

The **Affected plugin** dropdown is generated from `plugins/` by
`make generate`. When an issue is opened, the triage bot adds the matching
`plugin: <name>` label, or `area: catalog` for installation and catalog
problems.

## Triage flow

```
opened ── status: needs-triage
   │
   ├─► status: accepted  (+ priority: critical | high | low)  ── fixed by a PR ("Closes #N") ── closed: completed
   ├─► status: needs-info ── author replies ──► back to status: needs-triage (automatic)
   │         └── 14 days silent ─► status: stale ── 7 more days ─► closed: not planned (automatic)
   ├─► status: blocked   (link the blocker)
   └─► closed: not planned | duplicate   (GitHub's native close reasons; comment why)
```

- The maintainer aims to triage new issues within 7 days. This is a goal,
  not a guarantee: the project is community-maintained.
- `priority: critical` is reserved for broken installs, data loss, or a
  security-relevant defect. Unlabeled means normal priority.
- `help wanted` marks an accepted issue open to outside contributors.
- Only issues labeled `status: needs-info` ever go stale. The stale bot never
  touches other issues or any PR.

Automation lives in `.github/workflows/triage.yml` and
`.github/workflows/stale.yml`. The label definitions are in
[labels.md](labels.md).
