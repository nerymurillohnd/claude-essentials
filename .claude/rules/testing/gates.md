---
paths:
  - "scripts/**"
  - "tests/**"
  - "ruff.toml"
  - "pyrightconfig.json"
  - "shellcheckrc"
  - "docs/testing.md"
---

# Validation and gates

- The single entry point is `python3 scripts/check.py`: 9 gates, the same command locally and in CI, no Makefile.
- The gates are validate, repo, adrs, readmes, tests, format, python, workflows and schemas.
- The `repo` gate (`scripts/check_repo.py`) checks the catalog, names, SemVer, changelogs, READMEs, portability, self-containment, mods, labels and the tag pattern.
- No repository dependency is used: standard-library scripts run with `python3`, and tools resolved on PATH locally and pinned in CI.
- Pinned versions: prettier 3.9.9, actionlint 1.7.12, zizmor 1.30.1 (offline) and check-jsonschema with its built-in schemas.
- `ruff.toml` and `shellcheckrc` are copies of my strict global configurations, so CI applies the same rules as my machine: change the global file and the copy together. `-S style -a` (my `SHELLCHECK_OPTS`) has no rc equivalent and is not applied in CI.
- The 50 tests each inject one defect and check that the gate fails for that reason only.
- Markdownlint, link checking and Dependabot were deferred.
