// @ts-check
// Detects Keep a Changelog version sections ("## [X.Y.Z] - YYYY-MM-DD") in a
// plugin's CHANGELOG.md. See docs/contributing/versioning.md.
/** @param {string} value */
const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** @param {string} version */
function headingPattern(version) {
  return new RegExp(`^## \\[${escapeRegExp(version)}\\] - \\d{4}-\\d{2}-\\d{2}[ \\t]*$`, "m");
}

/**
 * @param {unknown} text CHANGELOG.md contents; anything but a string is "no entry".
 * @param {string} version
 * @returns {boolean}
 */
export function hasChangelogEntry(text, version) {
  return typeof text === "string" && headingPattern(version).test(text);
}
