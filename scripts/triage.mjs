// @ts-check
// GitHub Actions entrypoint for .github/workflows/triage.yml (ADR-0004).
// SECURITY: runs from a BASE-branch checkout. Pull request content is fetched
// through the API and treated as data only; nothing from the PR is executed.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { errorMessage } from "./lib/errors.mjs";
import { createClient, RAW, resolveRepo, resolveToken } from "./lib/github.mjs";
import { pluginLabel } from "./lib/labels.mjs";
import { listPluginDirs, manifestPath, readJson, rootDir } from "./lib/plugins.mjs";
import {
  areaLabels,
  authorReplyChanges,
  issueLabels,
  isValidPluginName,
  pluginLabels,
  reconcile,
} from "./lib/triage.mjs";
import { planVersions, pluginsTouched } from "./lib/version-plan.mjs";

/**
 * Only the payload fields this script reads.
 * @typedef {{ name: string }} GitHubLabel
 * @typedef {{ login: string }} GitHubUser
 * @typedef {{ number: number, body?: string | null, labels: GitHubLabel[], user: GitHubUser, pull_request?: unknown }} GitHubIssue
 * @typedef {{ number: number, labels: GitHubLabel[], base: { sha: string }, head: { sha: string } }} GitHubPullRequest
 * @typedef {{ filename: string, previous_filename?: string }} GitHubPrFile
 * @typedef {{ issue: GitHubIssue, comment: { user: GitHubUser }, pull_request: GitHubPullRequest }} GitHubEvent
 * @typedef {import("./lib/labels.mjs").Label} Label
 * @typedef {import("./lib/triage.mjs").LabelChanges} LabelChanges
 */

const eventPath = process.env["GITHUB_EVENT_PATH"];
if (!eventPath) throw new Error("GITHUB_EVENT_PATH is not set: run this from the triage workflow");
/** @type {GitHubEvent} */
const event = JSON.parse(readFileSync(eventPath, "utf8"));
const client = createClient({ token: resolveToken(), repo: resolveRepo() });
const repoPath = `/repos/${client.repo}`;
const enc = encodeURIComponent;
/** @type {Label[]} */
const staticLabels = readJson(join(rootDir, ".github", "labels.json"));
/** @param {readonly GitHubLabel[]} labels */
const names = (labels) => labels.map((label) => label.name);

/**
 * @param {readonly string[]} labelNames
 * @param {readonly Label[]} extraDefs
 */
async function ensureLabels(labelNames, extraDefs) {
  const defs = new Map([...staticLabels, ...extraDefs].map((label) => [label.name, label]));
  for (const name of labelNames) {
    if (await client.request("GET", `${repoPath}/labels/${enc(name)}`)) continue;
    const def = defs.get(name);
    if (!def) throw new Error(`Label "${name}" is not in the taxonomy`);
    try {
      await client.request("POST", `${repoPath}/labels`, {
        name: def.name,
        color: def.color,
        description: def.description,
      });
    } catch (error) {
      // 422: a concurrent run created it first. Anything else, or still missing, is real.
      const created = await client.request("GET", `${repoPath}/labels/${enc(name)}`);
      if (!errorMessage(error).includes("→ 422") || !created) throw error;
    }
  }
}

/**
 * @param {number} number Issue or PR number.
 * @param {LabelChanges} changes
 * @param {readonly Label[]} [extraDefs]
 */
async function apply(number, { add, remove }, extraDefs = []) {
  if (add.length > 0) {
    await ensureLabels(add, extraDefs);
    await client.request("POST", `${repoPath}/issues/${number}/labels`, { labels: add });
  }
  for (const name of remove) {
    await client.request("DELETE", `${repoPath}/issues/${number}/labels/${enc(name)}`);
  }
  console.log(`#${number}: +[${add.join(", ")}] -[${remove.join(", ")}]`);
}

/**
 * @param {string} path Repo-relative path.
 * @param {string} ref
 * @returns {Promise<string | null>} File contents, or null when absent at `ref`.
 */
async function rawAt(path, ref) {
  const encoded = path.split("/").map(enc).join("/");
  const text = await client.request(
    "GET",
    `${repoPath}/contents/${encoded}?ref=${enc(ref)}`,
    undefined,
    {
      accept: RAW,
    },
  );
  if (text !== null && typeof text !== "string")
    throw new Error(`${path}@${ref}: expected raw text`);
  return text;
}

