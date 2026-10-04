# Releasing

How plugin and marketplace versions, changelogs, tags, releases and labels work. Decisions: [ADR per-plugin-versioning](adr/decisions/ADR_2026-10-03_per-plugin-versioning.md), [ADR release-automation](adr/decisions/ADR_2026-10-03_release-automation.md), [ADR labels-and-pr-automation](adr/decisions/ADR_2026-10-03_labels-and-pr-automation.md).

**Contents:** [Versions](#versions) · [Commit messages](#commit-messages) · [Changelogs](#changelogs) · [Release a plugin](#release-a-plugin) · [Release the marketplace](#release-the-marketplace) · [Deprecate or remove a plugin](#deprecate-or-remove-a-plugin) · [Labels](#labels)

## Versions

Each plugin has its own [SemVer](https://semver.org/spec/v2.0.0.html) version in `plugins/<name>/.claude-plugin/plugin.json`, and only there. Claude Code reads `plugin.json` first, and users receive a new copy only when that version changes ([versions and updates](https://code.claude.com/docs/en/plugins/loading#versions-and-updates)). The marketplace has its own version in `.claude-plugin/marketplace.json`.

| Bump  | When                                | Examples                                                                                                     |
| ----- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| MAJOR | Users must change something         | Renamed or removed skill, agent or command; changed hook behavior; a new required setting; removed component |
| MINOR | New, backward-compatible capability | New skill, agent or option with a default                                                                    |
| PATCH | Fixes and documentation             | Bug fix, clearer instructions, README changes                                                                |

A MAJOR release needs a `### Migration` section stating what broke, who is affected and the exact steps to adapt.

## Commit messages

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), checked by `scripts/check_commit_msg.py` in CI and in the optional `commit-msg` hook:

```text
<type>(<scope>)!: <subject>

<body>

BREAKING CHANGE: <what breaks>
```

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Scope: the plugin name for plugin changes; `marketplace`, `scripts`, `ci` or `docs` otherwise.
- `!` or a `BREAKING CHANGE:` footer marks a breaking change and requires the `semver:major` label.

## Changelogs

Each plugin has `CHANGELOG.md` in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format; the marketplace has the root `CHANGELOG.md`. Contributors add notes under `## [Unreleased]` with the change types `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` and `Migration`. Notes are written for users: what changed for them, not how the code changed.

## Release a plugin

A release is a short sequence of explicit steps. They are deliberately not bundled into one command: that will make sense after the first real releases show which steps belong together ([ADR release-automation](adr/decisions/ADR_2026-10-03_release-automation.md)).

Requirements: a clean working tree on `main`, signing configured for commits and tags, Claude Code 2.1.289 or later.

1. **Notes.** Make sure `## [Unreleased]` in `plugins/<name>/CHANGELOG.md` describes every user-relevant change. To draft notes from history once there is enough of it, optionally run git-cliff without installing anything, and then rewrite the draft for users:

   ```bash
   uvx git-cliff@2.14.2 --include-path "plugins/<name>/**" --tag-pattern "^<name>--v" --unreleased
   ```

   The draft only lists commits; it never decides the bump and is never written to the changelog automatically.

2. **Bump.** Preview, then prepare the files:

   ```bash
   python3 scripts/bump_version.py plugin <name> <major|minor|patch> --dry-run
   python3 scripts/bump_version.py plugin <name> <major|minor|patch>
   ```

   The script refuses an empty `[Unreleased]`, a MAJOR without Migration, and a changelog that disagrees with `plugin.json`. It moves the notes into `## [<version>] - <date>` (UTC), bumps `plugin.json`, regenerates the README content that shows the version, and runs `claude plugin validate --strict` and `scripts/check_repo.py`. It does not commit, tag or push.

3. **Review and commit.** Read `git diff`, then commit (signed by your git configuration):

   ```bash
   git add plugins/<name> README.md
   git commit -m "chore(<name>): release <version>"
   ```

4. **Tag.** `claude plugin tag` checks that `plugin.json` and the catalog agree and creates the annotated tag `<name>--v<version>`, signed when `tag.gpgsign` is on. Verify the signature:

   ```bash
   claude plugin tag plugins/<name>
   git tag -v <name>--v<version>
   ```

5. **Publish, only when approved.** `git push origin main <name>--v<version>`. The push runs `.github/workflows/release.yml`, which checks the tag against `plugin.json` (`scripts/release_notes.py verify`), validates the plugin and publishes a GitHub Release whose notes are that version's changelog section (`scripts/release_notes.py notes`).

When protected branches require pull requests, do steps 2 and 3 on a branch, open a pull request with the `semver:` label, merge it, then run step 4 on the merged commit.

## Release the marketplace

Same steps on the root `CHANGELOG.md` and `marketplace.json`:

```bash
python3 scripts/bump_version.py marketplace <major|minor|patch>
git add CHANGELOG.md .claude-plugin/marketplace.json README.md
git commit -m "chore(marketplace): release <version>"
git tag -a marketplace--v<version> -m "marketplace <version>"
git tag -v marketplace--v<version>
```

Release the marketplace when plugins are added, deprecated or removed, or when distribution changes.

## Deprecate or remove a plugin

This section covers a whole plugin. To remove a component inside a plugin (a skill, agent, hook or command), deprecate it under `### Deprecated` in a plugin minor, keep it for at least one further minor release and 30 days, and remove it in the plugin's next major with a `### Migration` section.

1. Deprecate in a MINOR release: add `### Deprecated` with the replacement and the planned removal, and state it in the README Overview.
2. Keep the plugin for at least one further minor release and 30 days.
3. Remove it in a marketplace release: delete the entry and directory, add `"renames": { "<name>": null }` to `marketplace.json` (append-only), and note it in the root changelog. Never rename a published plugin unless a `renames` entry maps the old name to the new one ([rename or remove a plugin](https://code.claude.com/docs/en/plugins/host-marketplace#rename-or-remove-a-plugin)).

## Labels

Labels are defined in `.github/labels.yml` and synced by the Labels workflow. Path labels (`plugin:`, `category:`, `type:docs`, `type:chore`, `security-review`) are applied by the labeler; issue forms apply `status:needs-triage` and a `type:`. Maintainers apply one `semver:` label to every pull request that changes a plugin; `scripts/check_pr.py` enforces it. Release-note categories in `.github/release.yml` follow the same taxonomy.
