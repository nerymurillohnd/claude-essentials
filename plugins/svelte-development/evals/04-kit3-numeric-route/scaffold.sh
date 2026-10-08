#!/usr/bin/env bash
# SvelteKit 3 fixture, installed and committed.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
shared_dir="$(dirname "${case_dir}")/shared"
"${shared_dir}/kit3-app.sh"
