// Minimal GitHub REST client over fetch, shared by sync-labels.mjs and triage.mjs.
// No retries: every caller is idempotent and safe to re-run.
import { execFileSync } from "node:child_process";

export const RAW = "application/vnd.github.raw+json";

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

  async function request(method, path, body, { accept = "application/vnd.github+json" } = {}) {
    const headers = { Accept: accept, Authorization: `Bearer ${token}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetchImpl(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 204) return null;
    if (response.status === 404 && method === "GET") return null;
    if (!response.ok)
      throw new Error(`${method} ${path} → ${response.status} ${await response.text()}`);
    return accept.includes("raw") ? response.text() : response.json();
  }

  async function paginate(path) {
    const items = [];
    for (let page = 1; ; page += 1) {
      const separator = path.includes("?") ? "&" : "?";
      const batch = (await request("GET", `${path}${separator}per_page=100&page=${page}`)) ?? [];
      items.push(...batch);
      if (batch.length < 100) return items;
    }
  }

  return { repo, request, paginate };
}

export function parseRepoFromRemote(url) {
  const match = /github\.com[:/]([^/]+\/[^/]+?)(?:\.git)?\/?$/.exec(url.trim());
  if (!match) throw new Error(`Cannot derive owner/repo from remote ${url}`);
  return match[1];
}

export function resolveToken(env = process.env) {
  if (env.GITHUB_TOKEN || env.GH_TOKEN) return env.GITHUB_TOKEN || env.GH_TOKEN;
  try {
    return execFileSync("gh", ["auth", "token"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return undefined;
  }
}

export function resolveRepo(env = process.env) {
  if (env.GITHUB_REPOSITORY) return env.GITHUB_REPOSITORY;
  return parseRepoFromRemote(
    execFileSync("git", ["remote", "get-url", "origin"], { encoding: "utf8" }),
  );
}
