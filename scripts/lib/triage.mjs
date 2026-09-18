// Pure triage rules (ADR-0004): which labels an issue or PR should carry.
// scripts/triage.mjs gathers inputs from the GitHub event and API.
import { CATALOG_OPTION, PLUGIN_FIELD_LABEL } from "./issue-forms.mjs";
import { DEFERRED_LABEL, pluginLabelName, STATUS_LABELS } from "./labels.mjs";
import { pluginsTouched } from "./version-plan.mjs";

const COMMUNITY_FILES = new Set([
  ".github/pull_request_template.md",
  ".github/labels.json",
  "CONTRIBUTING.md",
  "CODE_OF_CONDUCT.md",
  "SECURITY.md",
]);
const TOOLING_FILES = new Set(["package.json", "package-lock.json", "biome.json", ".editorconfig"]);

export const AREA_RULES = Object.freeze([
  { label: "area: plugins", test: (f) => f.startsWith("plugins/") },
  {
    label: "area: catalog",
    test: (f) => f.startsWith(".claude-plugin/") || f.startsWith("schemas/"),
  },
  { label: "area: ci", test: (f) => f.startsWith(".github/workflows/") },
  {
    label: "area: tooling",
    test: (f) => f.startsWith("scripts/") || f.startsWith(".claude/") || TOOLING_FILES.has(f),
  },
  { label: "area: templates", test: (f) => f.startsWith("templates/") },
  { label: "area: docs", test: (f) => f.startsWith("docs/") || /^[^/]+\.md$/.test(f) },
  {
    label: "area: community",
    test: (f) => f.startsWith(".github/ISSUE_TEMPLATE/") || COMMUNITY_FILES.has(f),
  },
]);

const MANAGED_PREFIXES = ["area: ", "plugin: ", "bump: "];
const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Mirrors schemas/plugin.schema.json's "name" pattern/maxLength: a fork PR's
// changed paths are attacker-controlled, so any name derived from them must be
// validated before it is turned into a "plugin: <name>" label (ADR-0004).
const PLUGIN_NAME_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const MAX_PLUGIN_NAME = 42;

export function isValidPluginName(name) {
  return PLUGIN_NAME_PATTERN.test(name) && name.length <= MAX_PLUGIN_NAME;
}

export function areaLabels(files) {
  return AREA_RULES.filter((rule) => files.some(rule.test))
    .map((rule) => rule.label)
    .sort();
}

export function pluginLabels(files) {
  return pluginsTouched(files).filter(isValidPluginName).map(pluginLabelName);
}

export function formField(body, label) {
  const match = new RegExp(`^### ${escapeRegExp(label)}[ \\t]*\\n+([^\\n]*)`, "m").exec(body ?? "");
  const value = match?.[1]?.trim();
  return value && value !== "_No response_" ? value : null;
}

export function issueLabels(body, pluginNames) {
  const value = formField(body, PLUGIN_FIELD_LABEL);
  if (value === CATALOG_OPTION) return ["area: catalog"];
  if (value && pluginNames.includes(value)) return [pluginLabelName(value)];
  return [];
}

export function authorReplyChanges({ labels, author, commenter }) {
  if (author !== commenter || !labels.includes(STATUS_LABELS.info)) return { add: [], remove: [] };
  return {
    add: [STATUS_LABELS.triage],
    remove: [STATUS_LABELS.info, STATUS_LABELS.stale].filter((label) => labels.includes(label)),
  };
}

export function reconcile(current, desired) {
  const managed = (label) =>
    label !== DEFERRED_LABEL && MANAGED_PREFIXES.some((prefix) => label.startsWith(prefix));
  return {
    add: desired.filter((label) => !current.includes(label)),
    remove: current.filter((label) => managed(label) && !desired.includes(label)),
  };
}
