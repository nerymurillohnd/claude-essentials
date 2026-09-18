// Detects Keep a Changelog version sections ("## [X.Y.Z] - YYYY-MM-DD") in a
// plugin's CHANGELOG.md. See docs/contributing/versioning.md.
const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function headingPattern(version) {
  return new RegExp(`^## \\[${escapeRegExp(version)}\\] - \\d{4}-\\d{2}-\\d{2}[ \\t]*$`, "m");
}

export function hasChangelogEntry(text, version) {
  return typeof text === "string" && headingPattern(version).test(text);
}
