# LSP recipes for this repository

Each recipe was run against this repository on 2026-09-22 (basedpyright 1.40.1).
Positions are 1-based; see [Pointing at a symbol](../SKILL.md#pointing-at-a-symbol).

## Contents

- [Understand a file](#understand-a-file)
- [Impact analysis](#impact-analysis)
- [Dead-code audit](#dead-code-audit)
- [Safe rename](#safe-rename)
- [Change a signature](#change-a-signature)

## Understand a file

1. `documentSymbol` on the file: the full outline with lines, locals included.
2. `hover` on the functions you care about: signature, types, docstring.
3. `outgoingCalls` on the entry point (`main`) to see what it depends on.
4. Read with `offset`/`limit` only the bodies you still need.

## Impact analysis

Before changing what a symbol does:

1. `findReferences` on the definition: every Python use, across files.
2. `incomingCalls` on the function: each caller with its call sites (for
   example `floor_problem` → `smoke_run` at 216:15 and one test at 106:12,
   108:19).
3. The blind-spot search: `git grep -n -w <name>`, then read the hits the LSP
   did not list (fixtures, module paths, strings, docs).
4. List what breaks, what must change with it, and which tests cover each
   caller, before editing.

## Dead-code audit

1. `documentSymbol` on the file; take every top-level function, class and
   constant (and dataclass fields, whose readers are easy to lose).
2. `findReferences` on each. A symbol whose only reference is its own
   definition is a **candidate**, not a verdict.
3. For each candidate: `git grep -n -w <name>` across the whole repository, and
   check the blind spots (a fixture used by parameter name returns one
   reference; so does a function called only from `python -m`).
4. Only a candidate with no text use either is dead. Delete it with the Edit
   tool, confirm no new diagnostics arrive, and run the module's tests.
5. After removing or renaming, `workspaceSymbol` on the old name must return
   nothing, with a control query that does return something.

## Safe rename

There is no rename operation. This procedure finds every site, applies the
change through the tool the server hears, and proves nothing was missed.

1. **Collect Python sites:** `findReferences` on the definition. Note the count.
2. **Collect text sites:** `git grep -n -w <old>`; keep the hits outside the
   LSP list (module paths, strings, docs, fixtures). Leave dated history
   (`docs/superpowers/specs/*migration-log*`, released CHANGELOG entries) as it is.
3. **Check the new name is free:** `workspaceSymbol` on `<new>` returns nothing
   that would collide.
4. **Edit every site with the Edit tool**, never `sed`: the server only hears
   Edit and Write. Diagnostics after the first edit will say `"<new>" is not
   defined` and `"<old>" is not accessed`; that is expected until the last site.
5. **Prove completeness:**
   - after the last edit, no new diagnostics arrive;
   - `findReferences` on the new definition returns the same count as step 1;
   - `workspaceSymbol` on `<old>` returns nothing, and a control query returns
     something (so the empty result is real);
   - `git grep -n -w <old>` returns only the history you chose to keep;
   - `mcp__ide__getDiagnostics` on each touched file is empty.
6. **Run the gates:** the tests of every touched module, then `make lint-staged`.
7. A public name in a plugin's shipped Python is runtime: bump the plugin's
   version and add a CHANGELOG entry.

Measured run: renaming `_smoke` to `_smoke_one` in
`scripts/plugin_validation/run_plugin_suites.py` with Edit produced the two
expected mid-rename diagnostics after the first edit, none after the second,
two references for the new name and none for the old. The same rename done
with `sed` left the server reporting `_smoke`.

## Change a signature

1. `hover` on the definition for the current signature.
2. `incomingCalls` for every caller; `git grep -n -w` for callers the LSP
   cannot see.
3. Change the definition with Edit. The diagnostics that arrive list the call
   sites that no longer type-check (`reportCallIssue`,
   `reportArgumentType`); fix each with Edit until none arrive.
4. `mcp__ide__getDiagnostics` with no argument: the whole workspace clean.
5. Run the callers' tests.
