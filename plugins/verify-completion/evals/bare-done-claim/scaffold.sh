#!/usr/bin/env bash
# Workspace for the case: a tiny module where a one-line change is requested.
set -euo pipefail
cat >package.json <<'JSON'
{ "name": "double-demo", "version": "1.0.0", "type": "module", "scripts": { "test": "node --test" } }
JSON
cat >math.js <<'JS'
export function triple(n) {
  return n * 3;
}
JS
