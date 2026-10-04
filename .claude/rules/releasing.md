---
paths:
  - "CHANGELOG.md"
  - "plugins/**/CHANGELOG.md"
  - "plugins/**/.claude-plugin/plugin.json"
  - ".claude-plugin/marketplace.json"
  - "scripts/bump_version.py"
  - "scripts/release_notes.py"
  - ".github/workflows/release.yml"
  - "docs/releasing.md"
  - "templates/changelog/**"
---

# Versioning, tags and releases

- Only plugins are versioned and tagged. The catalog has no `version` (top-level or `metadata.version`); its history is the root `CHANGELOG.md` with `## YYYY-MM-DD` sections.
- The official tag format is `<name>--v<version>` (double hyphen, lowercase `v`).
- `claude plugin tag` runs `git tag -a`, which is signed through `tag.gpgsign`; check it with `git tag -v`.
- `claude plugin tag` refuses a dirty tree and a tag that already exists.
- Each plugin has independent SemVer and the version lives only in `plugin.json`; Claude Code does not validate SemVer.
- A component inside a plugin is deprecated in a plugin minor, kept for at least one more minor and 30 days, and removed in the plugin's next major.
- A whole plugin is deprecated the same way, then removed from the catalog in a pull request with a `renames` entry and a dated root changelog note (`docs/releasing.md`).
- Every change inside `plugins/<name>/` ships with a single-step bump of that plugin in the same pull request; a pull request may release several plugins and carries exactly one `semver:` label naming the highest bump among the plugins it releases. New plugins start at `0.1.0` and need no label.
- `plugins/**`, `marketplace.json`, workflows and `CODEOWNERS` change only through pull requests; docs, scripts, tests, rules and ADRs may be pushed directly by me after `python3 scripts/check.py` passes.
- `bump_version.py` moves `[Unreleased]` into a section dated in UTC and never commits or tags; the commit is part of the pull request, and `claude plugin tag` runs on the merged commit.
- The release workflow checks that tag and manifest match and publishes the changelog section as the GitHub Release.
- Use `uvx git-cliff@2.14.2` only for occasional drafts that are then reviewed.
- release-please was rejected because its commits and tags are not signed with my key.
- There will be no single release command until there are real releases.
- Every workflow, script and doc that consumes tags matches exactly `<name>--v<semver>`, never `v*` or `<name>-v*`.
- A full release in a throwaway clone verified the tag signature: `git tag -v` reports a good ED25519 signature.
- Release dates are UTC.
- If `version` is set and not bumped, users never receive the new commits.
