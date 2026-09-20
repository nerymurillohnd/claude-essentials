# Audit before wiring

Run this audit on the user's machine before proposing anything. Assume nothing:
not a Python project, not macOS, not a particular package manager, not that
basedpyright is installed. Report what you find; don't fix anything yet.

Copy this checklist and check off each item:

```
Audit:
- [ ] 1. Platform and shell
- [ ] 2. Where the user works
- [ ] 3. Python in scope
- [ ] 4. Configuration that applies
- [ ] 5. basedpyright and its language server
- [ ] 6. Interpreter
- [ ] 7. What already runs in Claude Code
- [ ] 8. Environment variables that change behavior
- [ ] 9. One real check
- [ ] 10. Proposal
```

## 1. Platform and shell

- `uname -s` (Darwin, Linux, MINGW/MSYS = Windows Git Bash). On WSL,
  `/proc/version` mentions Microsoft.
- `bash --version`, `jq --version`. The gate needs bash ≥ 3.2 and jq ≥ 1.6.
- Native Windows without Git Bash can't run the gate: say so and stop.

## 2. Where the user works

- The session's working directory, and `git rev-parse --show-toplevel` (may
  fail: not a repository is a valid answer).
- Ask which scope they want if it isn't obvious: this project (shared or
  local-only) or every project on this machine (user).

## 3. Python in scope

- Count Python files, pruning `.git`, `.venv`, `venv`, `node_modules`,
  `__pycache__`, `site-packages`. Zero is a valid answer: the gate still
  covers any `.py` Claude edits later.
- Project markers: `pyproject.toml`, `setup.py`, `setup.cfg`,
  `requirements*.txt`, `uv.lock`, `poetry.lock`, `Pipfile`, `environment.yml`.

## 4. Configuration that applies

- Walk up from the working directory: the first `pyrightconfig.json`, or a
  `pyproject.toml` with `[tool.basedpyright]` or `[tool.pyright]`. basedpyright
  reads no other file (not `basedpyrightconfig.json`) and has no user-level
  config.
- Both `[tool.pyright]` and `[tool.basedpyright]` in one file: basedpyright
  ignores the whole file. Report it as a blocker.
- Other type checkers configured (`mypy.ini`, `[tool.mypy]`, `ty.toml`,
  `[tool.ty]`, `pyrefly.toml`): they will disagree with basedpyright.
- A committed baseline (`.basedpyright/baseline.json` or `baselineFile`).

## 5. basedpyright and its language server

Look in this order, and report every hit with `--version`:

1. The project's environment: `.venv/bin/`, `venv/bin/` (Windows:
   `.venv/Scripts/*.exe`), walking up from the working directory.
2. `PATH` (`command -v basedpyright`).
3. Common tool locations: `~/.local/bin` (uv tool, pipx), Homebrew
   (`/opt/homebrew/bin`, `/usr/local/bin`, `/home/linuxbrew/.linuxbrew/bin`),
   a global npm prefix (`npm prefix -g`).

- `basedpyright-langserver` must sit next to the CLI (the packages ship both).
- Floor: 1.37.0. Newer than the version this skill was verified against
  (1.40.1)? Read the release notes first (see `sources.md`).
- Not found: give both install commands and let the user choose:
  project `uv add --dev basedpyright` (or the project's own tool), global
  `uv tool install basedpyright` (or `pipx`, `brew`, `npm i -g basedpyright`).
  Never install it yourself.

## 6. Interpreter

- The nearest `.venv`/`venv` interpreter walking up. Without one,
  basedpyright uses `python` on `PATH`, and imports of uninstalled packages
  are reported as missing.
- Poetry, conda, or another manager: find its environment (`poetry env info
  -p`, `conda info --envs`) and note it; the gate passes `--pythonpath` for
  roots without a config, and the language server needs a `.venv` link.

## 7. What already runs in Claude Code

- `claude --version` (may not be on `PATH` in desktop installs; then ask).
- Hooks in `~/.claude/settings.json`, `.claude/settings.json`,
  `.claude/settings.local.json` whose command mentions `pyright`: two gates
  would double every check.
- Enabled plugins that claim `.py` (`pyright-lsp`, `ty`, other basedpyright
  plugins): only the first registered language server runs.
- `disableAllHooks` set anywhere: the gate would not run.

## 8. Environment variables that change behavior

- `CI`, `GITHUB_ACTIONS`, and other CI markers exported in the user's shell:
  basedpyright switches to CI behavior (annotations, baseline `lock`). The
  gate neutralizes them, but tell the user.
- `CLAUDE_CODE_TOOL_MEMORY_LIMIT` (Linux/WSL): large projects can be killed
  silently.
- `UV_PYTHON_PREFERENCE=only-managed`: a reason the gate never uses `uv run`.

## 9. One real check

Run basedpyright once, from the config's directory (or the file's), with
`--outputjson --baselinemode discard`, on one Python file and, if a config
exists, on the whole project. Record the time and the counts. Treat
`could not be parsed`, `Config contains unrecognized setting`, or
`cannot have both` on stderr as a broken configuration even though the exit
code is 0 with `--outputjson`.

## 10. Proposal

Present, in plain words, before touching anything:

- What you found (steps 1-9), including every blocker and conflict.
- Scope: project (committed), local (this machine, this project), or user
  (every project on this machine).
- Configuration mode: `own` (the project's config, else basedpyright
  defaults), `profile` (the project's config, else the embedded profile,
  shown in full), or `pinned` (always the profile).
- Stop scope: `auto` (edited files clean plus no new breakage in their
  project; existing debt never blocks) or `project` (everything, as CI).
- Timeouts sized from step 9.

Wait for the user to approve or adjust. Silence or "ok" to something else is
not approval. Then run `manage.sh install` with the chosen options.
