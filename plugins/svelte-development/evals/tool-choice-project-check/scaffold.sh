#!/usr/bin/env bash
# Installs the shared SvelteKit 3 fixture, then copies this case's seed files over it.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
"$(dirname "${case_dir}")/shared/kit3-app.sh"
if [[ -d "${case_dir}/seed" ]]; then
  cp -R "${case_dir}/seed/." .
fi
