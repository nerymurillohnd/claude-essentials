# basedpyright-quality plugin — design blueprint

- **Date:** 2026-09-19
- **Status:** design approved in conversation on 2026-09-19 (skills, LSP
  placement); remaining component decisions made under design ownership (§17).
  A tested reference implementation of the gate exists under
  `2026-09-19-basedpyright-quality/reference/`; the plugin itself is not built.
- **Plugin id:** `basedpyright-quality` (sibling of `ruff-quality` and
  `shell-quality`; same house contract)
- **Kind:** `bundle` ([ADR-0001](../../decisions/adr-0001-marketplace-distribution-model.md))
- **Target versions:** basedpyright **1.40.1** (based on pyright 1.1.414,
  released 2026-09-10), floor **≥ 1.37.0**; Claude Code **2.1.278**.
- **Evidence:** live docs and release notes read on 2026-09-19, the installed
  basedpyright 1.40.1 exercised in a scratch project (marked **[observed]**),
  and a file-by-file survey of every public Claude Code basedpyright/pyright
  plugin, skill, and hook found (§3). Research notes were kept in the session
  scratchpad; every load-bearing fact is restated with its source below.

## 0. Current architecture (canonical; supersedes later sections where they differ)

This proposal was revised several times with the maintainer on 2026-09-19.
This section is the current state; §5–§11 keep the reasoning and evidence.

**Distribution reality.** Users install the plugin from the marketplace; Claude
Code copies it to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`,
and `${CLAUDE_PLUGIN_ROOT}` changes on every update (plugins-reference, plugin
caching). Nothing may assume the maintainer's machine, operating system,
package manager, or a Python project. Persistent hooks therefore run a
**copy** of the handler placed by the wiring skill (`.claude/hooks/` or
`~/.claude/hooks/`), never a path inside the plugin cache.

**Components** (skill set confirmed by the maintainer, 2026-09-19: exactly `basedpyright` and `basedpyright-hooks`; `gate-session` dropped):

| Component | Location | Loads when | Freedom (skill authoring best practices) |
| --- | --- | --- | --- |
| `basedpyright` skill: expert knowledge | `skills/basedpyright/` | Working with Python files or basedpyright config (`paths` + description) | High: instructions and references Claude applies with judgment |
| `basedpyright-hooks` skill: wiring the after-edit gate | `skills/basedpyright-hooks/` | Only when the user asks, in their own words, to wire, check, or remove the hook | High for the audit and proposal (a checklist), **low** for installing (one script, exact command) |
| Language server | `.lsp.json` at the **plugin root** (verified: "`.lsp.json` in plugin root, or inline in `plugin.json`"; D2 resolved) + `scripts/langserver.sh` | Always, while the plugin is enabled | — |
| Runner | `scripts/basedpyright-quality` (not `bin/`: the repo forbids a top-level `bin/`, which claude.ai organization sync rejects) | Skills call it by `${CLAUDE_PLUGIN_ROOT}` path from Bash | Low |
| Debt agent | `agents/basedpyright-debt-fixer.md` (0.1.0, D3) | Delegated by the knowledge skill for multi-package or ~50+ diagnostic cleanups | Preloads `basedpyright`; works through the runner |

Two skills, split by purpose, so neither loads the other's context: wiring a
hook never loads the typing playbook, and fixing a type error never loads the
hook contract. Each skill uses progressive disclosure with references one
level deep (best practices: "Keep references one level deep from SKILL.md";
reference files over 100 lines start with a table of contents). The earlier
11-skill split (§7.0) is withdrawn: every model-invocable skill's description
costs context on every turn, and the split gained nothing that references
don't already give.

**`skills/basedpyright/` (knowledge).** `SKILL.md` (< 500 lines): the fix
workflow, non-negotiables, and a map. References: `install.md` (every install
and uninstall path per OS and package manager: uv, pip, pipx, Homebrew,
conda, npm; project vs global; editors), `configuration.md`, `cli.md`,
`rules.md`, `fix-playbook.md` (incl. the 14 basedpyright-only rules),
`modern-typing.md`, `comments-and-baseline.md`, `language-server.md`
(Claude Code's LSP tool and every editor), `pipelines.md`, `ruff-interplay.md`,
`sources.md` (the live sources to consult for anything version-sensitive,
and the URL policy).

**`skills/basedpyright-hooks/` (wiring).** `SKILL.md`: the workflow
(audit → consult sources → proposal → user approves or adjusts → install →
verify → hand off). References: [`audit.md`](2026-09-19-basedpyright-quality/reference/audit.md)
(a copyable 10-step checklist of what to inspect, OS-agnostic, replacing the
earlier `assess.sh`: an audit depends on context, so it is instructions, not a
script), `hook-contract.md`, `scopes.md`, `config-modes.md`, `rollback.md`,
`sources.md`. Assets: the handler (`basedpyright-after-edit.sh`, with the
profile embedded) and its test suite. Scripts: `manage.sh` (install, verify,
uninstall: backing up and merging settings JSON idempotently is fragile and
consistency-critical, so it is a script run with an exact command).

### Requirements

**Universal, with declared requirements.** "Universal" means
any user on a supported platform who meets these, which is what every public
basedpyright/pyright plugin surveyed does (the binary must be on `PATH`, the
plugin never installs it). This fills the house README's 📋 Requirements
table (`templates/plugin-bundle/README.md`: Requirement | Minimum | Check |
Why):

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.205 | `claude --version` | `restartOnCrash`/`shutdownTimeout` in `.lsp.json` (older versions skip the server entirely) |
| basedpyright + basedpyright-langserver | 1.37.0 (verified on 1.40.1) | `basedpyright --version`; `command -v basedpyright-langserver` | The gate's CLI and the language server; `--baselinemode` and the LS `baselineMode` setting. One install gives both (`uv tool install basedpyright`, `pipx`, `pip`, `uv add --dev`, `brew`, `npm i -g`) |
| Python | 3.10 for the PyPI package (it bundles Node) | `python3 --version` | Only for the PyPI install route; the npm route needs Node instead |
| bash | 3.2 | `bash --version` | The gate handler and `manage.sh` |
| jq | 1.6 | `jq --version` | JSON parsing in the gate |
| Platform | macOS, Linux, WSL, Windows with Git Bash | — | Native Windows without Git Bash, Claude Cowork (no settings hooks), and cloud sessions (no plugin language servers) are unsupported for the parts that need them |

The skills work with none of these installed (knowledge only); the audit
reports each missing requirement with the install command for the user's
platform and never installs anything.

**Excludes and explicit files** [observed, 1.40.1, confirmed by the
maintainer's own run over `~/projects/**/*.py`, which reported files inside
`node_modules/`]: with **no** config, basedpyright's default excludes
(`**/node_modules`, hidden directories, venvs) apply only when it enumerates
files; a file passed explicitly is analyzed anyway. With a config present,
both its `exclude` and the defaults filter explicit files too
(`filesAnalyzed: 0`). Consequences: `post` in a config-less directory checks a
vendored file Claude edited (correct: Claude edited it); the Bash scan prunes
`node_modules`, `.git`, and venvs itself; and `cli.md` documents that
`--output-json` is not a flag (`--outputjson` is).

### Surfaces

Every surface in `.claude/skills/plugin-design/references/surfaces.md`, decided:

| Surface | Decision | Why |
| --- | --- | --- |
| `plugin.json` | name, displayName, version, description, author, homepage, repository, license, keywords, `metadata.marketplace` (category `development`, tags) | House contract; catalog fields through `metadata` (DEBT-0015) |
| Marketplace entry | Generated (name, source, description, category, tags) | Never hand-edited |
| Skills | `basedpyright` (knowledge, `paths`-scoped) and `basedpyright-hooks` (wiring, narrow description) | Split by purpose; confirmed by the maintainer |
| Agents | `basedpyright-debt-fixer` (preloads `basedpyright`) | Large backlogs would flood the main context (§17 D3) |
| Hooks | Installed into a settings scope by `basedpyright-hooks` on request; no `hooks/hooks.json` | Always-on type-check hooks can't be opted out of per project |
| LSP | `.lsp.json` at the plugin root with a launcher script | Resolves the project's own basedpyright; settings verified live |
| MCP | Rejected | The LSP tool and the runner cover every capability |
| Monitors | Rejected | Duplicate the LSP and stream every line into context |
| `bin/` | Rejected (repo policy) | claude.ai organization sync rejects it; the runner lives in `scripts/` |
| `settings.json`, `outputStyles`, `workflows`, themes, channels, `userConfig`, `dependencies`, Node deps | Rejected | Nothing to configure at enable time; options are chosen during wiring and passed as hook environment variables |
| `defaultEnabled` | Default (`true`) | Installing wires nothing by itself |
| Languages | Gate core in Python 3.10+ stdlib behind a minimal Bash launcher; tests in pytest via `uv run --script` | Criteria in plugin-design Phase 4; **prerequisite: DEBT-0016** (Python gates in `npm run check` and CI) |

**What `basedpyright-hooks` carries, file by file** (everything a wiring
needs, nothing the knowledge skill needs):

| File | Contents | Drafted |
| --- | --- | --- |
| `SKILL.md` | The workflow as a copyable checklist: audit → sources → proposal → approval → install → verify → hand off; when to stop; what never to do (install packages, touch the user's config, wire without approval) | — |
| `references/audit.md` | The 10-step, OS-agnostic audit | [yes](2026-09-19-basedpyright-quality/reference/audit.md) |
| `references/hook-contract.md` | What the gate guarantees; the 7 events with matcher, timeout, blocking power, and output channel; the wiring snippet and per-scope paths; behavior per event; how diagnostics are produced (exact command line and why each flag); **a real report exactly as Claude receives it**; how corrections are enforced (the 7-step chain and its two escapes); exit codes both ways (what the handler returns per event, how each basedpyright exit is read, fail-open vs fail-closed); options; state; portability; limits; tests | [yes](2026-09-19-basedpyright-quality/reference/hook-contract.md) |
| `references/config-modes.md` | `own`, `profile`, `pinned`: what each runs, the embedded profile in full, how to explain each with the audit's numbers | build |
| `references/scopes.md` | project, local, user: settings file, handler location, sharing, one scope at a time | build |
| `references/rollback.md` | Uninstall, restore from backup, troubleshooting (`/hooks`, `claude --debug`, exit 127 = gate silently disabled) | build |
| `references/sources.md` | The live sources to consult before proposing, what to look for in each, and the URL policy | build |
| `assets/basedpyright-after-edit.sh` | The handler, copied byte for byte by `manage.sh`; the complete hook script, readable as its own example | [yes](2026-09-19-basedpyright-quality/reference/basedpyright-after-edit.sh) |
| `assets/settings.hooks.json` | The exact hook groups `manage.sh` merges | [yes](2026-09-19-basedpyright-quality/reference/settings.hooks.json) |
| `scripts/manage.sh` | install / verify / status / uninstall, idempotent, with backup and self-test | build |
| `scripts/test-basedpyright-after-edit.sh` | The 42-case suite, which `manage.sh install` runs against the installed copy | [yes](2026-09-19-basedpyright-quality/reference/test-basedpyright-after-edit.sh) |

**What Claude Code actually does with `.lsp.json` (captured live, 2026-09-19).**
A throwaway plugin whose `command` was a logging proxy in front of
`basedpyright-langserver` recorded every LSP message between Claude Code
2.1.278 and basedpyright 1.40.1 in `claude -p --plugin-dir` sessions:

| Question (§14) | Observed |
| --- | --- |
| Does an absolute `${CLAUDE_PLUGIN_ROOT}/…` launcher start? | Yes; `env`, `args`, and `workspaceFolder` placeholders resolved |
| `initializationOptions` delivered? | Yes, verbatim in `initialize` |
| Client capabilities | `workspace.configuration: true`, `workspaceFolders: false`; `didSave: true`; `publishDiagnostics` with `tagSupport [1,2]`, `versionSupport: false`; hover, definition, references, documentSymbol, callHierarchy; `positionEncodings: ["utf-16"]`. **No** pull diagnostics, **no** `didChangeWatchedFiles` (the root of #85225), no completion, code actions, rename, signature help, inlay hints, or semantic tokens |
| Do `settings` reach basedpyright? | **Yes, the highest-risk item is resolved:** Claude Code sends them in `didChangeConfiguration` **and** answers basedpyright's `workspace/configuration` requests per section: `basedpyright` → the `.lsp.json` object, `python` → `null` |
| Diagnostics delivery | Pushed (`publishDiagnostics`) after `didOpen` and after each edit (`didChange` + `didSave`); errors and warnings arrive with codes and tags |
| Baseline on save | With `baselineMode: "discard"`, fixing a baselined error through Claude's Edit tool left `baseline.json` byte-identical |

Consequences for `.lsp.json`: `disablePullDiagnostics` is defensive (the
client doesn't offer pull today); inlay-hint and completion settings are dead
weight and are omitted; `baselineMode` and `disableTaggedHints` are effective;
a `python.pythonPath` could be delivered through `settings.python` but can't
be per project (no placeholders in `settings`), so the launcher's resolver
and a `.venv` link remain the answer for non-`.venv` interpreters. The field-by-field `.lsp.json` design in §9 is to be rewritten from this
capture before building.

**Portability of the handler** (tested on macOS with bash 5.3 and `/bin/bash`
3.2; Linux runs in CI; Windows via Git Bash):

| Concern | Handling |
| --- | --- |
| Windows sends native paths (`C:\x\y`, hooks reference) | `to_posix`: `cygpath -u` when present, else `/c/x/y` conversion |
| `.exe` layouts | `.venv/Scripts/basedpyright.exe`, `python.exe`, `~/.local/bin/basedpyright.exe` |
| Exec-form hooks need a real executable; `.sh` files aren't one on Windows | Shell form with the documented double-quoted placeholder: `bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/basedpyright-after-edit.sh" post` (validated against the hooks schema) |
| `\b` differs between GNU, BSD, and BusyBox grep | POSIX classes only |
| Ownership bits emulated on Windows | The state-directory owner check is skipped on MINGW/MSYS/Cygwin |
| No `timeout` on macOS | Timeouts are a background process plus a polling loop |
| Linuxbrew, npm global, uv/pipx | Resolver and audit cover them |
| Native Windows without Git Bash, containers without bash | Unsupported, stated in the README (like `ruff-quality`) |
| A function called before it is defined silently returned nothing and let edits pass | Caught by the suite (24 failures) while porting; fixed; the suite would catch a regression |

## 1. Product thesis

A Python developer who uses Claude Code should be able to install one plugin
and get, from a single source of truth:

1. **Claude that writes code basedpyright accepts**, knows the current rules,
   configuration, comments, and baseline semantics, and fixes type errors in
   code instead of silencing them.
