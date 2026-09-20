# The after-edit gate: hook contract

Verified 2026-09-19 against Claude Code 2.1.278 (hooks reference) and
basedpyright 1.40.1. Live documentation wins over this page: re-check the
[hooks reference](https://code.claude.com/docs/en/hooks) and the
[changelog](https://code.claude.com/docs/en/changelog) when Claude Code is
newer, and basedpyright's release notes when basedpyright is newer.

## Contents

1. What the gate guarantees
2. Events, hook types, and wiring
3. Behavior per event
4. How diagnostics are produced
5. What Claude reads (real example)
6. How corrections are enforced
7. Exit codes
8. Options
9. State and idempotency
10. Portability
11. What the gate cannot see
12. Tests

## 1. What the gate guarantees

After every tool call that writes a Python file (`.py`, `.pyi`, `.pyw`,
`.ipynb`), the basedpyright CLI checks that file and Claude receives the
result next to the tool result. While the file has diagnostics, Claude can
only edit that file or other Python files of the same project. Claude can't
end its turn, finish a subagent, or complete a task while an edited file is
dirty or its project has new breakage. Fixes must be in code. It works for
any Python file in any directory, with or without a project configuration.

## 2. Events, hook types, and wiring

All handlers are `type: "command"` hooks running one script,
`basedpyright-after-edit.sh <event>`.

| Event | Matcher | Handler | Timeout | Can it block? (hooks reference) | Output used |
| --- | --- | --- | --- | --- | --- |
| `PreToolUse` | `Write\|Edit\|NotebookEdit\|Bash` | `guard` | 120 s: normally milliseconds (it reads state), but the first write into a configured project takes the project snapshot, and a timed-out PreToolUse hook would silently skip it | Yes: blocks the tool call | exit 2 + `permissionDecision: "deny"` |
| `PostToolUse` | `Write\|Edit\|NotebookEdit\|Bash` | `post` | 120 s | No: "shows stderr to Claude; the tool already ran" | exit 2 + stderr report; one `systemMessage` for the user |
| `Stop` | — | `stop` | 300 s | Yes: Claude keeps working | exit 2 + stderr report |
| `SubagentStop` | — | `stop` | 300 s | Yes: the subagent keeps working | exit 2 + stderr report |
| `TaskCompleted` | — | `task-completed` | 10 s | Yes: the task stays open | exit 2 + stderr |
| `UserPromptSubmit` | — | `prompt` | 10 s | Yes, but the gate **never** blocks here | `additionalContext` (JSON only) |
| `SessionStart` | `compact\|resume` | `session-start` | 10 s | No | `additionalContext` |

**Wiring** (shell form, the same on macOS, Linux, WSL, and Windows Git Bash:
exec form would need a real executable, and a `.sh` file isn't one on
Windows):

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PROJECT_DIR}/.claude/hooks/basedpyright-after-edit.sh\" post",
  "timeout": 120,
  "statusMessage": "basedpyright: type-checking the edited file"
}
```

The complete block for all seven events is `settings.hooks.json` (validated
against the hooks schema). `manage.sh install` merges it into the chosen
scope and copies the handler next to it:

| Scope | Settings file | Handler copy |
| --- | --- | --- |
| project | `.claude/settings.json` | `.claude/hooks/basedpyright-after-edit.sh` (commit both) |
| local | `.claude/settings.local.json` | `.claude/hooks/basedpyright-after-edit.sh` (kept out of git) |
| user | `~/.claude/settings.json` | `~/.claude/hooks/basedpyright-after-edit.sh`, referenced as `"$HOME/.claude/hooks/…"` |

The handler is copied, never referenced inside the plugin cache: that path
changes on every plugin update.

## 3. Behavior per event

**`post`.** Collects the written Python files from `tool_input.file_path`,
`notebook_path`, `tool_response.filePath`, and `tool_response.bashEditDiff`.
For a Bash command that reported nothing, it finds `.py`/`.pyi`/`.pyw` files
newer than the mark the guard set before the command (at most 50; `.git`,
virtual environments, `node_modules`, and caches pruned). Each file is checked
from its project root. Diagnostics that block → the file is marked dirty,
the report goes to stderr, exit 2. Clean → the mark is removed, exit 0.
Excluded by the project's config → reported to the user as "not
type-checked", never as clean.

**`guard`.**
- On the first write into a configured project this session, it records the
  project's diagnostics before the edit (the snapshot `stop` compares
  against). It runs in a subshell: a failure leaves no snapshot and never
  denies the edit.
- While a file is dirty: `Write`/`Edit`/`NotebookEdit` are allowed only on
  dirty files and on other Python files of the same project (the fix can live
  where a type is defined). Anything else is denied. Read, Grep, Glob, and
  LSP are never locked.
- On `Bash`, always: denies `--writebaseline`, `--baselinemode auto|lock`,
  `disableAllHooks`, `enableTypeIgnoreComments`, and shell writes that carry a
  suppression comment or touch `pyrightconfig.json`, `pyproject.toml`,
  `.basedpyright/`, the handler, or settings. While a file is dirty, also any
  shell write. The whole compound command is searched (`cd x && echo y >
  z` is caught).

**`stop`.** For every project root touched this session:
1. The edited files must be clean.
2. `auto` (default), configured project: the whole project is re-checked,
   and diagnostics that weren't in the snapshot (compared by file, rule, and
   first message line, so moved lines don't count) block. This catches an
   edit that broke an importer Claude never opened. Existing debt doesn't
   block.
3. `project`: every diagnostic in the project blocks, as in CI.

**`task-completed`.** Refuses while any file is dirty.

**`prompt`.** Resets the block and denial counters. If a file is still dirty
(a previous turn ended through the max-blocks escape), the obligation is
injected into the new turn as `additionalContext`.

**`session-start`.** After compaction or resume, re-injects the dirty files as
`additionalContext`, so the obligation survives the summary.

## 4. How diagnostics are produced

```
cd <root> && env -u CI -u GITHUB_ACTIONS … NO_COLOR=1 \
  basedpyright --outputjson --baselinemode discard -p <root|profile> [--pythonpath <venv python>] <files…>
