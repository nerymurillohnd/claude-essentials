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
- `tests/test_integrity.py` reads the sources with `ast` and fails for silent defects: a test class that is not a `TestCase`, a renamed or duplicated test, an unused non-test method, a test or `assert*` helper with no assertion that can fail, a constant, `or True` or `x == x` assertion, and a module-level name in `scripts/*.py` that nothing in the tracked files mentions. Every rule has a negative test on a synthetic source. A test helper that asserts must be named `assert_*`, or the tests using it count as asserting nothing.
- Ruff and basedpyright skip scripts without a `.py` extension when they scan a directory, and basedpyright has no rule for missing return annotations (ruff `ANN201`–`ANN206` is the only one). `EXTENSIONLESS_SCRIPTS` in `scripts/check.py` passes each such script to the `python` gate by name; the integrity tests fail when a tracked file with a Python shebang and no extension is missing from it.
- The tests mutate the fixture plugin `tests/fixtures/plugins/sample-plugin/`, which `RepositoryFixture.install_fixture_plugin` adds to each temporary copy with its catalog entry, label and labeler rules; they never depend on a catalog plugin, so adding or removing one cannot break them.
- The fixture is never listed in the real catalog. Keep it a valid plugin: the `repo` gate must pass on it and Prettier checks its files.
- `.pre-commit-config.yaml` runs ruff (`ruff-check --fix`, `ruff-format`) and basedpyright (`--warnings`) through prek on every commit. Hook `rev`s equal `RUFF_VERSION` and `BASEDPYRIGHT_VERSION` in `scripts/check.py` (ruff with a `v` prefix, basedpyright without); change them together after reading the release notes of every version in between.
