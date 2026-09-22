#!/usr/bin/env bash
# A project that has never been through Ruff: several modules in an older style, and a
# project-level Ruff the skill can run in any sandbox. Nothing here is formatted.
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
mkdir -p .venv/bin app/services app/models
cp -L "${ruff}" .venv/bin/ruff
chmod 755 .venv/bin/ruff
printf '[project]\nname = "legacy"\nversion = "1.4.0"\nrequires-python = ">=3.12"\n' >pyproject.toml
for mod in app/__init__ app/services/__init__ app/models/__init__; do : >"${mod}.py"; done
for name in billing orders shipping invoices customers; do
  cat >"app/services/${name}.py" <<PY
import os,sys
def ${name}_total( items ,tax = 0.15 ) :
    subtotal=sum( [ i['price']*i['qty'] for i in items ] )
    return round( subtotal*(1+tax),2 )
class Service :
    def __init__( self,repo ) :
        self.repo=repo
    def get( self,id ) :
        return self.repo.find( id )
PY
done
