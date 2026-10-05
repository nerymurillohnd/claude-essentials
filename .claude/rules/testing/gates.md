---
paths:
  - "scripts/**"
  - "tests/**"
  - "pyrightconfig.json"
  - "shellcheckrc"
  - ".pre-commit-config.yaml"
  - "docs/testing.md"
---

# Validation and gates

- The single entry point is `scripts/check.py`: 10 gates, the same command locally and in CI.
- The gates are validate, repo, adrs, readmes, docs, tests, format, python, workflows and schemas.
- The `docs` gate (`scripts/check_docs.py`) fails when a copy of `repo.MIN_CLAUDE_CODE`, the gate list, a script or `check.py` target name, a rule's `paths`, a relative link, a `docs/*.md` reference or a project skill's `name` drifts from the code; when such a sentence moves, update `PIN_SITES` in that script. `validate` also checks the project's own `.claude/` skills and agents.
- The `repo` gate (`scripts/check_repo.py`) checks the catalog, names, SemVer, changelogs, READMEs, portability, self-containment, plugin scripts (shebang ⇔ mode 755, `#!/usr/bin/env <interpreter>` without a version, run by path), mods, labels, the tag pattern and local-only pre-commit hooks.
- No repository dependency and no tool version: standard-library scripts run by path through their shebang, and every gate runs the tool found on PATH (prettier, ruff, basedpyright, actionlint, zizmor `--offline`, check-jsonschema with its built-in schemas). `scripts/check.py ci-tools` installs the latest release of each on CI runners (ADR unpinned-tooling-and-shebang-interpreters).
- The repository has no ruff configuration: ruff falls back to my global `~/.config/ruff/ruff.toml`, and CI gets the same file from the `RUFF_CONFIG` Actions variable, which `scripts/check.py ci-tools` writes to the runner's `~/.config/ruff/ruff.toml` and checks that ruff uses (ADR ruff-config-from-actions-variable). After changing the global file, run `gh variable set RUFF_CONFIG < ~/.config/ruff/ruff.toml`. `shellcheckrc` is still a copy of my strict global configuration: change the global file and the copy together. `-S style -a` (my `SHELLCHECK_OPTS`) has no rc equivalent and is not applied in CI.
- Each test injects one defect and checks that the gate fails for that reason only; `scripts/check.py tests` reports the count.
- `tests/test_integrity.py` reads the sources with `ast` and fails for silent defects: a test class that is not a `TestCase`, a renamed or duplicated test, an unused non-test method, a test or `assert*` helper with no assertion that can fail, a constant, `or True` or `x == x` assertion, and a module-level name in `scripts/*.py` that nothing in the tracked files mentions. Every rule has a negative test on a synthetic source. A test helper that asserts must be named `assert_*`, or the tests using it count as asserting nothing.
- Ruff and basedpyright skip scripts without a `.py` extension when they scan a directory, and basedpyright has no rule for missing return annotations (ruff `ANN201`–`ANN206` is the only one). `EXTENSIONLESS_SCRIPTS` in `scripts/check.py` passes each such script to the `python` gate by name; the integrity tests fail when a tracked file with a Python shebang and no extension is missing from it.
- The tests mutate the fixture plugin `tests/fixtures/plugins/sample-plugin/`, which `RepositoryFixture.install_fixture_plugin` adds to each temporary copy with its catalog entry, label and labeler rules; they never depend on a catalog plugin, so adding or removing one cannot break them.
- The fixture is never listed in the real catalog. Keep it a valid plugin: the `repo` gate must pass on it, and Prettier checks its files except `skills/` (ADR skills-excluded-from-prettier).
- `.pre-commit-config.yaml` runs the installed ruff (`ruff check --fix`, `ruff format`) and basedpyright (`--warnings`) through prek on every commit, as `repo: local` hooks with `language: system`; the `repo` gate fails on a remote hook repository or a `rev`.
