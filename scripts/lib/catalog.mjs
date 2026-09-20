// @ts-check
// Builds and checks .claude-plugin/marketplace.json entries from plugin.json.
// Catalog-only fields (`category`, `tags`) live in plugin.json under
// `metadata.marketplace`: Claude Code never reads `metadata`
// (https://code.claude.com/docs/en/plugins-reference), and plugin.json has no
// `category`/`tags` of its own, while marketplace entries do
// (https://code.claude.com/docs/en/plugin-marketplaces). The allowed categories
// are defined once, in schemas/plugin.schema.json#/definitions/marketplaceCategory.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Ajv } from "ajv";
import ajvFormats from "ajv-formats";
import { rootDir } from "./plugins.mjs";

// ajv-formats is CommonJS: `.default` is the plugin function (same object at runtime) and what its typings declare.
const addFormats = ajvFormats.default;

/**
 * @typedef {{
 *   name: string,
 *   source: string,
 *   description: unknown,
 *   category?: unknown,
 *   tags?: unknown,
 * }} CatalogEntry
 */

/**
 * The marketplace entry `npm run generate` writes for one plugin. Key order is
 * fixed (name, source, description, category, tags) so the output is
 * deterministic; `category` and `tags` are omitted when the manifest has none.
 * @param {string} name
 * @param {string} source
 * @param {Record<string, unknown>} manifest A parsed plugin.json.
 * @returns {CatalogEntry}
 */
export function catalogEntry(name, source, manifest) {
  /** @type {CatalogEntry} */
  const entry = { name, source, description: manifest["description"] };
  const metadata = manifest["metadata"];
  const catalog =
    metadata && typeof metadata === "object"
      ? /** @type {Record<string, unknown>} */ (metadata)["marketplace"]
      : undefined;
  if (catalog && typeof catalog === "object") {
    const { category, tags } = /** @type {Record<string, unknown>} */ (catalog);
    if (category !== undefined) entry.category = category;
    if (tags !== undefined) entry.tags = tags;
  }
  return entry;
}

/**
 * Compares the catalog entries on disk with what `catalogEntry` would generate.
 * @param {readonly unknown[]} entries marketplace.json `plugins` (schema-validated).
 * @param {ReadonlyMap<string, Record<string, unknown>>} manifests plugin.json by name.
 * @returns {string[]} One problem per entry that differs; [] when all match.
 */
export function catalogEntryDrift(entries, manifests) {
  /** @type {string[]} */
  const problems = [];
  for (const raw of entries) {
    const entry = /** @type {CatalogEntry} */ (raw);
    const manifest = manifests.get(entry.name);
    if (!manifest) continue;
    const expected = catalogEntry(entry.name, entry.source, manifest);
    if (JSON.stringify(entry) !== JSON.stringify(expected)) {
      problems.push(
        `marketplace.json entry "${entry.name}" differs from plugins/${entry.name}/.claude-plugin/plugin.json (description, metadata.marketplace.category, or metadata.marketplace.tags) — run npm run generate`,
      );
    }
  }
  return problems;
}

/**
 * Compiles schemas/plugin.schema.json and schemas/marketplace.schema.json with
 * one Ajv instance, so the marketplace schema's `$ref`s into the plugin schema
 * (the single category list) resolve.
 * @param {string} [root]
 */
export function compileSchemas(root = rootDir) {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  /** @param {string} file */
  const load = (file) => JSON.parse(readFileSync(join(root, "schemas", file), "utf8"));
  const plugin = ajv.compile(load("plugin.schema.json"));
  const marketplace = ajv.compile(load("marketplace.schema.json"));
  return { plugin, marketplace };
}
