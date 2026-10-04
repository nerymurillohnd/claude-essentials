---
paths:
  - "scripts/**"
  - "tests/**"
  - ".github/workflows/**"
  - "ruff.toml"
  - "pyrightconfig.json"
---

# Repository maintenance scripts

These rules cover the scripts that generate, validate, verify, build and maintain this repository, not the scripts inside plugins.

- Write them in Python, using only the standard library and the repository's own modules.
- Start every script with `#!/usr/bin/env python3` and make it executable (mode 755) on disk and in git: `chmod +x <file>` and `git update-index --chmod=+x <file>`. Ruff EXE001 fails a shebang without the executable bit, and EXE002 an executable file without a shebang. Check the bit with `git ls-files -s`; expect `100755`.
- Modules that are only imported (`scripts/repo.py`, `tests/`) have no shebang and stay at mode 644.
- Run them as `python3 scripts/<path>.py`, never with `uv run`.
- Do not add a PEP 723 block, `pyproject.toml` or `uv.lock`: there are no dependencies to declare.
- When a script calls another script, use `sys.executable`, so the child runs on the same interpreter.
- The minimum is Python 3.12 (`ruff.toml` `target-version`, `pyrightconfig.json` `pythonVersion`). CI's ubuntu-24.04 system Python is 3.12.3 (runner image 20260927), so never use syntax or stdlib features newer than 3.12.
- Plugin scripts are different: they usually use `sh` because Claude Code runs them, and only very complex ones use Python.
