// @ts-check
// Enforces the plugin README contract (templates/plugin-README-reusable-template.md)
// and the root README catalog (templates/root-README-recommended-template.md), so a
// published plugin can't ship with missing sections, template drift, or no catalog row.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { manifestPath, pluginComponents, pluginKind, readJson } from "./plugins.mjs";

export const PLUGIN_TEMPLATE = "templates/plugin-README-reusable-template.md";
export const LICENSE_TEMPLATE = "templates/LICENSE-Apache-2.0-reusable-template.md";
const OPTIONAL_SECTIONS = new Set(["Other components", "FAQ"]);
const CORE_BADGES = ["Version", "License: Apache-2.0", "Kind", "Claude Code", "Claude Cowork"];
const PLACEHOLDER_ROW = "_No plugins published yet_";

/** Badge status (shields.io message) → the Compatibility vocabulary used in catalog cells. */
const STATUS_EMOJI = /** @type {Readonly<Record<string, string>>} */ ({
  supported: "✅",
  partial: "⚠️",
  not_tested: "🧪",
  not_supported: "❌",
});

/**
 * @typedef {{ order: string[], required: string[], badgeLabels: Set<string> }} Contract
 * @typedef {{ id: string, displayName: string, kind: string, code: string, cowork: string, minimums: Map<string, string> }} CatalogEntry
 */

/**
 * @param {string} line
 * @returns {string} Heading text without the leading "## " and emoji.
 */
export function headingTitle(line) {
  return line
    .replace(/^#+\s+/, "")
    .replace(/^[^\p{L}\p{N}]+/u, "")
    .trim();
}

/**
 * Lines outside HTML comments and, unless `keepFences`, outside fenced code blocks.
 * Fence lines themselves are always dropped from the result when not kept.
 * @param {string} markdown
 * @param {boolean} [keepFences]
 * @returns {string[]}
 */
function proseLines(markdown, keepFences = false) {
  /** @type {string[]} */
  const out = [];
  let inFence = false;
  let inComment = false;
  for (const line of markdown.split("\n")) {
    if (!inComment && line.startsWith("```")) {
      inFence = !inFence;
      if (keepFences) out.push(line);
    } else if (!inFence && line.includes("<!--")) inComment = !line.includes("-->");
    else if (inComment) inComment = !line.includes("-->");
    else if (!inFence || keepFences) out.push(line);
  }
  return out;
}

/**
 * @param {string} markdown
 * @returns {string[]} Level-2 section titles, in order.
 */
export function sectionTitles(markdown) {
  return proseLines(markdown)
    .filter((line) => line.startsWith("## "))
    .map(headingTitle);
}

/**
 * @param {string} template The master plugin README template.
 * @returns {Contract}
 */
export function readContract(template) {
  const order = sectionTitles(template);
  const badgeLabels = new Set(CORE_BADGES);
  for (const match of template.matchAll(/!\[([^\]]+)\]\(https:\/\/img\.shields\.io\//g)) {
    if (match[1]) badgeLabels.add(match[1]);
  }
  return { order, required: order.filter((s) => !OPTIONAL_SECTIONS.has(s)), badgeLabels };
}

/**
 * @param {string[]} found
 * @param {Contract} contract
 * @returns {string[]}
 */
function checkSections(found, contract) {
  /** @type {string[]} */
  const problems = [];
  for (const title of contract.required) {
    if (!found.includes(title)) problems.push(`missing required section "${title}"`);
  }
  for (const title of found) {
    if (!contract.order.includes(title)) problems.push(`unknown section "${title}"`);
  }
  const known = found.filter((title) => contract.order.includes(title));
  const expected = contract.order.filter((title) => known.includes(title));
  if (known.join("|") !== expected.join("|")) {
    problems.push(`sections out of template order: ${known.join(" → ")}`);
  }
  return problems;
}

/**
 * @param {string} markdown
 * @param {boolean} [keepFences] Include fenced code blocks in each body.
 * @returns {Map<string, string[]>} Section title → its lines ("" = header area).
 */
export function sectionBodies(markdown, keepFences = false) {
  /** @type {Map<string, string[]>} */
  const bodies = new Map([["", []]]);
  let current = "";
  let inFence = false;
  for (const line of proseLines(markdown, keepFences)) {
    if (line.startsWith("```")) inFence = !inFence;
    if (!inFence && line.startsWith("## ")) {
      current = headingTitle(line);
      bodies.set(current, []);
    } else {
      bodies.get(current)?.push(line);
    }
  }
  return bodies;
}

/**
 * @param {string} markdown
 * @returns {string[]}
 */
function checkAlerts(markdown) {
  /** @type {string[]} */
  const problems = [];
  for (const [title, lines] of sectionBodies(markdown)) {
    const alerts = lines.filter((line) =>
      /^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/.test(line),
    );
    if (alerts.length > 1)
      problems.push(`section "${title || "header"}" has ${alerts.length} alerts (max 1)`);
  }
  return problems;
}

/**
 * @param {string} markdown
 * @returns {string[]}
 */
function checkFences(markdown) {
  let open = false;
  let unlabeled = 0;
  for (const line of markdown.split("\n")) {
    if (!line.startsWith("```")) continue;
    if (!open && line.trim() === "```") unlabeled++;
    open = !open;
  }
  return unlabeled > 0 ? [`${unlabeled} code block(s) without a language (use text or bash)`] : [];
}

/**
 * @param {string} markdown
 * @returns {Map<string, string>} Badge alt text → its shields.io URL, from the header area.
 */
export function headerBadges(markdown) {
  const header = sectionBodies(markdown).get("")?.join("\n") ?? "";
  /** @type {Map<string, string>} */
  const badges = new Map();
  for (const match of header.matchAll(/!\[([^\]]+)\]\((https:\/\/img\.shields\.io\/[^)\s]+)\)/g)) {
    if (match[1] && match[2]) badges.set(match[1], match[2]);
  }
  return badges;
}

