// @ts-check
// Issue-form contract shared by the generator, the validator, and the triage bot
// (ADR-0004). The triage bot parses the rendered "### Affected plugin" section,
// so PLUGIN_FIELD_LABEL and the option strings must not drift.
import { isMap, isSeq, parseDocument } from "yaml";

export const PLUGIN_FIELD_ID = "plugin";
export const PLUGIN_FIELD_LABEL = "Affected plugin";
export const CATALOG_OPTION = "Marketplace catalog / installation";
export const UNSURE_OPTION = "Not sure";

/**
 * @param {readonly string[]} pluginNames
 * @returns {string[]}
 */
export function pluginDropdownOptions(pluginNames) {
  return [CATALOG_OPTION, ...pluginNames, UNSURE_OPTION];
}

/**
 * @param {string} source Issue-form YAML.
 * @param {readonly string[]} pluginNames
 * @returns {string} The form with a regenerated plugin dropdown, or `source` unchanged.
 */
export function withPluginOptions(source, pluginNames) {
  const doc = parseDocument(source);
  const body = doc.get("body");
  const items = isSeq(body) ? body.items : [];
  const targets = items.filter(isMap).filter((item) => item.get("id") === PLUGIN_FIELD_ID);
  if (targets.length === 0) return source;
  for (const item of targets) {
    item.setIn(["attributes", "options"], doc.createNode(pluginDropdownOptions(pluginNames)));
  }
  return doc.toString({ lineWidth: 0 });
}
