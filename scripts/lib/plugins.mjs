// Shared paths and readers for plugins/<name>/.claude-plugin/plugin.json.
// Used by every script under scripts/ so they agree on what a plugin is.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const rootDir = fileURLToPath(new URL("../..", import.meta.url));
export const pluginsDir = join(rootDir, "plugins");

export function listPluginDirs(dir = pluginsDir) {
  try {
    return readdirSync(dir)
      .filter((entry) => statSync(join(dir, entry)).isDirectory())
      .sort();
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

export function manifestPath(name, dir = pluginsDir) {
  return join(dir, name, ".claude-plugin", "plugin.json");
}

export function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}
