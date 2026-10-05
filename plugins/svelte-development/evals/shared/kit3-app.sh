#!/usr/bin/env bash
# Seeds the run's empty workspace with the plugin's SvelteKit 3 fixture, installed.
# Called by each case's scaffold.sh; runs only with `claude plugin eval --scaffold`.
set -euo pipefail

shared_dir="$(cd "$(dirname "$0")" && pwd)"
evals_dir="$(dirname "${shared_dir}")"
plugin_root="$(dirname "${evals_dir}")"

cp -R "${plugin_root}/skills/svelte-lsp-navigation/fixtures/kit3-app/." .
for name in package.json tsconfig.json vite.config.ts; do
  mv "${name}.example" "${name}"
done
npm install --no-audit --no-fund --loglevel=error
npx svelte-kit sync
