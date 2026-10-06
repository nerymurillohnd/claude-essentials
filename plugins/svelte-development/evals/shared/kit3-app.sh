#!/usr/bin/env bash
# Seeds the run's empty workspace with the plugin's SvelteKit 3 fixture, installed.
# Called by each case's scaffold.sh; runs only with `claude plugin eval --scaffold`.
set -euo pipefail

shared_dir="$(cd "$(dirname "$0")" && pwd)"
evals_dir="$(dirname "${shared_dir}")"
plugin_root="$(dirname "${evals_dir}")"

cp -R "${plugin_root}/skills/svelte-lsp-navigation/fixtures/kit3-app/." .
# The fixture README lists the known answers (symbols, mutation sites): keep it out of the
# workspace, so a case measures the tools, not a lookup of the expected result.
rm -f README.md
for name in package.json tsconfig.json vite.config.ts; do
  mv "${name}.example" "${name}"
done
# --include=dev: the fixture is all devDependencies, and a runner's npm may omit them.
# --ignore-scripts: the sync below replaces the fixture's prepare script.
npm install --include=dev --ignore-scripts --no-audit --no-fund --loglevel=error
if [[ ! -x node_modules/.bin/svelte-kit ]]; then
  echo "npm install left no node_modules/.bin/svelte-kit; npm configuration:" >&2
  npm config list >&2
  exit 1
fi
npx --no-install svelte-kit sync