```

| Choice | Reason |
| --- | --- |
| The CLI, not the language server | Awaited and deterministic. Claude Code doesn't wait for pushed LSP diagnostics (#93321); a cold server is irrelevant to the verdict |
| `cd <root>` **and** `-p` | basedpyright resolves configuration from the working directory; from elsewhere a project's own settings were ignored [observed] |
| `--baselinemode discard` | A plain run rewrites the committed `baseline.json` when errors went down; `lock` exits 3 when Claude fixes a baselined error |
| CI variables unset | Any `CI`/`GITHUB_ACTIONS` switches basedpyright to annotations and baseline `lock` |
| `--pythonpath` for roots without their own config | With `-p` at a config elsewhere, basedpyright ignores the project's `.venv` and uses `python` on `PATH` [observed] |
| Paths canonicalized (`pwd -P`), no `--` | A symlinked path defeats `exclude`; `--` makes basedpyright exit 4 |
| The root | The nearest directory with `pyrightconfig.json` or `[tool.basedpyright]`/`[tool.pyright]`, else the git root, else the file's directory |

**What blocks:**

| The file's root | Blocks on |
| --- | --- |
| Has its own config | basedpyright's verdict (exit 1), so `failOnWarnings` is honoured exactly as in CI |
| No config, `own` mode (basedpyright defaults: `recommended`, every rule) | Errors and warnings, except `reportMissingImports`, `reportMissingModuleSource`, `reportMissingTypeStubs`: packages not installed where basedpyright looks. They are reported, not blocking, because fixing them means installing packages, which is the user's decision |
| `profile` or `pinned` mode | The embedded profile's verdict (in it, the two "not installed" rules are `information`: shown, never failing) |

Rule-less diagnostics (syntax errors) hide the rest of that file's findings:
an unparseable file otherwise produces a cascade that adds nothing.

## 5. What Claude reads (real example)

Output of `post` for this edit, basedpyright 1.40.1, `recommended`:

```python
from typing import Any


