// @ts-check
// Syncs the repository's GitHub labels to the ADR-0004 taxonomy: .github/labels.json
// plus one derived "plugin: <name>" label per plugin. Dry-run by default.
// --apply writes; --prune also deletes labels outside the taxonomy (manual only).
import { join } from "node:path";
import { parseArgs } from "node:util";
import { createClient, resolveRepo, resolveToken } from "./lib/github.mjs";
import { buildTaxonomy, diffLabels } from "./lib/labels.mjs";
import { listPluginDirs, manifestPath, readJson, rootDir } from "./lib/plugins.mjs";

const { values } = parseArgs({
  options: {
    apply: { type: "boolean", default: false },
    prune: { type: "boolean", default: false },
  },
});

const desired = buildTaxonomy(
  readJson(join(rootDir, ".github", "labels.json")),
  listPluginDirs().map((name) => readJson(manifestPath(name))),
);
const client = createClient({ token: resolveToken(), repo: resolveRepo() });
const labelsPath = `/repos/${client.repo}/labels`;
const current = /** @type {import("./lib/labels.mjs").RemoteLabel[]} */ (
  await client.paginate(labelsPath)
);
const ops = diffLabels(current, desired, { prune: values.prune });

for (const op of ops) {
  const target = op.op === "create" ? op.label.name : op.from;
  const rename = op.op === "update" && op.from !== op.label.name ? ` → ${op.label.name}` : "";
  console.log(`${values.apply ? "" : "[dry-run] "}${op.op.padEnd(6)} ${target}${rename}`);
  if (!values.apply) continue;
  if (op.op === "create") {
    const { name, color, description } = op.label;
    await client.request("POST", labelsPath, { name, color, description });
  } else if (op.op === "update") {
    const { name, color, description } = op.label;
    await client.request("PATCH", `${labelsPath}/${encodeURIComponent(op.from)}`, {
      new_name: name,
      color,
      description,
    });
  } else {
    await client.request("DELETE", `${labelsPath}/${encodeURIComponent(op.from)}`);
  }
}

if (ops.length === 0) console.log(`Labels on ${client.repo} already match the taxonomy.`);
else
  console.log(
    `${ops.length} change(s) ${values.apply ? "applied" : "planned — re-run with --apply"}.`,
  );
