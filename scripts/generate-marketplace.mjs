// @ts-check
// Regenerates the `plugins` array in .claude-plugin/marketplace.json from
// each plugins/<name>/.claude-plugin/plugin.json on disk, so the catalog
// never drifts from what actually exists in plugins/.
import { readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { errorMessage, hasErrorCode } from "./lib/errors.mjs";
import { listPluginDirs, manifestPath, pluginsDir, rootDir } from "./lib/plugins.mjs";

const marketplacePath = join(rootDir, ".claude-plugin", "marketplace.json");

/**
 * @param {string} pluginName
 * @returns {{ name: string, description: string } & Record<string, unknown>}
 */
function readPluginManifest(pluginName) {
  /** @type {any} */
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath(pluginName), "utf8"));
  } catch (error) {
    if (hasErrorCode(error, "ENOENT")) {
      throw new Error(`plugins/${pluginName} has no .claude-plugin/plugin.json`);
    }
    throw new Error(
      `plugins/${pluginName}/.claude-plugin/plugin.json is not valid JSON: ${errorMessage(error)}`,
    );
  }
  if (manifest.name !== pluginName) {
    throw new Error(
      `plugins/${pluginName}/.claude-plugin/plugin.json has name "${manifest.name}", expected "${pluginName}" (directory name must match manifest name)`,
    );
  }
  if (!manifest.description) {
    throw new Error(`plugins/${pluginName}/.claude-plugin/plugin.json is missing a "description"`);
  }
  return manifest;
}

function main() {
  const marketplace = JSON.parse(readFileSync(marketplacePath, "utf8"));
  const pluginNames = listPluginDirs();

  marketplace.plugins = pluginNames.map((name) => {
    const manifest = readPluginManifest(name);
    const source = `./${relative(rootDir, join(pluginsDir, name))}`;
    return { name, source, description: manifest.description };
  });

  writeFileSync(marketplacePath, `${JSON.stringify(marketplace, null, 2)}\n`);
  console.log(`Wrote ${pluginNames.length} plugin(s) to ${relative(rootDir, marketplacePath)}`);
}

main();
