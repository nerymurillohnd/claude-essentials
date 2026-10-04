# Local toolchain (only for the repository's own scripts)

- Verified on 2026-10-03 with uv 0.12.22.
- In zsh, `python3` is uv's CPython 3.14.7 and `bash` is Homebrew's 5.3; outside zsh they are Xcode's 3.9.6 and `/bin/bash` 3.2.57.
- Your Bash tool is a non-interactive login zsh, but it takes its PATH from a shell snapshot Claude Code saves at session start, so changes to my shell files mid-session do not reach it.
- The scripts use Python 3.12 syntax and fail with `SyntaxError` under Xcode's 3.9.6; run them with `uv run` and PEP 723 `requires-python`, never with `python3`.
- A `#!/usr/bin/env python3 -` shebang does not run the script, because it reads the program from stdin.
- `pip3` resolves only to Xcode's `/usr/bin/pip3`; never use pip.
- `uv run` keeps one environment per script in `~/.cache/uv/environments-v2/` by design; those are not orphaned test files.
- Never touch that cache by hand: clean it with `uv cache prune` or `uv cache clean`.
- None of this says anything about the environments of the users who install the plugins.
