#!/usr/bin/env bash
# Builds a small Node.js service with recurring manual work and one broken
# Claude Code hook, so an automation audit has real evidence to find.
set -euo pipefail

git init -q -b main .
git config user.email "fixture@example.com"
git config user.name "Fixture"

mkdir -p src .github/workflows .claude scripts

cat >package.json <<'JSON'
{
  "name": "orders-service",
  "version": "1.4.2",
  "private": true,
  "type": "module",
  "scripts": {
    "lint": "eslint .",
    "format": "prettier --write .",
    "test": "node --test src/",
    "build": "tsc -p .",
    "db:migrate": "node scripts/migrate.js",
    "release": "node scripts/release.js"
  },
  "devDependencies": { "eslint": "^9.0.0", "prettier": "^3.0.0", "typescript": "^5.0.0" }
}
JSON

cat >src/orders.js <<'JS'
export function total(items) {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}
JS

cat >src/orders.test.js <<'JS'
import { test } from "node:test";
import assert from "node:assert";
import { total } from "./orders.js";
test("total", () => assert.equal(total([{ price: 2, qty: 3 }]), 6));
JS

cat >scripts/release.js <<'JS'
// Manual release: bump package.json, prepend CHANGELOG.md, tag. Run by hand.
console.log("bump version, edit CHANGELOG.md, git tag vX.Y.Z, push");
JS

cat >scripts/migrate.js <<'JS'
console.log("apply migrations in migrations/ to $DATABASE_URL");
JS

cat >.github/workflows/ci.yml <<'YML'
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
YML

cat >CLAUDE.md <<'MD'
# orders-service

- Run `npm run lint` and `npm test` before every commit.
- Never edit files in `migrations/` that are already merged; add a new migration.
- Releases: bump `package.json`, add a CHANGELOG entry, tag `vX.Y.Z`.
- The `.env` file holds real credentials; never read or print it.
MD

cat >.claude/settings.json <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format.sh" }]
      }
    ]
  }
}
JSON

printf 'DATABASE_URL=postgres://example.invalid/orders\n' >.env.example
printf 'node_modules/\n.env\n' >.gitignore
printf '# Changelog\n\n## 1.4.2\n\n- Fix rounding.\n' >CHANGELOG.md

git add -A
git commit -qm "feat: initial orders service"
for n in 1 2 3 4 5 6; do
  printf '\n<!-- %s -->\n' "${n}" >>CHANGELOG.md
  git commit -qam "style: fix lint errors after review (${n})"
  printf '%s\n' "// note ${n}" >>src/orders.js
  git commit -qam "chore(release): bump version and changelog (${n})"
done
for n in 1 2 3; do
  printf '%s\n' "// migration ${n}" >>scripts/migrate.js
  git commit -qam "fix(db): rerun migration after forgetting to apply it (${n})"
done
