# Ruff configuration in depth

Verified against Ruff 0.16.8 and
[docs.astral.sh/ruff/configuration](https://docs.astral.sh/ruff/configuration/)
on 2026-09-19.

## Discovery edge cases

| Situation | What Ruff does |
| --- | --- |
| `.ruff.toml`, `ruff.toml`, and `pyproject.toml` in one directory | Uses `.ruff.toml`, then `ruff.toml`, then `pyproject.toml` |
| `pyproject.toml` without `[tool.ruff]` | Skipped; discovery keeps walking up |
| A nested `ruff.toml` in `pkg/` | Files under `pkg/` use only that file; the root file is ignored unless `extend` points at it |
| No project configuration at all | The user-level file (`~/.config/ruff/{.ruff.toml,ruff.toml,pyproject.toml}`), else built-in defaults |
| `--config path/to/ruff.toml` | That file applies to every checked file; its relative paths resolve from the current directory |
| `--config "lint.select = ['F']"` | Overrides one key in every resolved configuration |
| `--isolated` | Ignores every configuration file |
| `~/Library/Application Support/ruff` on macOS | Still read but deprecated; move it to `~/.config/ruff/` |

Relative paths inside a discovered configuration (`exclude`, `src`,
`per-file-ignores` globs) resolve from that configuration's directory.

`exclude` and `extend-exclude` apply only to files Ruff *discovers*. A file
named on the command line is checked anyway unless `--force-exclude` is
passed, or `force-exclude = true` is set in the configuration.

## Rule selection strategy

- **Start from the defaults.** Ruff 0.16's 413 default rules are the
  maintainers' view of low-noise, high-value checks. Add families with
  `extend-select` rather than rebuilding the list with `select`.
- **Add a family, then read its findings.** Run
  `ruff check --statistics --extend-select X .` before adding a family to the
  configuration, so the size of the change is known.
- **`ignore` is for rules that conflict with a decision, not for noise.** A rule
  that fires a lot is usually pointing at real debt; fix it, or discuss it with
  the user, before ignoring it.
- **Per-file policy belongs in `per-file-ignores`, not in comments.** Tests
  legitimately use `assert` (`S101`) and magic values (`PLR2004`); scripts may
  print (`T201`). Declare that once in configuration.
- **Selectors:** a prefix (`"E"`, `"PL"`), a group (`"PLR"`), a single code
  (`"PLR2004"`), or `"ALL"`. Precedence when rules overlap: more specific wins
  (`ALL` < prefix < code). Preview adds category selectors (`correctness`,
  `suspicious`, `style`, …).

## The recommended profile, explained

The ruff-hooks skill can install this profile (it is
`skills/ruff-hooks/assets/ruff.toml` in the plugin). It is strict but built to
survive real projects:

| Setting | Why |
| --- | --- |
| `required-version = ">=0.16.0"` | The profile depends on 0.16 defaults; an older Ruff fails loudly instead of checking something else |
| `line-length = 100` | Readable on split screens; the formatter wraps to it |
| `extend-select`, not `select` | Keeps Ruff's 413 defaults, and new defaults in later releases |
| `E`, `W` | Full pycodestyle, minus the four formatter-conflicting codes |
| `N`, `D` (Google convention), `ANN` | Names, docstrings, and annotations make code reviewable and typecheckable |
| `S`, `BLE`, `TRY`, `EM` | Security and exception hygiene |
| `B` (default), `A`, `C4`, `SIM`, `RET`, `RSE`, `PIE`, `PERF`, `FURB`, `FLY`, `PL` | Correctness and simpler code |
| `DTZ`, `PTH`, `LOG`, `G` | Timezone-aware datetimes, pathlib, correct logging |
| `ERA`, `T10`, `PGH`, `RUF` | No commented-out code, no debugger calls, no blanket suppressions, no unused suppressions (`RUF100`) |
| `C90` with `max-complexity = 10` | Functions stay testable |
| `TID` with `ban-relative-imports = "all"` | Absolute imports only |
| Ignored `D100`, `D104`, `D105`, `D107` | Module, package, magic-method, and `__init__` docstrings mostly restate names |
| Tests: `S101`, `PLR2004`, `D`, `ANN` ignored | Tests assert and use literal values by design |
| `[format] docstring-code-format = true` | Code examples inside docstrings are formatted too |

With this profile Ruff 0.16.8 enables 701 rules and reports no formatter
conflicts.

## Common configuration mistakes

| Mistake | Effect | Fix |
| --- | --- | --- |
| `select = [...]` copied from a 0.15 setup | The 0.16 defaults (`I`, `B`, `UP`, `ASYNC`, …) are off | Switch to `extend-select`, or add the families you want explicitly |
| A parent `ruff.toml` expected to apply inside a package that has its own | The package ignores it | Add `extend = "../ruff.toml"` in the nested file |
| `D203` and `D213` listed in `ignore` next to `convention = "google"` | Redundant: the convention already disables them | Remove them from `ignore` |
| `TCH` in `select` | Deprecated alias; still accepted in 0.16.8 | Use `TC` |
| Formatter-conflicting rules selected through a prefix (`Q`, `COM`) | `ruff format` warns; the linter and formatter disagree | Add those codes to `ignore` |
| `exclude` set, file still checked from an editor or hook | The tool names the file explicitly | Pass `--force-exclude`, or set `force-exclude = true` |
| Relaxing `ignore` to get CI green | Debt hidden, not paid | Fix the code; if it is legacy code, baseline it deliberately with the user (see below) |

## Legacy codebases: the user's options (never Claude's shortcut)

When a large existing codebase fails a new rule set, these are the options to
**present to the user**; Claude does not pick one on its own:

1. Fix everything now, rule family by rule family, with `--statistics` to plan.
2. Adopt the rules for new and changed files only, by running Ruff on changed
   files in CI.
3. Baseline with `ruff check --add-noqa="<reason>"` (or `--add-ignore`) once,
   commit it separately, and burn it down; `RUF100` removes entries that
   became unused.
