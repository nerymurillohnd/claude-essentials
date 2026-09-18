// Runs the Claude Code CLI found on PATH: the maintainer's own install locally,
// and the version CI installs on the runner (CLAUDE_CODE_VERSION in the
// workflows). It is never a repo dependency (ADR-0003).
import { spawnSync } from "node:child_process";
import { rootDir } from "./plugins.mjs";

export const EMPTY_MARKETPLACE_WARNING = "Marketplace has no plugins defined";

export function runClaude(args, { cwd = rootDir } = {}) {
  const result = spawnSync("claude", args, { cwd, encoding: "utf8" });
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
