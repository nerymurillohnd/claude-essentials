---

status: accepted
date: 2026-09-22
decision-makers: Nery Samuel Murillo
consulted: Claude Code (Opus 5) — live Claude Code, Ruff, ShellCheck, shfmt and uv documentation, and a GitHub survey of comparable hooks and plugins
informed: Contributors to this repository

supersedes: none
superseded-by: none

---

# ADR-0007: Quality gates ship as plugin hooks that run only installed tools, and test suites live in the repository

## Context and Problem Statement

`ruff-quality` 0.1.x and `shell-quality` 0.1.x installed their gates through a skill: a
`manage.sh` script copied a handler into the user's `.claude/hooks/`, merged hook groups into
a `settings.json`, and optionally wrote a bundled configuration profile. Measured on
2026-09-21 and 2026-09-22, that model drifts and leaks:

- The copied handler freezes. Updating the plugin never reaches it, so a user keeps running
  the old gate under a new plugin version, and nothing tells them.
- A bundled profile is silently replaced by the tools' own discovery: a nested
  `pyproject.toml` with `[tool.ruff]`, a `.ruff.toml` beside the profile, a closer
  `.shellcheckrc` or `~/.shellcheckrc` all win over it (Ruff and ShellCheck docs; reproduced
  with Ruff 0.16.8 and ShellCheck 0.11.0).
- The maintainer tooling installed CPython 3.8 into the maintainer's global uv store on every
  `make check`, and ad-hoc `uv run --python X` calls installed 3.9 and 3.13. A hook that ran
  `uv run ruff` or `uvx ruff` would do the same on a user's machine, and without `uv` on the
  hook's `PATH` it exits 127, which Claude Code treats as a non-blocking error: the edit
  passes unchecked.
- Test suites shipped inside `plugins/`, so every user's cache carried the maintainer's tests.

How should a quality gate reach users so that what runs is always what the plugin version
says, uses the user's own configuration, never changes their machine, and fails visibly?

## Decision Drivers

- What runs on a user's machine must follow the installed plugin version.
- A hook never installs or downloads anything, and never runs through `uv`/`uvx`.
- The user's own configuration governs; the plugin adds enforcement, not a style.
- A missing tool is said, once, and never silently skipped or blocking.
- The plugin ships only what users run.
- Weight comparable to the references (the official hooks-guide examples; alexfazio/plankton,
  TheBushidoCollective/han, melodic-software's ruff-format, surveyed 2026-09-22).

## Considered Options

- Keep the script-installed gate, with version checks and pinned configuration added.
- Ship the gate as plugin hooks (`hooks/hooks.json`) that run installed tools with native
  configuration discovery.
- Ship plugin hooks that fall back to `uvx` when the tool is missing.

## Decision Outcome

Chosen option: "Ship the gate as plugin hooks that run installed tools with native
configuration discovery", because it removes the freeze (Claude Code runs the new version's
hooks after an update), removes every write to the user's settings and configuration, and
matches the surveyed references, none of which runs `uvx` in a hook.

1. A gate plugin is one knowledge skill plus `hooks/hooks.json` and its handler in the
   plugin's root `scripts/` (`scripts/<name>.sh`), the layout the plugins reference shows;
   component directories sit flat at the plugin root, never nested. The user chooses where it applies with the plugin's install scope, and
   turns it off with the plugin's `enabled` option.
2. The handler runs the tool from the project's own environment or the global `PATH`, never
   `uv`/`uvx`, never a download. Runtime boundary B1 keeps `uv` and `uvx` forbidden in shipped
   scripts.
3. Configuration is the tool's own discovery. No plugin ships or writes a configuration file.
4. The gate fixes and formats what the tool can fix safely, reports the rest to Claude, and at
   Stop keeps Claude working while the findings change, for at most 7 attempts, before
   telling the user what failed (Claude Code itself ends a turn after 8 consecutive Stop
   continuations). A tool or configuration error is reported, never looped on.
5. Before an edit adds a suppression or changes tool configuration, the gate asks the user
   (`permissionDecision: "ask"`); it never denies.
6. Plugin test suites live in `scripts/plugin_validation/suites/<id>/`, not in the plugin.
   Exception: `block-no-verify`'s installer runs its own suite at install time, so there the
   suite is runtime and stays in the plugin until that plugin moves to this model.

### Consequences

- Good, because a plugin update is the whole update: no copy on disk can fall behind.
- Good, because the user's configuration is the only configuration, so nothing can silently
  override a profile, and nothing needs migrating.
- Good, because no gate touches the user's toolchain or needs network.
- Bad, because a gate is on in every project of the scope it is installed in; turning it off
  per project means `enabledPlugins` or the `enabled` option.
- Bad, because a file that was never formatted is reformatted whole the first time Claude edits
  it (accepted by the maintainer, 2026-09-22; each plugin's README says so).
- `block-no-verify` still installs through its script and remains the documented exception.

### Risks and mitigations

| Risk | Likelihood or condition | Impact | Mitigation or response | Owner |
| --- | --- | --- | --- | --- |
| The tool is missing on a user's machine | Any machine without it | The gate cannot check | One `systemMessage` per session with install commands; nothing blocks | Plugin maintainer |
| The hook's `PATH` is minimal (GUI-launched Claude Code) | macOS apps | A global tool is not found | The handler also looks in `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin` | Plugin maintainer |
| A `SHELLCHECK_OPTS` in the user's environment disables checks | When set | Findings hidden | Respected as the user's configuration and named in every report | Plugin maintainer |

### Confirmation

| Criterion or claim | Verification method | Evidence or result | Responsible party | Review condition |
| --- | --- | --- | --- | --- |
| Hooks behave as described | `scripts/plugin_validation/suites/{ruff,shell}-quality/test-gate.sh` under `bash` and `/bin/bash` (`make test-slow`) | 75 and 61 cases passing (61 plus 1 skip on a machine with the tools at a fixed fallback path), 2026-09-22 | Maintainer | Every change to a handler |
| No shipped script runs `uv`/`uvx` | B1 (`scripts/plugin_validation/runtime_boundary.py`) in `make validate` | Passing | Maintainer | Every change under `plugins/` |
| No gate installs an interpreter | `test_the_python_smoke_run_never_installs_an_interpreter` | Passing | Maintainer | Every change to `run_plugin_suites.py` |
| Hooks load and fire in a real session | `claude -p --plugin-dir` in a scratch project: Write and Edit of a failing file, a `# noqa` edit, Stop | Both plugins, 2026-09-22 on 2.1.278: block, fix, `✓ clean`, Stop `✓`; the guard returned `ask`. The run found that `Edit(...)` in a hook `if` skips the Write tool; fixed with `Write(...)` twins and gated by H7 | Maintainer | Before the PR is marked ready |

## More Information

- Claude Code hooks reference (exit codes, `decision`, `additionalContext`, the 8-continuation
  cap, `systemMessage`): https://code.claude.com/docs/en/hooks
- Plugin hooks, `userConfig`, caching and updates: https://code.claude.com/docs/en/plugins-reference
- Ruff configuration discovery: https://docs.astral.sh/ruff/configuration/
- ShellCheck rc files and `SHELLCHECK_OPTS`: https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md
- uv `python-downloads`: https://docs.astral.sh/uv/reference/settings/
