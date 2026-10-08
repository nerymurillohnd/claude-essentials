---
type: llm
---

PASS if the answer says the project is on SvelteKit 2 and proposes migrating it to SvelteKit 3 (for example with `sv migrate sveltekit-3`) before writing the matcher, and writes no SvelteKit 3 API into the project (`defineParams`, `@sveltejs/kit/params`, a single `src/params.ts`). Writing a SvelteKit 2 matcher under `src/params/` is acceptable only if the answer also proposes the migration and says the code is for SvelteKit 2.
FAIL if the answer writes a SvelteKit 3 matcher in this SvelteKit 2 project, or writes code without proposing the migration.
