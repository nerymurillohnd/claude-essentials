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
const PLUGIN_LABEL_COLOR = "5319e7";
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

/** @param {string} name */
const labelKey = (name) => name.toLowerCase();

/**
 * @param {RemoteLabel} have
 * @param {Label} want
 * @returns {boolean} Whether GitHub's label already matches the taxonomy exactly.
 */
function isSameLabel(have, want) {
  return (
    have.name === want.name &&
    have.color.toLowerCase() === want.color &&
    (have.description ?? "") === want.description
  );
}

/**
 * The operation that brings one desired label into place, claiming the GitHub label
 * it reuses (by name first, then by the first unclaimed alias) so it's never reused
 * twice or pruned.
 * @param {Label} want
 * @param {ReadonlyMap<string, RemoteLabel>} byName Current labels by lower-cased name.
 * @param {Set<string>} claimed Lower-cased names already reused; updated in place.
 * @returns {LabelOp | null} null when the label already matches.
 */
function planLabel(want, byName, claimed) {
  const have = byName.get(labelKey(want.name));
  if (have) {
    claimed.add(labelKey(have.name));
    return isSameLabel(have, want) ? null : { op: "update", from: have.name, label: want };
  }
  const alias = (want.aliases ?? [])
    .map((name) => byName.get(labelKey(name)))
    .find((label) => label !== undefined && !claimed.has(labelKey(label.name)));
  if (alias) {
    claimed.add(labelKey(alias.name));
    return { op: "update", from: alias.name, label: want };
  }
  return { op: "create", label: want };
}

/**
 * @param {readonly RemoteLabel[]} current
 * @param {readonly Label[]} desired
 * @param {{ prune?: boolean }} [options]
 * @returns {LabelOp[]}
 */
export function diffLabels(current, desired, { prune = false } = {}) {
  const byName = new Map(current.map((label) => [labelKey(label.name), label]));
  /** @type {Set<string>} */
  const claimed = new Set();
  /** @type {LabelOp[]} */
  const ops = [];
  for (const want of desired) {
    const op = planLabel(want, byName, claimed);
    if (op) ops.push(op);
  }
  if (prune) {
    for (const have of current) {
      if (!claimed.has(labelKey(have.name))) ops.push({ op: "delete", from: have.name });
    }
  }
  return ops;
}
