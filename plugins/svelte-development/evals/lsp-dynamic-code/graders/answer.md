---
type: llm
weight: 2
---

PASS if the answer reports, in src/lib/components/Dynamic.svelte: the import of CounterButton, the component held in a `$state` variable and rendered as `<Active>`, and the lazy `import()` whose module is rendered as `<mod.default>`; and says that the `import()` path is a string the language server does not track as a reference.
FAIL if it says the language server cannot see dynamic usages, or misses any of the three usages.
