---
paths:
  - "scripts/**"
  - "tests/**"
  - ".pre-commit-config.yaml"
  - "pyrightconfig.json"
---

# Local toolchain (only for the repository's own scripts)

- Verified on 2026-10-05 with uv 0.12.23; CI installs the latest uv (`.github/workflows/validate.yml` sets no version).
- In zsh, `python3` is uv's CPython 3.14.8 (`~/.local/bin/python3`, checked 2026-10-05), found on PATH before macOS's; outside zsh it is Xcode's 3.9.6.
- In zsh, `bash` is Homebrew's 5.3; outside zsh it is `/bin/bash` 3.2.57.
- Your Bash tool is a non-interactive login zsh.
- It takes its PATH from a shell snapshot Claude Code saves at session start.
- Changes to my shell files mid-session do not reach it.
- `pip3` resolves only to Xcode's `/usr/bin/pip3`; never use pip.
- Never touch uv's cache by hand: clean it with `uv cache prune` or `uv cache clean`.
- None of this says anything about the environments of the users who install the plugins.
