#!/usr/bin/env node
// Regenerates the `plugins` array in .claude-plugin/marketplace.json from
// each plugins/<name>/.claude-plugin/plugin.json on disk, so the catalog
// never drifts from what actually exists in plugins/.
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("..", import.meta.url));
const pluginsDir = join(rootDir, "plugins");
const marketplacePath = join(rootDir, ".claude-plugin", "marketplace.json");

function listPluginDirs() {
  try {
    return readdirSync(pluginsDir)
      .filter((entry) => statSync(join(pluginsDir, entry)).isDirectory())
      .sort();
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function readPluginManifest(pluginName) {
  const manifestPath = join(pluginsDir, pluginName, ".claude-plugin", "plugin.json");
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`plugins/${pluginName} has no .claude-plugin/plugin.json`);
    }
    throw new Error(
      `plugins/${pluginName}/.claude-plugin/plugin.json is not valid JSON: ${error.message}`,
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
