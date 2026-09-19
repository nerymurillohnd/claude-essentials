// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";
import { createClient, parseRepoFromRemote, RAW } from "./github.mjs";

/**
 * @param {{ status?: number, body?: unknown }[]} responses Returned in order, one per call.
 */
function fakeFetch(responses) {
  /** @type {{ url: string, init: RequestInit | undefined }[]} */
  const calls = [];
  /**
   * @param {string | URL | Request} url
   * @param {RequestInit} [init]
   */
  const fn = (url, init) => {
    calls.push({ url: String(url), init });
    const next = responses.shift();
    if (!next) return Promise.reject(new Error("fakeFetch: more requests than scripted responses"));
    const { status = 200, body } = next;
    const payload =
      body === undefined ? null : typeof body === "string" ? body : JSON.stringify(body);
    return Promise.resolve(new Response(payload, { status }));
  };
  fn.calls = calls;
  return fn;
}

test("createClient requires a token", () => {
  assert.throws(() => createClient({ token: undefined, repo: "o/r" }), /token missing/);
});

test("paginate follows pages until a short page", async () => {
  const fetchImpl = fakeFetch([
    { body: Array.from({ length: 100 }, (_, i) => ({ i })) },
    { body: [{ i: 100 }] },
  ]);
  const client = createClient({ token: "t", repo: "o/r", fetchImpl });
  const items = await client.paginate("/repos/o/r/labels");
  assert.equal(items.length, 101);
  assert.equal(fetchImpl.calls.length, 2);
  const [first, second] = fetchImpl.calls;
  assert.match(first?.url ?? "", /\/repos\/o\/r\/labels\?per_page=100&page=1$/);
  assert.match(second?.url ?? "", /page=2$/);
  assert.equal(new Headers(first?.init?.headers).get("authorization"), "Bearer t");
});

test("paginate rejects a non-list response instead of spreading it", async () => {
  const fetchImpl = fakeFetch([{ body: { message: "not a list" } }]);
  const client = createClient({ token: "t", repo: "o/r", fetchImpl });
  await assert.rejects(client.paginate("/repos/o/r/labels"), /did not return a list/);
});

test("request treats DELETE of an already-removed resource as success", async () => {
  const fetchImpl = fakeFetch([{ status: 404, body: { message: "Label does not exist" } }]);
  const client = createClient({ token: "t", repo: "o/r", fetchImpl });
  assert.equal(await client.request("DELETE", "/repos/o/r/issues/1/labels/x"), null);
});

test("request maps 204 and GET 404 to null, returns raw text, throws otherwise", async () => {
  const fetchImpl = fakeFetch([
    { status: 204 },
    { status: 404, body: { message: "Not Found" } },
    { body: "raw file" },
    { status: 422, body: { message: "Validation Failed" } },
  ]);
  const client = createClient({ token: "t", repo: "o/r", fetchImpl });
  assert.equal(await client.request("DELETE", "/x"), null);
  assert.equal(await client.request("GET", "/missing"), null);
  assert.equal(await client.request("GET", "/raw", undefined, { accept: RAW }), "raw file");
  await assert.rejects(client.request("POST", "/labels", { name: "x" }), /422/);
});

test("parseRepoFromRemote handles https and ssh remotes", () => {
  assert.equal(
    parseRepoFromRemote("https://github.com/nerymurillohnd/claude-essentials.git"),
    "nerymurillohnd/claude-essentials",
  );
  assert.equal(parseRepoFromRemote("git@github.com:o/r.name.git"), "o/r.name");
  assert.throws(() => parseRepoFromRemote("https://gitlab.com/o/r"), /Cannot derive/);
});
