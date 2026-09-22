# Shell quality

`scripts/shell_quality/`. Shell is the default language for shipped hooks, so
every `.sh` file in the repository is linted, formatted, and executed by the same
rules Claude's own edits pass through. The backlog entry is `DEBT-0003`.

## Ground rules

- One discovery rule for shell scripts, shared by the gate and the `PostToolUse` hook. Two rules would let a file pass one and fail the other.
- ShellCheck takes its policy from `.shellcheckrc`; `shfmt` takes its style from `.editorconfig`. Neither is configured on a command line, so local and CI agree.
- New shell scripts need the exec bit (`100755`) and are tested by path, never with `bash script.sh`, because that masks a missing shebang or a missing bit.
- macOS ships bash 3.2 at `/bin/bash` while Homebrew's bash is on `PATH`. A plugin's users have both, so its suites run under both.

## `shell_files.py`

- `is_shell_script(path, first_line)` returns true for a `.sh` file, or for any file whose shebang runs `sh` or `bash`.
- `list_shell_files(root)` returns tracked files plus new files git does not ignore, so a new plugin's scripts are gated on the commit that introduces them, not the one after.
- This is the rule `.claude/hooks/` mirrors. Changing it here without changing the hook is the drift this area guards against.

## `lint_shell.py` — entrypoint

- Runs ShellCheck over every discovered script with the repository policy.
- Checks formatting with `shfmt` in diff mode; it reports, it does not rewrite.
- Applies to plugin scripts, hook scripts, and test suites alike. There is no exempt directory.

## Tests

- `test_shell_files.py` — discovery by extension and by shebang, including a file with no extension and an executable that is not shell.
- `run_plugin_suites.py` (`make test-slow`) — runs every plugin suite, which lives in the repository at `scripts/plugin_validation/suites/<id>/test-*.sh` (ADR-0007; `block-no-verify`'s runtime suite is the one exception inside `plugins/`). Each suite runs under `bash` from `PATH` and, when that resolves to a different binary, under `/bin/bash` too.

## Why the suites matter here

- The official validator never executes a hook. These suites are the only layer that proves a hook runs, blocks what it must block, and allows what it must allow.
- They are deterministic and free, so they belong in the gate rather than in an eval. Spending a model on what `bash -n` settles is the anti-pattern this separation exists to prevent.
