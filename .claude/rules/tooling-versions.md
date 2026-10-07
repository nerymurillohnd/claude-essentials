---
paths:
  - "scripts/**"
  - ".github/**"
  - ".pre-commit-config.yaml"
  - "docs/sourcing-log.md"
  - "THIRD_PARTY_NOTICES.md"
---

# Tools, licenses and pinned Actions

- No tool version is pinned (ADR unpinned-tooling-and-shebang-interpreters, 2026-10-05).
- The gates run the tools on PATH.
- `scripts/check.py ci-tools` installs the latest release of each on CI.
- Never record a tool version here or in a document.
- Tools the gates run: prek (MIT), ruff (MIT), basedpyright (MIT), prettier (MIT), actionlint (MIT), zizmor (MIT), check-jsonschema (Apache-2.0).
- CI installs actionlint from its latest GitHub release with `gh release download`.
- CI checks the release's own checksums file.
- The `download-actionlint.bash` script resolves "latest" to a version written into the script (1.7.11 at commit `914e7df`, checked 2026-10-05).
- Evaluated and deferred: git-cliff (Apache-2.0), commitlint (MIT), markdownlint-cli2 and its action (MIT), lychee-action (Apache-2.0); release-please supports `tag-separator` but stays rejected (see `.claude/rules/releasing.md`).
- GitHub Actions stay pinned by commit SHA, which zizmor requires.
- The version comment next to each SHA is the release it resolves to.
  - `actions/labeler` v7.0.0.
  - `actions/checkout` v7.0.1.
  - `actions/setup-node` v7.0.0.
  - `actions/upload-artifact` v7.0.1.
  - `astral-sh/setup-uv` v10.2.0.
  - `crazy-max/ghaction-github-labeler` v6.0.0 (MIT).
  - `anthropics/claude-code-action` v1.0.241 (MIT; checked 2026-10-04, ships Claude Code 2.1.289).
- `actions/setup-node` takes `node-version: lts/*`, a release channel, not a version.
- Standards: MADR 4.0.0, Contributor Covenant 3.0, Keep a Changelog 1.1.0, Conventional Commits 1.0.0, SemVer 2.0.0.
