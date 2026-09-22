# Versioning and releases

`scripts/versioning/`. Everything that decides whether a plugin owes a version
bump and everything that turns a merged bump into a tag. The rules are `ADR-0003`.

## Ground rules

- A plugin release is a merged version bump plus its `{name}--v{version}` tag. Plugins are not packages, so there are no GitHub Releases.
- Only runtime files force a bump — anything Claude Code loads. `README`, `CHANGELOG`, `LICENSE`, and `docs/` are exempt, as are the manifest fields Claude Code shows but never acts on.
- The rules live in one pure module with no I/O, because three different callers feed it from three different sources: git, the GitHub API, and the tagger.
- The same runtime/exempt split exists in `.claude/hooks/lib/plugin-paths.sh`. Changing one without the other is the failure mode; see the repo hooks reference.

## `version_plan.py`

- `EXEMPT_FILE` matches the paths under `plugins/<name>/` that never force a bump.
- `METADATA_KEYS` names the `plugin.json` fields that are catalog metadata, not runtime behaviour.
- `runtime_manifest_changed(before, after)` compares two manifests and ignores changes confined to metadata keys.
- `plugins_touched(changed_files)` maps a diff to the set of plugins that actually changed, and to whether each change was runtime or exempt.
- `plan_versions()` returns the required bump per plugin, ranked `initial < prerelease < patch < minor < major`.
- `bump_label_for(plugins)` collapses the plan into the single `bump:` label a PR should carry.
- `untagged_versions(plugins, existing_tags)` lists every plugin version on disk that has no tag yet.

## `changelog.py`

- `has_changelog_entry(text, version)` detects a Keep a Changelog section of the form `## [X.Y.Z] - YYYY-MM-DD`.
- A bump without its dated entry is an incomplete release, so this check is paired with the version check, never optional.

## `check_versions.py` — entrypoint

- Enforces `ADR-0003` on the current branch: every plugin changed since the merge base with `--base` must bump its `version` and add a dated `CHANGELOG` entry.
- `--deferred` corresponds to the `bump: deferred` PR label and is the only sanctioned way to postpone a bump.
- `--verify-tag` additionally runs `claude plugin tag <dir> --dry-run` for each new or bumped plugin, which needs a clean working tree; CI passes it.
- `--json` emits the plan for a workflow to consume.
- This is the `version-check` job. It fails the PR, so it must never be softened to make a branch merge.

## `tag_versions.py` — entrypoint

- Tags every plugin version that has no `{name}--v{version}` tag yet, using the official `claude plugin tag --push`.
- The official command validates the plugin, checks `plugin.json` against the marketplace entry, refuses a dirty tree, and refuses an existing tag. Reimplementing any of that here would be a second source of truth.
- Idempotent by design: running it twice tags nothing the second time.
- `--dry-run` prints the plan without creating anything.
- Release notes live in each plugin's `CHANGELOG.md`. The tag is the release.

## Tests

- `test_version_plan.py` — the exempt list, metadata-only manifest edits, the touched-plugin mapping, bump ranking, the `bump:` label, and untagged detection.
- `test_changelog.py` — section detection, including a version present with the wrong date format and a date present under the wrong version.
