---
type: llm
---

PASS if the reply reports, each with its file and line: (1) legacy Svelte 4 syntax in
+page.svelte (`export let data`, `$app/stores`/`$page`) with the Svelte 5 / SvelteKit 3
replacement ($props, $app/state); (2) the private API key used in the universal +page.ts load,
which also runs in the browser, so it must move to +page.server.ts; (3) unsanitised `{@html}`
of user content (XSS).
FAIL if any of the three is missing, or the reply claims it changed files.
