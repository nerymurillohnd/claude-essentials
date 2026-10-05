---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Unpinned tooling, and the shebang chooses the interpreter

## Purpose

Stop pinning the versions of the tools and the Python interpreter the repository runs, and make every script, in the repository and in plugins, choose its interpreter through its shebang.

## Scope

- Repository tooling: `scripts/`, `tests/`, `scripts/git-hooks/commit-msg`, `ruff.toml`, `pyrightconfig.json`, `.pre-commit-config.yaml`, `.github/workflows/`, and every document, rule, skill or agent that shows how to run a script or names a tool version.
- Plugin scripts: every file under `plugins/<name>/` that a hook, monitor, MCP server, LSP server or `bin/` entry runs.
- Out of scope, unchanged: the commit SHAs of GitHub Actions and of the actionlint download script (integrity, not tool versions; zizmor requires the Action SHAs), `repo.MIN_CLAUDE_CODE` and `metadata.minClaudeCodeVersion` (the minimum a plugin declares to its users, shown in the README badges), plugin SemVer versions and their badges.

## Context and problem statement

The repository has no runtime, no `pyproject.toml`, no `package.json` and no lockfile. Its gates run tools that are already installed on the maintainer's machine, yet the repository pins each of them (`*_VERSION` constants in `scripts/check.py`, `rev`s in `.pre-commit-config.yaml`, uv and Node versions in `validate.yml`, the Claude Code version in `release.yml`), pins a Python floor (`target-version` in `ruff.toml`, `pythonVersion` in `pyrightconfig.json`), and runs gates that keep the pins and the documents in step. Every tool release then becomes repository work, and the pins describe versions other than the ones that actually run.

Every script already starts with `#!/usr/bin/env python3` and is executable, but documents, CI and the scripts themselves start them with `python3 scripts/<name>.py` or `sys.executable`, so the shebang never chooses anything.

Plugin scripts run on each user's machine, which neither the maintainer nor CI can stand in for. The official docs run a plugin script by its path and require it to be executable: the plugin hooks example uses `"${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"` and says "make it executable" ([plugin components](https://code.claude.com/docs/en/plugins/components#hooks)); the hooks guide says "Hook scripts must be executable for Claude Code to run them" ([hooks guide](https://code.claude.com/docs/en/hooks-guide#block-edits-to-protected-files)); `bin/` executables need `chmod +x`. Installation keeps the executable bit: 2.1.86 "Fixed official marketplace plugin scripts failing with 'Permission denied' on macOS/Linux since v2.1.83" ([changelog](https://code.claude.com/docs/en/changelog)). No rule or gate requires a shebang or mode 755 in `plugins/` today, and the hooks rule shows an interpreter in front of the script (`bun "${CLAUDE_PLUGIN_ROOT}/…"`).

## Decision drivers

- Nothing in the repository is consumed by users except `plugins/`; the tooling runs on the maintainer's machine and on CI runners, each with its own installed tools.
- No version is recorded that someone must keep in step with what is installed.
- The interpreter is chosen in one place, the script's shebang.
- Plugin scripts follow the documented pattern and stay portable across users' machines.
- Gates are never weakened: a failure caused by a new tool release is fixed at its root.

## Considered options

- Unpinned tooling, shebang-chosen interpreters, and a plugin-script gate
- Keep the pins (status quo)
- Pin through a manifest and lockfile (`pyproject.toml`, `package.json`)

## Decision outcome

Chosen option: **unpinned tooling, shebang-chosen interpreters, and a plugin-script gate**, because the tools already run where the gates run, the repository has no environment to lock, and the docs define how a plugin script is run.

### Repository tooling

- Scripts are run by path: `scripts/check.py`, never `python3 scripts/check.py`. Documents, rules, skills, agents, workflows and the PR template use that form.
- A script that runs another script runs it by path, so the child's shebang chooses its interpreter; `sys.executable` is no longer used to start scripts. Running a module of the current interpreter (`-m unittest`) is not starting a script and keeps `sys.executable`.
- There is no Python floor: `target-version` leaves `ruff.toml` and `pythonVersion` leaves `pyrightconfig.json`. Without a target, ruff's linter applies no version-specific syntax check (`linter.unresolved_target_version = none`, checked with ruff 0.16.10), and basedpyright takes the version of the interpreter it finds.
- No tool version is pinned anywhere:
  - `scripts/check.py` keeps no `*_VERSION` constants;
  - locally, each gate runs the binary found on PATH, including zizmor, which stops running as `uvx zizmor@<version>`;
  - `scripts/check.py ci-tools` installs the latest release of each tool on CI runners; actionlint comes from its latest GitHub release, checked against the checksums file the release publishes, because its download script resolves "latest" to a version written into the script;
  - `validate.yml` sets no uv version and asks `actions/setup-node` for the `lts/*` channel, not a version; `release.yml` installs the latest Claude Code;
  - `.pre-commit-config.yaml` uses `repo: local` hooks with `language: system`, so prek runs the installed ruff and basedpyright and has no `rev`.
