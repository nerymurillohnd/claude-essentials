#!/usr/bin/env bash
# SvelteKit 3 fixture plus a short README for a docs-only task.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
shared_dir="$(dirname "${case_dir}")/shared"
"${shared_dir}/kit3-app.sh"
printf '%s\n' "# Counter demo" "" "A small SvelteKit app." >README.md
git add README.md
git -c user.name=eval -c user.email=eval@example.com -c commit.gpgsign=false \
  commit -q -m "readme"
