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
  - ".claude/skills/release-plugin/**"
  - ".claude/skills/plugin-versioning/**"
---

# Versioning, tags and releases

- Policy, levels, branches and the release steps: `docs/releasing.md`; maintainers release with the `release-plugin` skill (ADR release-orchestration), which stops at the open pull request, and `/github-ops:automatic-pr-lifecycle` handles reviews and the merge.

- Only plugins are versioned and tagged. The catalog has no `version` (top-level or `metadata.version`); its history is the root `CHANGELOG.md` with `## YYYY-MM-DD` sections.
- The official tag format is `<name>--v<version>` (double hyphen, lowercase `v`).
- `claude plugin tag` creates an annotated tag; whether it is signed depends on git's `tag.gpgsign`, so check it with `git tag -v`.
- `claude plugin tag` refuses a plugin directory with uncommitted changes and a tag that already exists, unless `--force` is passed.
- Each plugin has independent SemVer and the version lives only in `plugin.json`; Claude Code does not validate SemVer.
- release-please was rejected because its commits and tags are not signed with my key.
- The merge to `main` with a bump is the release users receive; the tag and GitHub Release are the signed record and serve dependency ranges, and Claude Code reads them only to resolve a dependent plugin's version constraint on this plugin, never to install a plugin itself (docs: host-marketplace, dependencies; checked 2026-10-04 on 2.1.289).
- Every workflow, script and doc that consumes tags matches exactly `<name>--v<semver>`, never `v*` or `<name>-v*`.
- A full release in a throwaway clone verified the tag signature: `git tag -v` reports a good ED25519 signature.
- Release dates are UTC.
- If `version` is set and not bumped, users never receive the new commits.
