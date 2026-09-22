# 📚 docs

[← claude-essentials](../README.md)

> How this marketplace is built, run, and changed — organized by purpose, not by date.

| Folder | What lives there | Start with |
| --- | --- | --- |
| [`decisions/`](decisions/) | ADRs: *why* the repo is built this way | [ADR-0001](decisions/adr-0001-marketplace-distribution-model.md) |
| [`contributing/`](contributing/) | How to add, version, and report on plugins | [plugins.md](contributing/plugins.md) |
| [`maintenance/`](maintenance/) | Pending and resolved technical-debt ledgers | [pending-debt.md](maintenance/pending-debt.md) |
| [`audits/`](audits/) | Dated, point-in-time review reports | [README](audits/README.md) |
| [`superpowers/`](superpowers/) | Design specs and implementation plans, kept after landing | [README](superpowers/README.md) |

## 🏛️ Decision records

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](decisions/adr-0001-marketplace-distribution-model.md) | Standalone skills and agents ship as single-component plugins | ✅ accepted |
| [0002](decisions/adr-0002-project-hooks.md) | Project hooks for session context, catalog integrity, and post-edit hygiene | ✅ accepted |
| [0003](decisions/adr-0003-plugin-versioning-and-tagging.md) | Explicit semver; CI enforces bumps and tags `{name}--v{version}` | ✅ accepted |
| [0004](decisions/adr-0004-issue-and-label-protocol.md) | Issue forms, triage flow, and labels kept as code | ✅ accepted |
| [0005](decisions/adr-0005-apache-2-0-license.md) | The marketplace and every plugin are Apache-2.0 | ✅ accepted |
| [0006](decisions/adr-0006-changelog-scope-skill-declaration-and-release-tooling.md) | Per-plugin changelogs, the default skill scan, and CI-enforced versioning | ✅ accepted |
| [0007](decisions/adr-0007-gates-ship-as-plugin-hooks.md) | Quality gates ship as plugin hooks that run only installed tools; test suites live in the repository | ✅ accepted |

New ADRs start from [`templates/adr-template.md`](../templates/adr-template.md).
Accepted ADRs are amended by appending `### Amendment — YYYY-MM-DD`, never rewritten.

## 🧭 Contributor guides

| Guide | Covers |
| --- | --- |
| [plugins.md](contributing/plugins.md) | Adding a plugin: shapes, manifest, content, catalog generation |
| [versioning.md](contributing/versioning.md) | When and how to bump, changelog entries, tags, renames |
| [issues.md](contributing/issues.md) | Issue forms and triage |
| [labels.md](contributing/labels.md) | The label taxonomy |

See also [`../templates/`](../templates/) for every reusable starting point.
