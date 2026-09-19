// @ts-check
// Narrowing helpers for `catch (error)`, where `error` is `unknown`: anything can
// be thrown, not only Error instances. Every script reports errors through these
// instead of assuming `error.code` / `error.message` exist.

/**
 * Whether `error` is a Node.js system error with the given `code` (e.g. "ENOENT").
 * @param {unknown} error
 * @param {string} code
 * @returns {error is NodeJS.ErrnoException}
 */
export function hasErrorCode(error, code) {
  return error instanceof Error && /** @type {NodeJS.ErrnoException} */ (error).code === code;
}

/**
 * A printable message for any thrown value.
 * @param {unknown} error
 * @returns {string}
 */
export function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}
