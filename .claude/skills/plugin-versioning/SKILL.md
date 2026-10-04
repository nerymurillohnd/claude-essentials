---
name: plugin-versioning
description: Decides whether a change needs a plugin release, which bump level, and whether it goes through a pull request or a direct push. Use when changing anything in plugins/ or .claude-plugin/marketplace.json, writing changelog notes, bumping or tagging a plugin, or before committing, pushing or opening a pull request.
---

# Plugin versioning and release flow

`docs/releasing.md` is the full procedure and wins over this skill if they ever differ. `scripts/check_pr.py` enforces every pull request rule below, and `python3 scripts/check.py` every repository rule.

## When to bump

Claude Code caches each plugin by name and version and delivers a new copy only when `version` in `plugin.json` changes. A plugin change merged without a bump gives users of the same version different files, so:

| Change                                                                                           | Release                                                              |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| Any file inside `plugins/<name>/` (skills, agents, hooks, MCP, README, CHANGELOG, `plugin.json`) | Bump that plugin in the same pull request                            |
| New plugin                                                                                       | No bump: it starts at `0.1.0`; `new_plugin.py` adds the catalog note |
| `marketplace.json` entry (description, category, tags) or `renames`                              | No bump: add a dated note to the root `CHANGELOG.md`                 |
| Scripts, tests, CI, `docs/`, `.github/`, root README, rules, ADRs                                | No bump                                                              |

Only plugins are versioned. The catalog has no `version` (neither top-level nor `metadata.version`) and no tags.

## Bump levels

- **MAJOR**: breaking for the user: a renamed or removed component, changed hook behavior, a new required setting. Needs a non-empty `### Migration` section.
- **MINOR**: a new compatible component or feature, or a component marked deprecated.
- **PATCH**: a fix or documentation change inside the plugin, including a README typo.

## Pull request or direct push

- **Pull request** for `plugins/**`, `.claude-plugin/marketplace.json`, `.github/workflows/**`, `CODEOWNERS`: `check_pr.py` and the security review only run on pull requests.
- **Direct push to `main`** only for docs, scripts, tests, rules, ADRs and the root README, only by the maintainer.
- **Branches** for pull requests are short-lived and deleted on merge, prefixed with the commit scope: `<plugin>/<topic>` (for example `hello-example/add-license`), or `marketplace/`, `scripts/`, `ci/` or `docs/` plus `<topic>` for other work. The `release-plugin` skill creates plugin branches and runs the whole flow below.
- **The merge is the release**: users receive `main`, cached by `version`, so a merged bump reaches them on their next update. The tag after the merge is the signed record; Claude Code does not read it to install.

## Checklists

Every commit is signed and follows Conventional Commits; the project skill `verify` runs `python3 scripts/check.py` before each commit.

Direct push:

```
- [ ] python3 scripts/check.py passes; fix every failure
- [ ] Changed scripts: shebang ⇔ mode 755, checked with git ls-files -s (100755)
- [ ] Signed commit, push to main, then confirm the Validate workflow passes on main
```

Plugin pull request:

```
- [ ] For each changed plugin: user-facing notes under ## [Unreleased] in plugins/<name>/CHANGELOG.md (### Migration for a MAJOR)
- [ ] python3 scripts/bump_version.py plugin <name> <major|minor|patch> --dry-run, then without --dry-run
- [ ] Review git diff: [Unreleased] is empty, the new section matches plugin.json
- [ ] python3 scripts/check.py and python3 scripts/check.py test-install (after committing: it tests HEAD)
- [ ] Exactly one semver: label: the highest bump among the released plugins (none for a new plugin or a non-plugin change)
- [ ] Title scope is the plugin name when one plugin changes, for example fix(<name>): <subject>; a ! title needs semver:major
- [ ] After the merge, for each released plugin: claude plugin tag plugins/<name>, then git tag -v <name>--v<version>
- [ ] Push the tag only when the maintainer approves that exact push
```

## Gotchas

- Never edit `version` by hand: `bump_version.py` also moves the notes, dates the section in UTC and regenerates the README badge; a hand edit fails `check_pr.py`.
- `bump_version.py` refuses an empty `## [Unreleased]`: write the notes first.
- A skipped version (`1.0.0 → 1.2.0`) fails: one pull request is exactly one bump per plugin.
- `[Unreleased]` is always empty on `main`; notes never wait there for a later release.
- Executable bit: ruff EXE001 fails a shebang without the bit and EXE002 the bit without a shebang. Git versions the bit and CI sees only the index, so set both: `chmod +x <file>` and `git update-index --chmod=+x <file>`. Imported modules have no shebang and stay 644 (`.claude/rules/repo-scripts.md`).
- `python3 scripts/check.py ci-tools` installs the pinned tools and runs only on CI.
