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

- The official tag format is `<name>--v<version>` (double hyphen, lowercase `v`), and the marketplace uses `marketplace--v<version>`.
- `claude plugin tag` runs `git tag -a`, which is signed through `tag.gpgsign`; check it with `git tag -v`.
- `claude plugin tag` refuses a dirty tree and a tag that already exists.
- Each plugin has independent SemVer and the version lives only in `plugin.json`; Claude Code does not validate SemVer.
- Deprecations are announced in a minor, the component is kept for at least one more minor and 30 days, and it is removed in the next major.
- `bump_version.py` moves `[Unreleased]` into a section dated in UTC and never commits or tags; the commit and `claude plugin tag` are manual.
- The release workflow checks that tag and manifest match and publishes the changelog section as the GitHub Release.
- Use `uvx git-cliff@2.14.2` only for occasional drafts that are then reviewed.
- release-please was rejected because its commits and tags are not signed with my key.
- There will be no single release command until there are real releases.
