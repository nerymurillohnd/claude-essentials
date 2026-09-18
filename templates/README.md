# templates

Starting points for anything this repo needs repeatably. Each carries its own
instructional HTML comment — read it before filling in `{{placeholders}}`.

## Plugin shapes

Copy one of these to `plugins/<plugin-id>/` — see [docs/contributing/plugins.md](../docs/contributing/plugins.md).

| Template | Gives you |
| --- | --- |
| [`plugin-bundle/`](plugin-bundle/) | Multiple skills/agents/commands/hooks together |
| [`plugin-skill-only/`](plugin-skill-only/) | Exactly one skill, nothing else |
| [`plugin-agent-only/`](plugin-agent-only/) | Exactly one subagent, nothing else |

## Repository documents

Copy these to the path noted, replace placeholders, delete the instructional comment.

| Template | Copy to | For |
| --- | --- | --- |
| [`root-README-recommended-template.md`](root-README-recommended-template.md) | `README.md` | The shape the live root README follows |
| [`plugin-README-reusable-template.md`](plugin-README-reusable-template.md) | `plugins/<id>/README.md` | Per-plugin README (already baked into each shape above) |
| [`adr-template.md`](adr-template.md) | `docs/decisions/adr-NNNN-*.md` | A new Architecture Decision Record |
| [`CHANGELOG-reusable-template.md`](CHANGELOG-reusable-template.md) | `CHANGELOG.md` | Keep-a-Changelog-style changelog (already baked into each plugin shape; tags follow `{plugin-name}--v{version}`, see [versioning.md](../docs/contributing/versioning.md)) |
| [`LICENSE-reusable-template.md`](LICENSE-reusable-template.md) | `LICENSE.md` | Canonical, unmodified MIT text |
| [`CODE_OF_CONDUCT-reusable-template.md`](CODE_OF_CONDUCT-reusable-template.md) | `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| [`SECURITY-reusable-template.md`](SECURITY-reusable-template.md) | `SECURITY.md` | Vulnerability reporting policy |
| [`pending-debt-template.md`](pending-debt-template.md) | `docs/maintenance/pending-debt.md` | Unresolved maintenance ledger |
| [`resolved-debt-template.md`](resolved-debt-template.md) | `docs/maintenance/resolved-debt.md` | Resolved maintenance ledger |

This repository's own root `README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`,
`SECURITY.md`, and `docs/maintenance/*.md` are live instances of the
templates above — kept in sync by hand, not generated.
