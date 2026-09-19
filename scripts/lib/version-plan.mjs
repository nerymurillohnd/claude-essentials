// @ts-check
// Pure version rules for plugins (ADR-0003). Inputs are gathered by
// check-versions.mjs (git), triage.mjs (GitHub API), or tag-versions.mjs; no I/O here.
// A plugin "release" is a merged version bump plus its {name}--v{version} tag —
// never a package or a GitHub Release.
import semver from "semver";
import { hasChangelogEntry } from "./changelog.mjs";

/**
 * @typedef {"initial" | "prerelease" | "patch" | "minor" | "major"} Bump
 * @typedef {"unchanged" | "removed" | "new" | "bumped" | "exempt" | "deferred"} PlanStatus
 * @typedef {{ version?: unknown } & Record<string, unknown>} Manifest
 *   A plugin.json object, not yet validated: `version` is the one field read by name.
 * @typedef {{
 *   name: string,
 *   status: PlanStatus,
 *   from: unknown,
 *   to: unknown,
 *   bump: Bump | null,
 *   errors: string[],
 * }} PluginPlan
 * @typedef {{
 *   changedFiles: readonly string[],
 *   base: ReadonlyMap<string, Manifest | null>,
 *   head: ReadonlyMap<string, Manifest | null>,
 *   changelogs: ReadonlyMap<string, string | null | undefined>,
 *   renames: Readonly<Record<string, string | null>>,
 *   existingTags: ReadonlySet<string>,
 *   deferred: boolean,
 * }} PlanContext
 */

/** @type {Readonly<Record<Bump, number>>} */
const RANK = { initial: 1, prerelease: 2, patch: 3, minor: 4, major: 5 };

// Paths (relative to plugins/<name>/) that Claude Code never loads at runtime, so
// changing them doesn't change the plugin. This list is CLOSED: anything not listed
// counts as runtime. Mirrored by .claude/hooks/lib/plugin-paths.sh — change both.
export const EXEMPT_FILE = /^(README\.md|CHANGELOG\.md|LICENSE(\.[^/]+)?|docs\/.+)$/;
export const METADATA_KEYS = new Set([
  "$schema",
  "version",
  "description",
  "displayName",
  "keywords",
  "author",
  "homepage",
  "repository",
  "license",
]);
const MANIFEST = ".claude-plugin/plugin.json";

/**
 * Recursively sorts object keys so JSON.stringify compares structure, not key order.
 * @param {unknown} value
 * @returns {unknown}
 */
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(/** @type {Record<string, unknown>} */ (value)[key])]),
    );
  }
  return value;
}

/**
 * @param {Manifest | null | undefined} before
 * @param {Manifest | null | undefined} after
 * @returns {boolean} Whether any non-metadata manifest field differs.
 */
export function runtimeManifestChanged(before, after) {
  /** @param {Manifest | null | undefined} manifest */
  const strip = (manifest) =>
    canonical(
      Object.fromEntries(Object.entries(manifest ?? {}).filter(([key]) => !METADATA_KEYS.has(key))),
    );
  return JSON.stringify(strip(before)) !== JSON.stringify(strip(after));
}

/**
 * @param {string} name
 * @param {readonly string[]} changedFiles Repo-relative paths.
 * @param {Manifest | null | undefined} before
 * @param {Manifest | null | undefined} after
 * @returns {string[]} Changed plugin-relative paths that Claude loads at runtime.
 */
function runtimeChanges(name, changedFiles, before, after) {
  const prefix = `plugins/${name}/`;
  return changedFiles
    .filter((file) => file.startsWith(prefix))
    .map((file) => file.slice(prefix.length))
    .filter((rel) =>
      rel === MANIFEST ? runtimeManifestChanged(before, after) : !EXEMPT_FILE.test(rel),
    );
}

/**
 * @param {unknown} version
 * @returns {version is string}
 */
