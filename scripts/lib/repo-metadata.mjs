// @ts-check
// Cross-checks repository metadata that automation depends on (ADR-0004).
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { Ajv } from "ajv";
import { parse } from "yaml";
import { PLUGIN_FIELD_ID, PLUGIN_FIELD_LABEL, pluginDropdownOptions } from "./issue-forms.mjs";
import {
  MAX_LABEL_DESCRIPTION,
  MAX_LABEL_NAME,
  PLUGIN_LABEL_PREFIX,
  REQUIRED_LABELS,
} from "./labels.mjs";

const COLOR = /^[0-9a-f]{6}$/;

// GitHub publishes no schema for issue forms; schemas/github/ vendors SchemaStore's
// (see each file's $comment). Structure only — repo rules stay in checkIssueForm.
/**
 * @param {string} rootDir
 * @returns {{ form: import("ajv").ValidateFunction, config: import("ajv").ValidateFunction }}
 */
export function issueFormValidators(rootDir) {
  const ajv = new Ajv({ allErrors: true, strict: false });
  /** @param {string} name */
  const load = (name) =>
    JSON.parse(readFileSync(join(rootDir, "schemas", "github", `${name}.schema.json`), "utf8"));
  return { form: ajv.compile(load("issue-forms")), config: ajv.compile(load("issue-config")) };
}

/**
 * @param {string} file
 * @param {unknown} data
 * @param {import("ajv").ValidateFunction} validate
 * @returns {string[]}
 */
export function checkSchema(file, data, validate) {
  if (validate(data)) return [];
  return (validate.errors ?? []).map(
    (err) => `.github/ISSUE_TEMPLATE/${file}: ${err.instancePath || "/"} ${err.message}`,
  );
}

/**
 * @param {unknown} labels Parsed `.github/labels.json`; its shape is what this checks.
 * @param {readonly string[]} [required]
 * @returns {string[]}
 */
export function checkLabels(labels, required = REQUIRED_LABELS) {
  if (!Array.isArray(labels)) return [".github/labels.json must be a JSON array"];
  /** @type {string[]} */
  const errors = [];
  /** @type {Set<string>} */
  const seen = new Set();
  // First pass: every label name, so an alias can be checked against names that appear
  // later in the array too (diffLabels matches aliases across the whole desired set).
  const allNames = new Set(
    labels
      .filter((label) => typeof label?.name === "string" && label.name !== "")
      .map((label) => label.name.toLowerCase()),
  );
  /** @type {Set<string>} */
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
    /** @type {unknown[]} */
    const aliases = Array.isArray(label.aliases) ? label.aliases : [];
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

/**
 * @param {string} file
 * @param {({ labels?: unknown, body?: unknown } & Record<string, unknown>) | null | undefined} form
 *   Parsed issue-form YAML (structure is checked separately against the GitHub schema).
 * @param {{ labelNames: ReadonlySet<string>, pluginNames: readonly string[] }} context
 * @returns {string[]}
 */
export function checkIssueForm(file, form, { labelNames, pluginNames }) {
  const where = `.github/ISSUE_TEMPLATE/${file}`;
  /** @type {string[]} */
  const errors = [];
  for (const key of ["name", "description", "body"]) {
    if (!form?.[key]) errors.push(`${where}: missing "${key}"`);
  }
  const rawLabels = form?.labels;
  /** @type {unknown[]} */
  const labels =
    typeof rawLabels === "string"
      ? rawLabels.split(",").map((l) => l.trim())
      : Array.isArray(rawLabels)
        ? rawLabels
        : [];
  for (const label of labels) {
    if (typeof label !== "string" || !labelNames.has(label))
      errors.push(`${where}: label "${label}" is not in .github/labels.json`);
  }
  /** @type {any[]} */
  const body = Array.isArray(form?.body) ? form.body : [];
  for (const item of body) {
    if (item?.id !== PLUGIN_FIELD_ID) continue;
    if (item.attributes?.label !== PLUGIN_FIELD_LABEL) {
      errors.push(
        `${where}: the "${PLUGIN_FIELD_ID}" dropdown label must be "${PLUGIN_FIELD_LABEL}"`,
      );
    }
    const expected = JSON.stringify(pluginDropdownOptions(pluginNames));
    if (JSON.stringify(item.attributes?.options) !== expected) {
      errors.push(`${where}: "${PLUGIN_FIELD_ID}" dropdown is stale — run npm run generate`);
    }
  }
  return errors;
}

const CANONICAL_SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

// Every workflow that installs the Claude Code CLI must pin the same canonical
// version in its top-level env (DEBT-0004), so CI jobs can't drift apart.
/**
 * @param {readonly { file: string, source: string, version: unknown }[]} workflows
 * @returns {string[]}
 */
export function checkClaudeCodeVersions(workflows) {
  /** @type {string[]} */
  const errors = [];
  const pinned = workflows.filter((w) => w.source.includes("@anthropic-ai/claude-code@"));
  for (const { file, version } of pinned) {
    const where = `.github/workflows/${file}`;
    if (version === undefined) {
      errors.push(`${where} installs Claude Code but sets no CLAUDE_CODE_VERSION in env`);
    } else if (!CANONICAL_SEMVER.test(String(version))) {
      errors.push(
        `${where}: CLAUDE_CODE_VERSION must be canonical semver, got ${JSON.stringify(version)}`,
      );
    }
  }
  const versions = new Set(pinned.map((w) => w.version).filter((v) => v !== undefined));
  if (versions.size > 1) {
    const list = pinned.map((w) => `${w.file}=${w.version}`).join(", ");
    errors.push(`CLAUDE_CODE_VERSION values must all be equal across workflows (${list})`);
  }
  return errors;
}

/**
 * @param {string} rootDir
 * @param {readonly string[]} pluginNames
 * @returns {string[]}
 */
export function validateRepoMetadata(rootDir, pluginNames) {
  /** @type {unknown} */
  const labels = JSON.parse(readFileSync(join(rootDir, ".github", "labels.json"), "utf8"));
  const errors = checkLabels(labels);
  // checkLabels already reported a non-array; don't crash before that error is shown.
  const labelNames = new Set(
    Array.isArray(labels) ? labels.map((label) => String(label?.name ?? "")) : [],
  );
  const formsDir = join(rootDir, ".github", "ISSUE_TEMPLATE");
  const forms = readdirSync(formsDir)
    .filter((file) => file.endsWith(".yml") && file !== "config.yml")
    .sort();
  const validators = issueFormValidators(rootDir);
  for (const file of forms) {
    const form = parse(readFileSync(join(formsDir, file), "utf8"));
    errors.push(...checkSchema(file, form, validators.form));
    errors.push(...checkIssueForm(file, form, { labelNames, pluginNames }));
  }
  const config = parse(readFileSync(join(formsDir, "config.yml"), "utf8"));
  errors.push(...checkSchema("config.yml", config, validators.config));
  const workflowsDir = join(rootDir, ".github", "workflows");
  const workflows = readdirSync(workflowsDir)
    .filter((file) => file.endsWith(".yml"))
    .sort()
    .map((file) => {
      const source = readFileSync(join(workflowsDir, file), "utf8");
      return { file, source, version: parse(source)?.env?.CLAUDE_CODE_VERSION };
    });
  errors.push(...checkClaudeCodeVersions(workflows));
  return errors;
}
