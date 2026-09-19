// @ts-check
// Minimal GitHub REST client over fetch, shared by sync-labels.mjs and triage.mjs.
// No retries: every caller is idempotent and safe to re-run.
import { execFileSync } from "node:child_process";

export const RAW = "application/vnd.github.raw+json";

/**
 * @typedef {(method: string, path: string, body?: unknown, options?: { accept?: string }) => Promise<unknown>} Request
 *   Resolves to the parsed JSON body (or raw text for RAW), or null for 204 and
 *   for 404 on GET/DELETE. Responses are external data: callers narrow them.
 * @typedef {{ repo: string, request: Request, paginate: (path: string) => Promise<unknown[]> }} GitHubClient
 */

/**
 * @param {{ token: string | undefined, repo: string, fetchImpl?: typeof fetch, baseUrl?: string }} options
 * @returns {GitHubClient}
 */
export function createClient({
  token,
  repo,
  fetchImpl = globalThis.fetch,
  baseUrl = "https://api.github.com",
}) {
  if (!token) {
    throw new Error(
      "GitHub token missing: set GITHUB_TOKEN (locally: GITHUB_TOKEN=$(gh auth token))",
    );
  }

  /** @type {Request} */
  async function request(method, path, body, { accept = "application/vnd.github+json" } = {}) {
    /** @type {Record<string, string>} */
    const headers = { Accept: accept, Authorization: `Bearer ${token}` };
    /** @type {RequestInit} */
    const init = { method, headers };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await fetchImpl(`${baseUrl}${path}`, init);
    if (response.status === 204) return null;
    // GET of a missing resource and DELETE of an already-gone one are not errors.
    if (response.status === 404 && (method === "GET" || method === "DELETE")) return null;
    if (!response.ok)
      throw new Error(`${method} ${path} → ${response.status} ${await response.text()}`);
    return accept.includes("raw") ? response.text() : response.json();
  }

  /**
   * @param {string} path A list endpoint.
   * @returns {Promise<unknown[]>}
   */
  async function paginate(path) {
    /** @type {unknown[]} */
    const items = [];
    for (let page = 1; ; page += 1) {
      const separator = path.includes("?") ? "&" : "?";
      const batch = (await request("GET", `${path}${separator}per_page=100&page=${page}`)) ?? [];
      // A non-list response would otherwise throw an opaque "not iterable", or be
      // spread character by character if it were a string.
      if (!Array.isArray(batch)) throw new Error(`GET ${path} did not return a list`);
      items.push(...batch);
      if (batch.length < 100) return items;
    }
  }

  return { repo, request, paginate };
}

/**
 * @param {string} url A git remote URL.
 * @returns {string} "owner/repo".
 */
export function parseRepoFromRemote(url) {
  const match = /github\.com[:/]([^/]+\/[^/]+?)(?:\.git)?\/?$/.exec(url.trim());
  if (!match?.[1]) throw new Error(`Cannot derive owner/repo from remote ${url}`);
  return match[1];
}

/**
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string | undefined}
 */
export function resolveToken(env = process.env) {
  const fromEnv = env["GITHUB_TOKEN"] || env["GH_TOKEN"];
  if (fromEnv) return fromEnv;
  try {
    return execFileSync("gh", ["auth", "token"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return undefined;
  }
}

/**
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string} "owner/repo".
 */
export function resolveRepo(env = process.env) {
  const fromEnv = env["GITHUB_REPOSITORY"];
  if (fromEnv) return fromEnv;
  return parseRepoFromRemote(
    execFileSync("git", ["remote", "get-url", "origin"], { encoding: "utf8" }),
  );
}
