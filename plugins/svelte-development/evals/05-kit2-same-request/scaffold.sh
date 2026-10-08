#!/usr/bin/env bash
# SvelteKit 2 project, not installed, committed.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
shared_dir="$(dirname "${case_dir}")/shared"
"${shared_dir}/kit2-app.sh"
