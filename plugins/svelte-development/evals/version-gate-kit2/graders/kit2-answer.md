---
type: llm
---

PASS if the answer adds a matcher file under src/params/ that exports a `match` function, renames or tells the user to rename the route folder to `[id=<matcher name>]`, and uses no SvelteKit 3 API such as `defineParams`, `@sveltejs/kit/params` or a single `src/params.ts` file. Mentioning that SvelteKit 3 does this differently is fine.
FAIL if the answer writes a SvelteKit 3 matcher (`src/params.ts` with `defineParams`) in this SvelteKit 2 project.