const isCanonical = (version) => typeof version === "string" && semver.valid(version) === version;
/**
 * @param {string} name
 * @param {string} version
 */
const entryHint = (name, version) =>
  `plugins/${name}/CHANGELOG.md has no "## [${version}] - YYYY-MM-DD" entry`;

/**
 * @param {readonly string[]} changedFiles
 * @returns {string[]} Sorted names of plugins with at least one changed file.
 */
export function pluginsTouched(changedFiles) {
  /** @type {Set<string>} */
  const names = new Set();
  for (const file of changedFiles) {
    const match = /^plugins\/([^/]+)\/./.exec(file);
    if (match?.[1]) names.add(match[1]);
  }
  return [...names].sort();
}

/**
 * @param {string} from Canonical version, strictly lower than `to`.
 * @param {string} to
 * @returns {Bump}
 */
function bumpKind(from, to) {
  if (semver.prerelease(to)) return "prerelease";
  const diff = semver.diff(from, to);
  if (diff === "major" || diff === "minor" || diff === "patch") return diff;
  // semver.diff only reports pre* kinds when `to` is a prerelease, handled above.
  throw new Error(`unexpected semver.diff(${from}, ${to}) = ${diff}`);
}

/**
 * @typedef {{ status: PlanStatus, bump: Bump | null, error?: string, done: boolean }} VersionChange
 *   How a present, canonical `after` version relates to `before`. `done` means no
 *   release checks apply (an error, or a change that needs no new version).
 */

/**
 * Same version on both sides: fine if only exempt files changed or the bump is
 * deferred; otherwise the runtime change needs a bump.
 * @param {string} name
 * @param {Manifest} before
 * @param {Manifest & { version: string }} after
 * @param {Pick<PlanContext, "changedFiles" | "deferred">} context
 * @returns {VersionChange}
 */
function unbumpedChange(name, before, after, { changedFiles, deferred }) {
  const runtime = runtimeChanges(name, changedFiles, before, after);
  if (runtime.length === 0) return { status: "exempt", bump: null, done: true };
  if (deferred) return { status: "deferred", bump: null, done: true };
  const listed = runtime.slice(0, 5).join(", ") + (runtime.length > 5 ? ", …" : "");
  return {
    status: "unchanged",
    bump: null,
    error: `plugins/${name} changed runtime files (${listed}) but "version" is still ${after.version}. Bump it (semver) and add a CHANGELOG.md entry, or have a maintainer apply the "bump: deferred" label.`,
    done: true,
  };
}

/**
 * @param {string} name
 * @param {Manifest | null} before
 * @param {Manifest & { version: string }} after
 * @param {Pick<PlanContext, "changedFiles" | "deferred">} context
 * @returns {VersionChange}
 */
function versionChange(name, before, after, context) {
  if (!before) return { status: "new", bump: "initial", done: false };
  if (!isCanonical(before.version)) return { status: "bumped", bump: "initial", done: false };
  const order = semver.compare(after.version, before.version);
  if (order < 0) {
    return {
      status: "unchanged",
      bump: null,
      error: `plugins/${name}: version went backwards (${before.version} → ${after.version})`,
      done: true,
    };
  }
  if (order === 0) return unbumpedChange(name, before, after, context);
  return { status: "bumped", bump: bumpKind(before.version, after.version), done: false };
}

/**
 * Checks for a version about to be released: its tag must be new and its
 * CHANGELOG.md must have a dated entry.
 * @param {string} name
 * @param {string} version
 * @param {Pick<PlanContext, "existingTags" | "changelogs">} context
 * @returns {string[]}
 */
function releaseErrors(name, version, { existingTags, changelogs }) {
  /** @type {string[]} */
  const errors = [];
  const tag = `${name}--v${version}`;
  if (existingTags.has(tag))
    errors.push(`plugins/${name}: tag ${tag} already exists; pick a new version`);
  if (!hasChangelogEntry(changelogs.get(name), version)) errors.push(entryHint(name, version));
  return errors;
}

