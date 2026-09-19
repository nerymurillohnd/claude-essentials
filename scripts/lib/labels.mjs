// @ts-check
// Label taxonomy (ADR-0004): authored labels live in .github/labels.json; one
// "plugin: <name>" label per plugins/<name>/ is derived, never authored.
/**
 * @typedef {{ name: string, color: string, description: string, aliases?: string[] }} Label
 *   An authored or derived label (`.github/labels.json` entry shape).
 * @typedef {{ name: string, color: string, description?: string | null }} RemoteLabel
 *   A label as GitHub returns it.
 * @typedef {{ op: "create", label: Label } | { op: "update", from: string, label: Label } | { op: "delete", from: string }} LabelOp
 */

export const PLUGIN_LABEL_PREFIX = "plugin: ";
export const PLUGIN_LABEL_COLOR = "5319e7";
export const MAX_LABEL_NAME = 50;
export const MAX_LABEL_DESCRIPTION = 100;

export const STATUS_LABELS = Object.freeze({
  triage: "status: needs-triage",
  info: "status: needs-info",
  stale: "status: stale",
});
export const BUMP_LABELS = Object.freeze([
  "bump: major",
  "bump: minor",
  "bump: patch",
  "bump: prerelease",
  "bump: initial",
  "bump: none",
]);
export const DEFERRED_LABEL = "bump: deferred";
export const AREA_LABELS = Object.freeze([
  "area: plugins",
  "area: catalog",
  "area: ci",
  "area: tooling",
  "area: templates",
  "area: docs",
  "area: community",
]);
// Labels that scripts, workflows, or issue forms reference by name.
export const REQUIRED_LABELS = Object.freeze([
  ...Object.values(STATUS_LABELS),
  ...BUMP_LABELS,
  DEFERRED_LABEL,
  ...AREA_LABELS,
]);

/**
 * @param {string} text
 * @param {number} max
 * @returns {string}
 */
const truncate = (text, max) => (text.length <= max ? text : `${text.slice(0, max - 1)}…`);

/**
 * @param {string} name
 * @returns {string}
 */
export function pluginLabelName(name) {
  return `${PLUGIN_LABEL_PREFIX}${name}`;
}

/**
 * @param {{ name: string, description?: string }} manifest
 * @returns {Label}
 */
export function pluginLabel({ name, description }) {
  return {
    name: pluginLabelName(name),
    color: PLUGIN_LABEL_COLOR,
    description: truncate(description || `Plugin ${name}`, MAX_LABEL_DESCRIPTION),
  };
}

/**
 * @param {readonly Label[]} staticLabels
 * @param {readonly { name: string, description?: string }[]} manifests
 * @returns {Label[]}
 */
export function buildTaxonomy(staticLabels, manifests) {
  return [...staticLabels, ...manifests.map(pluginLabel)];
}

/**
 * @param {readonly RemoteLabel[]} current
 * @param {readonly Label[]} desired
 * @param {{ prune?: boolean }} [options]
 * @returns {LabelOp[]}
 */
export function diffLabels(current, desired, { prune = false } = {}) {
  /** @param {string} name */
  const key = (name) => name.toLowerCase();
  const byName = new Map(current.map((label) => [key(label.name), label]));
  /** @type {Set<string>} */
  const claimed = new Set();
  /** @type {LabelOp[]} */
  const ops = [];
  for (const want of desired) {
    const have = byName.get(key(want.name));
    if (have) {
      claimed.add(key(have.name));
      const same =
        have.name === want.name &&
        have.color.toLowerCase() === want.color &&
        (have.description ?? "") === want.description;
      if (!same) ops.push({ op: "update", from: have.name, label: want });
      continue;
    }
    const alias = (want.aliases ?? [])
      .map((name) => byName.get(key(name)))
      .find((label) => label && !claimed.has(key(label.name)));
    if (alias) {
      claimed.add(key(alias.name));
      ops.push({ op: "update", from: alias.name, label: want });
      continue;
    }
    ops.push({ op: "create", label: want });
  }
  if (prune) {
    for (const have of current) {
      if (!claimed.has(key(have.name))) ops.push({ op: "delete", from: have.name });
    }
  }
  return ops;
}
