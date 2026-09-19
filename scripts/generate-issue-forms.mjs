// @ts-check
// Regenerates the "Affected plugin" dropdown in every issue form from plugins/
// on disk (ADR-0004), so the forms never offer a plugin that doesn't exist.
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { withPluginOptions } from "./lib/issue-forms.mjs";
import { listPluginDirs, rootDir } from "./lib/plugins.mjs";

const formsDir = join(rootDir, ".github", "ISSUE_TEMPLATE");
const pluginNames = listPluginDirs();
let updated = 0;
for (const file of readdirSync(formsDir)
  .filter((f) => f.endsWith(".yml") && f !== "config.yml")
  .sort()) {
  const path = join(formsDir, file);
  const before = readFileSync(path, "utf8");
  const after = withPluginOptions(before, pluginNames);
  if (after !== before) {
    writeFileSync(path, after);
    updated += 1;
  }
}
console.log(`Issue forms: ${updated} file(s) updated for ${pluginNames.length} plugin(s)`);