/**
 * @param {string} id
 * @param {Map<string, string>} badges
 * @param {Contract} contract
 * @returns {string[]}
 */
function checkBadges(id, badges, contract) {
  /** @type {string[]} */
  const problems = [];
  for (const label of CORE_BADGES) {
    if (!badges.has(label)) problems.push(`missing the "${label}" badge`);
  }
  const version = badges.get("Version") ?? "";
  if (version && !version.includes(`plugins%2F${id}%2F.claude-plugin%2Fplugin.json`)) {
    problems.push(
      `the Version badge must read plugins/${id}/.claude-plugin/plugin.json dynamically`,
    );
  }
  for (const label of badges.keys()) {
    if (!contract.badgeLabels.has(label)) {
      problems.push(
        `badge "${label}" is not in the template's requirement badge catalog; add it there first`,
      );
    }
  }
  for (const surface of ["Claude Code", "Claude Cowork"]) {
    if (badges.has(surface) && !surfaceStatus(badges.get(surface) ?? "")) {
      problems.push(
        `the "${surface}" badge status must be one of ${Object.keys(STATUS_EMOJI).join(", ")}`,
      );
    }
  }
  return problems;
}

/**
 * @param {string} url A shields.io static badge URL: .../badge/<label>-<status>-<color>...
 * @returns {string} The catalog emoji for its status, or "".
 */
export function surfaceStatus(url) {
  const status = /\/badge\/Claude_(?:Code|Cowork)-([a-z_]+)-/.exec(url)?.[1] ?? "";
  return STATUS_EMOJI[status] ?? "";
}

/**
 * @param {string} id
 * @param {Map<string, string[]>} bodies
 * @returns {string[]}
 */
function checkInstallation(id, bodies) {
  const text = bodies.get("Installation")?.join("\n") ?? "";
  /** @type {[string, string][]} */
  const required = [
    [`/plugin install ${id}@claude-essentials`, "the Claude Code install command"],
    ["Customize → Plugins → Add marketplace", "the Claude Cowork install steps"],
    ["In Cowork, use **Update** on the marketplace", "the Cowork update/uninstall line"],
  ];
  return required
    .filter(([needle]) => !text.includes(needle))
    .map(([, what]) => `Installation is missing ${what} from the template`);
}

