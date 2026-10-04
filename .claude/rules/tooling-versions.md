---
paths:
  - "scripts/**"
  - ".github/**"
  - ".pre-commit-config.yaml"
  - "docs/sourcing-log.md"
  - "THIRD_PARTY_NOTICES.md"
---

# Tooling versions (checked 2026-10-03; re-check before pinning)

- git-cliff 2.14.2 (Apache-2.0), commitlint 21.2.3 (MIT), markdownlint-cli2 0.23.3 and its action v24.2.0 (MIT).
- prek 0.5.4 (MIT), astral-sh/ruff-pre-commit v0.16.10, DetachHead/basedpyright-prek-mirror 1.40.1 (checked 2026-10-04; ruff 0.16.6–0.16.10 and basedpyright 1.39.8–1.40.1 release notes reviewed: basedpyright 1.40.0 dropped Python 3.8 and 3.9 from its PyPI package).
- prettier 3.9.9 (MIT), actionlint 1.7.12 (MIT), zizmor 1.30.1 (MIT), lychee-action v2.9.0 (Apache-2.0).
- actions/labeler v7.0.0, actions/checkout v7.0.1, actions/setup-node v7.0.0, astral-sh/setup-uv v10.2.0, crazy-max/ghaction-github-labeler v6.0.0 (MIT), anthropics/claude-code-action v1.0.241 (MIT; checked 2026-10-04, ships Claude Code 2.1.289).
- check-jsonschema 0.38.2 (Apache-2.0) (checked 2026-10-04).
- MADR 4.0.0, Contributor Covenant 3.0, Keep a Changelog 1.1.0, Conventional Commits 1.0.0, SemVer 2.0.0.
- release-please v17.11.2 supports `tag-separator`, but it stays rejected (see `.claude/rules/releasing.md`).
