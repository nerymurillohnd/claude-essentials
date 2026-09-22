# Labels

Labels are kept as code ([ADR-0004](../decisions/adr-0004-issue-and-label-protocol.md)).
[`.github/labels.json`](../../.github/labels.json) is the source of truth for
every label except `plugin: <name>`, which is derived from `plugins/`. Never
create or edit labels in the GitHub UI: the `Labels` workflow overwrites
drift on the next run.

| Family | Labels | Applied by | On |
| --- | --- | --- | --- |
| `type:` | `bug`, `feature`, `plugin-proposal`, `docs`, `maintenance`, `security` | Issue forms; maintainer on PRs | Issues, PRs |
| `status:` | `needs-triage`, `needs-info`, `accepted`, `blocked`, `stale` | Forms, maintainer, triage bot, stale bot | Issues |
| `priority:` | `critical`, `high`, `low` | Maintainer | Issues |
| `area:` | `plugins`, `catalog`, `ci`, `tooling`, `templates`, `docs`, `community` | Triage bot, from changed paths | PRs (and `area: catalog` on issues) |
| `plugin:` | one per plugin, derived | Triage bot | Issues, PRs |
| `bump:` | `major`, `minor`, `patch`, `prerelease`, `initial`, `none` | Triage bot, computed with the same rules as `version-check` | PRs |
| `bump: deferred` | — | **Maintainer only** | PRs |
| community | `help wanted` | Maintainer | Issues |

Resolution isn't a label. Close with GitHub's native reason (*completed*,
*not planned*, or *duplicate*) and a comment.

## How a PR's `bump:` label is computed

The triage bot runs the same `version_plan` rules as `make versions`
([versioning.md](versioning.md)). The label reflects the highest-impact change
across all touched plugins: `major` > `minor` > `patch` > `prerelease` >
`initial`. `none` means no plugin version changes. A PR that violates the
rules gets no `bump:` label, and its `version-check` job fails.

## Changing the taxonomy

1. Edit `.github/labels.json`. To rename a label while keeping it on existing
   issues, add the old name to `aliases`.
2. Run `make check`, which validates names, colors, lengths, and every
   label automation depends on.
3. Run `.venv/bin/python -m scripts.github.sync_labels` to preview the changes against GitHub. It's a dry
   run. Merging to `main` applies them through the `Labels` workflow.
4. Deleting labels that are no longer in the taxonomy is manual and must be
   reviewed first: run `.venv/bin/python -m scripts.github.sync_labels --prune`, then
   `.venv/bin/python -m scripts.github.sync_labels --apply --prune`.
