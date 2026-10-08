#!/usr/bin/env bash
# Svelte 5 on plain Vite (no SvelteKit), installed and committed.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
shared_dir="$(dirname "${case_dir}")/shared"
"${shared_dir}/svelte-vite-app.sh"
