---
type: llm
---

PASS if the answer lists the `label` prop's declaration in CounterButton's Props, its destructuring in `$props()` and its use in the markup, the parent in src/routes/+page.svelte that passes `label={42}`, and the two dynamic usages in src/lib/components/Dynamic.svelte (the component held in `Active` and the lazily imported `mod.default`); and says that `reset` is called from src/routes/+page.svelte.
FAIL if any of these locations is missing or an invented location is listed.
