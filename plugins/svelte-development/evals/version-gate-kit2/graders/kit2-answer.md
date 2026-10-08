---
type: llm
---

PASS if the answer says the project is on SvelteKit 2 and proposes migrating it to SvelteKit 3 (for example with `sv migrate sveltekit-3`) before writing any code, and writes no matcher file, because the user neither declined the migration nor asked to proceed without questions. Showing what the matcher would look like in either version is fine.
FAIL if the answer writes a matcher file (SvelteKit 2 under `src/params/` or SvelteKit 3 `src/params.ts`) or does not propose the migration.