def total(xs: list[int], label: str | None) -> int:
    print(label.upper())
    return sum(xs) + "0"


def load(raw: Any) -> dict[str, int]:
    return raw
```

```text
basedpyright: pkg/calc.py (project /path/to/demo)
2 error(s), 4 warning(s)
  pkg/calc.py:5:17  error  reportOptionalMemberAccess  "upper" is not a known attribute of "None"
  pkg/calc.py:6:12  error  reportOperatorIssue  Operator "+" not supported for types "int" and "Literal['0']"
  warnings by rule:
    2× reportAny  (first at pkg/calc.py:9:10)
    1× reportExplicitAny  (first at pkg/calc.py:9:15)
    1× reportUnknownVariableType  (first at pkg/calc.py:6:12)
Project type-checking policy (basedpyright gate installed by the user):
  - Positions above are 1-based line:column, the same convention the LSP tool uses. At each one, the LSP tool's `hover` shows the inferred type, `goToDefinition` locates the declaration of the type or symbol named in the message, and `findReferences` / `incomingCalls` list the callers affected by a signature change.
  - A language server that is still indexing can return an error or an empty result; up to 3 retries usually get an answer. When it still fails, Read and Grep give the same facts. This report, produced by the basedpyright CLI, is the verdict; LSP diagnostics are advisory.
  - The policy accepts fixes in code only. `# pyright: ignore`, `# type: ignore`, `cast(Any, ...)`, new `Any` annotations, and configuration or baseline changes are not accepted as fixes; a rule that looks wrong for the project is a question for the user.
  - The check re-runs on every edit of the file. Until it is clean, edits outside this project are denied.