/**
 * Checks one plugin README against the contract.
 * @param {string} id
 * @param {string} readme
 * @param {Contract} contract
 * @returns {string[]} Problems, prefixed with the README path.
 */
export function checkPluginReadme(id, readme, contract) {
  const problems = [
    ...checkSections(sectionTitles(readme), contract),
    ...checkAlerts(readme),
    ...checkFences(readme),
    ...checkBadges(id, headerBadges(readme), contract),
    ...checkInstallation(id, sectionBodies(readme, true)),
  ];
  if (readme.includes("{{")) problems.push("unreplaced {{placeholder}} left from the template");
  return problems.map((problem) => `plugins/${id}/README.md: ${problem}`);
}

/**
 * @param {Map<string, string>} badges
 * @returns {Map<string, string>} Requirement badge label → minimum version, from "≥" badges.
 */
export function badgeMinimums(badges) {
  /** @type {Map<string, string>} */
  const minimums = new Map();
  for (const [label, url] of badges) {
    const version = /\/badge\/[^/]*?-%E2%89%A5([0-9][0-9.]*)-/.exec(url)?.[1];
    if (version) minimums.set(label, version);
  }
  return minimums;
}

/**
 * @param {Map<string, string[]>} bodies
 * @returns {Map<string, string>} Lowercased requirement name → its Minimum cell.
 */
function requirementRows(bodies) {
  /** @type {Map<string, string>} */
  const rows = new Map();
  for (const line of bodies.get("Requirements") ?? []) {
    const cells = line.split("|").map((cell) => cell.trim());
    if (cells.length > 3 && cells[1] && cells[2]) {
      rows.set(cells[1].replaceAll("`", "").toLowerCase(), cells[2]);
    }
  }
  return rows;
}

/**
 * Every "≥" requirement badge must match the Requirements table.
 * @param {Map<string, string>} minimums
 * @param {Map<string, string[]>} bodies
 * @returns {string[]}
 */
export function checkRequirementMinimums(minimums, bodies) {
  const rows = requirementRows(bodies);
  /** @type {string[]} */
  const problems = [];
  for (const [label, version] of minimums) {
    const cell = rows.get(label.toLowerCase());
    if (cell === undefined) {
      problems.push(`badge "${label} ≥ ${version}" has no row in the Requirements table`);
    } else if (!cell.includes(version)) {
      problems.push(`Requirements says ${label} "${cell}", but its badge says ≥ ${version}`);
    }
  }
  return problems;
}

