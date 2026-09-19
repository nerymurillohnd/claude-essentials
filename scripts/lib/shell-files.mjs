// @ts-check
// Finds the repository's shell scripts (DEBT-0003) with the same rule the
// PostToolUse hook uses: a .sh file, or a file whose shebang runs sh or bash.
import { execFileSync } from "node:child_process";
import { closeSync, existsSync, openSync, readSync } from "node:fs";
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

// Tracked files plus new files Git doesn't ignore, so a new plugin's scripts and
// test suites are linted and run before their first commit; ignored paths
// (node_modules, caches) and deleted files never count.
/**
 * @param {string} [root]
 * @returns {string[]}
 */
export function listShellFiles(root = rootDir) {
  const files = execFileSync(
    "git",
    ["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--deduplicate"],
    { cwd: root, encoding: "utf8" },
  )
    .split("\0")
    .filter((file) => file !== "" && existsSync(join(root, file)));
  return files.filter((file) => {
    if (file.endsWith(".sh")) return true;
    try {
      return isShellScript(file, firstLine(join(root, file)));
    } catch {
      return false;
    }
  });
}
