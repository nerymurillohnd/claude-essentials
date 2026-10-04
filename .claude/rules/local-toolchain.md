# Local toolchain (only for the repository's own scripts)

- In zsh, `python3` is uv's CPython 3.14.7 and `bash` is Homebrew's 5.3; outside zsh they are Xcode's 3.9.6 and `/bin/bash` 3.2.57.
- Your Bash tool takes its PATH from a shell snapshot Claude Code saves at session start, so changes to my shell files mid-session do not reach it.
- A `#!/usr/bin/env python3 -` shebang does not run the script, because it reads the program from stdin.
- Run every repository script with `uv run` and PEP 723 `requires-python`, never with `python3` or pip.
- Never touch uv's environment cache by hand: clean it with `uv cache prune` or `uv cache clean`.
- None of this says anything about the environments of the users who install the plugins.
