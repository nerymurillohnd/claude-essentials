---
paths:
  - "scripts/**"
  - "tests/**"
  - ".github/workflows/**"
  - "pyrightconfig.json"
---

# Repository maintenance scripts

These rules cover the scripts that generate, validate, verify, build and maintain this repository, not the scripts inside plugins.

- Write them in Python, using only the standard library and the repository's own modules.
- Start every script with `#!/usr/bin/env python3` and make it executable (mode 755) on disk and in git: `chmod +x <file>` and `git update-index --chmod=+x <file>`. Ruff EXE001 fails a shebang without the executable bit, and EXE002 an executable file without a shebang. Check the bit with `git ls-files -s`; expect `100755`.
- Modules that are only imported (`scripts/repo.py`, `tests/`) have no shebang and stay at mode 644.
- Run them by path, `scripts/<path>.py`: the shebang chooses the interpreter. Never put `python3` or `uv run` in front.
- Do not add a PEP 723 block, `pyproject.toml` or `uv.lock`: there are no dependencies to declare.
- When a script calls another script, it runs it by path (`[str(path), *args]`), so the child's shebang chooses its interpreter. `sys.executable` is only for modules of the running interpreter (`-m unittest`).
- No Python version is pinned: the ruff configuration (the maintainer's global file) has no `target-version` and `pyrightconfig.json` no `pythonVersion` (ADR unpinned-tooling-and-shebang-interpreters). The maintainer's `python3` and CI's can differ (3.14 and 3.12 on 2026-10-05); a script that fails on CI's interpreter is fixed in the script.
- Plugin scripts are different: they usually use `sh` because Claude Code runs them, and only very complex ones use Python. Their shebang, mode and invocation rules are in `.claude/rules/plugins/hooks-and-permissions.md`.
