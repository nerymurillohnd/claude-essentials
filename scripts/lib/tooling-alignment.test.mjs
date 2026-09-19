// @ts-check
// The Knip MCP server (.mcp.json) must analyze the repo with the same knip that
// `npm run knip` and CI run. It resolves `knip` from its own install location, so
// it stays aligned only while npm dedupes it to the root copy.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

/**
 * @param {string} path
 * @returns {Record<string, unknown>}
 */
function readJson(path) {
  return /** @type {Record<string, unknown>} */ (JSON.parse(readFileSync(path, "utf8")));
}

const requireFromRoot = createRequire(join(rootDir, "package.json"));

test("the Knip MCP server runs the repo's own knip", () => {
  // Resolve through each package's public entry point: neither exports its
  // package.json.
  const requireFromMcp = createRequire(requireFromRoot.resolve("@knip/mcp"));
  const knipForMcp = requireFromMcp.resolve("knip");
  const knipForRepo = requireFromRoot.resolve("knip");
  assert.equal(
    dirname(knipForMcp),
    dirname(knipForRepo),
    `@knip/mcp uses ${knipForMcp}, not the repo's ${knipForRepo}; align the versions so npm dedupes them`,
  );
});

test("the Knip MCP server version is pinned exactly and started without a download", () => {
  const pkg = readJson(join(rootDir, "package.json"));
  const devDependencies = /** @type {Record<string, string>} */ (pkg["devDependencies"] ?? {});
  assert.match(
    devDependencies["@knip/mcp"] ?? "",
    /^\d+\.\d+\.\d+$/,
    "@knip/mcp must be an exact version",
  );
  assert.match(devDependencies["knip"] ?? "", /^\d+\.\d+\.\d+$/, "knip must be an exact version");
  const mcp = /** @type {{ mcpServers: Record<string, { command?: string, args?: string[] }> }} */ (
    readJson(join(rootDir, ".mcp.json"))
  );
  const server = mcp.mcpServers["knip"];
  assert.ok(server, ".mcp.json must define the knip server");
  assert.equal(server.command, "npx");
  assert.deepEqual(server.args, ["--no-install", "knip-mcp"]);
});
