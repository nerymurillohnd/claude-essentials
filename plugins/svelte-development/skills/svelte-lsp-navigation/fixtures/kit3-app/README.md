# kit3-app fixture

A minimal SvelteKit 3 project used by the `svelte-lsp-navigation` skill examples and by the plugin evals. It is not installed or built; it exists so the Svelte language server and `sv check` have known symbols to work on.

| Symbol | File | Use it to try |
| --- | --- | --- |
| `Counter` class | `src/lib/counter.svelte.ts` | `goToDefinition`, `findReferences` |
| `Resettable` interface | `src/lib/resettable.ts` | `goToImplementation` (implemented by `Counter`) |
| `formatCount` function | `src/lib/format.ts` | `prepareCallHierarchy`, `incomingCalls` (two callers) |
| `CounterButton` props | `src/lib/components/CounterButton.svelte` | `hover`, `documentSymbol` |
| Dynamic usages | `src/lib/components/Dynamic.svelte` | A component held in `$state`, a lazy `import()`, `import.meta.glob`, `svelte:element` and a function stored in an object: `documentSymbol`, `findReferences` |
| Deliberate error | `src/routes/+page.svelte` | `label={42}` where `label` is a `string`: a diagnostic after edits and in `sv check` |

The project configuration files carry an `.example` suffix (`package.json.example`, `tsconfig.json.example`, `vite.config.ts.example`) so that tools which detect them by name, such as dependency scanners and editors, ignore the fixture inside the plugin. To run it for real, copy the folder somewhere outside the plugin, drop the suffix, install and check:

```sh
for f in package.json tsconfig.json vite.config.ts; do mv "$f.example" "$f"; done
npm install
npm run check
```
