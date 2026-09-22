# Versioning a plugin

Every plugin in this marketplace uses **explicit semantic versioning**
([ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)). Claude
Code uses a plugin's `version` as its update cache key: installed users only
receive a change after `version` changes
([version management](https://code.claude.com/docs/en/plugins-reference#version-management)).

## The rule: bump when Claude would load something different

What decides a bump is **which file changed**, not how big the change is.
Claude Code keys its plugin cache on `version`. If runtime content changes
without a bump, users who already have `1.2.0` keep the old copy, and new
installs get the new content, still labeled `1.2.0`. Two different behaviors
then share one version, and bug reports stop being reproducible. In a plugin,
text *is* code: a one-word fix in a `SKILL.md` changes what the model does.

| Surface | Paths (relative to `plugins/<name>/`) | Bump? |
| --- | --- | --- |
| **Runtime**: Claude loads it | `skills/**` (including `references/` and skill scripts), `agents/**`, `commands/**`, `hooks/**`, `.mcp.json`, `.lsp.json`, `output-styles/**`, `monitors/**`, and every `plugin.json` field except the metadata below | **Yes**, at least PATCH |
| **Not runtime**: only people read it | `README.md`, `CHANGELOG.md`, `LICENSE*`, `docs/**` and `evals/**` at the plugin root (eval cases are never loaded by Claude), and `plugin.json` metadata: `description`, `displayName`, `keywords`, `author`, `homepage`, `repository`, `license`, `metadata` | **No** |
| **Anything else** | any path not listed above | **Yes**. The exempt list is closed, so unknown paths count as runtime |

A PR that changes runtime paths must:

1. bump `version` in `plugins/<name>/.claude-plugin/plugin.json`, and
2. add a dated entry `## [X.Y.Z] - YYYY-MM-DD` to `plugins/<name>/CHANGELOG.md`.

A PR that changes only non-runtime paths needs no bump, and its PR gets
`bump: none`. For a notable change of that kind, add a line under
`## [Unreleased]` in the CHANGELOG, which moves into the next versioned
section. It's recommended, not enforced: don't log every README typo.

The `version-check` CI job (`make versions` locally) enforces this
with the same classification (`scripts/versioning/version_plan.py`). Its error lists
the runtime files that need the bump. A change that needs no bump (docs,
READMEs, metadata, tooling) is pushed straight to `main`: the maintainer's
push guard (`.claude/hooks/guard-push.sh`) first requires a clean tree,
`bump: none`, and a passing `make check`, and CI re-runs both after the
push. A change that bumps a version goes through a PR, so `version-check`
gates the merge and the tag workflow runs on it. Never
put `version` in `.claude-plugin/marketplace.json`: the generator doesn't emit
it, and `plugin.json` would silently win anyway.

**Deferring a runtime change:** a maintainer can apply `bump: deferred` to
merge runtime changes without a bump on purpose, for example to batch several
typo fixes in skills into one PATCH. Installed users then don't receive the
change until the next bump. Contributors can't apply labels, so this is a
maintainer decision.

## Which number to bump

| Bump | When | Examples |
| --- | --- | --- |
| MAJOR | Existing users must change something | Removed or renamed a skill, agent, command, hook, MCP server, or argument; changed an invocation name; incompatible behavior; raised the minimum Claude Code version |
| MINOR | New capability, backward compatible | New skill/agent/command, new optional argument, new opt-in hook |
| PATCH | Fix, no new capability | Bug fix; skill or agent wording that corrects behavior |
| Prerelease | Test before a stable release | `2.0.0-beta.1`, `2.0.0-rc.1` |

**Renames are classified by what they rename:**

| Rename | Effect | Bump |
| --- | --- | --- |
| `skills/foo/` → `skills/bar/` | Changes the skill's invocation name unless its frontmatter pins `name` | MAJOR (MINOR pre-1.0) |
| `agents/foo.md` → `agents/bar.md`, or a command file | Changes the agent or command name users invoke | MAJOR (MINOR pre-1.0) |
| A folder inside a skill (e.g. `references/`) | The `SKILL.md` that points to it must change too | PATCH |
| `docs/` of the plugin | Not runtime | none |
| `plugins/<name>/` itself | Renames the plugin; needs a `renames` entry (see below) | MAJOR |

CI enforces *that* a bump happened. Choosing MAJOR over PATCH for a rename is
the reviewer's call, and this table is the reference.

Before `1.0.0`, breaking changes bump MINOR. New plugins usually start at
`0.1.0`. Move to `1.0.0` once the interface is stable. Version strings are
canonical semver without a `v` prefix or build metadata.

Prereleases are excluded from other plugins' dependency ranges unless the
range opts in (`^2.0.0-0`). Users installing from `main` do receive them,
though, because the latest version in the catalog is what gets installed.

## How a version reaches users

Plugins aren't packages: there's nothing to download and no GitHub Release.
Once a bumped version is merged to `main`, the marketplace catalog serves it.
Installed users get it through `/plugin update`, or automatically if they
enabled auto-update for this marketplace.

The `Tag plugin versions` workflow (`.github/workflows/tag-versions.yml`) runs
on every push to `main` that touches `plugins/**`. For each plugin version
without a tag, it runs the official `claude plugin tag plugins/<name> --push`.
That command:

- validates the plugin;
- checks that `plugin.json` agrees with the marketplace entry;
- creates the annotated tag `{name}--v{version}` on the merge commit.

That tag is what Claude Code uses to resolve other plugins' version
constraints on yours
([tag plugin releases](https://code.claude.com/docs/en/plugin-dependencies#tag-plugin-releases-for-version-resolution)).
The version's notes are its section in the plugin's `CHANGELOG.md`.

The workflow is idempotent: re-running it tags only what's missing. Tags
matching `*--v*` are protected against updates and deletion, so a tagged
version is never moved. To fix a bad version, ship a new one.

Run `python -m scripts.versioning.tag_versions` without `--dry-run` only in that workflow: it
relies on a fresh checkout whose tags mirror `origin`. Locally, use
`--dry-run`.

Before merge, CI runs the same `claude plugin tag --dry-run` (the `--verify-tag`
flag of `check-versions`), so tagging on `main` doesn't fail on a problem that
could have been caught in review.

## Removing or renaming a plugin

Add the old name to `renames` in `.claude-plugin/marketplace.json`: `null` if
it was removed, the new name if it was renamed. `renames` is append-only
history ([renames](https://code.claude.com/docs/en/plugin-marketplaces)).
`version-check` fails a removal that has no `renames` entry. The PR gets the
`bump: major` label.

## Commands

```bash
make versions                  # compare against origin/main
make versions VERSIONS_ARGS="--base main"   # compare against another ref
make -s versions VERSIONS_ARGS=--json        # machine-readable plan
make versions VERSIONS_ARGS=--verify-tag   # also run claude plugin tag --dry-run (needs a clean tree)
.venv/bin/python -m scripts.versioning.tag_versions --dry-run  # which versions the tagging workflow would tag
```
