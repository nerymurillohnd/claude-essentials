// Issue-form contract shared by the generator, the validator, and the triage bot
// (ADR-0004). The triage bot parses the rendered "### Affected plugin" section,
// so PLUGIN_FIELD_LABEL and the option strings must not drift.
import { parseDocument } from "yaml";

export const PLUGIN_FIELD_ID = "plugin";
export const PLUGIN_FIELD_LABEL = "Affected plugin";
export const CATALOG_OPTION = "Marketplace catalog / installation";
export const UNSURE_OPTION = "Not sure";

export function pluginDropdownOptions(pluginNames) {
  return [CATALOG_OPTION, ...pluginNames, UNSURE_OPTION];
}

export function withPluginOptions(source, pluginNames) {
  const doc = parseDocument(source);
  const body = doc.get("body");
  const items = body?.items ?? [];
  const targets = items.filter((item) => item.get?.("id") === PLUGIN_FIELD_ID);
  if (targets.length === 0) return source;
  for (const item of targets) {
    item.setIn(["attributes", "options"], doc.createNode(pluginDropdownOptions(pluginNames)));
  }
  return doc.toString({ lineWidth: 0 });
}
