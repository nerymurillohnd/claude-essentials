#!/usr/bin/env bash
# SvelteKit 3 fixture plus a seeded route with known problems.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
shared_dir="$(dirname "${case_dir}")/shared"
cp -R "${case_dir}/seed/." .
"${shared_dir}/kit3-app.sh"