/**
 * @param {string} name
 * @param {PlanContext} context
 * @returns {PluginPlan}
 */
function planPlugin(name, context) {
  const before = context.base.get(name) ?? null;
  const after = context.head.get(name) ?? null;
  /** @type {PluginPlan} */
  const result = {
    name,
    status: "unchanged",
    from: before?.version ?? null,
    to: after?.version ?? null,
    bump: null,
    errors: [],
  };
  if (!after) {
    result.status = "removed";
    if (!Object.hasOwn(context.renames, name)) {
      result.errors.push(
        `plugins/${name} was removed; add "${name}" to marketplace.json "renames" (null, or its new name)`,
      );
    }
    return result;
  }
  const version = after.version;
  if (!isCanonical(version)) {
    result.errors.push(
      `plugins/${name}: "version" must be valid semver like 1.2.3, got ${JSON.stringify(version)}`,
    );
    return result;
  }
  const change = versionChange(name, before, { ...after, version }, context);
  result.status = change.status;
  result.bump = change.bump;
  if (change.error) result.errors.push(change.error);
  if (!change.done) result.errors.push(...releaseErrors(name, version, context));
  return result;
}

/**
 * @param {readonly Pick<PluginPlan, "status" | "bump" | "errors">[]} plugins
 * @returns {string | null} The `bump:` label, or null when any plugin has errors.
 */
export function bumpLabelFor(plugins) {
  if (plugins.some((plugin) => plugin.errors.length > 0)) return null;
  /** @type {Bump | null} */
  let best = null;
  for (const plugin of plugins) {
    /** @type {Bump | null} */
    const kind = plugin.status === "removed" ? "major" : plugin.bump;
    if (kind && (!best || RANK[kind] > RANK[best])) best = kind;
  }
  return `bump: ${best ?? "none"}`;
}

/**
 * @param {{
 *   changedFiles: readonly string[],
 *   base: ReadonlyMap<string, Manifest | null>,
 *   head: ReadonlyMap<string, Manifest | null>,
 *   changelogs: ReadonlyMap<string, string | null | undefined>,
 *   renames?: Readonly<Record<string, string | null>>,
 *   existingTags?: ReadonlySet<string>,
 *   deferred?: boolean,
 * }} input
 * @returns {{ plugins: PluginPlan[], bumpLabel: string | null, ok: boolean }}
 */
export function planVersions({
  changedFiles,
  base,
  head,
  changelogs,
  renames = {},
  existingTags = new Set(),
  deferred = false,
}) {
  const context = { changedFiles, base, head, changelogs, renames, existingTags, deferred };
  const plugins = pluginsTouched(changedFiles).map((name) => planPlugin(name, context));
  return {
    plugins,
    bumpLabel: bumpLabelFor(plugins),
    ok: plugins.every((plugin) => plugin.errors.length === 0),
  };
}

/**
 * @typedef {{ name: string, version: string, tag: string, prerelease: boolean }} UntaggedVersion
 */

/**
 * @param {readonly { name: string, version: unknown, changelog: unknown }[]} plugins
 * @param {ReadonlySet<string>} existingTags
 * @returns {{ versions: UntaggedVersion[], errors: string[] }}
 */
export function untaggedVersions(plugins, existingTags) {
  /** @type {UntaggedVersion[]} */
  const versions = [];
  /** @type {string[]} */
  const errors = [];
  for (const { name, version, changelog } of plugins) {
    if (!isCanonical(version)) {
      errors.push(`plugins/${name}: invalid or missing "version" ${JSON.stringify(version)}`);
      continue;
    }
    const tag = `${name}--v${version}`;
    if (existingTags.has(tag)) continue;
    if (!hasChangelogEntry(changelog, version)) {
      errors.push(entryHint(name, version));
      continue;
    }
    versions.push({ name, version, tag, prerelease: semver.prerelease(version) !== null });
  }
  return { versions, errors };
}
