#!/usr/bin/env bash
# A small project whose calc.py carries two findings in Ruff's default rule set that its safe
# fixes leave for Claude (F841, whose fix is unsafe, and F821),
# and a project-level Ruff the plugin's hook can run: the sandbox has no Ruff of its own.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ruff=""
top=$(cd "${here}/../../../.." 2>/dev/null && pwd) || top=""
if [[ -n ${top} && -x ${top}/.venv/bin/ruff ]]; then ruff="${top}/.venv/bin/ruff"; fi
if [[ -z ${ruff} ]]; then ruff=$(command -v ruff) || ruff=""; fi
if [[ -z ${ruff} ]]; then
  printf "scaffold: no ruff to copy; run make setup in the marketplace checkout\n" >&2
  exit 1
fi
mkdir -p .venv/bin
cp -L "${ruff}" .venv/bin/ruff
chmod 755 .venv/bin/ruff
printf '[project]\nname = "calc"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n' >pyproject.toml
cat >calc.py <<'PY'
"""Small arithmetic helpers."""


def total(values):
    items = list(values)
    count = len(items)
    return sum(items)


def describe(values):
    return f"{len(values)} values, total {totl(values)}"
PY