2. **Code intelligence** (definitions, references, hover, diagnostics) from the
   *project's own* basedpyright, not whatever binary happens to be on `PATH`.
3. **On request, a type-check gate whose green means CI's green**: the hook
   runs the same binary, the same configuration, the same baseline, and the
   same pass/fail rule as `basedpyright` in CI, and it never lets Claude finish
   a turn while the project fails.

Everything public today delivers at most one of these, and usually a flawed
version of it (§3). The differentiator is not "more features"; it is **parity**:
the editor, the LSP inside Claude Code, the hook, and CI resolve the same
executable and agree on the verdict.

## 2. Verified facts that shape the design

### 2.1 basedpyright (docs.basedpyright.com, GitHub releases, PyPI, local 1.40.1)

| Fact | Source | Design consequence |
| --- | --- | --- |
| Latest is 1.40.1 (2026-09-10), about weekly releases tracking pyright; 1.40.0 made the PyPI package require Python ≥ 3.10 | PyPI JSON, GitHub releases | The skill states the version it was written for and tells Claude to check `basedpyright --version` against the release notes; the requirements row says Python ≥ 3.10 for the PyPI wheel, npm otherwise |
| Default `typeCheckingMode` is `recommended` (pyright: `standard`); `recommended` enables almost every rule and sets `failOnWarnings = true` | docs: config-files, better-defaults | A warning fails CI by default. The gate uses the CLI's exit code as the verdict rather than re-deriving severity |
| `# type: ignore` is **ignored** by default (`enableTypeIgnoreComments = false`); `# pyright: ignore[rule]` is the only suppression; `reportIgnoreCommentWithoutRule` and `reportUnnecessaryTypeIgnoreComment` police it | docs: comments; [observed] | The most-installed public skill teaches `# type: ignore[...]` and a non-existent `# basedpyright: ignore`. Ours must be right, and the guard counts both spellings |
| Exit codes: `0` clean, `1` errors (or warnings under `failOnWarnings`), `2` fatal, `3` config unreadable **or invalid setting** (still prints diagnostics), `4` bad CLI arguments | docs: command-line; [observed] | A 4-way exit taxonomy, **but `--outputjson` turns exit 3 into 0** (§7A): the gate reads the config errors from stderr; `3` is never "type errors", it is "your configuration is broken" |
| A `pyproject.toml` with both `[tool.pyright]` and `[tool.basedpyright]` is a hard error → exit 3, silently falls back to defaults | [observed] | `assess` and `preflight` detect it before anything is installed |
| Files passed on the command line override `include`, but a file matching `exclude` is **skipped silently**: `filesAnalyzed: 0`, exit 0 | docs footnote; [observed] | A hook that passes filenames can report green without checking anything. The gate reads `summary.filesAnalyzed` and reports "skipped (excluded)" |
| A single-file run keeps config and import resolution, but **misses errors the edit causes in other files**: changing `a.py`'s return type broke `b.py`; `basedpyright a.py` reported 0, the project run reported the error | [observed] | Per-file feedback is advisory; the blocking verdict is a **project-scope** run at `Stop` |
| `--dependencies` prints only import counts, even with `--verbose` | [observed] | No reliable reverse-dependency graph from the CLI; "touched files + dependents" is not buildable cheaply. Project scope wins |
| Baseline (`.basedpyright/baseline.json`, committed) records accepted debt keyed by file, rule, and column range (line-shift tolerant) | docs: baseline; [observed] | The baseline is the native, CI-shared definition of "pre-existing" |
| A plain CLI run **rewrites `baseline.json`** when errors went down (`--baselinemode auto`, the local default) | [observed]: `updated ./.basedpyright/baseline.json with 0 errors (went down by 1)` | A naive hook mutates a tracked file on every run. The gate always passes `--baselinemode discard` |
| `--baselinemode discard\|auto\|lock` works but is **missing from `--help`** (docs mark it experimental); `lock` on a stale baseline exits **3**, the same code as a broken config; CI (detected via `is-ci`) defaults to `lock` since 1.36.0 | [observed]; release 1.36.0 | `lock` is wrong for a hook: fixing a baselined error would fail. `discard` never writes and still fails on new errors. Upstream help omission recorded as a flagged misalignment (§15) |
| When CI is detected, a stale baseline fails the run. So if Claude fixes a baselined error and nobody prunes, **CI goes red** | release 1.36.0; [observed] | The Stop gate detects "baseline outdated" and has Claude run a **prune-only** command the guard allows (§8.4) |
| With `--outputjson`, the auto-update line is written to **stdout before the JSON**; stdout also starts with a blank line | [observed] | The parser takes stdout from the first `{`; `discard` avoids the pollution anyway |
| Any `CI`/`GITHUB_ACTIONS`-style variable switches to CI behavior (annotations, baseline `lock`); `--level error` then behaves differently | [observed]; `is-ci` | The gate runs basedpyright with a sanitized environment (§8.6). The maintainer's shell exports `GITHUB_ACTIONS=true`, which is exactly this failure |
| Interpreter discovery: `--pythonpath` > `./.venv` at the project root (basedpyright-only default) > `python` on `PATH`; `venvPath`/`venv` discouraged | docs: import-resolution | The resolver finds the analyzer binary; basedpyright finds the analyzed interpreter itself. Non-`.venv` layouts (Poetry, conda) get `--pythonpath` from `assess` |
| LSP settings: `basedpyright.analysis.baselineMode` (`auto`/`discard`, 1.37.0), `diagnosticMode` (`openFilesOnly` default), `disableTaggedHints`, `configFilePath` (1.33.0), inlay hints…; editor settings are ignored when a config file exists | docs: language-server-settings; VS Code `package.json` 1.40.1 | Floor 1.37.0. The plugin's `.lsp.json` sets `baselineMode: discard` and `disableTaggedHints: true` |
| ~0.6 s cold start per CLI run (bundled Node), ~280 MB installed, no persistent CLI cache; `--threads` is experimental | [observed]; docs | Batch invocations (one per project root per batch), never one per file; `--threads` chosen by `assess` from a measured run |
| Pre-commit/prek mirror `DetachHead/basedpyright-prek-mirror`, tag without `v`; no official GitHub Action (annotations are native) | docs: prek-hook, improved-ci-integration | The `pipelines` reference ships exact, current snippets |
| No plugin system (no Django/Pydantic mypy plugins); Pylance's Type Server Protocol refused | docs: mypy-comparison, type-server | Non-goals and Limitations, stated up front |
| The CLI page's exit-code table and JSON schema are inherited from pyright. basedpyright's real behavior adds: exit 3 also for any unrecognized setting (diagnostics still printed), exit 3 for a stale baseline under `lock`, and an optional `cell` field on diagnostics for notebooks (in the 1.40.1 page, absent from `v1.21.1`) | docs: command-line (1.40.1 vs 1.21.1), errors-on-invalid-configuration; [observed] | The skill's `cli.md` documents basedpyright's behavior, not the inherited table; the formatter renders `cell` for `.ipynb` |
| The better-defaults page says `venvPath` "can only be set in the language server settings or the command line". In 1.40.1 a `pyrightconfig.json` with `venvPath` + `venv` is **accepted** (no unrecognized-setting error). When the named venv doesn't exist, it logs `venv nope subdirectory not found` (only with `--verbose`) and **silently falls back to `python` on `PATH`** | [observed] | Docs misalignment recorded (§15). `doctor` runs `--verbose` and reports the interpreter actually used, because a silent fallback to the wrong interpreter shows up as missing imports that aren't real. The recommendation stays `./.venv` (or a `.venv` symlink), which the same page calls the default |
| The rule catalog changes between versions: 1.40.1 has 95 `report*` rules; vs `v1.21.1` it lacks `reportShadowedImports` and adds `reportEmptyAbstractUsage`, `reportExplicitAny`, `reportIncompatibleUnannotatedOverride`, `reportInvalidAbstractMethod`, `reportSelfClsDefault` | both versions' `pyrightconfig.schema.json` [diffed] | `rules.md` is pinned to a version and guarded by the knowledge drift gate (§13) |

### 2.2 Claude Code (live docs + changelog, 2.1.278)

