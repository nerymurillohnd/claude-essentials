// Shared paths and readers for plugins/<name>/.claude-plugin/plugin.json.
// Used by every script under scripts/ so they agree on what a plugin is.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
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

// ADR-0001 (amended): a plugin's kind is derived from what it ships, never declared.
// Single-component plugins must use the default layout (skills/<name>/SKILL.md or
// agents/<name>.md); any manifest-declared component path makes it a bundle.
const MANIFEST_COMPONENT_KEYS = [
  "commands",
  "agents",
  "skills",
  "hooks",
  "mcpServers",
  "lspServers",
  "outputStyles",
  "experimental",
];

function countEntries(dir, sub, keep) {
  try {
    return readdirSync(join(dir, sub)).filter((entry) => keep(join(dir, sub, entry), entry)).length;
  } catch (error) {
    if (error.code === "ENOENT") return 0;
    throw error;
  }
}

export function pluginComponents(dir, manifest) {
  return {
    skills: countEntries(dir, "skills", (path) => existsSync(join(path, "SKILL.md"))),
    agents: countEntries(dir, "agents", (_path, entry) => entry.endsWith(".md")),
    other:
      countEntries(dir, "commands", (_path, entry) => entry.endsWith(".md")) +
      countEntries(dir, "output-styles", () => true) +
      countEntries(dir, "monitors", () => true) +
      ["hooks/hooks.json", ".mcp.json", ".lsp.json"].filter((file) => existsSync(join(dir, file)))
        .length +
      MANIFEST_COMPONENT_KEYS.filter((key) => manifest[key] !== undefined).length,
  };
}

export function pluginKind({ skills, agents, other }) {
  if (other === 0 && skills === 1 && agents === 0) return "skill-only";
  if (other === 0 && agents === 1 && skills === 0) return "agent-only";
  return "bundle";
}

export function readmeKind(readme) {
  return /^\*\*Kind:\*\* `(bundle|skill-only|agent-only)`/m.exec(readme ?? "")?.[1] ?? null;
}

export function checkPluginKind(name, manifest, dir = pluginsDir) {
  const pluginDir = join(dir, name);
  const readmePath = join(pluginDir, "README.md");
  const declared = readmeKind(existsSync(readmePath) ? readFileSync(readmePath, "utf8") : null);
  const components = pluginComponents(pluginDir, manifest);
  const derived = pluginKind(components);
  if (declared === null) {
    return `plugins/${name}/README.md needs a "**Kind:** \`${derived}\`" line (ADR-0001)`;
  }
  if (declared !== derived) {
    const { skills, agents, other } = components;
    return `plugins/${name}/README.md declares Kind \`${declared}\` but its structure is \`${derived}\` (${skills} skill(s), ${agents} agent(s), ${other} other component(s)) — ADR-0001`;
  }
  return null;
}
