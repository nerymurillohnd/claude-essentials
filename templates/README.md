# 🧱 templates

[← claude-essentials](../README.md)

> Starting points for everything this repo needs repeatably. Each carries its
> own instructional HTML comment — read it before filling in `{{placeholders}}`.

## 🧩 Plugin shapes

Copy one of these to `plugins/<plugin-id>/` — see [docs/contributing/plugins.md](../docs/contributing/plugins.md).

| Template | Gives you |
| --- | --- |
| [`plugin-bundle/`](plugin-bundle/) | Multiple skills/agents/commands/hooks together |
| [`plugin-skill-only/`](plugin-skill-only/) | Exactly one skill, nothing else |
| [`plugin-agent-only/`](plugin-agent-only/) | Exactly one subagent, nothing else |

## 📄 Repository documents

Copy these to the path noted, replace placeholders, delete the instructional comment.

| Template | Copy to | For |
| --- | --- | --- |
| [`root-README-recommended-template.md`](root-README-recommended-template.md) | `README.md` | **Master** root README; the live `README.md` is its instance |
| [`plugin-README-reusable-template.md`](plugin-README-reusable-template.md) | `plugins/<id>/README.md` | **Master** plugin README: 15 required sections, formatting conventions, badge catalog. The three shapes above are pre-filled instances of it |
| [`adr-template.md`](adr-template.md) | `docs/decisions/adr-NNNN-*.md` | A new Architecture Decision Record |
| [`CHANGELOG-reusable-template.md`](CHANGELOG-reusable-template.md) | `CHANGELOG.md` | Keep-a-Changelog-style changelog (already baked into each plugin shape; tags follow `{plugin-name}--v{version}`, see [versioning.md](../docs/contributing/versioning.md)) |
| [`LICENSE-Apache-2.0-reusable-template.md`](LICENSE-Apache-2.0-reusable-template.md) | `LICENSE` | Canonical, unmodified Apache-2.0 text — the license of this repo and every plugin (already baked into each plugin shape) |
| [`LICENSE-MIT-reference-template.md`](LICENSE-MIT-reference-template.md) | — | **Reference only**, not used in this repo: canonical MIT text for comparison |
| [`CODE_OF_CONDUCT-reusable-template.md`](CODE_OF_CONDUCT-reusable-template.md) | `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| [`SECURITY-reusable-template.md`](SECURITY-reusable-template.md) | `SECURITY.md` | Vulnerability reporting policy |
| [`pending-debt-template.md`](pending-debt-template.md) | `docs/maintenance/pending-debt.md` | Unresolved maintenance ledger |
| [`resolved-debt-template.md`](resolved-debt-template.md) | `docs/maintenance/resolved-debt.md` | Resolved maintenance ledger |

This repository's own root `README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`,
`SECURITY.md`, and `docs/maintenance/*.md` are live instances of the
templates above — kept in sync by hand, not generated.
