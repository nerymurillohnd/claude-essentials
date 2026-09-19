// @ts-check
// Finds the repository's shell scripts (DEBT-0003) with the same rule the
// PostToolUse hook uses: a .sh file, or a file whose shebang runs sh or bash.
import { execFileSync } from "node:child_process";
import { closeSync, openSync, readSync } from "node:fs";
import { join } from "node:path";
import { rootDir } from "./plugins.mjs";

const SHELL_SHEBANG = /^#!.*[/\s](ba)?sh(\s|$)/;

/**
 * @param {string} path
 * @param {string} firstLine
 * @returns {boolean}
 */
export function isShellScript(path, firstLine) {
  return path.endsWith(".sh") || SHELL_SHEBANG.test(firstLine);
}

/**
 * @param {string} path
 * @returns {string}
 */
function firstLine(path) {
  const buffer = Buffer.alloc(128);
  const fd = openSync(path, "r");
  try {
    const bytes = readSync(fd, buffer, 0, buffer.length, 0);
    return buffer.subarray(0, bytes).toString("utf8").split("\n")[0] ?? "";
  } finally {
    closeSync(fd);
  }
}

// Tracked files only, so ignored paths (node_modules, caches) never count.
/**
 * @param {string} [root]
 * @returns {string[]}
 */
export function listShellFiles(root = rootDir) {
  const tracked = execFileSync("git", ["ls-files", "-z"], { cwd: root, encoding: "utf8" })
    .split("\0")
    .filter(Boolean);
  return tracked.filter((file) => {
    if (file.endsWith(".sh")) return true;
    try {
      return isShellScript(file, firstLine(join(root, file)));
    } catch {
      return false;
    }
  });
}
