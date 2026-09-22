---
name: basedpyright-lsp
description: Navigate, analyze and refactor this repository's Python with the basedpyright language server through the LSP tool instead of grep and whole-file reads — definitions, references, call hierarchies, types and docs, file outlines, dead-code checks, safe renames without a rename operation, and type-health validation with diagnostics, including the blind spots where LSP must be paired with a text search and the negative controls that prove an empty result is real. Use it whenever you read, trace, change, rename, delete or review any .py under scripts/ or plugins/ in claude-essentials, before editing unfamiliar code, before renaming or removing a symbol, before claiming a Python change is type-clean, and whenever an LSP call returns nothing and you must decide whether that means "none" or "not ready".
---

# basedpyright LSP in claude-essentials

The LSP tool answers questions about code structure: where a symbol is defined,
who uses it, what calls what, what type something has. It understands Python,
so it tells a function from a variable of the same name and follows imports
across files, which grep cannot. Use it first for Python navigation and
analysis; use grep or Read only for what it cannot see (section
[Blind spots](#blind-spots-pair-lsp-with-a-text-search)).

Measured on 2026-09-22 with basedpyright 1.40.1 and Claude Code 2.1.278.

## What runs, and how to check it

- Claude Code's LSP server comes from the `basedpyright` plugin of the
  `claude-code-lsps` marketplace. Its `.lsp.json` runs `basedpyright-langserver --stdio`
  by name, so `PATH` resolves it to the global
  `~/.local/bin/basedpyright-langserver` (a `uv tool` install). The repository's
  `.venv` has its own copy, which VS Code uses.
- Keep the two at the same version, or the editor, the LSP and `make types`
  disagree: `~/.local/bin/basedpyright --version` and `.venv/bin/basedpyright --version`.
- Confirm which server is live: `ps -axo pid,command | grep basedpyright-langserver`
  (the `--stdio` process is Claude Code's). `outgoingCalls` results that point
  into `~/.local/share/uv/tools/basedpyright/…/typeshed-fallback` also show the
  global server is answering.
- Configuration is `[tool.basedpyright]` in `pyproject.toml`: `include = ["scripts", "plugins"]`,
  `typeCheckingMode = "all"`. A file outside `include` is analyzed with less
  context; do not trust its diagnostics as the gate's.

## Operations

All operations take `filePath` (absolute), `line` and `character`, both
**1-based**; `workspaceSymbol` also takes `query`.

| Operation | Purpose | Use before |
| --- | --- | --- |
| `documentSymbol` | Every class, function, constant and local of a file, with lines | Reading any Python file: outline first, then read only the bodies you need |
| `hover` | Signature, inferred types and docstring at a position | Calling or changing an API you have not read |
| `goToDefinition` | Where the symbol at a position is defined | Modifying code that uses something unfamiliar; following an import |
| `findReferences` | Every usage of a symbol across the workspace | Renaming, deleting, or changing a symbol's behavior |
| `workspaceSymbol` | Search symbol names across the workspace | Locating code when you know a name but not a file; proving an old name is gone |
| `prepareCallHierarchy` | The call-hierarchy item at a position | Starting a call-graph walk |
| `incomingCalls` | Who calls this function, with call sites | Impact analysis before changing a signature or behavior |
| `outgoingCalls` | What this function calls | Tracing dependencies; understanding a function without reading its callees |
| `goToImplementation` | Implementations of an abstract member | Protocols and ABCs only; it returned nothing for a plain dataclass |

There is **no** diagnostics operation, **no** rename, **no** completion, and no
pagination or scope/find options in this tool. Diagnostics come from two other
places (see [Validating](#validating-a-change)); renaming is a procedure
([Safe rename](references/recipes.md#safe-rename)).

## Tool selection

| Task | Instead of | Use |
| --- | --- | --- |
| Find where something is defined | `grep`, reading files | `goToDefinition` |
| Find every usage | `grep -r` | `findReferences`, then the blind-spot search |
| Understand a file | reading it whole | `documentSymbol`, then `hover`, then Read with `offset`/`limit` on one body |
| Types, signature, docs | reading the implementation | `hover` |
| Find a symbol by name | `grep -rn "def name"` | `workspaceSymbol` |
| Who calls it / what it calls | reading callers one by one | `incomingCalls` / `outgoingCalls` |

Grep and Read stay right for comments, literal strings, Markdown, YAML, shell,
the Makefile, and every blind spot below.

## Pointing at a symbol

The tool has no `--find` marker: you give a line and a column, and the server
resolves the identifier under that column. Off by one character and it answers
"No hover information" or "No definition found", which says nothing about the
code.

1. Get the line from `documentSymbol` (or `grep -n`).
2. Get the column from the line's text: the first character of the name.
   `def name` at top level is column 5; a method `def name` inside a class is
   column 9; `class Name` is column 7; a top-level constant is column 1; for a
   use inside an expression, count from the line you read.
3. When a call answers "no information", re-read that line and fix the column
   before concluding anything.

To read a symbol's code without the whole file: `documentSymbol` gives its
start line; Read with `offset` at that line and a `limit` up to the next
symbol's line.

## Reliability: empty answers, cold server, stale index

- **Empty is ambiguous.** "No symbols found" and an empty diagnostics list mean
  either "none" or "not analyzed yet". Before trusting an empty answer, run the
  same operation on something you know exists (a symbol you just saw in
  `documentSymbol`). If the control answers, the empty result is real.
- **Cold server.** Right after a session starts or a plugin reloads, calls can
  return nothing. Retry the same call up to 5 times, with the control above,
  before reporting "not found".
- **Stale index after writes the server did not hear.** Measured: after renaming a
  function with `sed`, `documentSymbol` and `workspaceSymbol` still showed the old
  name; after a subagent rewrote a file, positions were 18 lines off. Reading the
  file with Read does **not** refresh it; the next Edit to that file does (the
  same query then returned the new line). So edit Python with Edit or Write when
  you will query the LSP afterwards. After a shell writer (`sed`, `make fix`,
  `ruff --fix`, `git checkout`) or a subagent's edits, compare one `documentSymbol`
  line with the file on disk before relying on any position; if they differ, the
  next Edit you make to that file brings the index back. `mcp__ide__getDiagnostics`
  sees files changed on disk, but with a delay: measured, the first call right after
  a shell write returned an empty list and the second returned the error. Retry it
  before trusting an empty answer. Its `code` field shows `[object Object]`; read the
  `message` instead.

## Blind spots: pair LSP with a text search

`findReferences` sees Python name bindings, nothing else. Measured: the pytest
fixture `scratch` in `scripts/plugin_validation/conftest.py` has **one**
reference (its definition) although several test modules use it, because
pytest injects fixtures by parameter name. So "only one reference" does not
mean "unused". Run `git grep -n -w <name>` too, and read every hit, when the
symbol can be reached by:

| Reach | Example in this repository |
| --- | --- |
| pytest fixture parameter names | `def test_x(scratch: Path)` |
| module paths in text | `python -m scripts.lint.lint_files` in the `Makefile`, workflows, `.claude/hooks/*.sh` |
| string keys and attribute names | `vars(namespace)["root"]`, `getattr(obj, "name")`, `monkeypatch.setattr("pkg.mod.name", …)` |
| documentation and instructions | `CLAUDE.md`, `.claude/rules`, skills, `docs/`, READMEs that cite a function |
| shell, jq, YAML, JSON | hook scripts, `checklist.json` verify commands |

## Validating a change

Two sources give diagnostics:

1. **After every Edit or Write** of a Python file, basedpyright's new
   diagnostics arrive with the tool result. Read them: a half-done rename shows
   `"new" is not defined` and `Function "old" is not accessed`, which is the
   signal to finish it.
2. **`mcp__ide__getDiagnostics`** asks VS Code (needs `/ide` connected). With a
   `uri` it checks one file; with no argument it returns every analyzed file,
   which is the workspace-wide check. It uses the `.venv` server, so it also
   confirms the two servers agree.

An empty diagnostics list is trustworthy only after a negative control: write a
throwaway `_neg_probe.py` in the same tree with `import os` and
`X: int = "not an int"`, confirm both errors are reported, then delete the probe
and confirm `ls` no longer finds it.

The LSP is fast feedback, not the gate. Before a commit, `make lint-staged`
(Ruff and basedpyright on changed files) and the tests of the modules you
touched still decide.

## Recipes

[references/recipes.md](references/recipes.md) has step-by-step procedures:

- [Understand a file without reading it whole](references/recipes.md#understand-a-file)
- [Impact analysis before a change](references/recipes.md#impact-analysis)
- [Dead-code audit](references/recipes.md#dead-code-audit)
- [Safe rename](references/recipes.md#safe-rename)
- [Change a signature](references/recipes.md#change-a-signature)
