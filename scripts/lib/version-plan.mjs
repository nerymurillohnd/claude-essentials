// Pure version rules for plugins (ADR-0003). Inputs are gathered by
// check-versions.mjs (git), triage.mjs (GitHub API), or tag-versions.mjs; no I/O here.
// A plugin "release" is a merged version bump plus its {name}--v{version} tag —
// never a package or a GitHub Release.
import semver from "semver";
import { hasChangelogEntry } from "./changelog.mjs";

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

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}

export function runtimeManifestChanged(before, after) {
  const strip = (manifest) =>
    canonical(
      Object.fromEntries(Object.entries(manifest ?? {}).filter(([key]) => !METADATA_KEYS.has(key))),
    );
  return JSON.stringify(strip(before)) !== JSON.stringify(strip(after));
}

export function runtimeChanges(name, changedFiles, before, after) {
  const prefix = `plugins/${name}/`;
  return changedFiles
    .filter((file) => file.startsWith(prefix))
    .map((file) => file.slice(prefix.length))
    .filter((rel) =>
      rel === MANIFEST ? runtimeManifestChanged(before, after) : !EXEMPT_FILE.test(rel),
    );
}

const isCanonical = (version) => typeof version === "string" && semver.valid(version) === version;
const entryHint = (name, version) =>
  `plugins/${name}/CHANGELOG.md has no "## [${version}] - YYYY-MM-DD" entry`;

export function pluginsTouched(changedFiles) {
  const names = new Set();
  for (const file of changedFiles) {
    const match = /^plugins\/([^/]+)\/./.exec(file);
    if (match) names.add(match[1]);
  }
  return [...names].sort();
}

function bumpKind(from, to) {
  if (semver.prerelease(to)) return "prerelease";
  return semver.diff(from, to).replace(/^pre/, "");
}

function planPlugin(
  name,
  { changedFiles, base, head, changelogs, renames, existingTags, deferred },
) {
  const before = base.get(name) ?? null;
  const after = head.get(name) ?? null;
  const errors = [];
  const result = {
    name,
    status: "unchanged",
    from: before?.version ?? null,
    to: after?.version ?? null,
    bump: null,
    errors,
  };

  if (!after) {
    result.status = "removed";
    if (!Object.hasOwn(renames, name)) {
      errors.push(
        `plugins/${name} was removed; add "${name}" to marketplace.json "renames" (null, or its new name)`,
      );
    }
    return result;
  }
  if (!isCanonical(after.version)) {
    errors.push(
      `plugins/${name}: "version" must be valid semver like 1.2.3, got ${JSON.stringify(after.version)}`,
    );
    return result;
  }
  if (!before) {
    result.status = "new";
    result.bump = "initial";
  } else if (!isCanonical(before.version)) {
    result.status = "bumped";
    result.bump = "initial";
  } else {
    const order = semver.compare(after.version, before.version);
    if (order < 0) {
      errors.push(`plugins/${name}: version went backwards (${before.version} → ${after.version})`);
      return result;
    }
    if (order === 0) {
      const runtime = runtimeChanges(name, changedFiles, before, after);
      if (runtime.length === 0) {
        result.status = "exempt";
        return result;
      }
      if (deferred) {
        result.status = "deferred";
        return result;
      }
      const listed = runtime.slice(0, 5).join(", ") + (runtime.length > 5 ? ", …" : "");
      errors.push(
        `plugins/${name} changed runtime files (${listed}) but "version" is still ${after.version}. Bump it (semver) and add a CHANGELOG.md entry, or have a maintainer apply the "bump: deferred" label.`,
      );
      return result;
    }
    result.status = "bumped";
    result.bump = bumpKind(before.version, after.version);
  }

  const tag = `${name}--v${after.version}`;
  if (existingTags.has(tag))
    errors.push(`plugins/${name}: tag ${tag} already exists; pick a new version`);
  if (!hasChangelogEntry(changelogs.get(name), after.version))
    errors.push(entryHint(name, after.version));
  return result;
}

export function bumpLabelFor(plugins) {
  if (plugins.some((plugin) => plugin.errors.length > 0)) return null;
  let best = null;
  for (const plugin of plugins) {
    const kind = plugin.status === "removed" ? "major" : plugin.bump;
    if (kind && (!best || RANK[kind] > RANK[best])) best = kind;
  }
  return `bump: ${best ?? "none"}`;
}

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

export function untaggedVersions(plugins, existingTags) {
  const versions = [];
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
