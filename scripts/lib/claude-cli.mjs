// @ts-check
// Runs the Claude Code CLI found on PATH: the maintainer's own install locally,
// and the version CI installs on the runner (CLAUDE_CODE_VERSION in the
// workflows). It is never a repo dependency (ADR-0003).
import { spawnSync } from "node:child_process";
import { rootDir } from "./plugins.mjs";

export const EMPTY_MARKETPLACE_WARNING = "Marketplace has no plugins defined";

/**
 * @param {string[]} args
 * @param {{ cwd?: string }} [options]
 * @returns {{ status: number | null, stdout: string, stderr: string }}
 */
export function runClaude(args, { cwd = rootDir } = {}) {
  const result = spawnSync("claude", args, { cwd, encoding: "utf8" });
  if (result.error) throw result.error;
  return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

/**
 * @typedef {{ path?: string, message?: string }} RawFinding
 * @typedef {{ file?: string, errors?: RawFinding[], warnings?: RawFinding[] }} ReportSection
 * @typedef {{ severity: "error" | "warning", file: string | undefined, path: string | undefined, message: string | undefined }} Finding
 */

/**
 * Flattens a `claude plugin validate --json` report into a list of findings.
 * @param {{ manifest?: ReportSection, contents?: ReportSection[] } | null | undefined} report
 * @returns {Finding[]}
 */
export function collectFindings(report) {
  /** @type {ReportSection[]} */
  const sections = [report?.manifest, ...(report?.contents ?? [])].filter(
    /** @returns {section is ReportSection} */ (section) => Boolean(section),
  );
  /**
   * @param {ReportSection} section
   * @param {"errors" | "warnings"} key
   * @param {Finding["severity"]} severity
   * @returns {Finding[]}
   */
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
