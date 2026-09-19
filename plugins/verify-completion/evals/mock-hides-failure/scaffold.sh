#!/usr/bin/env bash
# Workspace for the case: a retry helper whose only test uses a mock that can't fail.
set -euo pipefail
cat >package.json <<'JSON'
{ "name": "retry-demo", "version": "1.0.0", "type": "module", "scripts": { "test": "node --test" } }
JSON
cat >TICKET.md <<'MD'
# RETRY-12

`getWithRetry(client, url)` calls `client.get(url)` up to 3 times. It returns the
first successful response. If all 3 attempts fail, it must throw the last error.
MD
cat >retry.js <<'JS'
export async function getWithRetry(client, url, tries = 3) {
  for (let attempt = 0; attempt < tries; attempt++) {
    try {
      return await client.get(url);
    } catch {
      // try again
    }
  }
  return null;
}
JS
cat >retry.test.js <<'JS'
import assert from "node:assert/strict";
import { test } from "node:test";
import { getWithRetry } from "./retry.js";

const client = { get: async (url) => ({ status: 200, url }) };

test("returns the response", async () => {
  const res = await getWithRetry(client, "/users");
  assert.equal(res.status, 200);
});
JS
