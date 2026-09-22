# Installing and running Ruff

Verified on 2026-09-22 against Ruff 0.16.8, uv 0.12.17,
[docs.astral.sh/ruff/installation](https://docs.astral.sh/ruff/installation/),
and the uv pages linked below. Flags were confirmed with `uv run --help` and
`uvx --help` on uv 0.12.17.

## Contents

- [Install routes](#install-routes)
- [Choosing the command route](#choosing-the-command-route)
- [Why the uv flags matter](#why-the-uv-flags-matter)
- [One version everywhere](#one-version-everywhere)

## Install routes

Present these to the user; do not run an install unasked. A project
dependency comes first, because it pins the version for everyone who works on
the project.

| Route | Command | Notes |
| --- | --- | --- |
| uv project, dev dependency | `uv add --dev ruff` | Recorded in `pyproject.toml` and `uv.lock` |
| Poetry project | `poetry add --group dev ruff` | [Poetry docs](https://python-poetry.org/docs/cli/#add) |
| pip in a virtual environment | `pip install ruff`, pinned in the project's requirements file | |
| Global, via uv | `uv tool install ruff@latest` | Puts `ruff` on `PATH` |
| Global, other | `pipx install ruff`, `brew install ruff`, `conda install -c conda-forge ruff` | |
| Standalone installer (0.5.0+) | `curl -LsSf https://astral.sh/ruff/install.sh \| sh` (Windows: `powershell -c "irm https://astral.sh/ruff/install.ps1 \| iex"`) | Versioned URL: `https://astral.sh/ruff/<version>/install.sh` |
| Docker | `ghcr.io/astral-sh/ruff:<version>` | Useful in CI |

The installation page also lists pkgx, Arch (`pacman`), Alpine (`apk`), and
openSUSE packages. Distribution packages can lag behind PyPI; check
`ruff --version` after installing.

## Choosing the command route

Resolve once per session, in this order:

1. **Project virtual environment:** `.venv/bin/ruff` (Windows:
   `.venv\Scripts\ruff.exe`). Uses exactly what the project installed, with
   no resolution step.
2. **uv project with Ruff in `uv.lock`:**
   `uv run --locked --no-python-downloads ruff …`. Use this when there is no
   `.venv` yet, or when the environment may be out of date.
3. **`ruff` on `PATH`:** fine when the project does not pin Ruff. If it does
   (`required-version`, a lock file, a pre-commit `rev`), compare
   `ruff --version` with the pin first: different releases report different
   findings.
4. **`uvx --no-python-downloads ruff@<version> …`:** only with the user's
   consent, since it downloads Ruff from PyPI into uv's cache. Pin the
   version the project uses; never an unpinned `uvx ruff`.

Astral's own guidance runs `uv run ruff` or `uvx ruff` directly. Here the
two flags below are always added, because a plain call can change the lock
file or download an interpreter without anyone noticing.

## Why the uv flags matter

- **`--no-python-downloads`** ("Disable automatic downloads of Python", env
  `UV_PYTHON_DOWNLOADS=never`). By default "uv will automatically download
  Python versions when needed"
  ([python-versions](https://docs.astral.sh/uv/concepts/python-versions/)).
  Both `uv run` and `uvx` need an interpreter to build the environment, so
  without the flag a machine with no suitable Python gets one silently. With
  it, uv fails instead and you can tell the user.
- **`--locked`** ("Assert that the `uv.lock` will remain unchanged", env
  `UV_LOCKED`). "If the lockfile is not up-to-date, uv will raise an error
  instead of updating the lockfile"
  ([sync](https://docs.astral.sh/uv/concepts/projects/sync/)). Verified: with
  a dependency added to `pyproject.toml` but not locked, `uv run --locked
  --no-python-downloads ruff --version` printed "The lockfile at `uv.lock`
  needs to be updated, but `--locked` was provided." and exited 1 with
  `uv.lock` unchanged. It still created `.venv` before refusing.
- **`--frozen`** runs without checking the lock at all; prefer `--locked`,
  which fails loudly. **`--no-sync`** skips syncing the environment and runs
  whatever is installed.
- `uv run` locks and syncs before running by default, which can install
  packages (network). Add `--offline` when the network must not be used.

## One version everywhere

Ruff's findings and formatting change between minor releases
([versioning](https://docs.astral.sh/ruff/versioning/)). Keep these equal and
bump them in one change:

- the project dependency (`uv.lock`, requirements, Poetry lock);
- `required-version` in the Ruff configuration, if set;
- the pre-commit `rev` of `astral-sh/ruff-pre-commit`;
- the CI version (`astral-sh/ruff-action` `version`, or `uv run --locked`);
- editor extensions that bundle their own Ruff: the VS Code extension uses
  `ruff.path`, else the active environment's Ruff, else `PATH`, else its
  bundled copy ([ruff-vscode](https://github.com/astral-sh/ruff-vscode)).

Look up the current release before writing a pin
(<https://github.com/astral-sh/ruff/releases>); never write a version from
memory.