```

The user sees one line: `basedpyright-after-edit ✗ type errors in the file
Claude just edited; Claude must fix them before other work`.

Format rules: errors listed individually (up to 25, then a count); warnings
grouped by rule with their first position; positions 1-based like the LSP
tool; the whole report cut at 7,000 characters, because Claude Code moves text
over 10,000 characters to a file Claude isn't told to read. The policy block
is written as facts, not commands: imperative text injected by hooks can
trigger Claude's prompt-injection defenses (hooks reference).

After a Stop re-check, diagnostics in files Claude never edited appear under
"new diagnostics in files you did not edit": that is an edit breaking an
importer.

## 6. How corrections are enforced

| Step | Mechanism | Claude can't |
| --- | --- | --- |
| 1 | `post` exits 2 with the report after the edit | Miss the diagnostics: they arrive with the tool result |
| 2 | `guard` focus lock | Move on to unrelated edits while the file is dirty |
| 3 | `guard` Bash rules | Route around the lock or the policy through the shell |
| 4 | Every edit of the file re-runs `post` | Claim a fix without a clean re-check |
| 5 | `task-completed` | Mark a task done |
| 6 | `stop` / `subagent-stop` | End the turn, or finish a subagent, with a dirty file or new breakage |
| 7 | `session-start`, `prompt` | Lose the obligation through compaction or a new turn |

Two escapes keep the gate from trapping a session, both visible to the user:
the focus lock lets one edit through after 3 consecutive denials (a
cross-cutting fix outside the project), and Stop lets the turn end after 5
consecutive blocks (Claude Code itself overrides a Stop hook after 8).

## 7. Exit codes

**What the handler returns** (Claude Code: only exit 2 blocks; any other
non-zero code is a non-blocking error and the action proceeds):

| Event | Exit 0 | Exit 2 |
| --- | --- | --- |
| `post` | Clean, excluded, or not Python | Diagnostics that block, or the check couldn't run |
| `guard` | Allowed | Denied (with `permissionDecision: "deny"`), or the check couldn't run |
| `stop` | Clean, or the max-blocks escape | Keep working |
| `task-completed` | Nothing dirty | Task stays open |
| `prompt`, `session-start` | Always, including when the gate is broken (reported in `systemMessage`) | Never: exit 2 on `UserPromptSubmit` erases the user's prompt |

**How basedpyright's exits are read:**

| basedpyright | Meaning | Gate |
| --- | --- | --- |
| 0 | Clean | Pass (for roots without config, the JSON is still inspected) |
| 1 | Errors, or warnings with `failOnWarnings` | Blocks (by the rules in §4) |
| 2 | Fatal error | Fail closed: "basedpyright crashed" |
| 3 | Config unreadable, invalid setting, both tables, or stale baseline under `lock` | Fail closed: configuration is the user's decision |
| 4 | Bad arguments | Fail closed: a gate bug |
| ≥ 128 | Killed by a signal | Fail closed: usually Claude Code's tool memory cap on Linux/WSL |
| 0 **with `--outputjson` and a broken config** | basedpyright 1.40.1 exits 0 here and prints the error only to stderr | Read from stderr and treated as 3 |

**Fail closed or open:** edit-time events (`post`, `guard`, `stop`,
`task-completed`) fail closed with the reason (missing `jq` or basedpyright,
unreadable payload, timeout). `prompt` and `session-start` fail open with a
visible message, so a broken gate never locks the user out.

## 8. Options

Set as environment variables in the hook command, chosen during wiring:

| Variable | Values | Default |
| --- | --- | --- |
| `BPAE_CONFIG_MODE` | `own`, `profile`, `pinned` | `own` |
| `BPAE_CONFIG` | Path to a pyrightconfig used by `profile`/`pinned` | The embedded profile |
| `BPAE_STOP_SCOPE` | `auto`, `files`, `project` | `auto` |
| `BPAE_TIMEOUT` | Seconds per basedpyright run | 100 (below the hook timeout, so the gate always answers) |
| `BPAE_MAX_BLOCKS` | 1–7 | 5 |
| `BPAE_MAX_DENIALS` | Focus-lock denials before an edit passes | 3 |
| `BPAE_BASH_SCAN` | `1`, `0` | `1` |
| `BASEDPYRIGHT_BIN` | Absolute path to the CLI | Discovered: project `.venv`/`venv` walking up, `PATH`, `~/.local/bin`, Homebrew, Linuxbrew |

## 9. State and idempotency

Per session in `$TMPDIR/basedpyright-after-edit-<uid>/` (mode 0700, owner
checked except on Windows): touched files, dirty files, denial and block
counters, project snapshots, the Bash mark, and the materialized profile
(rewritten only when its content changed). Nothing is written in the project.
Installing twice changes nothing; uninstalling removes only the gate's groups
and handler.

## 10. Portability

macOS, Linux, WSL, and Windows with Git Bash; bash ≥ 3.2; jq ≥ 1.6;
basedpyright ≥ 1.37.0. Windows paths (`C:\…`) are converted with `cygpath`
(or by hand); `.exe` layouts are searched; no `timeout`, no `\b`, no
GNU-only flags. Native Windows without Git Bash and containers without bash
are unsupported.

## 11. What the gate cannot see

- Files changed by processes outside Claude's tools; Bash writes when the scan
  is off or the file is outside the working directory.
- Semantics: a clean type check isn't proof the code is right.
- Stop in `auto` mode without a snapshot (the first-touch run failed): only
  the edited files are checked, and the user is told.

## 12. Tests

`test-basedpyright-after-edit.sh` sends realistic payloads on stdin and runs
under the first `bash` on `PATH` and `/bin/bash`. 42 cases cover every row of
§2–§7, including: cross-file breakage caught at Stop; existing debt not
blocking in `auto` but blocking in `project`; a file with no config and a
missing package; `pinned` overriding a project; Bash writes found without
`bashEditDiff`; `--outputjson` hiding a broken config; `CI` variables
changing nothing; missing `jq` blocking edits but not prompts; death by
signal; the focus lock and its escape.
