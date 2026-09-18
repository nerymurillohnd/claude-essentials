// Runs the repo-pinned Claude Code CLI (devDependency @anthropic-ai/claude-code) so
// local checks and CI use the same version; falls back to `claude` on PATH.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { rootDir } from "./plugins.mjs";

export const EMPTY_MARKETPLACE_WARNING = "Marketplace has no plugins defined";

export function claudeBin(root = rootDir) {
  const local = join(root, "node_modules", ".bin", "claude");
  return existsSync(local) ? local : "claude";
}

export function runClaude(args, { cwd = rootDir } = {}) {
  const result = spawnSync(claudeBin(), args, { cwd, encoding: "utf8" });
  if (result.error) throw result.error;
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

// Flattens a `claude plugin validate --json` report into a list of findings.
export function collectFindings(report) {
  const sections = [report?.manifest, ...(report?.contents ?? [])].filter(Boolean);
  const pick = (section, key, severity) =>
    (section[key] ?? []).map((finding) => ({
      severity,
      file: section.file,
      path: finding.path,
      message: finding.message,
    }));
  return sections.flatMap((section) => [
    ...pick(section, "errors", "error"),
    ...pick(section, "warnings", "warning"),
  ]);
}
