---
type: llm
---

PASS if the reply says the project uses SvelteKit 2 (from package.json), proposes migrating
to SvelteKit 3 before writing the matcher, and asks whether to migrate or to proceed on
SvelteKit 2.
FAIL if it presents a SvelteKit 3 matcher (src/params.ts with defineParams) as ready to use in
this project, mixes SvelteKit 2 and 3 code, or never mentions the version.
