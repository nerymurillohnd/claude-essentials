---
paths:
  - "scripts/**"
  - "tests/**"
  - "ruff.toml"
  - "pyrightconfig.json"
  - "shellcheckrc"
  - ".pre-commit-config.yaml"
  - "docs/testing.md"
---

# Validation and gates

- The single entry point is `python3 scripts/check.py`: 10 gates, the same command locally and in CI.
- The gates are validate, repo, adrs, readmes, docs, tests, format, python, workflows and schemas.
- The `docs` gate (`scripts/check_docs.py`) fails when a copy of a pin, the gate list, a script or `check.py` target name, a rule's `paths`, a relative link, a `docs/*.md` reference or a project skill's `name` drifts from the code; when a pinned sentence moves, update `PIN_SITES` in that script. `validate` also checks the project's own `.claude/` skills and agents.
- The `repo` gate (`scripts/check_repo.py`) checks the catalog, names, SemVer, changelogs, READMEs, portability, self-containment, mods, labels, the tag pattern and the local hook pins.
- No repository dependency is used: standard-library scripts run with `python3`, and tools resolved on PATH locally and pinned in CI, except zizmor, which always runs pinned through `uvx zizmor@<version>`.
- Pinned versions: prettier 3.9.9, actionlint 1.7.12, zizmor 1.30.1 (offline) and check-jsonschema 0.38.2 with its built-in schemas.
- `ruff.toml` and `shellcheckrc` are copies of my strict global configurations, so CI applies the same rules as my machine: change the global file and the copy together. `-S style -a` (my `SHELLCHECK_OPTS`) has no rc equivalent and is not applied in CI.
- Each test injects one defect and checks that the gate fails for that reason only; `python3 scripts/check.py tests` reports the count.
- `.pre-commit-config.yaml` runs ruff (`ruff-check --fix`, `ruff-format`) and basedpyright (`--warnings`) through prek on every commit. Hook `rev`s equal `RUFF_VERSION` and `BASEDPYRIGHT_VERSION` in `scripts/check.py` (ruff with a `v` prefix, basedpyright without); change them together after reading the release notes of every version in between.
- Markdownlint, link checking and Dependabot were deferred.
