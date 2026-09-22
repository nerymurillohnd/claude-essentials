# shell-quality 0.2.0 — design

**Status:** approved by the maintainer on 2026-09-22 (plan `agile-growing-hejlsberg`), built
in the same branch. It replaces the unreleased 0.2.0 design of the same day, which kept the
script-installed gate. **Decision record:** [ADR-0007](../../decisions/adr-0007-gates-ship-as-plugin-hooks.md).
**Canonical user-facing contract:** [`plugins/shell-quality/README.md`](../../../plugins/shell-quality/README.md)
(hooks table, Requirements, Limitations). This spec records the decisions and their
evidence; it does not repeat the README's tables. It mirrors
[the ruff-quality design](2026-09-22-ruff-quality-design.md); only what differs is spelled
out here.

## Goal

Every shell script Claude writes or edits is formatted by shfmt and passes ShellCheck before
Claude finishes, with the tools the user already has and the configuration they already
find, without the plugin installing, downloading or configuring anything.

## What changed from 0.1.x, and why

Same model change as ruff-quality (ADR-0007): the `shell-hooks` skill, its `manage.sh`
installer, its bundled `shellcheckrc` and `editorconfig-shell` profiles and evals 03, 05 and
06 are removed; the gate ships as `hooks/hooks.json` + `scripts/shell-gate.sh`. A bundled rc
was measured to be silently replaced by any nearer `.shellcheckrc` or by `~/.shellcheckrc`
(ShellCheck reads the first rc found and merges nothing; reproduced on 0.11.0).

## Surfaces

| Surface | Decision | Why |
| --- | --- | --- |
| Skill `shell-lint` | Used | Workflow, discovery, SC-code fixes, bash 3.2 portability, pipelines, directives never to add |
| Hooks | Used, command type | Deterministic work; the suppression judgment goes to the user through `ask` |
| `userConfig.enabled` | Used | Turns the hooks off, keeps the skill |
| Agents, commands, MCP, LSP, workflows | Rejected | Nothing to delegate; bash-language-server belongs to the editor |
| Bundled `.shellcheckrc` / `.editorconfig` | Rejected | Project policy; each tool's discovery decides |

### Hook design (differences from ruff-quality)

- **PreToolUse** asks before an edit adds `# shellcheck disable=…` or
  `# shellcheck source=/dev/null`, changes `.shellcheckrc` or `shellcheckrc`, or changes the
  sections or shfmt keys of `.editorconfig` (`indent_style`, `indent_size`, `shell_variant`,
  `language_dialect`, `binary_next_line`, `switch_case_indent`, `case_indent`,
  `space_redirects`, `keep_padding`, `function_next_line`, `block_next_line`, `simplify`,
  `minify`, `ignore`). The newer key names are included although shfmt v3.14.1 ignores
  them, so an upgrade does not open a gap.
- **PostToolUse** on `.sh` and `.bash`: `shfmt -w` with no style flag (any parser or printer
  flag makes shfmt ignore every EditorConfig key), then `shellcheck -x -f gcc` from the
  script's directory. A `#!…zsh` script is skipped with a notice: ShellCheck does not
  support zsh.
- `SHELLCHECK_OPTS` is respected as the user's configuration and named in every report, since
  it survives `--norc` and can exclude codes.
- An `.editorconfig` `shell_variant` the script is not written in makes shfmt fail "via
  EditorConfig": that is a configuration error (reported, never looped on), unlike a real
  parse error, which is Claude's to fix.
- Stop (progress-based, forgets after giving up, capped report), marker-text comparison of
  directives, `if` twins (H7), tool resolution, state and the `enabled` switch are identical
  to ruff-quality.

## Requirements

The README's 📋 Requirements table is canonical: Claude Code 2.1.222 (2.1.269 for the
`/config` row), ShellCheck 0.10, shfmt 3.12 (3.13 for the `[[shell]]` sections the skill
describes), Bash 3.2, jq 1.6, Git Bash on Windows. Platforms: macOS, Linux, WSL, Windows with
Git Bash. Not Cowork.

## Non-goals

- Installing ShellCheck or shfmt, downloading anything, or using the network.
- Writing `.shellcheckrc`, `.editorconfig` or any configuration.
- Applying ShellCheck's `-f diff` fixes automatically.
- Extensionless scripts, `.bats`, zsh, files written through Bash, files Claude did not touch.
- Enforcement for humans and other tools: pre-commit and CI.

## Failure modes

| Failure | Behavior | Open or closed |
| --- | --- | --- |
| shellcheck or shfmt missing | One `systemMessage` per session naming what is missing; nothing checked | Open |
| jq missing | Same, naming jq | Open |
| shfmt cannot parse the script | A finding for Claude ("shfmt could not parse the script" plus shfmt's message): the edit broke the syntax | Closed on the file |
| ShellCheck exits above 1 (unreadable file, bad option in `SHELLCHECK_OPTS`) | Reported as a tool break, not as findings | Open for the edit, reported |
| zsh script | Skipped with a notice | Open |
| Findings after an edit | `block` + findings to Claude | Closed on the file |
| Findings at Stop | Up to 7 continuations, then a failure message | Closed, bounded |
| Directive or config change | `ask`; refused in `-p` mode | Closed pending the user |
| `enabled = false` | Every event exits 0 silently | Open by choice |

## Verification

- Suite `scripts/plugin_validation/suites/shell-quality/test-gate.sh` under `bash` and
  `/bin/bash`: 61 cases plus 1 skip on machines where the tools sit at a fixed fallback path
  (the missing-tool case cannot hide them there).
- Static gates: H1–H7, B1, `claude plugin validate --strict`.
- Live `[observed]`, 2026-09-22, Claude Code 2.1.278, `claude -p --plugin-dir`: Write of
  `run.sh` with unquoted expansions → `block` with SC2086 findings → Claude quoted them with
  Edit → `✓ run.sh: clean` → Stop `✓ 1 shell script(s) … pass shfmt and ShellCheck`.
- Evals: `plugins/shell-quality/evals/` 01, 02, 04 kept; 03 "fixes what the hook reports".
- Not exercised live: the Stop cap (suite), Windows.

## References

- Hooks reference and guide: https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/hooks-guide
- Plugins reference: https://code.claude.com/docs/en/plugins-reference
- ShellCheck man page (rc search, `SHELLCHECK_OPTS`): https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md
- shfmt man page at v3.14.1: https://github.com/mvdan/sh/blob/v3.14.1/cmd/shfmt/shfmt.1.scd
- Field survey: TheBushidoCollective/han (adopt: ShellCheck as plugin hooks; reject: its own
  binary), alexfazio/plankton (adopt: config protection + Stop guardian).