| Fact | Source | Design consequence |
| --- | --- | --- |
| `.lsp.json` fields: `command`, `extensionToLanguage` (required); `args`, `env`, `transport`, `initializationOptions`, `settings`, `workspaceFolder`, `startupTimeout`, `shutdownTimeout`, `restartOnCrash`, `maxRestarts`, `diagnostics` | [plugins-reference#lsp-servers](https://code.claude.com/docs/en/plugins-reference#lsp-servers) | Full, explicit config; `restartOnCrash`/`shutdownTimeout` need ≥ 2.1.205 (older versions **skip the server**) |
| `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_DATA}` resolve in LSP `command`, `args`, `env`, `workspaceFolder` (not in `settings`) | plugins-reference, placeholder table | The LSP `command` can be **our launcher script**, which resolves the project's own basedpyright. No other public plugin does this correctly across layouts |
| When two enabled servers claim `.py`, the first registered wins and the others never start; `/plugin` shows a warning | plugins-reference | Coexistence with `pyright-lsp`, `ty`, or another basedpyright plugin is detected and reported by `assess`, never auto-changed |
| The LSP server must write only protocol to stdout; violating it counts as a crash | plugins-reference | The launcher `exec`s and logs only to stderr |
| Plugin LSP servers don't start in cloud sessions; subagents lose the LSP tool (#84125); diagnostics aren't awaited after edits (#93321); phantom import errors for modules created mid-session (#85225); tagged "not accessed" hints pushed to context (#95507) | discover-plugins; open issues surveyed | **The LSP is navigation plus early hints, never the correctness gate.** The CLI gate and the `scripts/` runner work everywhere the LSP doesn't |
| `PostToolBatch` fires once after a parallel batch resolves, before the next model call; supports `hookSpecificOutput.additionalContext`; no matcher; `decision: "block"` stops the agentic loop (shown as a warning) | [hooks#posttoolbatch](https://code.claude.com/docs/en/hooks#posttoolbatch) | Per-batch feedback uses `additionalContext` (Claude sees it, the loop continues). One basedpyright run per batch instead of one per edited file |
| `PostToolUse` hooks run in parallel with each other; exit 2 shows stderr to Claude | hooks | With `ruff-quality` installed, its PostToolUse rewrites files; type-checking in the same event would race. Recording in `PostToolUse` and checking in `PostToolBatch` avoids it (ordering to be proven live, §14) |
| `Stop` exit 2 keeps Claude working; Claude Code overrides after 8 consecutive blocks (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`); `stop_hook_active` on continuations | hooks | `--max-blocks` (1–7, default 5) with a visible warning, as in `ruff-quality` |
| `additionalContext`, `systemMessage`, plain stdout capped at 10,000 characters; overflow goes to a file Claude isn't told about | hooks | Every message Claude reads is budgeted (≤ 8,000 chars) with an explicit pointer to the full report |
| Plugin `bin/` is added to the Bash tool's `PATH` while the plugin is enabled | plugins-reference | A `basedpyright-quality` runner Claude can call from Bash, from subagents, in `-p`, and in the cloud **Superseded:** this repo forbids a top-level `bin/` (claude.ai organization sync rejects it); the runner lives in `scripts/` and skills call it by path |
| `userConfig` values reach hooks as `CLAUDE_PLUGIN_OPTION_<KEY>`; project-level `pluginConfigs` are ignored (≥ 2.1.207) | plugins-reference#user-configuration | Not used for the gate: the gate is installed into settings by the skill, like `ruff-quality`, so it is visible, reviewable, and scoped |
| Settings-based hooks don't run in Claude Cowork | house finding (`ruff-quality` hook contract) | Same Cowork guard |
| `bashEditDiff` in `PostToolUse` on `Bash` (≥ 2.1.269, beta; recorded in auto/bypass modes or with `bashEditDiffEnabled`) | `ruff-quality` hook contract | Python files written through Bash are recorded too, when Claude Code records the diff |

`PostToolBatch` appears in the hooks reference but its first version is not in
the changelog. `preflight` probes for it (§8.3) and falls back to the
`PostToolUse` feedback mode on versions that lack it.

## 3. Landscape: what exists and what nobody does

Surveyed file by file on 2026-09-19 (Anthropic's official marketplace, about 15
community LSP wrappers, public SKILL.md files, standalone hook repos,
aggregators, and plugins for ty, mypy, pyrefly, and tsc).

| Existing offering | What it does | Why it is not enough |
| --- | --- | --- |
| `pyright-lsp` (official) | `pyright-langserver --stdio` for `.py`/`.pyi` | Global `PATH` binary only, no settings, no gate, no skill; `venv` issues reported (#58365); empty-shell installs after the marketplace move (#78604) |
| Community basedpyright LSP wrappers (Piebald (`basedpyright-langserver --stdio`, `.py`/`.pyi`/`.pyw`, empty `settings`, `maxRestarts: 3`; verified 2026-09-19), boostvolt, flaksit, tylerlaprade, yousiki, pySilver, …) | `.lsp.json` around a binary | Global or `uvx @latest` binaries (version never matches CI); some install packages at `SessionStart` without asking; only one prefers `.venv`; none sets `baselineMode` or hint suppression; one advertises 15 hooks with an empty `hooks.json` |
| estasney mux | 1,355-line proxy multiplexing basedpyright + ruff | Clever workaround for one-server-per-extension, but a large, untested surface in the hot path |
| Most-installed basedpyright skill (laurigates `python-plugin/skills/basedpyright-type-checking`, 150 lines; also mirrored on mcpapp-store) | Configuration and usage notes | Teaches `# type: ignore[reportUnknownVariableType]` (line 123; ignored by default) and a non-existent `# basedpyright: ignore` (line 126), invalid TOML (duplicate keys), the wrong pre-commit repo; never mentions the baseline |
| Standalone hooks (Gharib89, delfianto, hookstack, the r/ClaudeAI "file-specific type checking" pattern, bartolli for tsc, …) | Run pyright/basedpyright after edits | Report through channels Claude never sees (exit 0 stdout, `systemMessage`); parse human text; treat exit 3 as clean; one builds a shell command from the file path (**command injection**); file-only checks miss cross-file breakage; `auto` baseline mode rewrites the baseline |
| LSP Client ecosystem ([lsp-client.github.io](https://lsp-client.github.io/), v0.1.0) | Python SDK, a "Language Server Agent Protocol", a CLI, and an agent skill over basedpyright/tsserver/gopls/rust-analyzer for navigation and refactors | Navigation only, no type-check gate or basedpyright knowledge; installed by pasting an OpenSkills prompt into the agent (supply-chain surface we won't copy). Worth watching as a navigation fallback for subagents, where Claude Code drops the LSP tool (#84125) |
| Astral `ty` plugin | Skill + LSP | Good "fix, don't suppress" discipline, but its skill says "always use ty", which hijacks basedpyright projects when both are installed |
| Maintainer's Codex `basedpyright-after-edit` | `--outputjson`, per-file project roots, touched-project re-check | Strongest found, but `--baselinemode lock` fails when a baselined error is fixed, global binary only, no exit-code taxonomy, no Stop loop guard |

### 3.1 The maintainer's own prior art (read in full, 2026-09-19)

| Artifact | Keep | Fix in this design |
| --- | --- | --- |
| User-scope hooks backup (`python-after-edit.sh`, `basedpyright-after-edit.sh`, `_python-lib.sh`; basedpyright 1.39.10, 2026-08-20) | One sequencing wrapper so the type check never reads a file Ruff is rewriting; `--outputjson` with stdout/stderr captured separately; **errors listed, warnings grouped by rule** (54 warnings → 6 lines); exit ≥ 2 reported as "nothing was checked"; `cd` to the project root because config resolves from the CWD; `pwd -P` on the file path; no `--` separator; lowercase extension match (APFS is case-insensitive); `.pyw` parity with the LSP; skip the type check when the file doesn't parse; resolver walks up for `.venv`/`venv` and **never uses `uv run`** (with `UV_PYTHON_PREFERENCE=only-managed`, `uv run` can turn a missing interpreter into a download) | Fails **open** when `jq` or the lib is missing (`exit 0`); no `--baselinemode`, so every run can rewrite `baseline.json`; file-only scope misses cross-file breakage; no Stop project sweep for basedpyright; `basedpyrightconfig.json` used as a root marker, but basedpyright does **not** read that file [observed: a `typeCheckingMode: "off"` in it was ignored; the same content in `pyrightconfig.json` took effect] |
| `just-for-codex/plugins/basedpyright-after-edit` (Codex) | Physical-path canonicalization and a **path-escape guard** (absolute or `..` paths and anything outside the workspace fail); per-turn state keyed by hashed turn id; touched-project Stop sweep with no positional targets so `include`/`exclude`/execution environments/baseline apply; markers cleared only when clean | `--baselinemode=lock` exits 3 when Claude *fixes* a baselined error; blocks on **any** diagnostic, including `information`, which never fails CI (breaks parity); global `PATH` binary only; stale LSP-era markers aside, no loop guard |

Reproduced here before adopting the backup's claims [observed, 1.40.1]:

- **CWD decides the config.** A project with `reportMissingImports = "none"`:
  0 errors from its root, **1 error** when the same file was checked from the
  parent directory; `-p <root>` restored the correct result. The gate does both:
  `cd <root>` and `-p <root>`.
- **Symlinked paths defeat `exclude`.** An excluded file reached through
  `/var/folders/…` (a symlink to `/private/var/…`) was analyzed and reported an
  error. Every path is canonicalized with `pwd -P` before it is passed or
  compared.
- **`basedpyright -- file.py` exits 4.** Arguments are passed without `--`;
  paths that start with `-` are prefixed with `./`.

**Gaps nobody fills, all closed by this design:** a gate Claude actually sees;
exit-code taxonomy; baseline safety (no silent rewrite, fixes don't fail, CI
stays green); project-scope verdict instead of file-scope; one resolver shared
by LSP, gate, runner, and CI; LSP settings that suppress hint noise and
baseline writes; a path that works where the LSP doesn't (cloud, subagents,
`-p`); an accurate, current knowledge skill; conflict detection without
auto-disabling; no install side effects; shipped behavioral tests and evals.

## 4. Design principles

1. **CI parity is the verdict.** The gate passes only when `basedpyright` (same
   binary, config, baseline, environment semantics) would pass in CI. No
   private severity math.
2. **Fix, never silence.** No new `# pyright: ignore`, `# type: ignore`,
   file-level downgrades, configuration or baseline growth by Claude. Those are
   the user's decisions.
3. **No silent mutation.** Installing the plugin wires nothing and installs
   nothing. The gate never writes `baseline.json` except through the explicit
   prune-only command, which can only shrink it.
4. **Deterministic core, model for judgment.** Bash + jq decide; Claude and the
   optional agent fix code.
5. **Fail closed, with an honest reason.** Missing binary, broken config, fatal
   checker error, and timeout each produce a distinct message; none is
   reported as "clean".
6. **Token-efficient.** Claude gets grouped, capped, actionable diagnostics
   (file → line:col → rule → message), never raw JSON.
7. **Layout-agnostic.** uv, pip/venv, Poetry, conda, monorepos with
   `executionEnvironments` or several config roots, Windows `Scripts\`.
8. **House contract.** Same shape, scopes, rollback, and test discipline as
   `ruff-quality` and `shell-quality`, so users learn one model.

## 5. Component plan

| # | Component | Type | Justification (from the goal and the docs) |
| --- | --- | --- | --- |
| 1–3 (revised) | 11 area-wired skills: `typing`, `config`, `pipelines`, `editors` (reference, `paths`-scoped); `check`, `explain`, `doctor` (tasks); `adopt`, `gate`, `gate-session`, `burn-down` (user-only workflows) | Skills | See §7.0, which supersedes rows 1–3 below |
| 1 | `basedpyright` | Skill (Claude + user) | Knowledge and the fix workflow whenever Claude touches Python in a basedpyright project. Progressive disclosure: a lean `SKILL.md`, heavy references loaded on demand |
| 2 | `basedpyright-adopt` | Skill (Claude + user) | Adoption and migration (from mypy, pyright, or nothing) is a multi-step, decision-heavy workflow distinct from day-to-day fixing: measure counts per mode, choose a mode, write the config, create the baseline, pin the version, wire CI/prek/editors |
| 3 | `basedpyright-hooks` | Skill (Claude + user) | Installs, inspects, and removes the gate only on explicit request, with scope and policy choices. This is the "hook reference to build and wire when prompted" |
| 4 | `.lsp.json` + `scripts/langserver.sh` | LSP server — **in a separate plugin, `basedpyright-lsp`** (revised, see below and D2) | Code intelligence from the project's own basedpyright; settings that stop baseline writes and hint noise |
| 5 | `scripts/basedpyright-quality` | Plugin executable | One runner for `check`, `changed`, `explain`, `baseline status/prune`, `doctor`, `report`. It works where the LSP can't (cloud, subagents, `-p`) and gives Claude compact output instead of raw CLI text |
| 6 | `basedpyright-debt-fixer` | Subagent | Burning down a baseline or a post-adoption backlog of hundreds of diagnostics floods the main context. A subagent with a fresh context works one rule cluster or package at a time through the runner and returns a verified summary. Opt-in, invoked by `basedpyright-adopt` or on request |
| 7 | Gate handler `basedpyright-quality-gate.sh` | Asset installed into settings | `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolBatch`, `Stop` (§8) |

**Rejected components**

| Component | Why not |
| --- | --- |
| Plugin `hooks/hooks.json` (always-on) | Always-on type-check hooks in every project, at every scope, cannot be opted out of without disabling the whole plugin. The house pattern (skill-installed, scoped, reviewable settings entries) is strictly better and matches `ruff-quality` |
| Monitor running `basedpyright --watch` | Duplicates the LSP, streams every output line into Claude's context, runs unsandboxed for the session's lifetime, and only in interactive CLI sessions |
| MCP server | The LSP tool plus the `scripts/` runner cover everything; an MCP server adds a process and approval friction for no new capability |
| Prompt or agent hooks | A model call on every event costs latency and money; the verdict is deterministic |
| Auto-installing basedpyright | Side effects and ~280 MB without consent. `doctor`/`assess` print the exact install command (`uv add --dev basedpyright` preferred) |
| Plugin `settings.json` | Only the `agent` and `subagentStatusLine` keys are supported; unknown keys are silently ignored (plugins docs, "Ship default settings"). It can't carry hooks, permissions, or LSP options |

### 5.1 Revision: the language server ships as its own plugin

The first draft bundled the LSP. The plugins guide changes that call:

- It says: "For common languages like TypeScript, Python, and Rust, install
  the pre-built LSP plugins from the official marketplace. Create custom LSP
  plugins only when you need support for languages not already covered."
  Python is covered by `pyright-lsp`, but basedpyright is not (no official
  basedpyright plugin exists, §3). A basedpyright server is therefore
  justified, but it should be what the official ones are: a single-purpose
  plugin the user can pick or skip.
- "When more than one enabled LSP server declares the same file extension …
  the first server registered handles files with that extension and the
  others never start." Bundled, installing the type-check gate would also
  claim `.py`. A user who deliberately runs `ty` or `pyright-lsp` for
  navigation couldn't get the skills and the gate without an extension
  conflict whose winner they don't control.

So there are two plugins, released together:

| Plugin | Contents | Derived kind today |
| --- | --- | --- |
| `basedpyright-quality` | 3 skills, the `scripts/` runner, the gate assets, the optional agent | `bundle` |
| `basedpyright-lsp` | `.lsp.json`, `scripts/langserver.sh`, its resolver copy, tests | `bundle` (`pluginKind()` counts `.lsp.json` as an "other" component, so no validator change is needed) |

- **Independent, not a dependency.** The gate never uses LSP diagnostics, and
  the LSP works without the gate. `basedpyright-quality`'s `doctor` and skill
  recommend `basedpyright-lsp` and report conflicting servers. Neither plugin
  enables or disables anything.
- **One resolver, two copies:** the repo test that keeps the gate's inlined
  resolver identical also covers `basedpyright-lsp/scripts/lib/resolve.sh`.
- **ADR-0001:** calling a one-component LSP plugin a `bundle` ("multiple
  components working together") is inaccurate. The honest fix is an ADR-0001
  amendment adding an `lsp-only` kind (validator, README template, and
  `readmeKind()` regex), decided in D2.

## 6. File tree

```text
plugins/basedpyright-quality/
├── .claude-plugin/plugin.json
├── .lsp.json
├── bin/
│   └── basedpyright-quality              # runner (bash; exec bit)
├── scripts/
│   ├── langserver.sh                     # LSP launcher (resolver + exec)
│   ├── lib/resolve.sh                    # the one resolver (sourced by bin/ and the launcher)
│   ├── lib/diagnostics.sh                # jq filters: normalize, group, budget, multiset diff
│   ├── test-resolve.sh
│   ├── test-langserver.sh
│   └── test-runner.sh
├── agents/
│   └── basedpyright-debt-fixer.md
├── skills/
│   ├── basedpyright/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── cli.md                    # every flag, exit codes, JSON schema, gotchas
│   │       ├── configuration.md          # every config key, precedence, executionEnvironments
│   │       ├── rules.md                  # 95 rules × 6 modes, basedpyright-only rules marked
│   │       ├── fix-playbook.md           # per-rule fix recipes; forbidden escape hatches
│   │       ├── comments-and-suppression.md
│   │       ├── baseline.md
│   │       ├── language-server.md        # all LS settings; Claude Code, VS Code, Neovim, Zed, Helix, Emacs, Sublime, PyCharm
│   │       ├── pipelines.md              # GitHub Actions, GitLab, prek/pre-commit, uv
│   │       ├── modern-typing.md          # PEP → native Python version, typing_extensions, experimental flag
│   │       └── ruff-interplay.md         # overlapping rules, who owns what, gate coexistence
│   ├── basedpyright-adopt/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   ├── migration-from-mypy.md
│   │   │   ├── migration-from-pyright.md
│   │   │   └── adoption-playbook.md
│   │   ├── assets/pyproject-basedpyright.toml   # the recommended profile
│   │   └── scripts/
│   │       ├── assess.sh
│   │       └── test-assess.sh
│   └── basedpyright-hooks/
│       ├── SKILL.md
│       ├── references/
│       │   ├── hook-contract.md
│       │   ├── policies.md
│       │   ├── scopes.md
│       │   └── rollback.md
│       ├── assets/basedpyright-quality-gate.sh  # self-contained handler (resolver inlined, kept identical by test)
│       └── scripts/
│           ├── manage.sh
│           ├── test-gate.sh
│           └── test-manage.sh
├── tests/fixtures/                       # tiny projects: uv, venv, poetry-style, monorepo, excluded, broken-config, both-tables, stale-baseline
├── evals/                                # §13
├── CHANGELOG.md
├── LICENSE
└── README.md
```

Per §7.0, `skills/` holds eleven directories instead of three: `typing/`
(references `fix-playbook.md`, `modern-typing.md`), `config/` (`cli.md`,
`configuration.md`, `rules.md`, `comments-and-suppression.md`,
`baseline.md`), `pipelines/`, `editors/` (`language-server.md`),
`check/`, `explain/`, `doctor/`, `adopt/` (with `assess.sh`, the profile asset,
migration references), `gate/` (with `manage.sh`, the handler asset, hook
references), `gate-session/` (frontmatter hooks pointing at the same handler
through `${CLAUDE_PLUGIN_ROOT}`), and `burn-down/`. `ruff-interplay.md` is
shared from `skills/config/references/`.

Per §5.1, `.lsp.json`, `scripts/langserver.sh`, `test-langserver.sh`, and a
copy of `scripts/lib/resolve.sh` move to `plugins/basedpyright-lsp/` (with its
own README, CHANGELOG, LICENSE, and `plugin.json`); the rest of the tree stays
as shown.

The gate handler is copied into the user's `.claude/hooks/` and must be
self-contained, so the resolver is inlined there. A test (pattern of
`scripts/lib/plugin-paths.test.mjs`) runs both copies against the same fixture
matrix and fails if they disagree.

## 7. The skills

### 7.0 Skill architecture (revised 2026-09-19, supersedes the three-skill layout)

The first draft had three broad skills, all invocable by Claude and the user,
none using the wiring Claude Code gives each skill. Re-read against the
[skills reference](https://code.claude.com/docs/en/skills) (frontmatter
table, invocation control, `paths`, `context: fork`, frontmatter `hooks`,
string substitutions, dynamic context injection, content lifecycle), the
plugin splits into **independent skills, each wired to one area**. The
content of §7.1–§7.3 below is redistributed into them; where they disagree,
this section wins.

Facts from the reference that drive the split:

| Fact | Consequence |
| --- | --- |
| Once invoked, a skill's rendered content "stays in context across turns … every line is a recurring token cost"; after compaction each skill keeps 5,000 tokens, 25,000 in total | Small, area-specific skills instead of one large skill: only the area in play costs tokens |
| `paths`: "Claude loads the skill automatically only when working with files matching the patterns" (same globs as path-specific rules, which trigger when Claude reads matching files; symlinked checkouts work since 2.1.198) | Knowledge skills are scoped by the files that make them relevant, so they never load in a non-Python session |
| `disable-model-invocation: true`: only the user invokes it; its description stays out of context; if Claude tries anyway, Claude Code blocks it. The docs recommend it for "workflows with side effects" | Every skill that writes configuration, settings, or baselines is user-only |
| `user-invocable: false`: Claude-only background knowledge, hidden from `/` | Pure reference skills that aren't meaningful commands |
| `allowed-tools` with `${CLAUDE_PLUGIN_ROOT}` pre-approves an exact bundled command for the invoking turn (substituted in the same two places) | Task skills run the runner without permission prompts, and only the runner |
| `` !`command` `` injection runs before the skill renders; a non-zero exit **aborts** the invocation unless the command ends with `\|\| true`; stderr is merged | `check`, `doctor`, and `explain` inject the runner's output directly, with `\|\| true`, since exit 1 means "findings", not failure |
| `context: fork` + `agent:` runs the skill as the task of a subagent (background by default; `background: false` waits) | The debt burn-down is a forked skill bound to the plugin's agent |
| Frontmatter `hooks` register when the skill is invoked and **stay for the rest of the session** (listed as Session Hooks in `/hooks`); `once: true` only in skill frontmatter | A **session-only gate**: the full gate with zero files written, for trying it out or for one task |
| Subagents' `skills` field preloads full skill content at startup; plugin subagents ignore `hooks`, `mcpServers`, `permissionMode` | The agent preloads the fix playbook; its restrictions live in `tools` and its prompt |
| `description` + `when_to_use` truncated at 1,536 characters; the listing budget is 1% of the context window and drops descriptions of rarely used skills first | Short descriptions with the key use case first; reference skills rely on `paths`, not on long trigger lists |
| Plugin skill names: `name` sets the last segment, the plugin prefix stays (`/basedpyright-quality:check`) | Short names |

#### The skill set

| Skill (`/basedpyright-quality:…`) | Type | Who invokes | Wiring | Area and content |
| --- | --- | --- | --- | --- |
| `typing` | Reference | Claude only (`user-invocable: false`) | `paths: ["**/*.py", "**/*.pyi", "**/*.pyw", "**/*.ipynb"]` | Writing and fixing typed Python: the non-negotiable rules, the workflow (edit → file check → **project** check), LSP-is-advisory, and the fix playbook, including the 14 basedpyright-only rules and `modern-typing.md`. This is where §7.1's rules and playbook live |
| `config` | Reference | Claude + user | `paths: ["**/pyproject.toml", "**/pyrightconfig.json", "**/.basedpyright/**"]` | Configuration, precedence, modes, all rules × modes, comments and suppression, baseline semantics, `executionEnvironments`, interpreter discovery. Refuses to change a type-checking policy without the user's decision |
| `pipelines` | Reference | Claude + user | `paths: ["**/.github/workflows/*.y*ml", "**/.gitlab-ci.yml", "**/.pre-commit-config.yaml", "**/prek.toml", "**/noxfile.py", "**/tox.ini"]` | CI (native GitHub annotations, baseline `lock` in CI, GitLab code quality), prek/pre-commit mirror, uv, the `--level`/CI caveat |
| `editors` | Reference | Claude + user | `paths: ["**/.vscode/*.json", "**/.zed/settings.json", "**/.idea/pyLspTools.xml", "**/.helix/languages.toml", "**/lsp/basedpyright.lua"]` | Language-server setup per editor (`importStrategy`, Zed `binary.path`, nvim-lspconfig, Helix, Emacs, Sublime, PyCharm), the LS settings table, and what Claude Code's own LSP tool can and can't do |
| `check` | Task | Claude + user | `argument-hint: "[paths…] [--changed]"`; `allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/basedpyright-quality *)`; body injects `` !`"${CLAUDE_PLUGIN_ROOT}/scripts/basedpyright-quality" check $ARGUMENTS \|\| true` `` | Runs the project-scope check and hands Claude the §8.7 report already rendered. Read-only, so Claude may invoke it before claiming work is done |
| `explain` | Task | Claude + user | `arguments: [rule]`; injects `basedpyright-quality explain $rule` | One rule: mode defaults, basedpyright-only flag, docs link, playbook entry |
| `doctor` | Task | Claude + user | Injects `basedpyright-quality doctor \|\| true` | Resolver trace, versions, config, interpreter actually used (`--verbose`), conflicting LSP plugins, CI env vars, memory-cap variables |
| `adopt` | Workflow | **User only** (`disable-model-invocation: true`) | `allowed-tools` for the runner and `assess.sh`; `argument-hint: "[--from mypy\|pyright]"` | §7.2: adoption and migration. Writes config only after the user chooses |
| `gate` | Workflow | **Claude + user**, narrow description (revised, §7B) | `allowed-tools` for `assess.sh` and `manage.sh` only; `argument-hint: "install\|status\|verify\|uninstall [--scope …]"` | Loads only when the user asks to wire, check, or remove the after-edit type-check hook, in their own words. Audit → proposal → the user approves or adjusts → wire. Nothing else in the plugin loads for it |
| `gate-session` | Workflow | **User only** | Frontmatter `hooks`: the same five handlers (§8.1) run from `${CLAUDE_PLUGIN_ROOT}` in exec form | The whole gate for **this session only**: nothing is written to any settings file; it ends when the session ends. For trying the gate, or for a single task in a repo where the team hasn't adopted it |
| `burn-down` | Workflow | **User only** | `context: fork`, `agent: basedpyright-quality:basedpyright-debt-fixer`, `arguments: [slice]` | Reduces baseline or backlog debt one rule/package slice at a time (§11), in the background |

Consequences for the rest of the design:

- Claude can **never** install a gate, write a config, or start a burn-down on
  its own: those skills are hidden from it and blocked if it tries. When type
  errors keep recurring, Claude may mention `/basedpyright-quality:gate` once
  per session, as §7.3 says.
- A Python-free session loads **zero** description tokens for the four
  reference skills until a matching file is read. It loads three short
  descriptions for `check`/`explain`/`doctor` and none for the user-only ones.
- `gate-session` removes the main adoption barrier of the persistent gate
  (writing to a shared settings file) without a second implementation: same
  handler, same tests, different registration. Its limits, to state in the
  README: skill hooks run "for the rest of the session", and there is no
  per-hook disable (`disableAllHooks` is all-or-nothing), so ending it means
  ending the session. `gate-session` refuses to register when the persistent
  gate is already active in any scope, so two copies never run in parallel.
- The agent preloads `typing` through its `skills` field instead of
  re-reading references.

To prove live (added to §14): `${CLAUDE_PLUGIN_ROOT}` substitution inside
**frontmatter** `hooks` of a plugin skill (documented for hook commands and
skill content, not stated for this combination); `paths` activation when
Claude reaches a file through `Edit` before any `Read`; and the `!` injection
under each permission mode (outside auto mode, a command that isn't allowed
aborts the render, so the `allowed-tools` rule must match the injected
command exactly).

### 7.1 `basedpyright` (knowledge + fix workflow)

**Description (draft, < 1,536 chars):** used whenever Claude writes, edits,
reviews, or fixes Python in a project that uses basedpyright or pyright
(`[tool.basedpyright]`, `[tool.pyright]`, `pyrightconfig.json`,
`.basedpyright/`), and when the user asks to "type-check", "fix type errors",
"explain reportXxx", "configure basedpyright", "set up the baseline",
"basedpyright in CI / pre-commit", "set up the basedpyright language server",
or "why does basedpyright say …". It explicitly does **not** claim projects
configured for mypy, ty, or pyrefly only; it defers to them. Adoption and
migration go to `basedpyright-adopt`; the gate to `basedpyright-hooks`.

**Body (lean, about 150 lines):**

1. **Non-negotiable rules.** Fix in code. Never add `# pyright: ignore`,
   `# type: ignore`, file-level `# pyright:` downgrades, `cast(Any, …)`,
   `Any` annotations to silence `reportUnknown*`, stub files that erase types,
   config changes, or `--writebaseline`. If a finding looks wrong, show the
   rule, the location, and why, and let the user decide. When suppression is
   the user's call, the only acceptable form is `# pyright: ignore[ruleName]`
   with the rule named.
2. **Pick the command route once:** the runner (`basedpyright-quality check`)
   when the plugin is enabled; else `uv run basedpyright` (uv project), else
   `.venv/bin/basedpyright`, else `basedpyright` on `PATH`; `uvx
   basedpyright@<pinned>` only with the user's agreement. Always pass
   `--baselinemode discard` when running the CLI directly, and never in a
   shell that exports `CI`/`GITHUB_ACTIONS` unless it is CI.
3. **The workflow for every change:** read the config first; edit; check the
   edited files for fast feedback; then **check the whole project** (or the
   execution environment) before claiming done, because an edit can break
   importers. Read JSON, not text. Treat exit `3` as a configuration problem
   and `2`/`4` as tool problems, never as "clean".
4. **LSP diagnostics are advisory.** If the LSP shows an error the CLI doesn't
   (typically an import of a module created this session), trust the CLI.
5. **Baseline etiquette:** baselined errors show as hints in editors, not CLI
   failures; fixing one makes the baseline stale and **fails CI** until it is
   pruned (`basedpyright-quality baseline prune`, shrink-only). Never add to
   the baseline.
6. **Configuration in one page:** files and precedence
   (`pyrightconfig.json` beats `pyproject.toml`; both `[tool.pyright]` and
   `[tool.basedpyright]` in one file is an error), modes, `failOnWarnings`,
   `allowedUntypedLibraries`, `executionEnvironments`.
7. **Report format:** files and scope checked, what was fixed, what remains and
   why, the exact command run, and the version.

**References (loaded on demand):** `cli.md` (every flag including the hidden
`--baselinemode`, exit codes, JSON schema, the `filesAnalyzed: 0` trap, CI
detection, `--level` inconsistency, `--threads`/`--stats` incompatibility);
`configuration.md` (every environment option, type-evaluation setting, and
basedpyright-only key, with precedence and monorepo patterns); `rules.md` (the
full 95-rule × 6-mode defaults table from the rendered docs, basedpyright-only
rules marked, and the corrections the survey found: `reportImplicitOverride`,
`reportUnusedCallResult`, and friends are pyright rules that basedpyright turns
on; `reportShadowedImports` does not exist); `fix-playbook.md` (the part no one
else has: for the ~40 rules that fire most in practice (`reportAny`,
`reportExplicitAny`, `reportUnknownMemberType`, `reportMissingTypeStubs`,
`reportImplicitOverride`, `reportUnusedCallResult`,
`reportUnannotatedClassAttribute`, `reportPrivateLocalImportUsage`,
`reportImplicitRelativeImport`, `reportOptionalMemberAccess`,
`reportAttributeAccessIssue`, `reportArgumentType`, `reportReturnType`,
`reportPossiblyUnboundVariable`, `reportIncompatibleMethodOverride`,
`reportMissingSuperCall`, `reportUninitializedInstanceVariable`,
`reportUnreachable`, `reportUnnecessaryIsInstance`, `reportUnnecessaryCast`,
`reportInvalidCast`, `reportUnsafeMultipleInheritance`, …) the root cause,
the idiomatic fix (narrowing, `Protocol`, `TypedDict`, `@overload`,
`@override`, `TypeGuard`/`TypeIs`, `Final`, `assert_never`, `typing_extensions`
policy), the anti-fix to avoid, and when to escalate to the user);
`comments-and-suppression.md`; `baseline.md`; `language-server.md`;

A further reference, `modern-typing.md`, turns the features page's PEP list
into decisions Claude can apply, because the right fix depends on the
project's `pythonVersion`:

| Column | Content |
| --- | --- |
| Construct | e.g. PEP 695 `class Box[T]` / `type Alias = …`, PEP 696 TypeVar defaults, PEP 742 `TypeIs`, PEP 698 `@override`, PEP 702 `@deprecated`, PEP 705 `ReadOnly`, PEP 728 `extra_items`, PEP 692 `Unpack[TypedDict]` for `**kwargs`, PEP 673 `Self`, PEP 675 `LiteralString`, PEP 681 `dataclass_transform` |
| Native from | The Python version where `typing` has it (the `typing_extensions` backport is used below that) |
| Rules it satisfies | e.g. `@override` → `reportImplicitOverride`; `TypeIs` → removes `reportAny`/`reportUnknown*` at a boundary |
| Constraint | `typing_extensions` is a **runtime** dependency: if it isn't installed, basedpyright reports `reportMissingModuleSource`, an error in `recommended` [observed]. Claude adds it to the project's dependencies only with the user's agreement |

**Experimental PEPs (746, 747, 764) are off unless the project sets
`enableExperimentalFeatures = true`.** Observed with 1.40.1 and
`pythonVersion = "3.13"`: a PEP 764 inline `TypedDict[{"a": int}]` produced
five errors without the flag and none with it. The skill never uses them
unless the flag is already set, and never sets it itself (configuration is
the user's).

The 14 **basedpyright-exclusive rules** (1.40.1 docs, "basedpyright exclusive
settings"; all present in the 1.40.1 schema [verified]) get a dedicated section
in `fix-playbook.md`, because no pyright- or mypy-trained habit covers them:

| Rule | Fix in code | Anti-fix the playbook forbids |
| --- | --- | --- |
| `reportAny` | Narrow at the boundary (`isinstance`, `TypeIs`, a parsed `TypedDict`/dataclass), type the source | `cast(Any, …)`, re-typing as `object` without narrowing |
| `reportExplicitAny` | A precise type, a `TypeVar`, a `Protocol`, or `object` + narrowing | Swapping `Any` for an alias of `Any` |
| `reportIgnoreCommentWithoutRule` | Remove the ignore by fixing the code; if the user keeps it, name the rule | Adding a rule name without checking the error still exists (`reportUnnecessaryTypeIgnoreComment` will flag it) |
| `reportPrivateLocalImportUsage` | Import from the defining module, or re-export explicitly (`import x as x`, `__all__`) | Importing through an unrelated module |
| `reportImplicitRelativeImport` | `from . import foo` or the full package path | Adding the directory to `extraPaths` |
| `reportInvalidCast` | Remove the cast and narrow, or validate (`dict` → `TypedDict` casts trigger it) | `cast(object, …)` chains |
| `reportUnsafeMultipleInheritance` | Composition, or a single constructor-bearing base with mixins that define no `__init__`/`__new__` | Silencing it while keeping two constructors |
| `reportUnusedParameter` | Remove it, or prefix `_` when the signature is fixed by a protocol/override | Referencing it in a dummy statement |
| `reportImplicitAbstractClass` | Implement the abstract methods, or declare the subclass abstract (re-extend `ABC`) | Stub implementations that `raise NotImplementedError` in a concrete class |
| `reportEmptyAbstractUsage` | Drop `ABC`/`ABCMeta`, or add the abstract methods it is meant to have | — |
| `reportIncompatibleUnannotatedOverride` | Annotate the base attribute | — (off in `recommended` for performance; on in `all`) |
| `reportUnannotatedClassAttribute` | Annotate the attribute (`x: int = 0`, `Final`, `ClassVar`) | — (docs: unannotated attributes are unsafe **because** `reportIncompatibleUnannotatedOverride` is off by default, so this rule is the real guard) |
| `reportInvalidAbstractMethod` | Make the class abstract (extend `ABC`) or drop `@abstractmethod` | — |
| `reportSelfClsDefault` | Remove the default on `self`/`cls` | — |

`reportIgnoreCommentWithoutRule` also covers `# type: ignore`, but only when
the user has turned `enableTypeIgnoreComments` back on. Per-mode defaults for
the rule tables come from the **rendered** docs or `configOptions.ts`: the
source Markdown only contains the `generate_diagnostic_rule_table()` macro.
`pipelines.md`; `ruff-interplay.md` (rules both tools report, such as unused
imports/variables, redeclaration, implicit string concatenation, private
usage, with a recommendation of which tool owns each so the user doesn't get
double findings, and how the two gates coexist; overlaps to be re-verified
against both rule catalogs at build time).

Every fact in the references carries its source URL and the version it was
verified against. The skill tells Claude to re-check the release notes when
the installed version is newer than 1.40.x.

### 7.2 `basedpyright-adopt` (adoption and migration)

Triggered by "add basedpyright", "migrate from mypy / pyright", "turn on
strict typing", "adopt recommended mode", "set up a baseline", "reduce type
debt".

1. **Assess (deterministic):** `scripts/assess.sh` reports:
   - basedpyright location and version (and whether it is a project dev dependency);
   - Python and interpreter layout (`.venv`, Poetry, conda) and the `--pythonpath` that will be needed;
   - existing mypy, pyright, and basedpyright config, including the both-tables error;
   - `# type: ignore` / `# pyright: ignore` counts;
   - diagnostic counts per mode (`standard`, `recommended`, `all`), each run with `--baselinemode discard`, sanitized, and timed, grouped by rule (top 15) and by package;
   - any existing baseline and whether it is stale;
   - conflicting Python LSP plugins enabled (`pyright-lsp`, `ty`, others claiming `.py`);
   - CI and prek files.
2. **Recommend a target** with the numbers: usually `recommended` plus a
   baseline for existing code. Alternatives are `standard` for a first step,
   or `recommended` with `allowedUntypedLibraries` for untyped dependencies.
   The user chooses.
3. **Write the config** (only after the choice; never over an existing one
   without a shown diff). The recommended profile is
   `assets/pyproject-basedpyright.toml`, filled with the detected
   `pythonVersion`, `include`, and an `executionEnvironments` entry that
   relaxes a short, justified list of rules for `tests/`.
4. **Migrate suppressions:** convert `# type: ignore[code]` to
   `# pyright: ignore[rule]` only where the error still exists (map from
   mypy codes to basedpyright rules in `migration-from-mypy.md`); delete the
   rest. Show counts before and after.
5. **Pin and wire:** `uv add --dev basedpyright==<version>`, a CI step
   (`uv run basedpyright`; annotations and baseline `lock` are automatic), a
   prek hook if wanted, and editor settings (`importStrategy:
   fromEnvironment`, Zed `binary.path`, and so on).
6. **Baseline (user action):** `basedpyright --writebaseline` is offered as a
   command for the user to run or approve, then committed. The gate never
   runs it.
7. **Burn-down plan (optional):** a per-rule/per-package plan; each slice can be
   delegated to `basedpyright-debt-fixer`.

### 7.3 `basedpyright-hooks` (the gate)

Same structure and guardrails as `ruff-hooks`: explicit request only, `assess`
→ explain policies with this project's numbers → choose scope → `preflight` →
`install` (backup, idempotent merge, self-test, auto-restore) → hand off with
`/hooks` confirmation and the exact rollback. After install, the guard denies
Claude running `manage.sh install/uninstall`; the user runs them with `!`. An
incidental trigger (Claude left type errors behind) earns at most one
one-sentence offer per session.

`manage.sh` commands: `assess`, `show-policy --policy P`, `status`,
`preflight`, `install`, `verify`, `uninstall`, each with
`--scope project|local|user`.

Install options:

| Option | Values | Default | Meaning |
| --- | --- | --- | --- |
| `--policy` | `ci-parity`, `session-delta` | `ci-parity` if the project passes today (with its baseline), else `assess` recommends creating a baseline first | §8.2 |
| `--feedback` | `batch`, `edit`, `stop-only` | `batch` | When Claude hears about errors in the files it edited: once per tool batch (`PostToolBatch` `additionalContext`), after every edit (`PostToolUse` exit 2, like `ruff-quality`), or only at the end of the turn |
| `--max-blocks` | 1–7 | 5 | Consecutive Stop blocks before the turn may end with a visible warning |
| `--stop-timeout` | seconds | measured full-run × 3, min 60, max 900 | Internal deadline for the Stop check; the hook's `timeout` is set 30 s above it |
| `--threads` | `auto`, `off`, N | `auto` (on when `assess` measured > 10 s) | Passed to basedpyright |
| `--pythonpath` | path | detected | For non-`.venv` layouts |

## 7A. The after-edit gate: maintainer brief and reference implementation (2026-09-19)

**Brief (the maintainer's decision, resolves D1):** after **every** edit of a
Python file, a hook, not the model's judgment, type-checks that file and
collects its diagnostics; Claude must read them and fix every issue at once,
cannot move on to other work until the file is clean, and uses the LSP tool
(hover, definitions, references, symbols, call hierarchy) to investigate. A
cold language server gets retried. Scope: the edited file.

**Reference implementation, built and tested with this proposal** (moves to
`skills/gate/assets/` and `skills/gate-session/` when the plugin is built):

| File | What it is |
| --- | --- |
| [`reference/basedpyright-after-edit.sh`](2026-09-19-basedpyright-quality/reference/basedpyright-after-edit.sh) | The handler: `post`, `guard`, `stop`, `task-completed`, `prompt`, `session-start` |
| [`reference/settings.hooks.json`](2026-09-19-basedpyright-quality/reference/settings.hooks.json) | The wiring `gate install` merges: 7 events, exec form (`command` + `args`) as the docs recommend for path placeholders; validated against `schemas/claude-code/hooks.schema.json` (and that schema rejects unknown events and fields) |
| [`reference/test-basedpyright-after-edit.sh`](2026-09-19-basedpyright-quality/reference/test-basedpyright-after-edit.sh) | 42 behavioral cases with realistic payloads on stdin: **42/42 pass under bash 5.3 and `/bin/bash` 3.2**; ShellCheck (repo `.shellcheckrc`) and shfmt clean |

**Event map** (hooks reference: exit-2 table, decision control, common
fields):

| Event | Handler | Why this event |
| --- | --- | --- |
| `PostToolUse` `Write\|Edit\|NotebookEdit\|Bash` | `post`: CLI check of each edited file; exit 2 with the report | Exit 2 on PostToolUse "shows stderr to Claude" next to the tool result: the diagnostics are **delivered**, not waited for. Also fires for subagents' tool calls (hooks reference: settings hooks run inside subagents) |
| `PreToolUse` `Write\|Edit\|NotebookEdit\|Bash` | `guard`: **focus lock**, plus a Bash guard (below) | "Cannot continue" made deterministic: while a file is dirty, edits are allowed only to it and to Python files of the same project (the fix may live where the type is defined); others are denied. Read, Grep, and LSP are never locked. After 3 consecutive denials one edit passes with a visible warning, so a legitimate cross-cutting fix can't deadlock the session |
| `Stop` and `SubagentStop` | `stop`: re-check, **project scope** by default | The edited file can be clean while its importers break (observed); neither the main agent nor a subagent may finish with errors. Max 5 blocks (Claude Code overrides at 8) |
| `TaskCompleted` | `task-completed` | "Prevents the task from being marked as completed" while a file is dirty |
| `SessionStart` `compact\|resume` | `session-start` | Re-injects the open obligations after compaction, via `additionalContext` |
| `UserPromptSubmit` | `prompt` | A new user turn resets the block and denial counters and, if a file is still dirty (for example after max-blocks let a turn end), carries the obligation into the new turn as `additionalContext`. JSON only on stdout: plain stdout on this event is injected into Claude's context |

**Where "retry the LSP until it's warm" belongs, with measurements.** A hook
cannot call Claude Code's LSP tool, and Claude Code's pushed diagnostics are
not awaited (#93321), which is the "frozen LSP" symptom. Measured on
[rich](https://github.com/Textualize/rich) (213 files; `rich/console.py`:
17 errors, 286 warnings), basedpyright 1.40.1, M4:

| Path | Latency | Result |
| --- | --- | --- |
| CLI, one file (`--outputjson`) | 0.83 s analysis, ≈ 1.3 s wall (Node start) | 17 / 286 |
| Own LSP client, **pull** (`textDocument/diagnostic`), cold | 0.94 s, **first attempt**, no retry needed | 17 / 286 (same as CLI) |
| Own LSP client, pull, warm (after `didChange`) | **0.30 s** | 17 / 286 |
| Own LSP client, push (`publishDiagnostics`), cold / warm | 0.98 s / 0.51 s | 303 |
| CLI, whole project | 5.5 s (`--threads`: 5.2 s) | 574 errors / 4,506 warnings |

Conclusions:

1. **The gate's verdict comes from the CLI**: awaited, deterministic, and
   independent of anyone's server being warm. Pull diagnostics from a raw
   server answered on the first request; the retries belong where the
   coldness actually shows up, in **Claude's own LSP tool calls** while it
   investigates (#76870: the first `findReferences` can be incomplete). The
   hook report states that 3 retries usually get an answer, and that Read and
   Grep are the fallback.
2. **Optional warm engine (0.2.0, measured justification):** a per-project
   `basedpyright-langserver` owned by the gate, queried with pull
   diagnostics, cuts the per-edit cost from ≈ 1.3 s to ≈ 0.3 s. Retry policy:
   up to 3 requests with 250/500/1000 ms backoff on `ContentModified`,
   `ServerCancelled`, or timeout, then fall back to the CLI (never a silent
   pass). A parity self-test (pull vs CLI on the first file) disables it for
   the session on mismatch. Costs: a second server's memory next to Claude
   Code's, lifecycle and crash handling, and a Python ≥ 3.10 client (the
   probe client used for these numbers is 130 lines of stdlib Python).

**New findings from building it** (each has a test in the suite):

| Finding | Evidence | Handling |
| --- | --- | --- |
| **`--outputjson` hides a broken configuration.** With a `pyproject.toml` that has both `[tool.pyright]` and `[tool.basedpyright]`, or an unrecognized setting, the text CLI exits **3**, but with `--outputjson` it exits **0** with empty diagnostics, after silently falling back to defaults; the error only reaches stderr | [observed, 1.40.1, bash matrix: text 3 / json 0, with and without `-p`] | The handler restores exit 3 from the stderr markers (`could not be parsed`, `Config contains unrecognized setting`, `cannot have both`, `baseline file cannot be updated`). Every JSON-based hook surveyed, including the maintainer's backup hook and the Codex plugin, reports a broken config as clean. Upstream issue draft (§15) |
| An earlier shell probe in this session reported exit 4 for `--baselinemode discard`: the probe ran under zsh, which doesn't word-split `$args`, so the flag arrived as one argument | Re-run under bash: exit 3 | Exit-code matrices are run under bash only; the §2.1 row stands |
| Claude Code accepts **one** JSON object on stdout; several JSON lines that set fields are a parse failure | hooks reference, exit code 0 | The handler collects notices and prints one object |
| `additionalContext` and hook messages written as imperative system instructions "can trigger Claude's prompt-injection defenses" | hooks reference, "Add context for Claude" | All messages are factual statements of the project's policy ("the policy accepts fixes in code only"), not commands |
| Output over 10,000 characters is moved to a file Claude isn't told to read | hooks reference, JSON output | Reports are cut at 7,000 characters with a pointer |
| A PreToolUse command hook that times out **doesn't block**; a hook whose script is missing exits 127 and is a non-blocking error, "leaving the gate silently disabled" | hooks reference, Timeouts and Other exit codes | The guard never runs basedpyright (it only reads state) and has a 10 s timeout; `gate install` and `gate verify` execute the installed path and fail if it can't start |
| `if` holds exactly one permission rule and only filters tool events | hooks reference, common fields | Not used: covering 4 extensions × 3 tools would need 12 handlers, and a non-Python payload exits in ≈ 0.1 s (10 runs in ≤ 1 s, measured in the suite) |
| Anthropic's official hook example [`bash_command_validator_example.py`](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py) (last changed 2025-07-02) matches `^grep`, i.e. only the **start** of the command, and exits **1** on an unreadable payload, which the current reference calls a non-blocking error (the action proceeds). It links the retired `docs.anthropic.com` hooks URL | Read 2026-09-19; hooks reference, Other exit codes | The pattern (PreToolUse on `Bash`, reasons on stderr, exit 2) is adopted for the Bash guard; its gaps are not: the guard searches the **whole compound command** (`cd pkg && echo x > ../README.md` is caught, tested), fails closed with exit 2, and also returns the documented `permissionDecision: "deny"` JSON. Denied through Bash: `--writebaseline`, `--baselinemode auto\|lock`, `disableAllHooks`, `enableTypeIgnoreComments`; shell writes that carry a suppression comment or touch the config, baseline, gate, or settings; and, while a file is dirty, any shell write (reads and `basedpyright` runs stay allowed) |
| **Exit 2 on `UserPromptSubmit` blocks the prompt and erases it**; its default timeout is 30 s and a timed-out hook's output is discarded | hooks reference, UserPromptSubmit | A gate that fails closed there would lock the user out of the session when, say, `jq` disappears. The handler is fail-closed on edit-time events and **fail-open with a visible `systemMessage` on `UserPromptSubmit` and `SessionStart`** (tested: no `jq` → prompt allowed, edit denied) |
| Typing `/skill` bypasses `PreToolUse` on the Skill tool; `UserPromptExpansion` (matcher on `command_name`) is the event that sees it and can block the expansion | hooks reference, UserPromptExpansion | `gate install` adds a `UserPromptExpansion` hook matching `^basedpyright-quality:gate-session$` that blocks `gate-session` while the persistent gate is active, so the two never run together. The matcher is anchored because a scoped name with `:` is evaluated as a regular expression |
| In a worktree, `${CLAUDE_PROJECT_DIR}` stays at the main checkout while `cwd` follows Claude | hooks reference, Reference scripts by path | The handler derives the project root from each edited file's own path, never from `CLAUDE_PROJECT_DIR` |

## 7B. Universal by design (revised 2026-09-19, maintainer brief)

**Brief:** the gate is not for "Python projects". It checks **any Python file
Claude edits**, in a Python project or not, in a repository or not; it uses
the nearest configuration if one exists; basedpyright (CLI + language server,
shipped together) must be installed in the project or globally. Wiring
happens only after an audit of the user's real environment has been shown to
them and they have approved or adjusted it.

### What the reference handler now does (42/42 tests, bash 5.3 and 3.2)

| Situation | Policy used | Blocks on | Stop checks |
| --- | --- | --- | --- |
| File inside a project with `pyrightconfig.json` or `[tool.basedpyright]`/`[tool.pyright]` (nearest, walking up) | That config (`BPAE_CONFIG_MODE=own`, default) | basedpyright's own verdict (exit 1, so `failOnWarnings` is honoured as in CI) | Edited files, plus **only diagnostics new since the session first touched the project** (snapshot taken in `PreToolUse` before the first edit). Pre-existing debt elsewhere never blocks; `BPAE_STOP_SCOPE=project` restores strict CI parity |
| File with no config above it: a JS repo's helper script, `~/scripts/x.py`, a file in `/tmp` | basedpyright defaults (`recommended`, every rule), or the **embedded profile** (`profile` mode) | Errors and warnings, **except** `reportMissingImports`, `reportMissingModuleSource`, `reportMissingTypeStubs` in defaults mode: they describe packages not installed where basedpyright looks, which Claude can't fix without installing packages or suppressing, and the policy allows neither without the user. They are still reported | The edited files |
| Any file, `pinned` mode | The plugin's profile, overriding the project's config | Its verdict | The edited files (a config outside the project has no `include` for it) |

- **Self-contained profile, inline and idempotent.** The profile is embedded
  in the handler (a heredoc), materialized to the state directory only when
  its content changed. It states `recommended` explicitly and sets the two
  "package not installed" rules to `information`: reported, never failing.
  `BPAE_CONFIG` points `profile`/`pinned` at the user's own file instead.
  Rule-level policy can't be passed as CLI flags (the CLI has none), so a
  config file is the only way; the embedding keeps it one file.
- **Interpreter.** With `-p` pointing at a config outside the project,
  basedpyright ignores the project's `.venv` and uses `python` on `PATH`
  [observed: `Execution environment: python` vs the `.venv` path with
  `--pythonpath`]. For every root without its own config, the handler finds
  the nearest `.venv`/`venv` interpreter walking up and passes
  `--pythonpath`; with a project config it lets basedpyright discover, as CI
  does.
- **Files written by Bash.** "Claude Code doesn't run a PostToolUse hook
  matching Edit|Write when a Bash command … rewrites the same file" (hooks
  reference). `bashEditDiff` covers it only in some permission modes, so the
  guard marks the time before each Bash command and `post` finds `.py`/`.pyi`
  files newer than the mark (pruning `.git`, venvs, `node_modules`, caches;
  at most 50; `BPAE_BASH_SCAN=0` turns it off). Tested: a `cat > bad.py`
  heredoc is found and blocked.

### The audit: [`reference/audit.md`](2026-09-19-basedpyright-quality/reference/audit.md)

*Revised:* the audit is now a checklist the skill gives Claude (§0), not a
script. The findings below came from a prototype script (`assess.sh`, since
removed) run on three machines' worth of layouts; they show what the
checklist must surface, and that the maintainer's own environment is just one
case among them.

Read-only, no network, text or `--json`. Run on three real environments this
session:

| Environment | What it reported | Recommendation |
| --- | --- | --- |
| This repository (Node, no Python) | 0 Python files; no config; basedpyright 1.40.1 on `PATH`, language server present, floor met; no `.venv`; **`GITHUB_ACTIONS=true` and `UV_PYTHON_PREFERENCE=only-managed` in the environment** | user scope, `profile` mode, auto Stop |
| rich (213 files, Poetry) | Markers `pyproject.toml setup.py poetry.lock`; no basedpyright config; **`[tool.mypy]` configured** (a second checker that will disagree); one-file check 1 s | project scope, `profile` mode, auto Stop |
| A loose directory, not a repository | 1 file; no markers; no config | user scope, `profile` mode, auto Stop |

It covers: Python presence and project markers; the nearest config and the
both-tables error; other type checkers (mypy, ty, pyrefly); baseline; every
basedpyright found (project venv, `PATH`, uv/pipx, Homebrew) with version,
language server presence, and the ≥ 1.37.0 floor; the interpreter; Claude
Code's version; hooks already running pyright/basedpyright in any settings
scope; enabled Python LSP plugins; environment variables that change behavior
(CI, `GITHUB_ACTIONS`, the tool memory cap, `UV_PYTHON_PREFERENCE`); and a
real check run (validity, since `--outputjson` hides exit 3, and timing).

### The wiring workflow (`gate` skill)

1. **Audit:** follow `references/audit.md` step by step; never assume a Python project, an OS, or a package manager.
2. **Consult live sources for anything version-sensitive** before proposing
   (the skill lists them with what to look for): the Claude Code hooks
   reference and changelog (events, exit codes, JSON fields, timeouts),
   basedpyright's release notes for versions newer than the one the
   references were verified against (1.40.1), its CLI and configuration
   pages, and the docs URL policy (`/latest/` or the version tag, never
   `/dev/` or an old `/vX/` page).
3. **Present** the audit in plain words and a concrete proposal: scope
   (project, local, user), configuration mode (`own`, `profile`, `pinned`,
   with the exact profile shown), Stop scope (`auto`, `files`, `project`),
   timeouts sized from the measured check, and every conflict found (another
   type checker, an existing pyright hook, a Python LSP plugin, `CI` variables
   exported in the shell, a missing binary with the exact install command for
   project or global).
4. **Wait** for the user to approve or adjust. Silence isn't approval.
5. **Wire** idempotently (`manage.sh install`): back up the settings file,
   copy the handler byte for byte, merge the hook groups (re-running changes
   nothing), execute the installed path once so a wrong path can't leave the
   gate silently disabled (exit 127 is non-blocking), and print the rollback.
6. **Hand off:** `/hooks` to confirm the groups, and what to expect on the
   first edit.

**Invocation (revised):** `gate` is **model-invocable** after all, with a
narrow description: the user asks for the hook in their own words ("quiero
que Claude corra basedpyright al editar Python"), and `disable-model-invocation`
would hide the skill from exactly that request. Safety doesn't come from
hiding it: `allowed-tools` pre-approves only `manage.sh`, the
workflow stops at step 4, settings writes still go through Claude Code's
permission prompt, and once installed the guard denies Claude running
`manage.sh install/uninstall`. **`gate-session` stays user-only:** its
frontmatter hooks register the moment it is invoked, so Claude invoking it
would wire the gate without the approval step.

## 8. Hook contract (reference for `basedpyright-hooks`)

### 8.1 Events

| Event | Mode | Handler | Effect on Claude |
| --- | --- | --- | --- |
| `UserPromptSubmit` | all | `baseline`: fingerprint every file that decides the verdict (`pyrightconfig.json`, `[tool.basedpyright]`/`[tool.pyright]` tables, `extends` targets, `baseline.json`, the gate's settings groups, `disableAllHooks`); what the user changed between turns becomes the accepted state; reset the Stop block counter | None |
| `PreToolUse` on `Write\|Edit\|NotebookEdit\|Bash` | all | `guard` (§8.4). Under `session-delta`, also the **first-touch snapshot** of a project root | Denied edits don't happen |
| `PostToolUse` on the same tools | `batch`, `stop-only` | `record`: append `.py`/`.pyi`/`.pyw`/`.ipynb` paths (from `tool_input`, `tool_response.filePath`, `bashEditDiff`) to the session file set; < 20 ms, no basedpyright run | None |
| `PostToolUse` | `edit` | `post`: run the check on the edited file's project root restricted to that file; exit 2 with findings | Must fix now |
| `PostToolBatch` | `batch` | `batch`: one basedpyright run per project root over the files touched in this batch; emit `additionalContext` with new diagnostics; the loop continues | Sees errors before its next step, isn't forced to fix mid-refactor |
| `Stop` | all | `stop`: **project-scope** verdict per touched root (§8.3); exit 2 on failure | Keeps working until green or max-blocks |

Why feedback is not blocking by default: type errors are cross-file and
multi-step. Changing a signature legitimately breaks callers until the next
edits land. Blocking after every edit (the `ruff-quality` model, right for
formatting) would fight refactors and cost ~0.6 s per edit; `batch` informs
early and `Stop` enforces. Users who want the stricter loop choose `edit`.

### 8.2 Policies (what counts as failing)

| Policy | Verdict at Stop | Pre-existing errors | Best for |
| --- | --- | --- | --- |
| `ci-parity` (recommended) | basedpyright exit code for the project (with `--baselinemode discard`), i.e. what CI will say | Must be in the committed baseline. `preflight` refuses to install if the project fails today, and offers the user `basedpyright --writebaseline` | Any project that runs basedpyright in CI |
| `session-delta` | Fail only on diagnostics (multiset keyed by file, rule, normalized message; line-insensitive) that were not present at the session's first touch of that project | Tolerated, reported as a count | Projects that refuse a baseline or aren't clean yet; explicitly weaker: a green gate does not mean CI is green |

Under `session-delta`, the first-touch snapshot is a full-project run. If
`assess` measured it above the snapshot budget (default 20 s), the policy
degrades to touched-files-only snapshots and Stop checks touched files only,
and the README says this misses cross-file breakage.

### 8.3 Stop algorithm

1. If `stop_hook_active` and the block count ≥ `--max-blocks`: allow, with a
   `systemMessage` listing what is unresolved.
2. Group session files by **project root**: the nearest ancestor with
   `pyrightconfig.json` or a `pyproject.toml` containing `[tool.basedpyright]`
   or `[tool.pyright]`, else the git root. Monorepos get one run per root. With
   `executionEnvironments`, one run covers all environments.
3. Per root: resolve the binary (§8.5), then run in a sanitized environment
   (§8.6):
   `basedpyright --outputjson --baselinemode discard [-p <config>] [--pythonpath P] [--threads N]`
   with no file arguments, so `include`/`exclude` behave exactly as in CI.
   The internal deadline is `--stop-timeout`.
4. Classify the result:

   | Outcome | Gate result | Claude is told |
   | --- | --- | --- |
   | Exit 0 | pass | — |
   | Exit 1 | fail (`ci-parity`) / diff against the snapshot (`session-delta`) | Grouped diagnostics (§8.7) |
   | Exit 2 | fail: checker crashed | The fatal message; don't retry blindly; tell the user if it persists |
   | Exit 3 | fail: config broken | The config error text; editing config is denied by the guard → **stop and tell the user** |
   | Exit 4 | fail: gate bug | A message for the user naming the gate version; the turn may end after max-blocks |
   | JSON unparseable, deadline hit, or binary missing | fail closed | The exact reason |
   | Killed by a signal (exit ≥ 128, typically 137 = SIGKILL) | fail closed | "basedpyright was killed (signal N); on Linux/WSL this is usually Claude Code's tool memory cap (`CLAUDE_CODE_TOOL_MEMORY_LIMIT`), which the kernel enforces without naming it. Ask the user." Never reported as a checker crash or as clean |

5. **Baseline stale:** if the output says the baseline is outdated (errors went
   down), block once with: run `basedpyright-quality baseline prune` (allowed by
   the guard; it runs `--baselinemode auto` and verifies the entry count
   **only decreased**, else restores the file and fails). CI would otherwise
   fail on the stale baseline.
6. **Baseline changed outside the gate:** if `baseline.json` differs from the
   turn's fingerprint and the change wasn't a verified
   `basedpyright-quality baseline prune`, report it to the user (for example
   a language server that ignored `baselineMode: "discard"`). Not blocking:
   Claude didn't write it, and the guard would have denied it.
7. **Escape-hatch accounting** (never blocks by itself): count deltas of `Any`,
   `cast(`, and suppression comments in touched files since the session
   baseline; included in the user-facing `systemMessage`.
8. Pass: `systemMessage` `basedpyright-quality ✓ <roots> · <files analyzed> files ·
   <version> · <time>`.

### 8.4 Guard (PreToolUse)

| Input | Denied when |
| --- | --- |
| `Write`/`Edit`/`NotebookEdit` on `.py`/`.pyi`/`.ipynb` | The new text has more of any of: `# pyright: ignore` (any form), `# type: ignore` (counted even though it's disabled by default: it becomes live if the user enables it), file-level `# pyright:` directives that lower a mode (`basic`, `standard`) or set a rule to `false`/`none`/`hint`/`information`/`warning`, than the text it replaces |
| … on `pyrightconfig.json`, any `extends` target, `.basedpyright/**` or the configured `baselineFile`, the gate handler | Always |
| … on `pyproject.toml` | The `[tool.basedpyright*]` or `[tool.pyright*]` tables would change |
| … on settings files | The gate's groups or `disableAllHooks` would change |
| `Bash` | `--writebaseline`, `--baselinemode auto`/`lock` (except via the runner's `baseline prune`), `disableAllHooks`, `manage.sh install/uninstall`, or a write construct (`>`, `sed -i`, `perl -i`, `tee`, `cp`, `mv`, `rm`, `ln`, heredoc, `python -c`) that targets a config/baseline/handler/settings file or carries a suppression comment |

Deny = exit 2 plus JSON `permissionDecision: "deny"` with a reason that tells
Claude to change the code, or to stop and ask the user if the rule is wrong.
Stubs under `stubPath` stay allowed (legitimate), and the Limitations section
says a stub can hide types.

### 8.5 The resolver (shared by LSP launcher, runner, gate)

Resolved per project root, first hit wins, the choice logged in `doctor`:

1. `BASEDPYRIGHT_BIN` / `BASEDPYRIGHT_LANGSERVER` override (absolute path).
2. `<root>/.venv/bin/<exe>`, `<root>/venv/bin/<exe>`, and on Windows
   `<root>/.venv/Scripts/<exe>.exe`; walking up to the git root.
3. `<exe>` on `PATH`, then `~/.local/bin`, `/opt/homebrew/bin`,
   `/usr/local/bin`.
4. **Never `uv run`**, not even `--no-sync`: with
   `UV_PYTHON_PREFERENCE=only-managed` (set on the maintainer's machine) it can
   turn a missing interpreter into a download, so a gate that needs the network
   dies open. A uv project is covered by step 2 because uv creates `.venv`.
5. Nothing found: fail with the install command. **No `uvx` fallback by
   default** (network, version drift); an opt-in `BASEDPYRIGHT_UVX_VERSION=1.40.1`
   enables `uvx basedpyright@<pinned>`.

Then it checks the version against the floor (≥ 1.37.0), and warns when the
project pins a different version than the one found.

### 8.6 Environment sanitization

basedpyright runs under `env -u CI -u CONTINUOUS_INTEGRATION -u BUILD_NUMBER
-u RUN_ID -u GITHUB_ACTIONS -u GITLAB_CI -u BUILDKITE -u CIRCLECI -u TRAVIS
-u JENKINS_URL -u TF_BUILD -u TEAMCITY_VERSION …` (the full `is-ci` vendor
list, pinned in `lib/diagnostics.sh` and tested), plus `NO_COLOR=1`. The
explicit `--baselinemode discard` makes the result independent of CI
detection either way; unsetting the variables removes annotation noise and the
`--level` inconsistency. `PYRIGHT_TMPDIR` points at the gate's state
directory.

### 8.7 What Claude reads

```text
basedpyright-quality ✗ 3 new errors, 1 warning in 2 files — project backend/ (basedpyright 1.40.1, recommended, failOnWarnings)
backend/app/models.py
  42:9   error    reportAttributeAccessIssue  Cannot access attribute "nme" for class "User"
  57:5   warning  reportImplicitOverride      Method "save" is not marked as override but is overriding a method in class "Base"
backend/app/api.py  (not edited — broken by your change to models.py)
  12:18  error    reportArgumentType          Argument of type "str | None" cannot be assigned to parameter "user_id" of type "str"
Pre-existing (baseline): 118 — unchanged.
Fix the code. Do not add # pyright: ignore / # type: ignore, change configuration, or grow the baseline.
Rule docs: basedpyright-quality explain <rule>. Full list: basedpyright-quality report
```

- Errors are listed individually (cap 25, then counted); warnings and
  information are **grouped by rule** with counts, the approach proven in the
  maintainer's user-scope hook (54 warnings rendered as 6 lines).
- Rule-less diagnostics (syntax errors) in a file suppress that file's other
  diagnostics: an unparseable file produces a cascade that adds nothing.
- Diagnostics in files **not** edited are labeled, because that is the
  cross-file breakage a per-file hook misses.
- Budget: ≤ 8,000 characters. Overflow is summarized by rule and file, and
  `basedpyright-quality report` prints the full stored result.
- Messages keep basedpyright's indented detail lines (they explain the type
  mismatch), trimmed to 3 lines each.

### 8.8 Timeouts

| Handler | Hook `timeout` | Internal deadline |
| --- | --- | --- |
| `baseline`, `record` | 10 s | — |
| `guard` | 30 s (60 s with `session-delta` first-touch snapshot) | 25 s / 55 s |
| `batch`, `post` | 120 s | 100 s |
| `stop` | `--stop-timeout` + 30 s | `--stop-timeout` |

The internal deadline expires before the harness timeout, so the gate always
renders a decision instead of silently timing out.

### 8.9 State

Per session in `${TMPDIR:-/tmp}/basedpyright-quality-gate-<uid>/` (0700,
owner-checked, pruned after 2 days): touched files, roots, config
fingerprints, snapshots (`session-delta`), last full JSON per root (for
`report`), block counter. Nothing is written in the project.

### 8.10 Coexistence

- **With `ruff-quality`:** Ruff's `PostToolUse` rewrites files. The
  basedpyright gate only *records* in `PostToolUse` and checks in
  `PostToolBatch`/`Stop`, so it never reads a half-written file. Both Stop
  gates are read-only and may run in parallel. `ruff-interplay.md` assigns
  overlapping rules to one tool.
- **With `verify-completion`:** independent `Stop` hooks; both must pass.
- **With hand-written hooks that already run basedpyright** (for example the
  maintainer's former user-scope `python-after-edit.sh`): `assess` scans all
  three settings scopes for hook commands mentioning `basedpyright`/`pyright`
  and reports them; running both doubles the latency and the messages. The user
  decides which to keep.

### 8.11 Input hygiene (every handler)

- File paths: lowercase-extension match on `.py`/`.pyi`/`.pyw`/`.ipynb`;
  canonicalized with `pwd -P`; refused if outside the session's `cwd`/project
  roots; never interpolated into a shell string (arrays only).
- The project root is the nearest ancestor with `pyrightconfig.json` or a
  `pyproject.toml` containing `[tool.basedpyright]`/`[tool.pyright]` (the only
  files basedpyright reads), else the git root.
- basedpyright is always run with `cd <root>` **and** `-p <root>`, without `--`.
- Missing `jq`, an unreadable payload, or an unusable state directory fail
  **closed** (exit 2 with the reason), never `exit 0`.
- **With another Python LSP plugin:** the gate doesn't depend on the LSP.

## 9. Language server

`.lsp.json`:

```json
{
  "basedpyright": {
    "command": "${CLAUDE_PLUGIN_ROOT}/scripts/langserver.sh",
    "args": ["--stdio"],
    "extensionToLanguage": { ".py": "python", ".pyi": "python", ".pyw": "python" },
    "workspaceFolder": "${CLAUDE_PROJECT_DIR}",
    "startupTimeout": 30000,
    "shutdownTimeout": 5000,
    "restartOnCrash": true,
    "maxRestarts": 3,
    "initializationOptions": { "disablePullDiagnostics": true },
    "settings": {
      "basedpyright": {
        "disableTaggedHints": true,
        "analysis": {
          "baselineMode": "discard",
          "diagnosticMode": "openFilesOnly",
          "autoImportCompletions": true,
          "inlayHints": { "variableTypes": false, "callArgumentNames": false, "functionReturnTypes": false, "genericTypes": false }
        }
      }
    }
  }
}
```

- **Launcher** `scripts/langserver.sh`: sources `lib/resolve.sh`, resolves
  `basedpyright-langserver` for `$CLAUDE_PROJECT_DIR` (§8.5), `exec`s it with
  the given args, and never writes to stdout. On failure it prints the install
  command to stderr and exits non-zero (visible in `/plugin` Errors and
  `claude --debug`).
- **`baselineMode: discard`** stops the LS from rewriting the committed
  baseline while Claude edits. **`disableTaggedHints`** removes the
  "not accessed" noise that Claude Code currently pushes into context (#95507).
  Inlay hints are off because Claude Code has no use for them.
- Type-checking behavior (mode, rules, includes) comes **only** from the
  project's config file, so the LSP and the CLI agree. `.ipynb` is not mapped:
  Claude Code's LSP support for notebooks is unverified; the CLI gate covers
  notebooks.
- `restartOnCrash`/`shutdownTimeout` need Claude Code ≥ 2.1.205; the
  compatibility section states it, because older versions skip the server
  entirely.
- **What Claude actually gets from the server.** basedpyright's LS offers
  completion, auto-import, signature help, hover, definitions, references,
  rename, symbols, call hierarchy, organize imports, and quick fixes (such as
  adding `@override`). Claude Code's `LSP` tool (2.1.278) exposes nine
  operations: `goToDefinition`, `findReferences`, `hover`, `documentSymbol`,
  `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`,
  `incomingCalls`, and `outgoingCalls`, plus pushed diagnostics. **No rename,
  code actions, completion, signature help, or organize imports.** The skill
  therefore teaches:
  - **Renames:** `findReferences`, then edits, then a project-scope check. A
    text search alone misses re-exports and attribute access.
  - **Fixes the LS would offer as quick fixes** (`@override`, removing an
    unnecessary cast, `reportSelfClsDefault`): applied by hand, from the
    fix-playbook.
  - **Import ordering:** Ruff owns it, never basedpyright's organize imports,
    as the basedpyright docs themselves recommend.
  - **Impact analysis before changing a signature:** `incomingCalls` or
    `findReferences` first, so the Stop gate isn't the first to find the
    breakage.
- **How the `settings` actually reach basedpyright** (LSP 3.18 §workspace
  configuration, and `languageServerBase.ts` read 2026-09-19). There are two
  channels: the server can request settings with `workspace/configuration`
  (server → client), or the client can push them with
  `workspace/didChangeConfiguration` (client → server). basedpyright's
  `getConfiguration()` **only uses the pushed settings when the client does
  not advertise `workspace.configuration`**. If the client advertises it, the
  server asks, and whatever the client answers wins. Claude Code documents
  that `.lsp.json` `settings` are sent through `didChangeConfiguration`. So
  `baselineMode: "discard"` and `disableTaggedHints` take effect only if
  Claude Code either doesn't advertise `workspace.configuration` or answers
  those requests from the same `settings`. This is the highest-risk
  unverified assumption in the LSP part (§14, item 2). The design doesn't
  depend on it for safety:
  - **Defense in depth for the baseline:** the gate already fingerprints
    `baseline.json` every turn. A change not made by
    `basedpyright-quality baseline prune` is reported to the user at Stop
    ("the baseline changed outside the gate; review before committing"), so
    an LS that ignored `discard` and rewrote it on save is caught.
  - **If Claude Code answers `workspace/configuration` with nothing,** and no
    workaround exists, the plugin documents that hint suppression doesn't
    apply. The limitation is the hint noise of #95507, not correctness,
    because the gate never uses LSP diagnostics.
- **`initializationOptions.disablePullDiagnostics: true`** — not on the docs
  page (`/dev/` and 1.40.1 are identical, diffed 2026-09-19), but in the VS Code
  manifest and in `languageServerBase.ts`: the server switches to **pull**
  diagnostics when the client advertises
  `textDocument.diagnostic.dynamicRegistration`, unless this
  **initialization option** (not a setting) is `true`. Claude Code's docs
  describe diagnostics being pushed after edits; forcing push mode removes the
  dependence on which capabilities Claude Code advertises. Whether it
  advertises pull support, and whether it advertises file watching (the root of
  the phantom-import issue #85225), is to be read from `claude --debug` LSP
  logs (§14). The other manifest-only key, `importStrategy`, is VS Code
  extension behavior; our launcher is its equivalent (`fromEnvironment`).
- **LS commands** (docs: usage/commands): *Organize Imports*, *Restart
  Server* (clears cached types after installing stubs or libraries), and
  *Write new errors to baseline*. Claude Code's LSP tool can't execute
  workspace commands, so:
  - there is no in-session restart. After Claude installs a dependency or
    stubs, stale LSP diagnostics are expected; the skill tells Claude to trust
    the CLI and suggests `/reload-plugins` (whether it restarts the server is to
    be proven live, §14);
  - the docs state the LS **updates the baseline on save** when errors were
    only removed. `baselineMode: "discard"` in `.lsp.json` is what stops that,
    whether or not Claude Code sends `didSave`.
- **Settings checked against the 1.40.1 language-server page:**
  `disableTaggedHints` is a top-level `basedpyright.*` key and `baselineMode`
  is under `basedpyright.analysis.*`, as in the block above. None of the
  discouraged keys (`diagnosticSeverityOverrides`, `include`, `exclude`,
  `ignore`, `extraPaths`, `typeCheckingMode`, `stubPath`, `typeshedPaths`,
  `useLibraryCodeForTypes`, `baselineFile`) is set: the docs recommend the
  config file so the LS and the CLI behave the same, which is this plugin's
  parity principle. `python.*` keys other than `pythonPath`/`venvPath` are not
  read by basedpyright; the skill says so for users coming from Pylance.
- **Two limits of a static `.lsp.json`**, because `settings` accept no
  placeholders:
  1. **Config in a subdirectory (monorepo).** The LS searches for the config
     from the workspace root; `basedpyright.analysis.configFilePath` would fix
     it but can't be set per project. The CLI gate is unaffected (it runs from
     each config's own root). `doctor` detects configs below the workspace root
     and tells the user the LS will use defaults there.
  2. **Interpreter outside `./.venv`** (Poetry's central venvs, conda). The LS
     only auto-detects `./.venv`; `python.pythonPath` can't be set per project.
     The gate passes `--pythonpath`; for the LS, `doctor` recommends a `.venv`
     symlink to the environment (for example
     `ln -s "$(poetry env info -p)" .venv`), which is the documented
     basedpyright default rather than the discouraged `venvPath`.
- `autoImportCompletions` only affects completions; import-suggestion code
  actions come from `reportUndefinedVariable` (docs note). Irrelevant to
  Claude, kept at the default.
- **Conflicts:** `assess`/`doctor` list other enabled plugins claiming `.py`
  and explain that the first registered wins; the user decides which to
  disable. Nothing is changed automatically.

## 10. The `scripts/basedpyright-quality` runner

A Bash CLI on the Bash tool's `PATH` while the plugin is enabled. It works in
subagents, `-p`, and cloud sessions where the LSP doesn't.

| Command | Does |
| --- | --- |
| `check [paths…] [--project DIR]` | Resolve, sanitize, run with `--outputjson --baselinemode discard`, print §8.7 format; exit mirrors basedpyright's taxonomy |
| `changed [--since REF]` | Project-scope run, output filtered to files changed vs `REF` (default `HEAD`) plus labeled cross-file fallout |
| `explain <rule>` | Mode defaults, basedpyright-only flag, docs URL, and the fix-playbook entry, from the skill's references (offline) |
| `baseline status` | Entry count by rule/file; stale or not; since when |
| `baseline prune` | `--baselinemode auto`, then verify the count only decreased; restore and fail otherwise |
| `report [--root DIR]` | The full last result stored by the gate or the runner |
| `doctor` | Resolver trace, versions (installed vs pinned vs floor), config found, interpreter used, conflicting LSP plugins, CI env vars present, both-tables error, timing of a full run |

No `write-baseline` command, on purpose.

## 11. The `basedpyright-debt-fixer` agent

- **Tools:** `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`. Plugin subagents
  ignore `hooks`/`permissionMode`, so the constraints are written into the
  instructions and enforced by the gate if it is installed.
- **Input:** one slice (a rule, or a rule within a package) and the baseline
  entries or diagnostics for it.
- **Loop:** run `basedpyright-quality check` on the slice, fix by the
  fix-playbook, re-run the **project** check, and stop when the slice is clean
  or when a fix needs a product decision.
- **Output:** files changed, diagnostics before/after, anything escalated, the
  exact verification command and its result. It never touches config,
  suppressions, or the baseline (the parent prunes).

## 12. Non-goals and failure modes (→ README "What it does not do" / "Limitations")

**Non-goals:** installing basedpyright; replacing Ruff (formatting and linting
stay with Ruff); supporting mypy plugins (Django, Pydantic, SQLAlchemy) that
basedpyright cannot; checking the whole repository on every edit; writing or
growing baselines; choosing a type-checking mode for the user; multiplexing
several language servers into one.

**Memory.** Claude Code's own docs name pyright among the language servers
that "can consume significant memory on large projects" (discover-plugins,
code intelligence issues). On Linux and WSL, when the user sets
`CLAUDE_CODE_TOOL_MEMORY_LIMIT` (≥ 2.1.233), Bash commands (the runner) are
always capped, and language servers (`lsp`), hook commands (`hooks`), and
plugin commands (`plugin`) are capped too unless excluded with
`CLAUDE_CODE_TOOL_MEMORY_CGROUP_EXCLUDE`; which kinds are capped by default is
decided server-side and can change. Hooks that can block an action are
exempt. The kernel kills an over-limit process "and nothing in its result
names the cap" (tools-reference, memory limit). The gate and runner therefore
treat death by signal as its own outcome (§8.3), `doctor` prints both
variables, and the README tells large-repo users on Linux to exclude `lsp`
or raise the limit.

**Failure modes, each with a defined behavior:** binary missing (fail closed,
install command); version below floor (preflight refuses; runtime fail closed);
broken or both-tables config (exit 3 path; guard stops Claude editing it); a
file excluded by config (reported as skipped, not clean); huge project (the
measured timeout, `--threads`, the `session-delta` degradation documented);
non-`.venv` interpreter (`--pythonpath` from assess); Windows (`Scripts\`,
Git Bash only, like the siblings); Cowork (refuse); LSP conflict (report);
the LSP not running (cloud/subagents; the runner and gate still work); stale
baseline (prune path); files changed outside Claude's tools or by Bash without
`bashEditDiff` (not seen until Stop's project run, which still covers them
under `ci-parity`).

## 13. Verification

**Behavioral suites** (run under `bash` and `/bin/bash` 3.2 by `npm test`,
like the siblings):

- `test-resolve.sh`: every layout fixture (uv, `.venv`, `venv`, Windows-style
  `Scripts`, PATH, override, missing), version floor, pinned-vs-found warning.
- `test-langserver.sh`: stdout is protocol-clean (a fake server echo test);
  failure path writes only stderr.
- `test-runner.sh`: exit taxonomy 0–4 with fixtures (clean, errors,
  broken config, both tables, bad args), the `filesAnalyzed: 0` exclusion
  trap, stdout pollution before `{`, CI env sanitization (run with
  `GITHUB_ACTIONS=true` and assert identical results), baseline prune
  shrink-only (and restore on growth), output budget, config resolution from
  a foreign CWD (must match the root run), an excluded file reached through a
  symlinked path (must stay excluded), a path starting with `-`, an
  `information`-only result (must pass, as in CI), a fake binary that kills itself with SIGKILL (must report the signal outcome, not a crash or a pass), a decoy
  `basedpyrightconfig.json` (must be ignored as a root marker).
- `test-gate.sh`: every event with realistic full payloads (`cwd`,
  `transcript_path`, `session_id`); the cross-file breakage case
  (edit `a.py`, error in `b.py` must block at Stop); guard deny matrix
  (every suppression spelling, config, baseline, settings, Bash constructs);
  `session-delta` multiset diff with line shifts; max-blocks; timeouts via a
  slow fake binary; adversarial large payloads timed under `/bin/bash`
  (plugin-delivery rule); payloads passed via stdin, never argv.
- `test-manage.sh`: install/verify/uninstall per scope, idempotency, backup
  and restore on failed self-test, refusal paths (Cowork, second scope,
  `disableAllHooks`, failing project under `ci-parity`).
- A drift test: the resolver inlined in the gate handler equals
  `scripts/lib/resolve.sh` behavior on the fixture matrix.
- **Knowledge drift gate** (`test-references.sh`): extracts every `report*`
  name from the skill's references, writes them all into a scratch
  `pyrightconfig.json`, and runs the pinned basedpyright. The binary rejects
  unknown keys (`Config contains unrecognized setting "…"`, exit 3), so a
  renamed or removed rule fails the suite offline. The reverse check (every
  rule the binary accepts appears in `rules.md`) uses the rule list from the
  pinned version's `pyrightconfig.schema.json`, vendored under
  `tests/fixtures/` with its source tag. Written because the docs themselves
  drift: pages for `v1.21.1` still list `reportShadowedImports` (removed) and
  lack five rules added since, and a first draft of this blueprint said
  `reportPossiblyUnbound` where the real name is
  `reportPossiblyUnboundVariable`; both are caught by this gate [observed].

**Evals** (`claude plugin eval`, README table updated in the same branch):

| Case | Checks |
| --- | --- |
| `fix-type-error` | Fixes a `reportOptionalMemberAccess` by narrowing; no suppression, no `Any` (regex `not_contains`) |
| `type-ignore-misconception` | User asks to "just add `# type: ignore`": explains it's ignored by default and proposes a fix or `# pyright: ignore[rule]` as the user's decision |
| `cross-file-check` | After changing a signature, runs a project-scope check, not a file-only one (`tool_used` on the runner/CLI without file args) |
| `baseline-stale` | After fixing a baselined error, prunes via the runner, never `--writebaseline` |
| `hook-request-gated` | Asks scope and policy; writes no settings before the choice |
| `adopt-from-mypy` | Assesses first, recommends with counts, maps `# type: ignore[code]` correctly |
| `ignores-mypy-project` | Negative trigger: mypy-only project, skill doesn't claim it |
| `ignores-concept-question` | Negative trigger: generic typing question unrelated to basedpyright |
| `paths-activation` | Editing a `.py` file loads `typing` (`tool_used: Skill`); a Markdown-only task loads none of the four reference skills |
| `no-self-install` | "Set up type checking hooks" with the plugin enabled: Claude points to `/basedpyright-quality:gate` and writes no settings (user-only skill not invoked by Claude) |
| `check-before-done` | After a multi-file change, Claude runs `check` (project scope) before its final message |

## 14. Things to prove live before calling it done

1. `PostToolBatch` ordering relative to other hooks' `PostToolUse` (the
   `ruff-quality` rewrite race), and its minimum Claude Code version for
   `preflight`.
2. `settings` delivery (highest risk in the LSP part): whether Claude Code
   advertises `workspace.configuration`, and if so what it answers to
   basedpyright's `workspace/configuration` requests for the `basedpyright`
   and `basedpyright.analysis` sections. Proven end to end with a fixture: a
   file with an unused symbol (the tagged hint must not reach Claude) and a
   baselined error that gets fixed and saved (`baseline.json` must not
   change).
3. Whether `${CLAUDE_PROJECT_DIR}` in `workspaceFolder` behaves in
   multi-root/`/add-dir` sessions.
4. `additionalContext` from `PostToolBatch` reaching Claude in `-p` runs.
5. basedpyright `.ipynb` CLI diagnostics carrying `cell` ids through our
   formatter.
6. The docs describe `command` as "the LSP binary to execute (must be in
   PATH)", and they also resolve `${CLAUDE_PLUGIN_ROOT}` in `command`. Prove
   that an absolute launcher path starts, and that a failing launcher shows up
   in the `/plugin` Errors tab with its stderr message.
7. From `claude --debug` LSP logs: the client capabilities Claude Code sends
   in `initialize` (pull diagnostics, `didChangeWatchedFiles`, `didSave`),
   and that diagnostics still arrive with `disablePullDiagnostics: true`.
8. Whether `/reload-plugins` restarts the basedpyright server (the only way
   to clear its caches after a dependency install, since the LSP tool can't
   run *Restart Server*).

## 15. Repository-wide changes this plugin needs

| Change | Why |
| --- | --- |
| `ci.yml`: install basedpyright from `tests/requirements-basedpyright.txt` (exact `==` pin, Dependabot-managed; the exact install command is verified at build time); `npm run validate` checks every workflow installs from that file | The suites need the real binary, like `RUFF_VERSION` |
| `scripts/lib/plugins.mjs`: README template and validator: document **LSP servers** and **executables** in the "MCP, permissions, and network" section (or a new section) | First plugin shipping `.lsp.json` and `bin/`; the README contract must describe them |
| `CLAUDE.md`: `npm run check` needs basedpyright on `PATH` | Same as Ruff/ShellCheck |
| Root README catalog row; `marketplace.json` via `npm run generate` | Standard |
| `docs/maintenance/pending-debt.md`: record the flagged upstream misalignments (the better-defaults page says `venvPath` is not a config-file setting, but 1.40.1 accepts it there; `--baselinemode` absent from `--help`; `--level` differs under CI detection; `--outputjson` stdout pollution) with evidence, to re-check each release | "Flag misalignment, never accommodate" |
| Skill references cite only `https://docs.basedpyright.com/latest/` or the `v<version>` tag they were verified against. Versioned pages like `/v1.21.1/` (2024-11-13) are **outdated**: that language-server page lacks `baselineMode`, `configFilePath`, `fileEnumerationTimeout`, `autoFormatStrings`, `useTypingExtensions`, `callArgumentNamesMatching`, and `baselineFile`, and says `inlayHints.genericTypes` defaults to `false` (it is `true` in 1.40.1) | Old versioned pages rank high in search results |
| Source policy for the skills: third-party articles are leads, never sources. Example checked 2026-09-19: aifreeapi.com's "Claude Code LSP" guide (2025-12-30, Claude Code 2.0.74) tells users to set `ENABLE_LSP_TOOL=1`, a variable absent from the current env-var reference and the changelog. It lists 5 LSP operations including a `getDiagnostics` operation that the tool doesn't have (the 2.1.278 tool has 9, and diagnostics are pushed). Its "900x faster" figure has no measurement behind it | Nine-month-old blog posts outrank the docs in search; the skill must not repeat them |
| Docs URL policy extended: never cite `/dev/` pages (the unreleased `main` branch) as current behavior; use them only to anticipate the next release, labeled as such | `/dev/` and `/v1.21.1/` both rank in search results; neither describes the pinned version |
| Pin basedpyright for CI in a Dependabot-managed file (`tests/requirements-basedpyright.txt`, pip ecosystem) instead of a bare env var. Each release (about weekly, the same day as pyright per the upstream policy page) opens a PR that runs the suites and the knowledge drift gate against the new binary | Turns release cadence into a gate: a renamed rule, a changed exit code, or a new flag behavior fails CI with the exact reference to update. Pinning basedpyright also pins its pyright base (`--version` prints both) |
| Upstream issue drafts (maintainer decides whether to file) for the three basedpyright behaviors above | They're bugs or doc gaps, not ours to work around silently |

## 16. Delivery plan

1. **0.1.0 (one PR):** all three skills, the LSP + launcher, the runner, the
   gate with `ci-parity` and `session-delta`, `batch`/`edit`/`stop-only`
   feedback, the suites, the evals, README/CHANGELOG, repo-wide changes.
   `/plugin-release-review basedpyright-quality` on the first complete draft
   and after each change; `/pr-delivery` to finish.
2. **0.2.0:** `basedpyright-debt-fixer` agent, if D3 defers it; fix-playbook
   expansion driven by eval failures.

Estimated size, by the siblings: ~2,500 lines of Bash (handler, manage,
runner, resolver, assess), ~1,800 lines of tests, ~3,000 lines of reference
Markdown.

## 17. Decisions for the maintainer

| # | Decision | Recommendation |
| --- | --- | --- |
| D1 | **Resolved by the maintainer (2026-09-19):** block after every edit of a Python file, on that file, with a focus lock until it is clean, plus the Stop/SubagentStop project check. `batch` and `stop-only` remain install options, not defaults | See §7A |
| D2 | **Resolved by the maintainer (2026-09-19): `.lsp.json` at this plugin's root.** Consequence, stated in the README and reported by the audit: with `pyright-lsp`, `ty`, or another basedpyright plugin enabled, only the first registered `.py` server starts; the gate and skills don't depend on the LSP either way | §9 |
| D5b | **Resolved (2026-09-19): no.** The plugin ships exactly two skills, `basedpyright` and `basedpyright-hooks` | §0 |
| D3 | **Decided (design ownership, 2026-09-19): `basedpyright-debt-fixer` ships in 0.1.0.** Evidence: a real project (rich) reports 574 errors and 4,506 warnings in `recommended`; working that in the main thread floods the context the fix playbook and conversation need. A subagent starts with a fresh context, preloads the knowledge skill (`skills: [basedpyright]`), works one rule or package slice through the CLI runner (subagents lose the LSP tool, #84125), and returns a verified summary. Its edits are still gated: settings hooks run inside subagents, and the gate registers `SubagentStop`. The knowledge skill delegates to it when a requested cleanup spans more than one package or ~50 diagnostics. Kept honest by an eval pair (same backlog fixture with and without the agent); if the agent doesn't win, it's cut before release | §11 |
| D4 | **Decided (design ownership, 2026-09-19): Stop scope `auto` by default.** The gate is universal and can be wired at user scope, where no project can be pre-checked; `auto` blocks on edited files plus new breakage anywhere in their project (tested) and never on existing debt. `project` (CI parity) and `files` stay install options the audit offers when they fit | §7B |
| D5 | Name: `basedpyright-quality` (house pattern) | Keep |
| D6 | `uvx` fallback in the resolver | Off by default, opt-in via env var, pinned version only |

## 18. Risks

| Risk | Mitigation |
| --- | --- |
| basedpyright ships weekly; flags (`--baselinemode` is experimental) can change | Version floor + `doctor`; the suites run against the pinned CI version; a Dependabot-style pin bump is a normal PR |
| Project-scope Stop runs are slow on large repos | Measured by `assess`; `--threads`; per-root runs; explicit timeout; `session-delta` degradation documented |
| Claude Code LSP defects (#93321, #85225, #95507, #84125) | The LSP is never the gate; the skill tells Claude to trust the CLI |
| Guard heuristics can't see every Bash trick | Stop's project run and config fingerprints still catch the result; limitation documented, same as `ruff-quality` |
| Rule overlap with Ruff produces double findings | `ruff-interplay.md` ownership table; the user decides |

## References

Verdicts for every surveyed plugin, skill, hook, and the maintainer's own prior art are in §3 and §3.1; the documentation and repositories below are the sources those verdicts and the design rest on.


- basedpyright docs: https://docs.basedpyright.com/latest/ (configuration/config-files,
  configuration/comments, configuration/language-server-settings,
  configuration/command-line, benefits-over-pyright/*, usage/import-resolution,
  usage/mypy-comparison, installation/*)
- basedpyright releases: https://github.com/DetachHead/basedpyright/releases (1.33.0–1.40.1)
- PyPI: https://pypi.org/project/basedpyright/
- Schema: https://github.com/DetachHead/basedpyright/blob/v1.40.1/packages/vscode-pyright/schemas/pyrightconfig.schema.json
- prek mirror: https://github.com/DetachHead/basedpyright-prek-mirror
- Claude Code: https://code.claude.com/docs/en/plugins-reference ,
  https://code.claude.com/docs/en/hooks , https://code.claude.com/docs/en/discover-plugins ,
  https://code.claude.com/docs/en/skills , https://code.claude.com/docs/en/plugin-evals ,
  https://code.claude.com/docs/en/changelog
- Official marketplace: https://github.com/anthropics/claude-plugins-official (`pyright-lsp`)
- Claude Code issues: #93321, #85225, #95507, #84125, #76870, #58365, #78604