const NETWORK_TOOL =
  /\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod)\b|\/dev\/(tcp|udp)\/|(^|[;&|(`\s])nc\s/;
const SCRIPT_FILE = /\.(sh|bash|zsh|py|js|mjs|cjs|ts|ps1|rb)$/;
const NOT_RUNTIME = /^(README\.md|CHANGELOG\.md|LICENSE|docs\/|evals\/)/;

/**
 * @param {string} dir
 * @returns {string[]} Every file under `dir`, recursively.
 */
function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

/**
 * Every plugin README states its network posture, and a README that declares no
 * network use must not ship scripts that call out. The missing-badge case is the
 * one that misleads: a reader scanning the badge row sees nothing about the
 * network and assumes there is none.
 * @param {string} pluginDir
 * @param {Map<string, string>} badges
 * @returns {string[]}
 */
export function checkNetworkClaim(pluginDir, badges) {
  const badge = badges.get("Network");
  if (badge === undefined) {
    return [
      "the badge row has no Network badge; every plugin states its network posture (network-none, network-optional or network-required)",
    ];
  }
  if (!/\/badge\/network-none-/.test(badge)) return [];
  /** @type {string[]} */
  const problems = [];
  for (const path of walk(pluginDir)) {
    const rel = relative(pluginDir, path);
    if (NOT_RUNTIME.test(rel)) continue;
    const text = readFileSync(path, "utf8");
    if (!SCRIPT_FILE.test(rel) && !text.startsWith("#!")) continue;
    const hit = text
      .split("\n")
      .findIndex((line) => !line.trimStart().startsWith("#") && NETWORK_TOOL.test(line));
    if (hit >= 0) {
      problems.push(`the Network badge says none, but ${rel}:${hit + 1} calls a network tool`);
    }
  }
  return problems;
}

/**
 * Every CHANGELOG heading ([Unreleased] and each version) has its compare/tag link.
 * @param {string} changelog
 * @returns {string[]}
 */
export function checkChangelogLinks(changelog) {
  const headings = [...changelog.matchAll(/^## \[([^\]]+)\]/gm)].map((match) => match[1] ?? "");
  const defined = new Set(
    [...changelog.matchAll(/^\[([^\]]+)\]: https:\/\/\S+$/gm)].map((match) => match[1] ?? ""),
  );
  return headings
    .filter((heading) => !defined.has(heading))
    .map((heading) => `CHANGELOG.md has no link definition for [${heading}]`);
}

/**
 * @param {string} text
 * @returns {string} `text` escaped for use inside a RegExp.
 */
function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * @param {string} rootReadme
 * @returns {string[][]} Cells of each body row in the "Plugin catalog" table.
 */
export function catalogRows(rootReadme) {
  const lines = sectionBodies(rootReadme).get("Plugin catalog") ?? [];
  return lines
    .filter((line) => line.startsWith("|"))
    .slice(2)
    .map((line) =>
      line
        .slice(1, line.endsWith("|") ? -1 : undefined)
        .split("|")
        .map((cell) => cell.trim()),
    );
}

/**
 * @param {string[]} row
 * @param {CatalogEntry} entry
 * @returns {string[]}
 */
function checkRow(row, entry) {
  const [link = "", , kind = "", code = "", cowork = "", requirements = ""] = row;
  /** @type {string[]} */
  const problems = [];
  const expectedLink = `[${entry.displayName}](plugins/${entry.id}/README.md)`;
  if (link !== expectedLink) problems.push(`first cell must be ${expectedLink}`);
  if (kind !== `\`${entry.kind}\``) problems.push(`kind must be \`${entry.kind}\``);
  if (code !== entry.code) problems.push(`Claude Code must be ${entry.code} (its README badge)`);
  if (cowork !== entry.cowork)
    problems.push(`Claude Cowork must be ${entry.cowork} (its README badge)`);
  for (const [label, version] of entry.minimums) {
    const pattern = new RegExp(
      `\`?${escapeRegExp(label)}\`?\\s*≥\\s*${escapeRegExp(version)}\\b`,
      "i",
    );
    if (!pattern.test(requirements)) {
      problems.push(`Additional requirements must include ${label} ≥ ${version}`);
    }
  }
  return problems.map((problem) => `README.md catalog row for ${entry.id}: ${problem}`);
}

/**
 * Checks the root README catalog: exactly one row per plugin, sorted by id,
 * matching each plugin's README, and no placeholder row once plugins exist.
 * @param {string} rootReadme
 * @param {CatalogEntry[]} entries Sorted by id.
 * @returns {string[]}
 */
export function checkRootCatalog(rootReadme, entries) {
  const rows = catalogRows(rootReadme);
  if (entries.length === 0) return [];
  /** @type {string[]} */
  const problems = [];
  if (rows.some((row) => row[0] === PLACEHOLDER_ROW)) {
    problems.push(`README.md catalog still has the "${PLACEHOLDER_ROW}" row`);
  }
  const listed = rows.filter((row) => row[0] !== PLACEHOLDER_ROW);
  const ids = listed.map((row) => /\(plugins\/([^/]+)\/README\.md\)/.exec(row[0] ?? "")?.[1] ?? "");
  const expected = entries.map((entry) => entry.id);
  if (ids.join("|") !== expected.join("|")) {
    problems.push(
      `README.md catalog must list exactly ${expected.join(", ")} (sorted); it lists ${ids.join(", ") || "none"}`,
    );
  }
  entries.forEach((entry, index) => {
    const row = listed[index];
    if (row && ids[index] === entry.id) problems.push(...checkRow(row, entry));
  });
  return problems;
}

/**
 * @param {string} rootDir
 * @param {string} id
 * @param {string} readme
 * @returns {CatalogEntry}
 */
function catalogEntry(rootDir, id, readme) {
  const pluginDir = join(rootDir, "plugins", id);
  const manifest = readJson(manifestPath(id, join(rootDir, "plugins")));
  const title = headingTitle(readme.split("\n").find((line) => line.startsWith("# ")) ?? id);
  const badges = headerBadges(readme);
  return {
    id,
    displayName: typeof manifest.displayName === "string" ? manifest.displayName : title,
    kind: pluginKind(pluginComponents(pluginDir, manifest)),
    code: surfaceStatus(badges.get("Claude Code") ?? ""),
    cowork: surfaceStatus(badges.get("Claude Cowork") ?? ""),
    minimums: badgeMinimums(badges),
  };
}

/**
 * @param {string} template The Apache-2.0 LICENSE template, whose comment records the canonical SHA-256.
 * @returns {string} The expected SHA-256 of a plugin LICENSE file.
 */
export function licenseSha(template) {
  const sha = /SHA-256 ([0-9a-f]{64})/.exec(template)?.[1];
  if (!sha) throw new Error(`${LICENSE_TEMPLATE} no longer records the license SHA-256`);
  return sha;
}

/**
 * ADR-0005: every plugin ships the verbatim Apache-2.0 text and declares it.
 * @param {string} id
 * @param {Buffer} license The plugin's LICENSE bytes.
 * @param {unknown} declared plugin.json `license`.
 * @param {string} expectedSha
 * @returns {string[]}
 */
export function checkLicense(id, license, declared, expectedSha) {
  /** @type {string[]} */
  const problems = [];
  const sha = createHash("sha256").update(license).digest("hex");
  if (sha !== expectedSha) {
    problems.push(
      `plugins/${id}/LICENSE is not the verbatim Apache-2.0 text (sha256 ${sha.slice(0, 12)}…); copy it from ${LICENSE_TEMPLATE}`,
    );
  }
  if (declared !== "Apache-2.0") {
    problems.push(`plugins/${id}/.claude-plugin/plugin.json license must be "Apache-2.0"`);
  }
  return problems;
}

/**
 * Validates every plugin README and the root catalog.
 * @param {string} rootDir
 * @param {string[]} pluginDirs Sorted plugin ids.
 * @returns {string[]} Problems; empty when everything conforms.
 */
export function validateReadmes(rootDir, pluginDirs) {
  const contract = readContract(readFileSync(join(rootDir, PLUGIN_TEMPLATE), "utf8"));
  const expectedSha = licenseSha(readFileSync(join(rootDir, LICENSE_TEMPLATE), "utf8"));
  /** @type {string[]} */
  const problems = [];
  /** @type {CatalogEntry[]} */
  const entries = [];
  for (const id of pluginDirs) {
    const readme = readFileSync(join(rootDir, "plugins", id, "README.md"), "utf8");
    problems.push(...checkPluginReadme(id, readme, contract));
    const manifest = readJson(manifestPath(id, join(rootDir, "plugins")));
    const license = readFileSync(join(rootDir, "plugins", id, "LICENSE"));
    problems.push(...checkLicense(id, license, manifest.license, expectedSha));
    const pluginDir = join(rootDir, "plugins", id);
    const badges = headerBadges(readme);
    const changelog = readFileSync(join(pluginDir, "CHANGELOG.md"), "utf8");
    problems.push(
      ...checkRequirementMinimums(badgeMinimums(badges), sectionBodies(readme)).map(
        (problem) => `plugins/${id}/README.md: ${problem}`,
      ),
      ...checkNetworkClaim(pluginDir, badges).map((problem) => `plugins/${id}: ${problem}`),
      ...checkChangelogLinks(changelog).map((problem) => `plugins/${id}/${problem}`),
    );
    const entry = catalogEntry(rootDir, id, readme);
    const title = headingTitle(readme.split("\n").find((line) => line.startsWith("# ")) ?? "");
    if (title !== entry.displayName) {
      problems.push(
        `plugins/${id}/README.md: title "${title}" must equal plugin.json displayName "${entry.displayName}"`,
      );
    }
    entries.push(entry);
  }
  problems.push(...checkRootCatalog(readFileSync(join(rootDir, "README.md"), "utf8"), entries));
  return problems;
}