- The checks that kept pins in step are removed with their tests: the pre-commit `rev` check in `scripts/check_repo.py` and the pin checks in `scripts/check_docs.py`.
- Documents list tools and licenses without versions (`.claude/rules/tooling-versions.md`, `docs/sourcing-log.md`, `.claude/rules/testing/gates.md`, `docs/testing.md`).

### Plugin scripts

- A plugin script starts with `#!/usr/bin/env <interpreter>`; the interpreter name carries no version (`python3`, never `python3.12`) and the shebang names no absolute interpreter path.
- A file with a shebang is mode 755 in git, and an executable file has a shebang. A file that is only sourced or imported has neither.
- Hooks, monitors, MCP servers and LSP servers run a plugin script by its path (`"${CLAUDE_PLUGIN_ROOT}/scripts/x.sh"`), never with an interpreter in front of it; tools the user installs (`npx <package>`, `uvx <package>`) are not plugin scripts.
- The `repo` gate checks the three rules above, with injected-defect tests on the fixture plugin.

### Consequences

- Good, because there is nothing to bump, and no document can drift from an installed version.
- Good, because the gates run the tools that are actually installed, and the shebang alone decides the interpreter.
- Good, because plugin scripts follow the documented pattern, and a missing shebang or executable bit fails before release instead of on a user's machine.
- Bad, because a new tool release can fail a gate on CI in a pull request that changed nothing related; the fix goes to the code or the configuration, never to a silent pin. Pinning again needs a new ADR.
- Bad, because the maintainer's tools and CI's can differ in version, so a gate can pass on one and fail on the other until both are on the latest release.
- Bad, because the maintainer's `python3` and CI's can differ (3.14 and 3.12 on 2026-10-05): a script that uses newer syntax passes locally and fails on CI, which is the intended signal.

### Confirmation

- The plugin-script gate fails on each injected defect: a shebang without mode 755, mode 755 without a shebang, a versioned or absolute interpreter, and an interpreter in front of a plugin script in `hooks.json`, a monitor, `.mcp.json` or `.lsp.json`.
- No `*_VERSION` constant, `rev`, `target-version`, `pythonVersion`, uv or Node version, or Claude Code install version remains in the repository; no document or skill runs a script through `python3`; the `repo` gate fails on a remote pre-commit hook repository or a `rev`.
- `scripts/check.py`, and `scripts/check.py test-install` on HEAD, pass locally and on CI with the latest tools.
- `scripts/sync_readmes.py --check` passes and no README badge changes.
- Revisit if new tool releases break CI more often than they help, or if the repository gains a runtime environment.

## Pros and cons of the options

### Unpinned tooling, shebang-chosen interpreters

- Good, because it removes every version that someone must keep in step with what is installed.
- Bad, because CI results depend on the latest releases at run time.

### Keep the pins

- Good, because a tool release cannot change CI results without a reviewed bump.
- Bad, because every release becomes repository work, and the pins describe versions other than the ones the maintainer runs.

### A manifest and lockfile

- Good, because one file would hold every version.
- Bad, because it adds an environment, an install step and a lockfile to a repository that has no runtime, which [ADR validation-stack](ADR_2026-10-03_validation-stack.md) already rejected.

## More information

This record replaces part of [ADR validation-stack](ADR_2026-10-03_validation-stack.md) (scripts run with `python3`, `sys.executable`, the Python 3.12 minimum, pinned CI tools and pre-commit `rev`s) and part of [ADR minimum-claude-code-version](ADR_2026-10-03_minimum-claude-code-version.md) (CI installs exactly the pinned version); both keep the rest of their decisions and get a dated pointer note. Approved by the maintainer in the Claude Code session of 2026-10-05.
