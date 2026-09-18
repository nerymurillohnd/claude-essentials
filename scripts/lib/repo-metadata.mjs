// Cross-checks repository metadata that automation depends on (ADR-0004).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  MAX_LABEL_DESCRIPTION,
  MAX_LABEL_NAME,
  PLUGIN_LABEL_PREFIX,
  REQUIRED_LABELS,
} from "./labels.mjs";

const COLOR = /^[0-9a-f]{6}$/;

export function checkLabels(labels, required = REQUIRED_LABELS) {
  if (!Array.isArray(labels)) return [".github/labels.json must be a JSON array"];
  const errors = [];
  const seen = new Set();
  // First pass: every label name, so an alias can be checked against names that appear
  // later in the array too (diffLabels matches aliases across the whole desired set).
  const allNames = new Set(
    labels
      .filter((label) => typeof label?.name === "string" && label.name !== "")
      .map((label) => label.name.toLowerCase()),
  );
  const seenAliases = new Set();
  for (const label of labels) {
    if (typeof label?.name !== "string" || label.name === "") {
      errors.push('.github/labels.json: every label needs a non-empty "name"');
      continue;
    }
    const where = `.github/labels.json "${label.name}"`;
    const key = label.name.toLowerCase();
    if (seen.has(key)) errors.push(`${where}: duplicate (label names are case-insensitive)`);
    seen.add(key);
    if (label.name.length > MAX_LABEL_NAME)
      errors.push(`${where}: name longer than ${MAX_LABEL_NAME}`);
    if (label.name.startsWith(PLUGIN_LABEL_PREFIX)) {
      errors.push(
        `${where}: "${PLUGIN_LABEL_PREFIX}*" labels are derived from plugins/; don't list them`,
      );
    }
    if (!COLOR.test(label.color ?? ""))
      errors.push(`${where}: color must be 6 lowercase hex digits`);
    const description = label.description ?? "";
    if (description.length < 1 || description.length > MAX_LABEL_DESCRIPTION) {
      errors.push(`${where}: description must be 1–${MAX_LABEL_DESCRIPTION} characters`);
    }
    const aliases = label.aliases ?? [];
    if (!aliases.every((alias) => typeof alias === "string")) {
      errors.push(`${where}: aliases must be strings`);
    } else {
      for (const alias of aliases) {
        const aliasKey = alias.toLowerCase();
        if (allNames.has(aliasKey)) errors.push(`${where}: alias "${alias}" is also a label name`);
        if (seenAliases.has(aliasKey)) {
          errors.push(`${where}: alias "${alias}" is already an alias of another label`);
        }
        seenAliases.add(aliasKey);
      }
    }
  }
  for (const name of required) {
    if (!seen.has(name.toLowerCase()))
      errors.push(`.github/labels.json: "${name}" is required by automation`);
  }
  return errors;
}

export function validateRepoMetadata(rootDir) {
  const labels = JSON.parse(readFileSync(join(rootDir, ".github", "labels.json"), "utf8"));
  return checkLabels(labels);
}
