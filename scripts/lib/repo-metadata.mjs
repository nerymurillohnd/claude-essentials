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
 * Errors for one label's own fields (name length and prefix, color, description).
 * @param {Record<string, unknown>} label A label whose `name` is a non-empty string.
 * @param {string} where
 * @returns {string[]}
 */
function labelFieldErrors(label, where) {
  const name = /** @type {string} */ (label["name"]);
  /** @type {string[]} */
  const errors = [];
  if (name.length > MAX_LABEL_NAME) errors.push(`${where}: name longer than ${MAX_LABEL_NAME}`);
  if (name.startsWith(PLUGIN_LABEL_PREFIX)) {
    errors.push(
      `${where}: "${PLUGIN_LABEL_PREFIX}*" labels are derived from plugins/; don't list them`,
    );
  }
  const color = label["color"];
  if (typeof color !== "string" || !COLOR.test(color)) {
    errors.push(`${where}: color must be 6 lowercase hex digits`);
  }
  const description = label["description"];
  if (
    typeof description !== "string" ||
    description.length < 1 ||
    description.length > MAX_LABEL_DESCRIPTION
  ) {
    errors.push(`${where}: description must be 1–${MAX_LABEL_DESCRIPTION} characters`);
  }
  return errors;
}

/**
 * Errors for one label's `aliases`: must be an array of strings that collide with no
 * label name and with no other label's alias (aliases are case-insensitive).
 * @param {unknown} aliases
 * @param {string} where
 * @param {ReadonlySet<string>} allNames Lower-cased names of every label.
 * @param {Set<string>} seenAliases Lower-cased aliases seen so far; updated in place.
 * @returns {string[]}
 */
function aliasErrors(aliases, where, allNames, seenAliases) {
  if (aliases === undefined) return [];
  if (!Array.isArray(aliases) || !aliases.every((alias) => typeof alias === "string")) {
    return [`${where}: aliases must be an array of strings`];
  }
  /** @type {string[]} */
  const errors = [];
  for (const alias of aliases) {
    const aliasKey = alias.toLowerCase();
    if (allNames.has(aliasKey)) errors.push(`${where}: alias "${alias}" is also a label name`);
    if (seenAliases.has(aliasKey)) {
      errors.push(`${where}: alias "${alias}" is already an alias of another label`);
    }
    seenAliases.add(aliasKey);
  }
  return errors;
}

/**
 * @param {unknown} label
 * @returns {label is Record<string, unknown> & { name: string }}
 */
const hasName = (label) =>
  typeof label === "object" &&
  label !== null &&
  typeof (/** @type {Record<string, unknown>} */ (label)["name"]) === "string" &&
  /** @type {Record<string, unknown>} */ (label)["name"] !== "";

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
  const allNames = new Set(labels.filter(hasName).map((label) => label.name.toLowerCase()));
  /** @type {Set<string>} */
  const seenAliases = new Set();
  for (const label of labels) {
    if (!hasName(label)) {
      errors.push('.github/labels.json: every label needs a non-empty "name"');
      continue;
    }
    const where = `.github/labels.json "${label.name}"`;
    const key = label.name.toLowerCase();
    if (seen.has(key)) errors.push(`${where}: duplicate (label names are case-insensitive)`);
    seen.add(key);
    errors.push(...labelFieldErrors(label, where));
    errors.push(...aliasErrors(label["aliases"], where, allNames, seenAliases));
  }
  for (const name of required) {
    if (!seen.has(name.toLowerCase()))
      errors.push(`.github/labels.json: "${name}" is required by automation`);
  }
  return errors;
}

/**
 * A form's `labels` as a list: GitHub accepts a comma-separated string or an array.
 * @param {unknown} rawLabels
 * @returns {unknown[]}
 */
function formLabels(rawLabels) {
  if (typeof rawLabels === "string") return rawLabels.split(",").map((l) => l.trim());
  return Array.isArray(rawLabels) ? rawLabels : [];
}

/**
 * Errors for the generated plugin dropdown (the triage bot parses its rendering).
 * @param {unknown} body The form's `body`.
 * @param {string} where
 * @param {readonly string[]} pluginNames
 * @returns {string[]}
 */
function pluginDropdownErrors(body, where, pluginNames) {
  /** @type {any[]} */
  const items = Array.isArray(body) ? body : [];
  const expected = JSON.stringify(pluginDropdownOptions(pluginNames));
  return items
    .filter((item) => item?.id === PLUGIN_FIELD_ID)
    .flatMap((item) => [
      ...(item.attributes?.label === PLUGIN_FIELD_LABEL
        ? []
        : [`${where}: the "${PLUGIN_FIELD_ID}" dropdown label must be "${PLUGIN_FIELD_LABEL}"`]),
      ...(JSON.stringify(item.attributes?.options) === expected
        ? []
        : [`${where}: "${PLUGIN_FIELD_ID}" dropdown is stale — run npm run generate`]),
    ]);
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
  const missing = ["name", "description", "body"]
    .filter((key) => !form?.[key])
    .map((key) => `${where}: missing "${key}"`);
  const unknownLabels = formLabels(form?.labels)
    .filter((label) => typeof label !== "string" || !labelNames.has(label))
    .map((label) => `${where}: label "${label}" is not in .github/labels.json`);
  return [...missing, ...unknownLabels, ...pluginDropdownErrors(form?.body, where, pluginNames)];
}

const CANONICAL_SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

/**
 * @typedef {{ uses?: unknown, with?: Record<string, unknown> }} WorkflowStep
 */

/**
 * Every `actions/setup-node` step of a parsed workflow, with its job name.
 * @param {unknown} parsed
 * @returns {{ job: string, step: WorkflowStep }[]}
 */
function setupNodeSteps(parsed) {
  const jobs = /** @type {{ jobs?: Record<string, { steps?: WorkflowStep[] }> } | null} */ (parsed)
    ?.jobs;
  return Object.entries(jobs ?? {}).flatMap(([job, definition]) =>
    (definition.steps ?? [])
      .filter((step) => String(step.uses ?? "").startsWith("actions/setup-node@"))
      .map((step) => ({ job, step })),
  );
}

/**
 * Every `actions/setup-node` step must read the Node version from `.nvmrc`, so CI
 * runs exactly the version contributors use locally (no floating `node-version`).
 * @param {readonly { file: string, parsed: unknown }[]} workflows
 * @returns {string[]}
 */
export function checkNodeVersionSource(workflows) {
  return workflows.flatMap(({ file, parsed }) =>
    setupNodeSteps(parsed)
      .filter(
        ({ step }) =>
          step.with?.["node-version-file"] !== ".nvmrc" ||
          step.with?.["node-version"] !== undefined,
      )
      .map(
        ({ job }) =>
          `.github/workflows/${file} (${job}): setup-node must use "node-version-file: .nvmrc" and no "node-version"`,
      ),
  );
}

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
      const parsed = parse(source);
      return { file, source, parsed, version: parsed?.env?.CLAUDE_CODE_VERSION };
    });
  errors.push(...checkClaudeCodeVersions(workflows));
  errors.push(...checkNodeVersionSource(workflows));
  return errors;
}