/**
 * @param {string} path
 * @param {string} ref
 * @returns {Promise<any>} Parsed JSON, or null when absent; validated by the caller.
 */
async function jsonAt(path, ref) {
  const text = await rawAt(path, ref);
  return text === null ? null : JSON.parse(text);
}

async function onIssue() {
  const { issue } = event;
  const current = names(issue.labels);
  const pluginNames = listPluginDirs();
  const add = issueLabels(issue.body, pluginNames).filter((label) => !current.includes(label));
  // Base-checkout manifests are trusted, so a plugin label labels.yml hasn't
  // synced yet can be created with its real description.
  const defs = pluginNames.map((name) => pluginLabel(readJson(manifestPath(name))));
  if (add.length > 0) await apply(issue.number, { add, remove: [] }, defs);
}

async function onIssueComment() {
  if (event.issue.pull_request) return;
  const changes = authorReplyChanges({
    labels: names(event.issue.labels),
    author: event.issue.user.login,
    commenter: event.comment.user.login,
  });
  if (changes.add.length > 0 || changes.remove.length > 0) await apply(event.issue.number, changes);
}

/**
 * @param {GitHubPullRequest} pr
 * @param {readonly string[]} changedFiles
 * @returns {Promise<string | null>}
 */
async function bumpLabelForPr(pr, changedFiles) {
  /** @type {Map<string, import("./lib/version-plan.mjs").Manifest | null>} */
  const base = new Map();
  /** @type {Map<string, import("./lib/version-plan.mjs").Manifest | null>} */
  const head = new Map();
  /** @type {Map<string, string | undefined>} */
  const changelogs = new Map();
  try {
    for (const name of pluginsTouched(changedFiles)) {
      const manifest = `plugins/${name}/.claude-plugin/plugin.json`;
      base.set(name, await jsonAt(manifest, pr.base.sha));
      head.set(name, await jsonAt(manifest, pr.head.sha));
      changelogs.set(name, (await rawAt(`plugins/${name}/CHANGELOG.md`, pr.head.sha)) ?? undefined);
    }
    const marketplace = (await jsonAt(".claude-plugin/marketplace.json", pr.head.sha)) ?? {};
    const tags = /** @type {GitHubLabel[]} */ (await client.paginate(`${repoPath}/tags`)).map(
      (tag) => tag.name,
    );
    return planVersions({
      changedFiles,
      base,
      head,
      changelogs,
      renames: marketplace.renames ?? {},
      existingTags: new Set(tags),
      deferred: names(pr.labels).includes("bump: deferred"),
    }).bumpLabel;
  } catch (error) {
    console.log(`Release label skipped: ${errorMessage(error)}`);
    return null;
  }
}

async function onPullRequest() {
  const pr = event.pull_request;
  const files = /** @type {GitHubPrFile[]} */ (
    await client.paginate(`${repoPath}/pulls/${pr.number}/files`)
  );
  const changedFiles = files.flatMap((file) =>
    file.previous_filename ? [file.filename, file.previous_filename] : [file.filename],
  );
  const bumpLabel = await bumpLabelForPr(pr, changedFiles);
  const desired = [
    ...areaLabels(changedFiles),
    ...pluginLabels(changedFiles),
    ...(bumpLabel ? [bumpLabel] : []),
  ];
  // Descriptions for plugin labels created here are placeholders: PR content
  // is untrusted, and labels.yml rewrites them from plugin.json after merge.
  // Names are validated first: an invalid name would make ensureLabels() throw
  // before applying any label, and pluginLabelName() could exceed GitHub's
  // 50-char label-name limit and be rejected with a 422 (ADR-0004).
  const extraDefs = pluginsTouched(changedFiles)
    .filter(isValidPluginName)
    .map((name) => pluginLabel({ name, description: `Plugin ${name}` }));
  await apply(pr.number, reconcile(names(pr.labels), desired), extraDefs);
}

/** @type {Record<string, () => Promise<void>>} */
const handlers = {
  issues: onIssue,
  issue_comment: onIssueComment,
  pull_request_target: onPullRequest,
};
const eventName = process.env["GITHUB_EVENT_NAME"] ?? "";
// Own keys only: an inherited name such as "toString" must not resolve to a handler.
const handler = Object.hasOwn(handlers, eventName) ? handlers[eventName] : undefined;
if (handler) await handler();
else console.log(`Ignoring event ${eventName || "(none)"}`);
