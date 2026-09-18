#!/usr/bin/env node
// GitHub Actions entrypoint for .github/workflows/triage.yml (ADR-0004).
// SECURITY: runs from a BASE-branch checkout. Pull request content is fetched
// through the API and treated as data only; nothing from the PR is executed.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createClient, RAW, resolveRepo, resolveToken } from "./lib/github.mjs";
import { pluginLabel } from "./lib/labels.mjs";
import { listPluginDirs, readJson, rootDir } from "./lib/plugins.mjs";
import {
  areaLabels,
  authorReplyChanges,
  issueLabels,
  pluginLabels,
  reconcile,
} from "./lib/triage.mjs";
import { planVersions, pluginsTouched } from "./lib/version-plan.mjs";

const event = JSON.parse(readFileSync(process.env.GITHUB_EVENT_PATH, "utf8"));
const client = createClient({ token: resolveToken(), repo: resolveRepo() });
const repoPath = `/repos/${client.repo}`;
const enc = encodeURIComponent;
const staticLabels = readJson(join(rootDir, ".github", "labels.json"));
const names = (labels) => labels.map((label) => label.name);

async function ensureLabels(labelNames, extraDefs) {
  const defs = new Map([...staticLabels, ...extraDefs].map((label) => [label.name, label]));
  for (const name of labelNames) {
    if (await client.request("GET", `${repoPath}/labels/${enc(name)}`)) continue;
    const def = defs.get(name);
    if (!def) throw new Error(`Label "${name}" is not in the taxonomy`);
    await client.request("POST", `${repoPath}/labels`, {
      name: def.name,
      color: def.color,
      description: def.description,
    });
  }
}

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

async function rawAt(path, ref) {
  const encoded = path.split("/").map(enc).join("/");
  return client.request("GET", `${repoPath}/contents/${encoded}?ref=${enc(ref)}`, undefined, {
    accept: RAW,
  });
}

async function jsonAt(path, ref) {
  const text = await rawAt(path, ref);
  return text === null ? null : JSON.parse(text);
}

async function onIssue() {
  const { issue } = event;
  const current = names(issue.labels);
  const add = issueLabels(issue.body, listPluginDirs()).filter((label) => !current.includes(label));
  if (add.length > 0) await apply(issue.number, { add, remove: [] });
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

async function bumpLabelForPr(pr, changedFiles) {
  const base = new Map();
  const head = new Map();
  const changelogs = new Map();
  try {
    for (const name of pluginsTouched(changedFiles)) {
      const manifest = `plugins/${name}/.claude-plugin/plugin.json`;
      base.set(name, await jsonAt(manifest, pr.base.sha));
      head.set(name, await jsonAt(manifest, pr.head.sha));
      changelogs.set(name, await rawAt(`plugins/${name}/CHANGELOG.md`, pr.head.sha));
    }
    const marketplace = (await jsonAt(".claude-plugin/marketplace.json", pr.head.sha)) ?? {};
    const tags = (await client.paginate(`${repoPath}/tags`)).map((tag) => tag.name);
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
    console.log(`Release label skipped: ${error.message}`);
    return null;
  }
}

async function onPullRequest() {
  const pr = event.pull_request;
  const files = await client.paginate(`${repoPath}/pulls/${pr.number}/files`);
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
  const extraDefs = pluginsTouched(changedFiles).map((name) =>
    pluginLabel({ name, description: `Plugin ${name}` }),
  );
  await apply(pr.number, reconcile(names(pr.labels), desired), extraDefs);
}

const handlers = {
  issues: onIssue,
  issue_comment: onIssueComment,
  pull_request_target: onPullRequest,
};
const handler = handlers[process.env.GITHUB_EVENT_NAME];
if (handler) await handler();
else console.log(`Ignoring event ${process.env.GITHUB_EVENT_NAME}`);
