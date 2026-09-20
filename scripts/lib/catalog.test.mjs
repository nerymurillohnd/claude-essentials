// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";
import { catalogEntry, catalogEntryDrift, compileSchemas } from "./catalog.mjs";

const schemas = compileSchemas();

/** @param {Record<string, unknown>} [extra] */
const manifest = (extra = {}) => ({
  name: "demo",
  version: "0.1.0",
  description: "Does one thing.",
  ...extra,
});

/** @param {Record<string, unknown>[]} plugins */
const marketplace = (plugins) => ({
  name: "claude-essentials",
  owner: { name: "Owner" },
  plugins,
});

test("catalogEntry copies category and tags from metadata.marketplace in a fixed key order", () => {
  const entry = catalogEntry(
    "demo",
    "./plugins/demo",
    manifest({
      metadata: { marketplace: { tags: ["git-hooks", "guardrails"], category: "security" } },
    }),
  );
  assert.deepEqual(Object.keys(entry), ["name", "source", "description", "category", "tags"]);
  assert.deepEqual(entry, {
    name: "demo",
    source: "./plugins/demo",
    description: "Does one thing.",
    category: "security",
    tags: ["git-hooks", "guardrails"],
  });
});

test("catalogEntry omits category and tags when the manifest has none", () => {
  for (const extra of [{}, { metadata: {} }, { metadata: { catalogId: "x" } }]) {
    assert.deepEqual(Object.keys(catalogEntry("demo", "./plugins/demo", manifest(extra))), [
      "name",
      "source",
      "description",
    ]);
  }
  const categoryOnly = catalogEntry(
    "demo",
    "./plugins/demo",
    manifest({ metadata: { marketplace: { category: "testing" } } }),
  );
  assert.deepEqual(Object.keys(categoryOnly), ["name", "source", "description", "category"]);
});

test("plugin schema requires metadata.marketplace and accepts an allowed category", () => {
  assert.equal(schemas.plugin(manifest()), false);
  assert.equal(schemas.plugin(manifest({ metadata: {} })), false);
  assert.equal(
    schemas.plugin(
      manifest({
        metadata: {
          catalogId: "free-form keys stay allowed",
          marketplace: { category: "development", tags: ["shell", "lint"] },
        },
      }),
    ),
    true,
  );
  assert.equal(
    schemas.plugin(
      manifest({
        metadata: {
          marketplace: {
            category: "development",
            tags: ["a", "b", "c", "d", "e", "f", "g", "h"],
          },
        },
      }),
    ),
    true,
    "eight tags is the documented maximum and must still pass",
  );
});

test("plugin schema rejects an unknown category, a missing category, bad tags, and extra keys", () => {
  const invalid = [
    { category: "utilities" },
    { tags: ["lint"] },
    { category: "testing", tags: ["Not Kebab"] },
    { category: "testing", tags: [] },
    { category: "testing", tags: ["lint", "lint"] },
    { category: "testing", tags: ["a", "b", "c", "d", "e", "f", "g", "h", "i"] },
    { category: "testing", keywords: ["lint"] },
  ];
  for (const catalog of invalid) {
    assert.equal(
      schemas.plugin(manifest({ metadata: { marketplace: catalog } })),
      false,
      JSON.stringify(catalog),
    );
  }
});

test("marketplace schema accepts generated entries and rejects an unknown category", () => {
  const entry = { name: "demo", source: "./plugins/demo", description: "d" };
  assert.equal(schemas.marketplace(marketplace([entry])), true);
  assert.equal(
    schemas.marketplace(marketplace([{ ...entry, category: "security", tags: ["git-hooks"] }])),
    true,
  );
  assert.equal(schemas.marketplace(marketplace([{ ...entry, category: "utilities" }])), false);
  assert.equal(schemas.marketplace(marketplace([{ ...entry, tags: ["Upper"] }])), false);
});

test("catalogEntryDrift reports entries that differ from what generate would write", () => {
  const withCatalog = manifest({
    metadata: { marketplace: { category: "security", tags: ["git-hooks"] } },
  });
  const manifests = new Map([["demo", withCatalog]]);
  const generated = catalogEntry("demo", "./plugins/demo", withCatalog);
  assert.deepEqual(catalogEntryDrift([generated], manifests), []);

  const { tags: _tags, ...stale } = generated;
  const [problem] = catalogEntryDrift([stale], manifests);
  assert.match(problem ?? "", /"demo" differs .* run npm run generate/);
  assert.equal(catalogEntryDrift([{ ...generated, category: "testing" }], manifests).length, 1);
  assert.deepEqual(catalogEntryDrift([{ name: "absent", source: "./x" }], manifests), []);
});

test("plugin schema accepts the documented component fields and dependency objects", () => {
  const withMeta = { metadata: { marketplace: { category: "development" } } };
  assert.equal(
    schemas.plugin(
      manifest({
        ...withMeta,
        dependencies: ["other-plugin", { name: "vault", version: "^2.0.0" }],
        userConfig: { token: { type: "string", title: "Token", sensitive: true } },
        workflows: "./workflows/",
        outputStyles: ["./styles/a.md"],
        defaultEnabled: false,
        settings: { agent: "reviewer" },
      }),
    ),
    true,
  );
  assert.equal(
    schemas.plugin(manifest({ ...withMeta, dependencies: [{ version: "1.0.0" }] })),
    false,
  );
  assert.equal(schemas.plugin(manifest({ ...withMeta, defaultEnabled: "no" })), false);
});
