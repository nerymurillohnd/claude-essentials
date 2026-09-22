# Migration log — Python toolchain and governance refactor

Evidence for every phase gate of `~/.claude/plans/consolidated-governance-refactor.md`
Part B. One heading per gate; each box is checked only with output from the current
tree. This file is committed with step 7 and re-read by `repo-auditor` at step 12.

## Gate 0 — pre-flight (2026-09-21)

- [x] branch `refactor/python-toolchain-and-governance` created from `13d345c`
- [x] first commit `a19bc6d` holds the demolition and the carried trees; tree clean; not pushed
- [x] parent check after `git fetch --prune origin`:

  ```text
  HEAD~1=13d345cd4e956578db136f139d34a4813b32beae origin/main=13d345cd4e956578db136f139d34a4813b32beae
  PARENT_OK
  porcelain=0
  ```

- [x] tool versions:

  ```text
  uv: uv 0.12.17 (635500036 2026-09-18 aarch64-apple-darwin)
  make: GNU Make 3.81
  claude: 2.1.278 (Claude Code)
  shellcheck: version: 0.11.0
  shfmt: 3.14.1
  jq: jq-1.8.2
  ```

- [x] `uv python list --only-installed | grep 3.14`: `cpython-3.14.7-macos-aarch64-none` present
- [x] `.claude/hooks/lib/checklist.sh abort "superseded by the toolchain refactor"` → see below
- [x] `.claude/state/audits/` and `.claude/.cache/hooks/bash-stamp-*` cleared (`audits=0 stamps=0`)
- [x] `sha256sum schemas/github/*.json` (compared again at gate 9 after the move):

  ```text
  0988613c0ace111998e94d1883ad1a6110fbd8525385e1bff88ccb102e851e60  schemas/github/issue-config.schema.json
  31ed735665dfe33739dc41a2342871d32199154ea8a1dd7411ca6303a0e868c5  schemas/github/issue-forms.schema.json
  ```

  ```text
  $ .claude/hooks/lib/checklist.sh abort "superseded by the toolchain refactor"
  aborted
  abort rc=0                       # .claude/state/checklists/.active is gone
  ```

## Gate 1 — `evals/**` and tests exempt (2026-09-21)

- [x] `git ls-files 'scripts/*.mjs' 'scripts/**/*.mjs' | wc -l` is 0 (in `a19bc6d`)
- [x] no `evals/results/` file tracked; `git check-ignore -v plugins/block-no-verify/evals/results/x.json` → `.gitignore:57:**/evals/results/`
- [x] `plugin_path_is_exempt` table, run under `bash` (5.x) and `/bin/bash` (3.2):

  ```text
  exempt  evals/a/b.md          exempt  test-x.sh           exempt  scripts/test-hooks.sh
  exempt  tests/a.sh            exempt  skills/x/tests/a.sh exempt  LICENSE.md
  exempt  docs/a.md             exempt  README.md
  RUNTIME evalsx/b.md           RUNTIME skills/x/evals/y    RUNTIME test-x/y.sh
  RUNTIME tests                 RUNTIME hooks/hooks.json    RUNTIME LICENSE.x/y
  RUNTIME skills/test-a.sh.bak  RUNTIME testsuite/a
  /bin/bash: exempt / runtime / exempt
  ```

  `shellcheck` and `shfmt -d` on `plugin-paths.sh`: clean (`SHELL_OK`).
- [x] `git diff origin/main -- docs/decisions | grep -E '^-[^-]' | wc -l` → 0 (ADR-0003 amendment appended only)
- [x] `git ls-files 'plugins/*/evals/*' | wc -l` → 105 before this step (29 + 18 + 19 + 19 + 20, incl. the five `.gitignore`); decision: the five per-suite `evals/.gitignore` are removed and the root `.gitignore` keeps the single rule `**/evals/results/` (plan Part F)
- [x] `grep -c '|||||||' docs/maintenance/resolved-debt.md` → 0
- [x] the five `evals/README.md` "CI policy" sections rewritten to D2 (runtime classification selects; `evals/**` never does)
- [ ] `git status --porcelain` empty after this step's commit (filled below)

## Gate 2 — Python scaffold, `pyproject.toml`, `Makefile`, `.vscode/` (2026-09-21)

### Decisions taken beyond the plan

- **`exclude-newer = "4 days"` accepted by uv 0.12.17.** No absolute-timestamp fallback was
  needed. The lock records the span, exactly as upstream basedpyright does:

  ```text
  $ grep -n 'exclude-newer' uv.lock
  6:exclude-newer = "0001-01-01T00:00:00Z" # This has no effect and is included for backwards compatibility when using relative exclude-newer values.
  7:exclude-newer-span = "P4D"
  ```

- **`shellcheck-py` and `shfmt-py` adopted (§A5 condition met).** Installed into a throwaway
  venv and the bundled binaries executed; both equal the maintainer's pinned local versions,
  so they join the dev group and ShellCheck/shfmt no longer need Homebrew in CI:

  ```text
  $ shellcheck --version | sed -n 2p          # local, Homebrew
  version: 0.11.0
  $ shfmt --version
  3.14.1
  $ uv pip install shellcheck-py shfmt-py     # scratch venv
   + shellcheck-py==0.11.0.1
   + shfmt-py==4.2.0
  $ probe-venv/bin/shellcheck --version | sed -n 2p
  version: 0.11.0
  $ probe-venv/bin/shfmt --version
  v3.14.1
  ```

- **Unpinned dev dependencies resolved under the cooldown, then written back as exact pins**
  so a Dependabot bump shows in the manifest: `actionlint-py==1.7.12.24`,
  `jsonschema==4.26.0`, `pytest==9.1.1`,
  `pytest-github-actions-annotate-failures==0.4.2`, `pyyaml==6.0.3`,
  `types-pyyaml==6.0.12.20260906`, `zizmor==1.30.1`.

- **`PY_FILES` deviates from §A7** and reads
  `git ls-files --cached --others --exclude-standard -- 'scripts/*.py'` instead of
  `git ls-files -- '*.py'`. Reason: a module written but not yet staged would otherwise skip
  `make lint` entirely, which is exactly when a lint error is cheapest to fix. `--others
  --exclude-standard` adds untracked, non-ignored files; the `scripts/*.py` pathspec keeps
  `plugins/**/*.py` out until Follow-up PR #1 adds it with its own floor.

- **Not-yet-ported recipe lines are `#`-prefixed make comments at column 0**, each carrying
  `# ported at step N`, rather than stubs that exit 1. A column-0 comment inside a rule is
  ignored by GNU Make 3.81 without ending the recipe (verified with `make -n`), it is not
  echoed, and a later step uncomments one character. Stubs that exit 1 would make
  `make check` unusable for the whole migration.

- **`subprocess` under the Ruff floor (`S` selected, zero suppressions).** Measured, not
  assumed: `S607` demands a literal absolute executable path in `argv`, and `S603` demands
  that *every* element of `argv` be a literal — a `Final` constant, a `shutil.which` result
  or a `*args` splat all trip it. Evidence:

  ```text
  subprocess.run(["git", "status"], ...)                      -> S607
  subprocess.run([GIT_FINAL_CONST, "rev-parse", ...], ...)    -> S603
  subprocess.run(["/usr/bin/git", "ls-files", *args], ...)    -> S603
  subprocess.run(["/usr/bin/git", "ls-files", "-z"],
                 executable=shutil.which("git"), ...)         -> clean
  ```

  Resolution, with no rule ignored and no `noqa`: every call spells its full command out as
  string literals with an absolute `argv[0]`, and the binary actually executed is the one
  resolved from `PATH` and passed through `subprocess`'s documented `executable=` parameter.
  `git` never reads `argv[0]`. The consequence is a design constraint for every later step:
  **a command line can never be assembled at runtime**. `tracked_files()` therefore runs a
  literal `git ls-files -z` and filters the result in Python with `fnmatch.fnmatchcase`,
  whose `*` crosses `/` the same way a default git pathspec does (pinned by a test).
  Ruff's own documentation calls `S603` "prone to false positives"; if the maintainer
  prefers, the alternative is an explicit, recorded policy exception, which this step did
  not take.

- **`TRY003` shaped the exception hierarchy.** A raise site may not carry a long message, so
  `CommandFailedError` holds the command line in a `ClassVar` and the subclasses
  (`GitRevParseFailedError`, `GitLsFilesFailedError`) each name their own command. Raise
  sites pass only the detail. This is what the rule asks for, not a workaround.

- **`Any` is converted once, in one place.** `json.loads` is annotated `-> Any`, which
  `reportAny` rejects. `scripts/common/plugins.py` binds it to a
  `Callable[[str], object]` alias, so `load_json` returns `object` and no caller ever
  handles an `Any`. Narrowing a JSON object uses a `TypeIs[Mapping[object, object]]` guard
  whose body never touches the narrowed value — `isinstance(value, dict)` alone yields
  `dict[Unknown, Unknown]` and trips `reportUnknownVariableType`.

- **`.vscode/settings.json`, `tasks.json` and `launch.json` were written in the canonical
  JSON form** (`json.dumps(obj, indent=2, ensure_ascii=False) + "\n"`) so step 6's
  `json_files.py` finds zero churn in files this step authored. The cost is the loss of the
  blank-line grouping the §A16 block uses for readability; the comments were already
  impossible, since these are strict JSON.

- **`.vscode/settings.json` `yaml.schemas` keeps the §A16 target paths** (`.github/schemas/…`).
  Those files live under `schemas/github/` until step 9 moves them, so the two YAML schema
  associations resolve to nothing until that step. Left as written on purpose.

- **"eval this plugin" passes the union of the suites' tool grants**
  (`--allow-tools Bash Write Edit WebFetch`): four suites document `Bash Write Edit` and
  `agent-self-knowledge` documents `Bash WebFetch`. A case still only receives what its own
  `allowed_tools` lists, so the union does not widen any case.

### Checklist

- [x] `uv sync --locked` exit 0; `uv lock --check` exit 0; `.venv/bin/python --version` equals
  the `.python-version` line

  ```text
  $ uv sync --locked
  Resolved 23 packages in 15ms
  Checked 21 packages in 5ms
  exit=0
  $ uv lock --check
  Resolved 23 packages in 3ms
  exit=0
  $ cat .python-version
  3.14
  $ .venv/bin/python --version
  Python 3.14.7
  ```

- [x] `ls ruff.toml .ruff.toml pyrightconfig.json` reports all three absent

  ```text
  $ ls ruff.toml .ruff.toml pyrightconfig.json
  ls: .ruff.toml: No such file or directory
  ls: pyrightconfig.json: No such file or directory
  ls: ruff.toml: No such file or directory
  ```

- [x] resolved Ruff settings, and the before/after equivalence proof

  ```text
  $ .venv/bin/ruff check --show-settings scripts/__init__.py | grep -nE 'line_length|target_version|required_version|respect_gitignore' | grep -v per_file
  84:file_resolver.respect_gitignore = true
  1571:linter.unresolved_target_version = 3.14
  1594:linter.line_length = 100
  1744:linter.pycodestyle.max_line_length = 100
  1770:formatter.unresolved_target_version = 3.14
  1792:analyze.target_version = 3.14
  ```

  `--show-settings` prints `target_version` as `3.14`, not `py314`, and does **not** print
  `required-version` at all. That key is still enforced; proved separately with a config that
  cannot be satisfied:

  ```text
  $ .venv/bin/ruff --version
  ruff 0.16.8
  $ printf 'required-version = ">=99.0.0"\n' > /tmp/reqver/ruff.toml
  $ .venv/bin/ruff check --config /tmp/reqver/ruff.toml /tmp/reqver/a.py
  ruff failed
    Cause: Failed to load configuration `/tmp/reqver/ruff.toml`
    Cause: Required version `>=99.0.0` does not match the running version `0.16.8`
  ```

  Equivalence: `ruff check --show-settings scripts/__init__.py` captured with `ruff.toml`
  still present (it has precedence over `pyproject.toml`) and again after `git rm ruff.toml`.
  1781 lines each; the entire diff is the config path, the three added excludes and
  `per-file-target-version`. `fixable`/`unfixable` and `respect-gitignore` produce no diff
  because the global file already carries them:

  ```diff
  2c2
  < Settings path: ".../claude-essentials/ruff.toml"
  ---
  > Settings path: ".../claude-essentials/pyproject.toml"
  68a69,71
  > 	"**/evals/**",
  > 	"docs/",
  > 	"templates/",
  1569c1572,1578
  < linter.per_file_target_version = {}
  ---
  > linter.per_file_target_version = {
  > 	absolute_matcher = ".../plugins/agent-self-knowledge/**"
  > basename_matcher = "plugins/agent-self-knowledge/**"
  > negated = false
  > data = 3.9
  >
  > }
  1762c1771,1777
  < formatter.per_file_target_version = {}
  ---
  > formatter.per_file_target_version = {
  > 	absolute_matcher = ".../plugins/agent-self-knowledge/**"
  > basename_matcher = "plugins/agent-self-knowledge/**"
  > negated = false
  > data = 3.9
  >
  > }
  ```

- [x] basedpyright runs with no Node on `PATH`

  ```text
  $ env -i PATH=/usr/bin:/bin HOME=$HOME .venv/bin/basedpyright --version
  basedpyright 1.40.1
  based on pyright 1.1.414
  exit=0
  ```

- [x] `--threads` accepted and `.venv` is in the search paths

  ```text
  $ PATH=.venv/bin:$PATH .venv/bin/basedpyright --verbose --threads=4 scripts
  Execution environment: file:///…/claude-essentials/.venv/bin/python
    Search paths:
      /…/claude-essentials/.venv/lib/python3.14/site-packages/basedpyright/dist/typeshed-fallback/stdlib
      /…/claude-essentials/.venv/lib/python3.14/site-packages/basedpyright/dist/typeshed-fallback/stubs/...
      /…/claude-essentials/.venv/lib/python3.14/site-packages
  Found 13 source files
  exit=0
  ```

  Note the argument shape: `--threads` takes an *optional* count, so
  `basedpyright --threads scripts` consumes `scripts` as that count and dies with
  "Unexpected error". Either `--threads=<n> <path>` or `<path> --threads` works. `make types`
  passes no path at all (the config's `include` supplies it), so it is unaffected.

- [x] mini-racer compiles JavaScript under 3.14.7

  ```text
  $ .venv/bin/python -c "import py_mini_racer; print(py_mini_racer.MiniRacer().eval('1+1'))"
  2
  ```

- [x] suppression probes in `scripts/common/_probe.py`, each deleted afterwards

  **Deviation from the gate as written.** `x: int = 1  # type: ignore` does **not** fail
  `make types`: with `enableTypeIgnoreComments = false` the comment is not processed at all,
  so there is nothing to report as unnecessary. What the setting does guarantee is that the
  comment can never silence a real error:

  ```text
  # probe: x: int = 1  # type: ignore
  $ make types
  0 errors, 0 warnings, 0 notes          exit=0

  # probe: x: int = "not an int"  # type: ignore
  $ make types
  _probe.py:3:10 - error: Type "Literal['not an int']" is not assignable to declared type "int"
    "Literal['not an int']" is not assignable to "int" (reportAssignmentType)
  1 error, 0 warnings, 0 notes           exit=2
  ```

  A `pyright`-flavoured ignore *is* reported, by both rules the plan named:

  ```text
  # probe: x: int = 1  # pyright: ignore
  $ make types
  _probe.py:3:15 - error: `pyright: ignore` comment must specify a rule (eg. `# pyright: ignore[ruleName]`) (reportIgnoreCommentWithoutRule)
  _probe.py:3:15 - error: Unnecessary "# type: ignore" comment (reportUnnecessaryTypeIgnoreComment)
  ```

  Conclusion: Q3's grep stays the guard for a bare `# type: ignore`, as the plan's
  contingency anticipated. Rules recorded: `reportIgnoreCommentWithoutRule`,
  `reportUnnecessaryTypeIgnoreComment`, `reportAssignmentType`.

  `Any` probe — three rules fire, two type rules and one lint rule:

  ```text
  # probe: def f() -> Any: return 1
  $ make types
  _probe.py:6:5 - error: Return type is Any (reportAny)
  _probe.py:6:12 - error: Type `Any` is not allowed (reportExplicitAny)
  exit=2
  $ .venv/bin/ruff check --output-format concise scripts/common/_probe.py
  _probe.py:6:12: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `f`
  ```

  ```text
  $ rm -f scripts/common/_probe.py && make types
  0 errors, 0 warnings, 0 notes          exit=0
  ```

- [x] `make help` lists every §A7 target

  ```text
  setup — create/refresh .venv from uv.lock (the only target that calls uv)
  generate — 10 regenerate catalog + issue forms, then fail on diff
  lint — 20 ruff format --check + ruff check (explicit .py list), shell, json, text bytes, actionlint, zizmor
  lint-staged — same checks, only on staged + modified + untracked files (guard-commit)
  types — 30 basedpyright, typeCheckingMode=all + failOnWarnings, venv interpreter, GitHub annotations in CI
  test-fast — 40 in-process tests
  validate — 50 catalog + plugin invariants (M P C S H R B W E G T Q X)
  validate-cli — 60 claude plugin validate --strict on marketplace + every plugin
  test-slow — 70 process-spawning tests + plugin suites under bash and /bin/bash + plugin Python under its floor
  versions — version-bump rules and route vs the latest tags / origin/main
  fix — writer: ruff format, ruff check --fix (safe), shfmt -w, canonical JSON
  fix-file — writer for one file (post-edit hook): make fix-file FILE=path
  clean — prune .claude/.cache/hooks stamps and stale state
  ```

- [x] `make lint types test-fast` exit 0

  ```text
  $ make lint && make types && make test-fast
  13 files already formatted
  All checks passed!
  0 errors, 0 warnings, 0 notes
  21 passed, 6 deselected in 0.03s
  GATE exit=0
  ```

  The full suite, slow markers included: `27 passed in 0.31s`.

- [x] `make -n check` prints the chain in §A7 order

  ```text
  git diff --exit-code -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
  .venv/bin/python -m ruff format --check <13 files>
  .venv/bin/python -m ruff check <13 files>
  PATH=".../.venv/bin:$PATH" .venv/bin/basedpyright --threads
  .venv/bin/python -m pytest -m "not slow and not coverage_matrix"
  .venv/bin/python -m pytest -m slow
  ```

- [x] canonical-JSON churn measured with a one-off snippet (not committed), nothing rewritten

  ```text
  tracked .json files                       : 33
  excluded (schemas/github/**, node_modules): 2
  compared                                  : 31
  differ from canonical form                : 16
    .claude/settings.json
    .github/labels.json
    .mcp.json
    biome.json
    plugins/verify-completion/.claude-plugin/plugin.json
    schemas/claude-code/hooks.schema.json
    schemas/claude-code/lsp.schema.json
    schemas/claude-code/marketplace.schema.json
    schemas/claude-code/mcp.schema.json
    schemas/claude-code/monitors.schema.json
    schemas/claude-code/plugin-manifest.schema.json
    schemas/marketplace.schema.json
    schemas/plugin.schema.json
    templates/plugin-agent-only/.claude-plugin/plugin.json
    templates/plugin-bundle/.claude-plugin/plugin.json
    templates/plugin-skill-only/.claude-plugin/plugin.json
  not parsable as strict JSON               : 1
    tsconfig.json (JSONC: comments; a Node file, deleted in a later step)
  ```

  Only one plugin manifest is in the list, and a whitespace-only manifest change is not a
  version bump (runtime comparison is on parsed JSON, §A5).

- [x] VS Code workspace-scope table. Every key that belongs to an extension was read from the
  installed extension's own `package.json` under `~/.vscode/extensions/`. **No key has
  `application` or `machine` scope, so nothing was removed from `settings.json`.**
  `machine-overridable` is settable in a workspace file by definition; a key with no declared
  scope defaults to `window`.

  | Key | Scope | Owner |
  | --- | --- | --- |
  | `python.defaultInterpreterPath` | machine-overridable | ms-python.python 2026.4.0 |
  | `python.terminal.activateEnvironment` | resource | ms-python.python 2026.4.0 |
  | `python.terminal.activateEnvInCurrentTerminal` | resource | ms-python.python 2026.4.0 |
  | `python.languageServer` | window | ms-python.python 2026.4.0 |
  | `python.testing.pytestEnabled` | resource | ms-python.python 2026.4.0 |
  | `python.testing.unittestEnabled` | resource | ms-python.python 2026.4.0 |
  | `python.testing.pytestArgs` | resource | ms-python.python 2026.4.0 |
  | `python.analysis.typeCheckingMode` | resource | ms-python.vscode-pylance 2026.3.1 |
  | `basedpyright.importStrategy` | resource | detachhead.basedpyright 1.40.1 |
  | `basedpyright.disableOrganizeImports` | resource | detachhead.basedpyright 1.40.1 |
  | `basedpyright.analysis.diagnosticMode` | resource | detachhead.basedpyright 1.40.1 |
  | `ruff.enable` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.nativeServer` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.importStrategy` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.lint.enable` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.showSyntaxErrors` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.organizeImports` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.fixAll` | window | charliermarsh.ruff 2026.82.0 |
  | `ruff.path` | resource | charliermarsh.ruff 2026.82.0 |
  | `ruff.interpreter` | resource | charliermarsh.ruff 2026.82.0 |
  | `ruff.configurationPreference` | resource | charliermarsh.ruff 2026.82.0 |
  | `ruff.format.backend` | resource | charliermarsh.ruff 2026.82.0 |
  | `ruff.codeAction.fixViolation` | resource | charliermarsh.ruff 2026.82.0 |
  | `ruff.codeAction.disableRuleComment` | resource | charliermarsh.ruff 2026.82.0 |
  | `shellcheck.enable` | resource | timonwong.shellcheck 0.40.1 |
  | `shellcheck.run` | resource | timonwong.shellcheck 0.40.1 |
  | `shellcheck.useWorkspaceRootAsCwd` | resource | timonwong.shellcheck 0.40.1 |
  | `shellcheck.executablePath` | machine-overridable | timonwong.shellcheck 0.40.1 |
  | `yaml.schemas` | window (no declared scope) | redhat.vscode-yaml 1.24.0 |
  | `yaml.format.enable` | language-overridable | redhat.vscode-yaml 1.24.0 |
  | `json.schemaDownload.enable` | window (no declared scope) | VS Code built-in json-language-features |
  | `shellformat.path` | **scope unverified** | foxundermoon.shell-format not installed |
  | `shellformat.useEditorConfig` | **scope unverified** | foxundermoon.shell-format not installed |
  | `shellformat.flag` | **scope unverified** | foxundermoon.shell-format not installed |
  | `makefile.configureOnOpen` | **scope unverified** | ms-vscode.makefile-tools not installed |

  Keys removed from `settings.json`: **none**. Core VS Code keys (`editor.*`, `files.*`,
  `search.*`, `terminal.integrated.env.*`, `git.*`, `task.problemMatchers.neverPrompt`) are
  not extension-owned; their scopes are registered in compiled code and could not be read
  statically from the minified bundle, so they are reported as not statically verified
  rather than as verified.

- [ ] in VS Code, the Ruff and basedpyright status items show `.venv/bin/ruff` and
  `.venv/bin/basedpyright` — **not verified**: this step ran headless, with no editor session.

- [x] `git status --short` and `git diff --stat` at the end of the step

  ```text
  $ git status --short
  ## refactor/python-toolchain-and-governance
   M .editorconfig
   M .gitignore
   M .vscode/extensions.json
  D  ruff.toml
  ?? .python-version
  ?? .vscode/launch.json
  ?? .vscode/settings.json
  ?? .vscode/tasks.json
  ?? Makefile
  ?? pyproject.toml
  ?? scripts/
  ?? uv.lock

  $ git diff --stat
   .editorconfig           |  6 ++++++
   .gitignore              |  2 ++
   .vscode/extensions.json | 24 +++++++++++++++++++++++-
   3 files changed, 31 insertions(+), 1 deletion(-)

  $ git diff --cached --stat
   ruff.toml | 161 --------------------------------------------------------------
   1 file changed, 161 deletions(-)
  ```

### Orchestrator verification (2026-09-21)

- Re-ran `make lint && make types && make test-fast` → `0 errors, 0 warnings, 0 notes`, `21 passed, 6 deselected`, `GATE_OK`; `uv lock --check` clean; `ls ruff.toml .ruff.toml pyrightconfig.json` → 3 × "No such file".
- Policy floor asserted with a one-off script: `select` repo ⊇ global (missing: none); `ignore` repo ⊆ global (extra: none); no `per-file-ignores`; basedpyright `all` + `failOnWarnings`, `enableTypeIgnoreComments = false`, `allowedUntypedLibraries = []`, the only `report* = false` is `reportImplicitStringConcatenation`.
- Because `shellcheck-py==0.11.0.1` and `shfmt-py==4.2.0` are in the lock, `.vscode/settings.json` now names `${workspaceFolder}/.venv/bin/shellcheck` and `${workspaceFolder}/.venv/bin/shfmt` (self-sufficient workspace); verified `.venv/bin/shellcheck --version` → 0.11.0 and `.venv/bin/shfmt --version` → v3.14.1.
- Gate 1 closing box: `git status --porcelain` was empty after commit `ed0de71`.
- Open item carried to the maintainer: the VS Code status-bar check (Ruff and basedpyright items showing the `.venv` binaries) needs an editor session.
- **Design constraint found (S603):** under the floor, any `subprocess` call with a non-literal argv element is flagged (`ruff rule S603`: "Prone to false positives"). Probe: literal argv → clean; one dynamic element, tuple, `check_output`, or a resolved `executable=` with a dynamic list → S603. Decision requested from the maintainer before step 3 (see conversation).
- **S603 decision (maintainer, 2026-09-21):** "Ignorar S603 en global y repo". `S603` added to the `ignore` list of `~/.config/ruff/ruff.toml` and mirrored in `[tool.ruff.lint] ignore` of `pyproject.toml` (Q2 stays true: repo ignores ⊆ global ignores). Probe re-run: the four S603 hits disappear; `S607` still fires on a partial executable path. Recorded for ADR-0007.

---

## Gate 3 — `scripts/versioning/` (2026-09-21)

Modules built: `semver.py`, `version_plan.py`, `changelog.py`, `check_versions.py`,
`tag_versions.py`, with `conftest.py` (temporary-repository builders), `test_semver.py`,
`test_version_plan.py`, `test_changelog.py`, `test_changelog_immutable.py`,
`test_check_versions.py`, `test_tag_versions.py`, and `scripts/harness/test_plugin_paths.py`.
`scripts/common/` gained three generic helpers (`git_output`, `git_output_or_none`,
`parse_json`) plus `GitCommandFailedError`, each with tests. The `versions` recipe of the
`Makefile` is uncommented.

### Decisions taken beyond the plan

- **A `V1`–`V6` invariant family for this area (P14).** §A6 has no row for "a bump is owed",
  so the six defects this area catches needed ids of their own. They live in
  `version_plan.VERSIONING_INVARIANTS` with the defect written next to each, and
  `test_versioning_invariants_are_documented` keeps the list honest:
  V1 runtime change without a bump, V2 a version lower than the published one, V3 a first
  release that is not `0.1.0`, V4 a removed directory with no `renames` null entry, V5
  (warning) a removal with no prior deprecation release, V6 a version `claude plugin tag
  --dry-run` refuses. An unparseable `version` reuses **M5** and a manifest with no `version`
  reuses **M4**, rather than minting a seventh id for a defect §A6 already names.

- **"Changed vs base" is defined as one union, deletions included.** `changed_paths(root,
  base)` is `git diff --name-only --no-renames <base>` (base tree against the *working tree*,
  so committed and uncommitted changes both count, and deleted paths are listed) unioned with
  `git ls-files --others --exclude-standard` (untracked files git does not ignore), sorted and
  deduplicated. This is exactly the pair `plugin_runtime_change` in `plugin-paths.sh` already
  ran, so the hook and the gate see the same set.

- **The route's allowlist has a name half and a content half** (maintainer decision,
  2026-09-21; the first draft of this step made it path-only and routed a metadata edit to a
  pull request, which contradicts the root `CLAUDE.md` "main" bullet and §A11 "Direct push:
  exempt plugin files"). Two files are decided by what they contain, because the interesting
  part of each is generated or purely descriptive:

  | File | Direct when | Pull request when |
  | --- | --- | --- |
  | `plugins/<id>/.claude-plugin/plugin.json` | its runtime view (parsed object minus `METADATA_KEYS`) equals the base's, which covers a `description`/`keywords`/`author` edit and a pure reformat | anything Claude acts on moved |
  | `.claude-plugin/marketplace.json` | parsed, it differs from the base in nothing but the generated `plugins` array | `renames` or any other top-level field moved |

  Both comparisons are against the **base ref**, not the plugin's tag: the question is what
  this push adds to `main`, not what the published version contains. The rule lives in one
  place, `version_plan.content_exempt_paths`, which `route` calls and hands to
  `is_direct_push_allowed` as `content_exempt`; the name rule never recomputes it. The module
  docstring carries the wording for step 11 to copy into `docs/contributing/versioning.md`.

- **`version` is the empty string for a removed plugin.** The JSON contract types `version` as
  a string and a removed plugin has no manifest to read. The empty string also makes the
  generic route rule (`version != tagged` ⇒ pull request) fire without a special case, and it
  renders as `<name> removed` in the text report.

- **`tagged` is a version string, not a tag name.** The task defines `required` as "runtime
  changed AND `version == tagged`", which only type-checks if both are versions. The tag name
  is reachable from `plan.plugins[*].tagged` plus the plugin (or predecessor) name, and
  `version_plan.TagRef` carries it internally.

- **No line but the last may contain `bump: `.** `guard-push.sh` searches the *whole* output
  for `bump: none`, so a per-plugin line reading `bump: patch` would let an unbumped push
  through. Per-plugin lines therefore read `needs patch`, `bumped from 0.1.0 (patch)` or
  `deferred`, and `test_no_plugin_line_can_contain_the_label_prefix` pins that.

- **`needs <level>` always prints `patch`.** The gate can only compute the *minimum* level a
  runtime change owes; MAJOR or MINOR is the reviewer's call from the §A11 lifecycle table.

- **`bump_level` calls a move confined to the prerelease line `prerelease`.** That includes
  promoting `1.0.0-rc.1` to `1.0.0`: the release line did not move, so no MAJOR/MINOR/PATCH
  applies. A decrease is `invalid`, never a level.

- **Label precedence** (ascending, `invalid` excluded): `none` < `initial` < `prerelease` <
  `patch` < `minor` < `major` < `removal`.

- **`--verify-tag` with no `claude` on PATH is a V6 finding and a non-zero exit**, never a
  silent skip: the check was explicitly requested. Without the flag nothing is printed.

- **Emergency removal is detected, not declared.** A removal whose latest tag's CHANGELOG
  section carries no `### Deprecated` heading gets the V5 *warning*; one that does gets
  nothing. That is what separates the `removal` and `emergency_removal` route cases.

- **`conftest.py` added under `scripts/versioning/`.** `test_check_versions.py` and
  `test_tag_versions.py` need the same temporary repository as `test_version_plan.py`;
  duplicating ~120 lines of builders three times was the alternative.

- **`git_output` uses `check=False` and inspects `returncode`.** `CalledProcessError.stderr`
  is typed `Any`, and reading it violates `reportAny` (probed: assigning it to an
  `object`-annotated variable still fires). `CompletedProcess[str].stderr` is `str`, so the
  real stderr reaches the message with no suppression.

- **`semver.VERSION_PATTERN` is anchored with `\Z`, not `$`.** The first run of
  `test_parse_rejects_everything_outside_the_grammar` caught `"1.0.0\n"` being accepted,
  because `$` also matches before a trailing newline. `EXEMPT_FILE` uses `\Z` for the same
  reason.

- **The stale `S603` sentence in `scripts/common/plugins.py`'s module docstring was
  corrected**, since `S603` is now ignored repository-wide; the literal-absolute-`argv[0]`
  plus `executable=` pattern stays, because `S607` still requires it.

### Findings about the repository

- **C1 fails for four plugins today, not three.** The plan named `ruff-quality`,
  `shell-quality` and `verify-completion`. `block-no-verify` fails too: it links `0.1.1`
  correctly with `compare/` and then links its newest release `0.1.2` with `tree/`. No
  CHANGELOG was edited. The four are recorded in `test_changelog_immutable.C1_DEBT`, and
  `test_no_plugin_outside_the_recorded_debt_mixes_link_styles` keeps a fifth from joining
  until the validator lands at step 5.

  ```text
  block-no-verify   | [0.1.2] should link to .../compare/block-no-verify--v0.1.1...block-no-verify--v0.1.2, not .../tree/block-no-verify--v0.1.2
  ruff-quality      | [0.1.1] should link to .../compare/ruff-quality--v0.1.0...ruff-quality--v0.1.1, not .../tree/ruff-quality--v0.1.1
  shell-quality     | [0.1.1] should link to .../compare/shell-quality--v0.1.0...shell-quality--v0.1.1, not .../tree/shell-quality--v0.1.1
  verify-completion | [0.1.1] should link to .../compare/verify-completion--v0.1.0...verify-completion--v0.1.1, not .../tree/verify-completion--v0.1.1
  ```

- **C2 is clean: 10/10 released sections equal their text at their tag** (the plan's
  expectation, confirmed).

- **`.claude-plugin/marketplace.json` has no `renames` key yet**, so `read_renames` returns
  `{}` on both sides and no rename or removal is in flight.

### Checklist

- [x] `make -s versions` prints five `exempt` lines and exactly `Computed label: bump: none`
      as the last line

  ```text
  $ make -s versions
  agent-self-knowledge 0.1.0 exempt
  block-no-verify 0.1.2 exempt
  ruff-quality 0.1.1 exempt
  shell-quality 0.1.1 exempt
  verify-completion 0.1.1 exempt
  Computed label: bump: none
  $ echo $?
  0
  ```

- [x] `make -s versions VERSIONS_ARGS=--json | jq -e '.route == "pr"'` exits 0 (the gate's own
      inputs changed) and no plugin reports `runtime_changed`

  ```text
  $ make -s versions VERSIONS_ARGS=--json
  {
    "route": "pr",
    "label": "bump: none",
    "deferred": false,
    "plugins": [
      {
        "name": "agent-self-knowledge",
        "predecessor": null,
        "tagged": "0.1.0",
        "version": "0.1.0",
        "runtime_changed": false,
        "first_runtime_path": null,
        "required": false,
        "ok": true,
        "reason": "no runtime change since agent-self-knowledge--v0.1.0"
      },
      {
        "name": "block-no-verify",
        "predecessor": null,
        "tagged": "0.1.2",
        "version": "0.1.2",
        "runtime_changed": false,
        "first_runtime_path": null,
        "required": false,
        "ok": true,
        "reason": "no runtime change since block-no-verify--v0.1.2"
      },
      {
        "name": "ruff-quality",
        "predecessor": null,
        "tagged": "0.1.1",
        "version": "0.1.1",
        "runtime_changed": false,
        "first_runtime_path": null,
        "required": false,
        "ok": true,
        "reason": "no runtime change since ruff-quality--v0.1.1"
      },
      {
        "name": "shell-quality",
        "predecessor": null,
        "tagged": "0.1.1",
        "version": "0.1.1",
        "runtime_changed": false,
        "first_runtime_path": null,
        "required": false,
        "ok": true,
        "reason": "no runtime change since shell-quality--v0.1.1"
      },
      {
        "name": "verify-completion",
        "predecessor": null,
        "tagged": "0.1.1",
        "version": "0.1.1",
        "runtime_changed": false,
        "first_runtime_path": null,
        "required": false,
        "ok": true,
        "reason": "no runtime change since verify-completion--v0.1.1"
      }
    ]
  }
  $ make -s versions VERSIONS_ARGS=--json | jq -e '.route == "pr"'
  true
  $ echo $?
  0
  $ make -s versions VERSIONS_ARGS=--json | jq '[.plugins[] | select(.runtime_changed)] | length'
  0
  ```

- [x] `.venv/bin/python -m scripts.versioning.tag_versions --dry-run` prints the idle line

  ```text
  $ .venv/bin/python -m scripts.versioning.tag_versions --dry-run
  Every plugin version is already tagged.
  $ echo $?
  0
  ```

- [x] the route-table cases are covered and pass: the plan's fourteen, the four the
      maintainer added on 2026-09-21, and four more covering the failure side of `runtime`,
      `new_plugin`, `removal` and the manifest content rule

  | §B case | test |
  | --- | --- |
  | `runtime` | `test_route_runtime` |
  | `exempt_only` | `test_route_exempt_only` |
  | `evals_only` | `test_route_evals_only` |
  | `tests_only` | `test_route_tests_only` |
  | `gate_only` | `test_route_gate_only` |
  | `formatting_only_plugin_json` | `test_route_formatting_only_plugin_json` (now `direct`) |
  | `metadata_only_plugin_json` | `test_route_metadata_only_plugin_json` |
  | `catalog_plugins_array_only` | `test_route_catalog_plugins_array_only` |
  | `catalog_renames_changed` | `test_route_catalog_renames_changed` |
  | `new_plugin` | `test_route_new_plugin` |
  | `rename` | `test_route_rename` |
  | `deprecation` | `test_route_deprecation` |
  | `removal` | `test_route_removal` |
  | `emergency_removal` | `test_route_emergency_removal` |
  | `multi_plugin` | `test_route_multi_plugin` |
  | `deferred_merge` | `test_route_deferred_merge` |
  | `post_merge_push` | `test_route_post_merge_push` |

  ```text
  $ .venv/bin/python -m pytest -m slow -k route -vv
  collecting ... collected 277 items / 255 deselected / 22 selected

  scripts/versioning/test_version_plan.py::test_route_runtime PASSED       [  4%]
  scripts/versioning/test_version_plan.py::test_route_runtime_with_a_bump_passes PASSED [  9%]
  scripts/versioning/test_version_plan.py::test_route_exempt_only PASSED   [ 13%]
  scripts/versioning/test_version_plan.py::test_route_evals_only PASSED    [ 18%]
  scripts/versioning/test_version_plan.py::test_route_tests_only PASSED    [ 22%]
  scripts/versioning/test_version_plan.py::test_route_gate_only PASSED     [ 27%]
  scripts/versioning/test_version_plan.py::test_route_formatting_only_plugin_json PASSED [ 31%]
  scripts/versioning/test_version_plan.py::test_route_metadata_only_plugin_json PASSED [ 36%]
  scripts/versioning/test_version_plan.py::test_route_metadata_edit_that_touches_runtime_is_a_pull_request PASSED [ 40%]
  scripts/versioning/test_version_plan.py::test_route_catalog_plugins_array_only PASSED [ 45%]
  scripts/versioning/test_version_plan.py::test_route_catalog_renames_changed PASSED [ 50%]
  scripts/versioning/test_version_plan.py::test_route_catalog_top_level_field_changed PASSED [ 54%]
  scripts/versioning/test_version_plan.py::test_route_new_plugin PASSED    [ 59%]
  scripts/versioning/test_version_plan.py::test_route_new_plugin_must_start_at_the_initial_version PASSED [ 63%]
  scripts/versioning/test_version_plan.py::test_route_rename PASSED        [ 68%]
  scripts/versioning/test_version_plan.py::test_route_deprecation PASSED   [ 72%]
  scripts/versioning/test_version_plan.py::test_route_removal PASSED       [ 77%]
  scripts/versioning/test_version_plan.py::test_route_emergency_removal PASSED [ 81%]
  scripts/versioning/test_version_plan.py::test_route_removal_without_a_renames_entry_fails PASSED [ 86%]
  scripts/versioning/test_version_plan.py::test_route_multi_plugin PASSED  [ 90%]
  scripts/versioning/test_version_plan.py::test_route_deferred_merge PASSED [ 95%]
  scripts/versioning/test_version_plan.py::test_route_post_merge_push PASSED [100%]

  ====================== 22 passed, 255 deselected in 5.35s ======================

  $ .venv/bin/python -m pytest -m slow -vv -k content_exempt
  collecting ... collected 277 items / 274 deselected / 3 selected

  scripts/versioning/test_version_plan.py::test_content_exempt_paths_clears_only_what_it_should PASSED [ 33%]
  scripts/versioning/test_version_plan.py::test_content_exempt_paths_refuses_a_manifest_that_moved_runtime PASSED [ 66%]
  scripts/versioning/test_version_plan.py::test_content_exempt_paths_refuses_a_catalog_that_moved_policy PASSED [100%]

  ====================== 3 passed, 274 deselected in 1.05s =======================
  ```

- [x] `test_changelog_immutable` reports 10/10 released sections equal to their tag, and
      `test_plugin_paths` passes under both bash binaries

  ```text
  $ .venv/bin/python -m pytest -m slow -vv -k "changelog_immutable or plugin_paths"
  collecting ... collected 268 items / 264 deselected / 4 selected

  scripts/harness/test_plugin_paths.py::test_bash_mirror_agrees_with_python[/opt/homebrew/bin/bash] PASSED [ 25%]
  scripts/harness/test_plugin_paths.py::test_bash_mirror_agrees_with_python[/bin/bash] PASSED [ 50%]
  scripts/versioning/test_changelog_immutable.py::test_every_released_section_equals_its_text_at_its_tag PASSED [ 75%]
  scripts/versioning/test_changelog_immutable.py::test_no_plugin_outside_the_recorded_debt_mixes_link_styles PASSED [100%]

  ====================== 4 passed, 264 deselected in 0.26s =======================
  $ .venv/bin/python -c "…count the sections compared…"
  compared 10/10 released sections
     agent-self-knowledge 0.1.0
     block-no-verify 0.1.0
     block-no-verify 0.1.1
     block-no-verify 0.1.2
     ruff-quality 0.1.0
     ruff-quality 0.1.1
     shell-quality 0.1.0
     shell-quality 0.1.1
     verify-completion 0.1.0
     verify-completion 0.1.1
  findings: []
  ```

  `/opt/homebrew/bin/bash` is 5.3.20 and `/bin/bash` is Apple's 3.2.57; both classify all
  nineteen table paths identically to `version_plan.is_exempt`.

- [x] `make lint types test-fast` exit 0, and `make test-slow`'s pytest step exit 0

  ```text
  $ make lint types test-fast >/dev/null 2>&1; echo $?
  0
  $ .venv/bin/python -m pytest -m slow -q
  ................................................................         [100%]
  $ echo $?
  0
  $ .venv/bin/python -m pytest -m slow | tail -1
  64 passed, 213 deselected in 11.02s
  $ .venv/bin/python -m pytest | tail -1
  277 passed in 10.72s
  ```

  Full suite: 277 tests, 213 fast and 64 slow. `make lint` covers 26 `.py` files,
  `make types` reports `0 errors, 0 warnings, 0 notes`.

- [x] zero suppressions in the new code

  ```text
  $ grep -rnE "# *(noqa|type: ?ignore|pyright: ?ignore|basedpyright: ?ignore)|cast\(" --include='*.py' scripts/
  $ echo $?
  1
  ```

- [x] `claude plugin tag --help` — the flags `tag_versions.py` relies on

  ```text
  $ claude plugin tag --help
  Usage: claude plugin tag [options] [path]

  Create a {name}--v{version} git tag for a plugin release, validating that
  plugin.json and any enclosing marketplace entry agree

  Options:
    --dry-run            Print what would be tagged without creating it
    -f, --force          Skip the dirty-working-tree and tag-already-exists checks
    -h, --help           Display help for command
    -m, --message <msg>  Tag annotation message (use %s for the version)
    --push               Push the tag to --remote after creating it
    --remote <name>      Remote to push to with --push (default: "origin")
  ```

  Only `--dry-run` and `--push` are used. `--force` is never used: `*--v*` tags are immutable
  by ruleset, so a forced retag could not land anyway.

- [x] `git status --short` and `git diff --stat` at the end of the step

  ```text
  $ git status --short
  ## refactor/python-toolchain-and-governance
   M Makefile
   M docs/superpowers/specs/2026-09-21-refactor-migration-log.md
   M scripts/common/errors.py
   M scripts/common/plugins.py
   M scripts/common/test_errors.py
   M scripts/common/test_plugins.py
  ?? scripts/harness/test_plugin_paths.py
  ?? scripts/versioning/changelog.py
  ?? scripts/versioning/check_versions.py
  ?? scripts/versioning/conftest.py
  ?? scripts/versioning/semver.py
  ?? scripts/versioning/tag_versions.py
  ?? scripts/versioning/test_changelog.py
  ?? scripts/versioning/test_changelog_immutable.py
  ?? scripts/versioning/test_check_versions.py
  ?? scripts/versioning/test_semver.py
  ?? scripts/versioning/test_tag_versions.py
  ?? scripts/versioning/test_version_plan.py
  ?? scripts/versioning/version_plan.py

  $ git diff --stat
   Makefile                                           |   2 +-
   .../specs/2026-09-21-refactor-migration-log.md     | 383 +++++++++++++++++++++
   scripts/common/errors.py                           |  19 +
   scripts/common/plugins.py                          |  97 +++++-
   scripts/common/test_errors.py                      |  12 +
   scripts/common/test_plugins.py                     |  43 +++
   6 files changed, 545 insertions(+), 11 deletions(-)
  ```

  The thirteen new modules and test files are untracked, so `git diff --stat` does not count
  them;
  `git status --short` lists every one.

Nothing was committed, pushed or tagged; no tag was created in this repository at any point.

### External unsafe-fix run

External unsafe-fix run at ~01:45: files re-read: `scripts/common/errors.py`,
`scripts/common/plugins.py`, `scripts/common/test_errors.py`, `scripts/common/test_plugins.py`,
`scripts/versioning/semver.py`, `version_plan.py`, `changelog.py`, `check_versions.py`,
`tag_versions.py`, `conftest.py`, `test_semver.py`, `test_version_plan.py`,
`test_changelog.py`, `test_changelog_immutable.py`, `test_check_versions.py`,
`test_tag_versions.py`, `scripts/harness/test_plugin_paths.py`, `Makefile`; changes found:
none surviving in the delivered files.

One change by an external `--fix` pass was seen and repaired *during* the step, before this
audit: while `version_plan.py` was half-written (its constants and helpers on disk, its plan
builder not yet appended), an outside pass removed the four imports that were unused at that
instant (`plugin_ids`, `announces_deprecation`, `released_body_at_tag`, `bump_level`) and moved
`Finding` into the `TYPE_CHECKING` block. `ruff check` caught it immediately as `F821 Undefined
name` once the builder landed; the import block was rewritten and the module has been clean
since. Nothing else was altered, and `.claude/hooks/post-edit.sh` is not the cause: it is still
the Biome-era hook and runs no Python tooling at all (a stale-tooling item for the step that
owns the hooks).

The maintainer ran `ruff check --fix --unsafe-fixes` over the repository from a terminal while
this step was in progress. Every file written in this step was re-read in full and compared
against what it was written to be. Two differences from the first draft were found and both
were explained:

1. **`{key: "x" for key in METADATA_KEYS}` → `dict.fromkeys(METADATA_KEYS, "x")`** in
   `test_version_plan.py`. This is Ruff's `C420`, and under this repository's floor the rule
   **fires as an error and its fix is marked safe**, so it was applied by the plain
   `ruff check --fix` run in this step, not by the unsafe fixer. Probed in a scratch file:

   ```text
   $ .venv/bin/python -m ruff check scripts/versioning/_c420probe.py
   C420 [*] Unnecessary dict comprehension for iterable; use `dict.fromkeys` instead
   Found 1 error.
   [*] 1 fixable with the `--fix` option.
   ```

   The value is the immutable string `"x"`, so `fromkeys` sharing one object across keys
   cannot bite here, and the assertion is unchanged. Keeping the comprehension would fail
   `make lint`.

2. **`"\u2192"` written as a literal `→`** in `check_versions.py` and `test_check_versions.py`.
   Identical Python strings. Ruff was probed and does not perform this rewrite
   (`ruff check --fix --unsafe-fixes --select ALL` plus `ruff format` on a file containing the
   escape left it untouched). The rendered bytes were checked directly:

   ```text
   >>> plugin_line(...)
   'alpha 0.1.0 runtime: skills/demo/SKILL.md → needs patch'
   bytes: b'alpha 0.1.0 runtime: skills/demo/SKILL.md \xe2\x86\x92 needs patch'
   contains 'bump: ': False
   ```

Checks run to prove nothing else moved:

- **Tracked diffs read line by line.** `scripts/common/errors.py`, `plugins.py`,
  `test_errors.py`, `test_plugins.py` and `Makefile` show only the intended additions.
- **Byte audit.** Every non-ASCII character in every file of this step is accounted for
  (`→` ×8, `—` ×4, `…` ×1, `§` ×6, all in docstrings or rendered output) and there is no
  stray control character anywhere under `scripts/`.
- **No unsafe fix is pending.** `ruff check --unsafe-fixes --diff` over the whole `PY_FILES`
  set prints nothing, and the rewrites an unsafe pass leaves behind (`contextlib.suppress`,
  tuple `startswith`, `next(iter(...))`) appear nowhere.
- **Mutation testing, to prove no *test* was weakened.** Seven deliberate defects were seeded
  one at a time and every one was caught:

  | Seeded defect | Caught by |
  | --- | --- |
  | `evals/` removed from `EXEMPT_FILE` | 5 failures, including both bash parity tests |
  | `route` ignores `renames_changed` | not caught — the rename fixture is already `pr` by two other rules; the rule itself is covered by `test_read_renames_*` |
  | `LABEL_PREFIX` changed | `test_the_golden_last_line`, `test_render_puts_the_label_last`, `test_an_unbumped_runtime_change_fails` |
  | `bump_level` returns `patch` where `minor` is owed | 5 failures across `test_semver` and the rename/deprecation/multi-plugin route cases |
  | `released_body_at_tag` always None | `test_check_released_bodies_catches_a_rewritten_release` |
  | `required` hard-coded False | `test_route_runtime` and both `check_versions` failure cases |
  | `--dry-run` no longer reaches the CLI | `test_dry_run_reports_the_tag_without_creating_it` |

  Two further mutations were seeded against the content rule added on 2026-09-21:

  | Seeded defect | Caught by |
  | --- | --- |
  | the catalog rule clears every `marketplace.json` change | `test_route_catalog_top_level_field_changed` |
  | the manifest rule clears every `plugin.json` change | `test_content_exempt_paths_refuses_a_manifest_that_moved_runtime` |

  The second was not caught by any route case, because a manifest edit that moves runtime is
  already a pull request through "this plugin's runtime changed"; the negative assertion was
  therefore added against `content_exempt_paths` itself, which is the rule's single home. The
  same masking explains the one uncaught mutation above: the rename case is already routed to
  `pr` by "version differs from its tag" and by "a path outside the allowlist changed", so
  switching off `renames_changed` cannot change its answer.

- **Byte-identical restore.** SHA-256 of all 26 `scripts/**/*.py` files was taken before the
  mutations and compared after each restore; the final comparison is clean, so the audit left
  the tree exactly as it found it.

  ```text
  $ diff /tmp/.../sha.before /tmp/.../sha.end && echo "ALL 26 FILES BYTE-IDENTICAL"
  ALL 26 FILES BYTE-IDENTICAL TO THE PRE-AUDIT STATE
  ```

- **Gate re-run after the audit**: `make lint` clean, `make types` `0 errors, 0 warnings,
  0 notes`, 212 fast + 56 slow tests pass, `make -s versions` still ends in
  `Computed label: bump: none`, `tag_versions --dry-run` still prints
  `Every plugin version is already tagged.`

`plugins/` was not touched at any point in this step.

### Carried to later steps

- `.github/workflows/ci.yml` still calls `node scripts/check-versions.mjs`, and
  `docs/contributing/versioning.md` still documents the npm commands and `scripts/lib/
  version-plan.mjs`. Both are rewired at the steps that own them (6 and 8).
- `check_versions` raises a usage error (exit 2) when `--base` cannot be resolved. The push
  event passes `--base ${{ github.event.before }}`, which is forty zeros when a branch is
  created; if that case ever reaches `main`, step 6 must special-case it in the workflow or
  here.
- The C1 validator, and the decision on whether to repair the four CHANGELOG footers, belong
  to step 5.

## Gate 4 — `scripts/marketplace/`, `scripts/github/` (2026-09-21)

Twelve modules and twelve test modules were written against §A5, §A6 (M1–M10, G1–G3) and
§A11. Nothing deleted from this repository was read or restored (P13): the catalog entry
shape, the label taxonomy, the triage rules and the pins were rebuilt from the plan and from
the tracked artifacts themselves.

**Files created**

```text
scripts/common/jsontext.py            canonical_json + the JSON narrowing predicates
scripts/common/test_jsontext.py
scripts/marketplace/catalog.py        MARKETPLACE_CATEGORIES, name/tag rules, catalog_entry,
                                      build_plugins_array, check_renames (M9), check_links (M10)
scripts/marketplace/generate_marketplace.py
scripts/marketplace/validate_marketplace.py   MARKETPLACE_INVARIANTS + M1–M10, --list, --root
scripts/marketplace/conftest.py       fixture marketplace tree
scripts/marketplace/test_catalog.py
scripts/marketplace/test_generate_marketplace.py
scripts/marketplace/test_validate_marketplace.py
scripts/github/client.py              stdlib REST client, injectable transport, apply-gated writes
scripts/github/labels.py              Label, REQUIRED_LABELS (incl. `bump: removal`), validate, plan
scripts/github/sync_labels.py         dry run by default, --apply, --prune
scripts/github/issue_forms.py         PyYAML + jsonschema validation, dropdown and label checks
scripts/github/generate_issue_forms.py  targeted text rewrite of the `id: plugin` options block
scripts/github/repo_metadata.py       CLAUDE_CODE_VERSION, tool pins (G3), workflow SHAs,
                                      pipeline invocation (G2, advisory)
scripts/github/triage_rules.py        pure path/answer/bump rules
scripts/github/triage.py              event CLI, dry run by default
scripts/github/conftest.py            recording transport + fixture tree
scripts/github/test_client.py  test_labels.py  test_sync_labels.py  test_issue_forms.py
scripts/github/test_generate_issue_forms.py  test_triage_rules.py  test_triage.py
scripts/github/test_repo_metadata.py
```

**Files modified**: `Makefile` (the two `generate` lines uncommented) and
`.claude-plugin/marketplace.json` (the `$schema` key removed by `make generate` itself).
`plugins/`, `schemas/`, `.github/labels.json` and `.github/ISSUE_TEMPLATE/` were not edited.

### Decisions taken beyond the plan

- **`canonical_json` lives in `scripts/common/jsontext.py`, not in `scripts/lint/json_files.py`.**
  Step 4 needs the canonical serialisation before step 6 exists, and two copies would be two
  policies (P1). `json_files.py` imports it at step 6; the module also holds `is_json_object`
  and `is_json_array`, the two `TypeIs` predicates every narrowing site needs under
  basedpyright `all`.
- **`GITHUB_SCHEMAS_DIR` is defined in `issue_forms.py`.** The plan places the constant with
  `repo_metadata`, but `issue_forms` is its only consumer and `repo_metadata` would then
  declare a constant it never uses. It is still exactly one definition, flipped to
  `.github/schemas` at step 9 by editing that one line.
- **`catalog_entry` takes a keyword-only `path`.** The narrowing helpers in
  `scripts/common/plugins.py` name the offending file in every shape error; without the path
  a bad manifest would raise an error that does not say which manifest.
- **`validate_marketplace` takes `--root`.** The ten seeded-defect probes below run against a
  scratch copy of the tree; without it they would have to mutate the working tree.
- **`triage.py` applies no `bump:` label from a base-only checkout.** `check_versions`
  answers "what does this working tree owe against this base", so in the base checkout
  `triage.yml` performs it would always answer `bump: none` — wrong on every pull request
  that bumps anything. The entrypoint therefore computes the label only when `HEAD` is the
  event's head or merge commit, or when `--versions-json` supplies the document, and
  otherwise applies no `bump:` label rather than a confident wrong one. Stale `bump:` labels
  are still removed, and `bump: deferred` is still preserved. **This is the one item of the
  step that the plan's wording does not resolve**: §A5 says triage "runs `check_versions` on
  the base checkout with `--base`", which cannot produce a correct answer. Step 7, which owns
  `triage.yml`, must either feed `--versions-json` from a separate job or give
  `check_versions` a two-ref comparison mode.
- **`AUTH_ENV_VARIABLE` rather than `TOKEN_VARIABLE`.** Ruff's `S105` flags any string
  literal assigned to a name containing `token`, and the floor allows no suppression.

### Gate 4 checklist

- [x] `make generate` exit 0 and the diff over the two generated artifacts shows **only** the
      `$schema` removal.

  The generators are idempotent on this tree; the recipe's own `git diff --exit-code` refuses
  while the removal is uncommitted, which is by instruction (this step does not commit).

  ```text
  $ make generate
  .venv/bin/python -m scripts.marketplace.generate_marketplace
  .claude-plugin/marketplace.json unchanged
  .venv/bin/python -m scripts.github.generate_issue_forms
  .github/ISSUE_TEMPLATE: dropdowns unchanged
  git diff --exit-code -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
  diff --git i/.claude-plugin/marketplace.json w/.claude-plugin/marketplace.json
  @@ -1,5 +1,4 @@
   {
  -  "$schema": "../schemas/marketplace.schema.json",
     "name": "claude-essentials",
  make: *** [generate] Error 1
  make generate exit=2

  $ git add .claude-plugin/marketplace.json && make generate
  .claude-plugin/marketplace.json unchanged
  .github/ISSUE_TEMPLATE: dropdowns unchanged
  git diff --exit-code -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
  make generate exit=0
  ```

  ```text
  $ git diff --stat -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
   .claude-plugin/marketplace.json | 1 -
   1 file changed, 1 deletion(-)
  ```

  The tracked catalog was already canonical JSON: apart from the `$schema` line the generated
  document is byte-identical to the file. No other tracked file was reformatted.

- [x] `sync_labels` dry run against the live repository, exit 0, nothing pruned.

  ```text
  $ GITHUB_TOKEN=$(gh auth token) .venv/bin/python -m scripts.github.sync_labels
  labels: GitHub already matches the taxonomy
  exit=0
  ```

  **This differs from the plan's expectation** ("lists only `bump: removal` and the `area:`
  text changes") for one reason: those are text changes to `.github/labels.json`, which step 7
  owns and this step may not touch. With the file exactly as tracked, the live taxonomy
  already matches — including the five `plugin: <id>` labels, whose derived colour `5319e7`
  and 100-character truncated description were reproduced from the live labels. Adding the
  one new entry to the taxonomy produces exactly the expected single create:

  ```text
  --- plan with .github/labels.json exactly as tracked today ---
  labels: GitHub already matches the taxonomy
  --- plan with `bump: removal` added, as step 7 will ---
  create bump: removal
  ```

  Nothing is planned for pruning, and the run is read-only: `GET /repos/.../labels` only.

- [x] `validate_marketplace` passes on the tree, and each of M1–M10 fires on a seeded defect.

  ```text
  $ .venv/bin/python -m scripts.marketplace.validate_marketplace
  marketplace catalog: M1-M10 pass
  exit=0
  ```

  Every probe was seeded into a fresh copy of the tracked tree under the session scratchpad
  and checked with `--root <copy>`; the working tree was never mutated.

  | Probe seeded in the scratch copy | Line that fired |
  | --- | --- |
  | `plugin.json` `name` changed to `beta` | `M1 plugins/ruff-quality/.claude-plugin/plugin.json: manifest `name` is 'beta' but the directory is 'ruff-quality'` |
  | category changed to `misc` | `M2 …: category 'misc' is not one of: automation, database, deployment, design, development, learning, monitoring, productivity, security, testing` |
  | nine tags | `M3 …: 9 tags; between 1 and 8 allowed` |
  | `license` changed to `MIT` | `M4 …: `license` is 'MIT', not 'Apache-2.0'` |
  | `version` changed to `1.0` | `M5 …: '1.0' is not a canonical version: expected X.Y.Z, X.Y.Z-beta.N or X.Y.Z-rc.N, with no `v` prefix and no build metadata` |
  | directory renamed to 43 `a` characters | `M6 plugins/aaa…a/.claude-plugin/plugin.json: 'aaa…a' is 43 characters; at most 42 keeps `plugin: <name>` inside GitHub's limit` |
  | entry description hand-edited | `M7 .claude-plugin/marketplace.json: its `plugins` array does not match the manifests on disk; run `make generate`` |
  | `version` key added to an entry | `M8 .claude-plugin/marketplace.json: entry 'agent-self-knowledge' carries a `version` key; the catalog never pins one` |
  | `renames` maps a plugin that still ships | `M9 .claude-plugin/marketplace.json: `renames` maps 'ruff-quality', but `plugins/ruff-quality/` still ships` |
  | `homepage` points at another plugin | `M10 plugins/ruff-quality/.claude-plugin/plugin.json: `homepage` '…/plugins/other' does not end with '/plugins/ruff-quality'` |

  All ten runs exited 1. Two further M9 and M10 cases (a removed plugin that keeps its root
  README row; a `$schema` hint with nothing behind it) are covered by
  `test_validate_marketplace.py` rather than by a scratch probe, because both need a tree with
  a plugin removed.

- [x] `validate_marketplace --list`

  ```text
  M1  `plugin.json` `name` equals its directory name — a catalog/directory mismatch breaks install
  M2  `metadata.marketplace.category` is one of `MARKETPLACE_CATEGORIES` — free-text categories
  M3  `tags`: one to eight, unique, `^[a-z0-9]+(-[a-z0-9]+)*$` — unbounded or duplicated tags
  M4  required fields `name`, `description`, `version`, `metadata.marketplace.category`, `author.name`, `license == "Apache-2.0"` — ADR-0005 drift
  M5  `version` is canonical SemVer: no `v`, no build metadata, prerelease `-(beta|rc).N` — the official CLI accepts `1.0`, which Claude Code then orders differently
  M6  `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and is at most 42 characters — DEBT-0021: `plugin: <name>` would exceed GitHub's 50-character label limit
  M7  `marketplace.json` is byte-equal to the generated document — hand edits to a generated array
  M8  disk and catalog agree both ways, and no entry carries a `version` key — a stale catalog
  M9  `renames` values are a string or null; no key still ships; a null has no README row — DEBT-0006: a catalog that offers a plugin that no longer exists
  M10  `homepage` ends with `/plugins/<id>`; no `$schema` points at a missing path — dead links
  ```

- [x] `make generate lint types test-fast` exit 0 (run with the `$schema` removal staged, so
      the recipe's diff check passes); `pytest -m slow` exit 0.

  ```text
  $ git add .claude-plugin/marketplace.json && make generate lint types test-fast
  make generate lint types test-fast exit=0
  418 passed, 93 deselected in 0.48s

  $ .venv/bin/python -m pytest -m slow
  93 passed, 418 deselected in 11.37s

  $ PATH=.venv/bin:$PATH .venv/bin/basedpyright --threads
  0 errors, 0 warnings, 0 notes
  ```

  Counts at this point: **418 fast + 93 slow = 511** tests, up from 212 + 56 at the end of
  step 3; the entrypoint fixes below raise it to 422 + 98. Every
  test that spawns a process — `repo_root()`, `git remote get-url`, `git rev-parse` — carries
  `@pytest.mark.slow`, matching the convention `scripts/common/test_plugins.py` set.

- [x] `git status --short` and `git diff --stat` at the end.

  ```text
  $ git diff --stat
   .claude-plugin/marketplace.json | 1 -
   .claude/settings.json           | 3 ++-
   Makefile                        | 4 ++--
   pyproject.toml                  | 2 +-
  ```

  `.claude/settings.json` and `pyproject.toml` were modified by the concurrent steps running
  in the same session, not by this one. This step's own changes are the `$schema` removal, the
  two uncommented `generate` lines, twenty-six new files under `scripts/`, and this entry.

### Entrypoint error handling — two runtime findings, fixed in this step

A runtime probe of the CLIs found two entrypoints that ended in a raw traceback instead of a
message. Both are fixed here, and the convention is now applied to every `main()` this step
touches: **catch `MaintainerError` and `OSError`, print one `error: <message>` line to stderr,
return the entrypoint's own failure status.** A traceback tells a maintainer where the code
broke; it does not tell them what they did wrong.

`scripts/common/errors.py` gained one class for the case neither side owned:

```python
class MissingPathError(MaintainerError):
    """A file or directory an entrypoint was pointed at does not exist."""
```

**Finding 1 — `validate_marketplace --root /nonexistent`.** `collect()` now refuses a root
that is not a directory and a tree with no catalog, before anything tries to read a file.

```text
$ .venv/bin/python -m scripts.marketplace.validate_marketplace --root /nonexistent
error: /nonexistent: the repository root does not exist
exit=2

$ .venv/bin/python -m scripts.marketplace.validate_marketplace --root <an empty directory>
error: <…>/.claude-plugin/marketplace.json: the marketplace catalog does not exist
exit=2
```

Before the fix the same command ended in
`FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/.claude-plugin/marketplace.json'`.
Covered by `test_a_root_that_does_not_exist_is_one_line`,
`test_a_tree_without_a_catalog_is_one_line` and `test_collect_refuses_a_missing_root`.

**Finding 2 — `tag_versions --dry-run` with no `claude` on PATH.** The raising body moved to
`_tag()` and `main()` converts. Note that the probe command in the report does not reproduce
on this tree: with every version already tagged, `pending_tags()` is empty and the CLI is
never resolved, so the command prints `Every plugin version is already tagged.` and exits 0.
The defect is real but needs a pending tag. Reproduced in a scratch repository with one
untagged plugin version and a PATH that provides git but not `claude`:

```text
$ env PATH=/usr/bin:/bin .venv/bin/python -m scripts.versioning.tag_versions --dry-run
error: `claude` is not on PATH; run `make setup` and check the requirements
exit=2
```

Covered by `test_main_reports_a_missing_cli_as_one_line`, which builds a PATH directory
holding a single `git` symlink so the missing binary is `claude` and nothing else.

**Status convention, settled.** An earlier draft returned 1 here on the grounds that
`tag_versions` already used 1 for a refusal. That was corrected: **2 is the status for a
command that could not run** (bad root, no working tree, no `GITHUB_TOKEN`, no `claude`), and
**1 is reserved for a finding about a plugin** — in this entrypoint, the CLI refusing a tag it
was asked to create. A missing binary teaches nothing about any plugin, so it is not a
finding.

**The same convention, applied as the other entrypoints were written.** In each one
`repo_root()` moved inside the `try`, so a run outside a working tree is a message too:

| Entrypoint | Failure its test exercises | Status | Test |
| --- | --- | --- | --- |
| `validate_marketplace` | `--root` that is not there | 2 | `test_a_root_that_does_not_exist_is_one_line` |
| `validate_marketplace` | tree with no catalog | 2 | `test_a_tree_without_a_catalog_is_one_line` |
| `validate_marketplace` | the precondition itself | — | `test_collect_refuses_a_missing_root` |
| `generate_marketplace` | run outside a working tree | 2 | `test_main_outside_a_repository_is_one_line` |
| `generate_issue_forms` | run outside a working tree | 2 | `test_main_outside_a_repository_is_one_line` |
| `sync_labels` | `GITHUB_TOKEN` unset | 2 | `test_main_without_a_token_is_one_line` |
| `triage` | truncated `GITHUB_EVENT_PATH` payload | 2 | `test_main_with_an_unreadable_event_is_one_line` |
| `tag_versions` | `claude` not installed | 2 | `test_main_reports_a_missing_cli_as_one_line` |

Every one of those tests asserts both the exit status and that `Traceback` does not appear on
stderr.

```text
$ .venv/bin/python -m pytest -k "one_line or refuses_a_missing_root" -v
scripts/github/test_generate_issue_forms.py::test_main_outside_a_repository_is_one_line
scripts/github/test_sync_labels.py::test_main_without_a_token_is_one_line
scripts/github/test_triage.py::test_main_with_an_unreadable_event_is_one_line
scripts/marketplace/test_generate_marketplace.py::test_main_outside_a_repository_is_one_line
scripts/marketplace/test_validate_marketplace.py::test_a_root_that_does_not_exist_is_one_line
scripts/marketplace/test_validate_marketplace.py::test_a_tree_without_a_catalog_is_one_line
scripts/marketplace/test_validate_marketplace.py::test_collect_refuses_a_missing_root
scripts/versioning/test_tag_versions.py::test_main_reports_a_missing_cli_as_one_line
8 passed, 512 deselected
```

**Gate re-run after the fixes** — no regression in step 3's evidence:

```text
$ .venv/bin/python -m scripts.versioning.tag_versions --dry-run
Every plugin version is already tagged.
$ make -s versions | tail -1
Computed label: bump: none
$ .venv/bin/python -m scripts.marketplace.validate_marketplace
marketplace catalog: M1-M10 pass
$ GITHUB_TOKEN=$(gh auth token) .venv/bin/python -m scripts.github.sync_labels
labels: GitHub already matches the taxonomy
$ make lint types test-fast
422 passed, 98 deselected in 0.47s
exit=0
$ .venv/bin/python -m pytest -m slow -q
98 passed, 422 deselected in 11.64s
exit=0
$ PATH=.venv/bin:$PATH .venv/bin/basedpyright --threads
0 errors, 0 warnings, 0 notes
```

Counts after the fixes: **422 fast + 98 slow = 520** tests, up from 418 + 93. No suppression
appears anywhere under `scripts/`.

### Observations and carried items

- **G1 does not fail today, and `make validate` is still not wired.** The plan's Makefile
  marker for `validate_marketplace` says "ported at step 4", but the instruction for this step
  was to uncomment only the two `generate` lines. `validate_marketplace` therefore runs by
  hand and in tests; wiring the `validate` recipe belongs to the step that also adds
  `validate_plugins` (step 5), which is where the G invariants are emitted.
- **`bump: removal` is the one required label the taxonomy does not declare yet.**
  `labels.missing_required()` returns exactly `["bump: removal"]` today.
  `test_only_the_step_seven_label_is_missing_today` asserts `⊆ {"bump: removal"}`, so it
  passes now and keeps passing once step 7 adds the entry.
- **G2's pipeline check is advisory, as specified.** `repo_metadata.collect()` on this tree
  reports exactly one finding, a warning:
  `G2 .github/workflows/ci.yml: the gate workflow runs no `make` target, so CI and `make check`
  can drift (advisory until step 7)`. Step 7 flips it to an error when `ci.yml` is rewired.
- **`good first issue` is neither required nor an error.** D5 drops it from the taxonomy; the
  text removal is step 7's, and until then the label validates cleanly.
- **`jsonschema` needs no stub package.** Probed under basedpyright `all` with
  `allowedUntypedLibraries = []`: `reportMissingTypeStubs` does not fire, and
  `validator_for`/`iter_errors` are precisely typed, which is why `issue_forms` carries an
  explicit recursive `JsonValue` alias and narrows YAML into it.
- **`repo_metadata` works around YAML 1.1.** PyYAML resolves the bare workflow key `on` to
  the boolean `True`, so the trigger block would be unreachable by name; `workflow_document`
  normalises it and `test_the_on_key_survives_yaml_one_point_one` pins the behaviour.

### Decision carried to Follow-up PR #1 (2026-09-21)

- `per-file-target-version` for `plugins/agent-self-knowledge/**` is inert in this PR (`make lint` covers `scripts/` only) and its value is provisional. In Follow-up PR #1 it must equal the Python floor the plugin README declares, measured by running `ccdocs.py` under that version; a G3 check asserts the three agree (README row, this key, the CI `uv python install` line). The plugin contract itself is the shebang `#!/usr/bin/env python3` (B1): the script runs with whatever `python3` the installing machine has.

### Orchestrator verification of gate 4 (2026-09-21)

- Re-ran `make lint && make types && make test-fast` → clean, `0 errors, 0 warnings, 0 notes`, `422 passed, 98 deselected`; `pytest -m slow -q` → 98 passed.
- Runtime probes at the CLI surface (scratch clone with tags): `validate_marketplace --list` (10 rows), M5/M7/M8 on seeded defects, `--root /nonexistent` → `error: /nonexistent: the repository root does not exist` rc 2; `tag_versions --dry-run` with an untagged bump and no `claude` on PATH → `error: \`claude\` is not on PATH; run \`make setup\`…` rc 1; `sync_labels` dry run → `labels: GitHub already matches the taxonomy`; `generate_issue_forms` → `dropdowns unchanged`; `make generate` rc 0 with the `$schema` removal staged.
- Accepted beyond the plan: `canonical_json` lives in `scripts/common/jsontext.py` (step 6's `json_files` imports it); `GITHUB_SCHEMAS_DIR` lives in `issue_forms.py`; `bump: removal` is created by the step-7 `labels.json` edit (dry run proves `create bump: removal`).
- Carried: a `Makefile` prerequisite that fails with `run make setup` when `.venv/bin/python` is absent (step 6).

## Gate 5 — `scripts/plugin_validation/` (2026-09-21)

Ported: `claude_cli`, `cli_coverage`, `evals`, `frontmatter`, `hook_contract`, `kind`,
`readme_contract`, `run_plugin_suites`, `runtime_boundary`, `script_env`, `validate_claude`,
`validate_plugins`, `workflows`, plus `scripts/common/javascript.py` (the V8 helper both
`hook_contract` and `workflows` use, P12) and one `test_*.py` per module, `conftest.py` and
`test_templates.py`. The three `Makefile` recipe lines marked `# ported at step 5` are
uncommented, and the `# ported at step 4` line in `validate` with them (see the decisions
below).

- [x] `.venv/bin/python -m scripts.plugin_validation.validate_plugins --list` prints every ID of §A6

```text
M1  `plugin.json` `name` equals its directory name — a catalog/directory mismatch breaks install
M2  `metadata.marketplace.category` is one of `MARKETPLACE_CATEGORIES` — free-text categories
M3  `tags`: one to eight, unique, `^[a-z0-9]+(-[a-z0-9]+)*$` — unbounded or duplicated tags
M4  required fields `name`, `description`, `version`, `metadata.marketplace.category`, `author.name`, `license == "Apache-2.0"` — ADR-0005 drift
M5  `version` is canonical SemVer: no `v`, no build metadata, prerelease `-(beta|rc).N` — the official CLI accepts `1.0`, which Claude Code then orders differently
M6  `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and is at most 42 characters — DEBT-0021: `plugin: <name>` would exceed GitHub's 50-character label limit
M7  `marketplace.json` is byte-equal to the generated document — hand edits to a generated array
M8  disk and catalog agree both ways, and no entry carries a `version` key — a stale catalog
M9  `renames` values are a string or null; no key still ships; a null has no README row — DEBT-0006: a catalog that offers a plugin that no longer exists
M10  `homepage` ends with `/plugins/<id>`; no `$schema` points at a missing path — dead links
P1  the kind the files derive equals the README `**Kind:**` line — ADR-0001 drift
P2  `LICENSE` is byte-equal to the Apache-2.0 template — SPDX detection
P3  `CHANGELOG.md` has a dated section for the manifest version — a release with no notes
P4  no `{{placeholder}}` survives in a shipped file — template leftovers
P5  no top-level `bin/` in a plugin — an undeclared runtime
C1  CHANGELOG footer links use one style, `tree/` then `compare/` — mixed link styles
C2  a released section still reads as it did at its tag — DEBT-0009: rewritten history
S1  frontmatter starts on line 1 and parses as YAML — DEBT-0022: a skill that never loads
S2  frontmatter keys are documented (warning) — upstream additions
S3  `description` plus `when_to_use`: present, under the cap, imperative — truncated listings
S4  `allowed-tools` entries parse and name a tool (unknown: warning) — inert grants
S5  an agent `name` has no `:` and a `description` is present — a load failure
S6  an agent's `skills:` entries resolve on disk — dangling references
H1  `hooks.json` parses; events and handler types are documented — shape drift
H2  every regex matcher compiles under V8 and matches a tool — `Write|Edit[`
H3  every exact matcher names a known tool (warning) — a typo that fires nothing
H4  a `command` is present and non-empty — the CLI catches absent, not empty
H5  a `${CLAUDE_PLUGIN_ROOT}` path exists, is executable, has a shebang — a dead handler
H6  `timeout` is numeric and within the event's documented default — a silent cancel
R1  the template's sections, in order, optional ones only when earned — a README that hides a limit
R2  badge order, kind slug and surface statuses match the files — a badge that outranks the table
R3  a ✅ row carries a dated `Last verified` — an unproven claim
R4  the network badge is present and not `none` for a networked plugin — an undisclosed request
R5  every invoked binary has a Requirements row and a symptom line — a plugin that never fires
R6  every environment variable the scripts read is named — an undiscoverable knob
R7  each shape template differs from the master only where it may — template rot
R8  the root catalog lists every plugin, sorted, with its display name — a stale catalog row
R9  no eval score table and no `Δ` column — numbers that go stale silently
R10  a plugin whose hooks run `bash` marks Windows without Git Bash ❌ — a silent no-op on Windows
R11  every `/<id>:<skill>` in the Skills table exists — a dead slash command
R12  `SECURITY.md` and `CODE_OF_CONDUCT.md` keep their templates' sections — policy drift
R13  the Cowork badge does not outrank a skill's `compatibility` — a contradicted claim
R14  each catalog status is the collapse of the Compatibility rows — ambiguous statuses
B1  shebangs, commands, grants and imports stay inside the runtime boundary — a plugin that assumes uv
W1  a workflow's `meta` is literal, its phases declared, its body runs — a workflow that throws
E1  a suite has a README, three cases and one must-not-fire case — a vanity suite
E2  every case has a prompt and at least one grader — a case that cannot fail
E3  `results/` is git-ignored and never tracked — run output in the repository
E4  the suite README names the plugin and states the CI policy — a suite that claims to gate
G1  `labels.json` shape, required labels and the generated dropdown — taxonomy drift
G2  `uses:` pinned to a SHA, `CLAUDE_CODE_VERSION` equal, `make` invoked — DEBT-0004
G3  tool pins agree across the lock, the floors and the workflows — a silent mismatch
V1  a runtime file changed since the plugin's tag but `version` did not (ADR-0003)
V2  a manifest version lower than the one already published
V3  a plugin's first release numbered something other than 0.1.0
V4  a plugin directory removed with no `renames` entry mapping it to null
V5  a removal with no prior deprecation release (warning)
V6  `claude plugin tag --dry-run` would refuse an untagged version
T1  `templates/**` pass R and S with `{{…}}` tolerated — template rot (templates test)
Q1  the quality floor: no per-file config, no downgraded rule — a seeded `extend-ignore` (hygiene test, step 6)
Q2  the rigor floor: the repo policy is at least the global one — global drift (hygiene test, step 6)
Q3  no suppressions in code files — a silenced finding (hygiene test, step 6)
X1  one home per canonical table — duplicated policy (hygiene test, step 6)
X2  vendored schemas are SHA-256 pinned — a silent edit (hygiene test, step 6)
X3  accepted ADRs are append-only — rewritten history (hygiene test, step 6)
X4  no stale Node tooling references — documentation that names a deleted tool (hygiene test, step 6)
X5  LICENSE, CODE_OF_CONDUCT and SECURITY are verbatim to their templates — license detection (hygiene test, step 6)
```

- [x] `make validate` exit 0 on the tree after the exempt-file fixes

```text
.venv/bin/python -m scripts.marketplace.validate_marketplace
marketplace catalog: M1-M10 pass
.venv/bin/python -m scripts.plugin_validation.validate_plugins
B1 plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py: declares a shebang but is not tracked as 100755 (DEBT-0029)
G2 .github/workflows/ci.yml: the gate workflow runs no `make` target, so CI and `make check` can drift (advisory until step 7)
plugins: every invariant passes (2 warning(s))
```

- [x] `make -s versions` still prints five `exempt` lines and `Computed label: bump: none`

```text
agent-self-knowledge 0.1.0 exempt
block-no-verify 0.1.2 exempt
ruff-quality 0.1.1 exempt
shell-quality 0.1.1 exempt
verify-completion 0.1.1 exempt
Computed label: bump: none
```

### Exempt files edited, and the invariant that refused each one

| File | ID that fired | Edit |
| --- | --- | --- |
| `plugins/{agent-self-knowledge,block-no-verify,ruff-quality,shell-quality,verify-completion}/README.md` | R9 | the eval score table (and its `Δ` column) moved verbatim to `docs/audits/2026-09-20-<plugin>-eval.md`, replaced by the §A10 sentence |
| `plugins/agent-self-knowledge/README.md` | R5 | a `curl` Requirements row (minimum 7.64, check `curl --version`) and a Limitations row naming the symptom; `curl` is invoked by the skill's `allowed-tools` grant |
| `plugins/block-no-verify/README.md` | R5 | a Limitations row naming the symptom of a missing `jq` |
| `plugins/shell-quality/README.md` | R5 | a Limitations row naming the symptom of a missing `git` |
| `plugins/{ruff-quality,shell-quality,verify-completion}/README.md` | R6 | `BNV_TEST_BASH` documented (their suites read it as the fallback); the `npm test` sentence replaced by the `make check` one (§A10) |
| `plugins/shell-quality/README.md` | R6 | `SHELLCHECK_BIN` and `SHFMT_BIN` documented; the gate reads both |
| `plugins/{block-no-verify,ruff-quality,shell-quality,verify-completion}/CHANGELOG.md` | C1 | the second release's footer link changed from `tree/` to `compare/<prev>...<tag>`; footer links only, which C2 allows |

No plugin runtime file was touched: `make -s versions` prints five `exempt` lines above.

### Probe table — every negative probe of Part D §5 that belongs to this step

`.venv/bin/python -m pytest -m slow -vv -k probe` (14 parametrised cases; each asserts the
ID fires with the defect present and is gone once it is removed):

| Probe | ID | Fires, then passes after removal |
| --- | --- | --- |
| matcher `Write\|Edit[` | H2 | PASSED |
| hook `command` set to `""` | H4 | PASSED |
| fragment command pointing at a missing shipped file | H5 | PASSED |
| `description: a: b` | S1 | PASSED |
| eval suite with no must-not-fire case | E1 | PASSED |
| `#!/usr/bin/env -S uv run --script` shebang | B1 | PASSED |
| workflow with a syntax error | W1 | PASSED |
| workflow whose `meta` is not a literal | W1 | PASSED |
| workflow using an undeclared phase | W1 | PASSED |
| workflow using `import(` | W1 | PASSED |
| rewritten released CHANGELOG body | C2 | PASSED |
| README with a `Δ` column | R9 | PASSED |
| `**Kind:**` line that disagrees with the files | P1 | PASSED |
| `{{placeholder}}` in a shipped file | P4 | PASSED |

```text
===================== 15 passed, 651 deselected in 15.74s ======================
```

- [x] `make validate-cli` exit 0

```text
.venv/bin/python -m scripts.plugin_validation.validate_claude
pass  claude plugin validate . --strict
      Validating marketplace manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/.claude-plugin/marketplace.json
      
      ✔ Validation passed
pass  claude plugin validate plugins/agent-self-knowledge --strict
      Validating plugin manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/plugins/agent-self-knowledge/.claude-plugin/plugin.json
      
      ✔ Validation passed
pass  claude plugin validate plugins/block-no-verify --strict
      Validating plugin manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/plugins/block-no-verify/.claude-plugin/plugin.json
      
      ✔ Validation passed
pass  claude plugin validate plugins/ruff-quality --strict
      Validating plugin manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/plugins/ruff-quality/.claude-plugin/plugin.json
      
      ✔ Validation passed
pass  claude plugin validate plugins/shell-quality --strict
      Validating plugin manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/plugins/shell-quality/.claude-plugin/plugin.json
      
      ✔ Validation passed
pass  claude plugin validate plugins/verify-completion --strict
      Validating plugin manifest: /Users/nerymurillohnd/projects/marketplace/claude-essentials/plugins/verify-completion/.claude-plugin/plugin.json
      
      ✔ Validation passed
```

- [x] `make test-slow` exit 0 — `TEST_SLOW_RC=0`

```text
121 passed, 545 deselected, 2 warnings in 63.78s (0:01:03)
pass  plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh  [/opt/homebrew/bin/bash]  PASS
pass  plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh  [/bin/bash]  PASS
pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh  [/opt/homebrew/bin/bash]  PASS
pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh  [/bin/bash]  PASS
pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh  [/opt/homebrew/bin/bash]  PASS
pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh  [/bin/bash]  PASS
pass  plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh  [/opt/homebrew/bin/bash]  PASS
pass  plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh  [/bin/bash]  PASS
pass  plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh  [/opt/homebrew/bin/bash]  PASS
pass  plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh  [/bin/bash]  PASS
pass  plugins/verify-completion/scripts/test-hooks.sh  [/opt/homebrew/bin/bash]  125 passed, 0 failed
pass  plugins/verify-completion/scripts/test-hooks.sh  [/bin/bash]  125 passed, 0 failed
```

Twelve (suite × interpreter) pairs, 6 of them under `/bin/bash`, which is the bash 3.2 floor
the plugins target. `pytest -m slow -v -k plugin_suites` parametrises its smoke over the same
interpreters, so the `/bin/bash` id appears in its verbose output.

- [x] the plugin Python floor run (advisory, `DEBT-0029`)

```text
DEBT-0029 advisory: uv python install 3.7 -> exit 2: error: No download found for request: cpython-3.7-macos-aarch64-none
DEBT-0029 advisory: agent-self-knowledge: 3.7 is not downloadable; falling back to the lowest uv offers, 3.8
DEBT-0029 advisory: agent-self-knowledge: interpreter /Users/nerymurillohnd/.local/share/uv/python/cpython-3.8-macos-aarch64-none/bin/python3.8 (Python 3.8)
DEBT-0029 advisory: plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py --help -> exit 0
```

`uv` publishes no CPython 3.7 build for this platform, so the runner falls back to the lowest
version it does offer and says so. The advisory prefix means the outcome never changes the
target's exit status; `DEBT-0029` records the gap and Follow-up PR #1 closes it.

- [x] `make generate lint types test-fast` exit 0 — `544 passed, 122 deselected` (fast), `0 errors, 0 warnings, 0 notes` (basedpyright)

### Follow-up PR #1 findings (reported, not fixed here)

- **B1 warning:** `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py`
  declares `#!/usr/bin/env python3` but is tracked `100644` (`EXE001` shape). Tagged
  `DEBT-0029`; fixing it is a runtime edit and needs a version bump.
- **Declared floor is not the tested floor.** The README advertises Python 3.7; uv can only
  install 3.8 or newer, so the advisory run exercises 3.8. Either the floor moves or the
  README states which version is actually verified.
- **`verify-completion` README** still shows `claude plugin eval … --scaffold` in its
  maintainer block; the plugin ships no scaffold (§A13). Left for step 11, which owns that
  sweep, because the line is documentation rather than an invariant this step enforces.
- **`.claude/rules/plugin-authoring.md`** tells the author to keep the README eval table up
  to date, which R9 now forbids, and still names `npm run check` and `scripts/lib/*.mjs`.
  Step 10 rewrites that file.
- **G2 on `ci.yml`** stays a warning: the gate workflow invokes no `make` target yet. Step 7
  switches CI and closes it.

### Decisions beyond the plan, and why

- **`test_vars.py` was not created.** Its content (the `*_TEST_BASH` rules) lives in
  `script_env.py` beside the extraction it depends on. pytest collects every module named
  `test_*.py`, so a module with that name would be imported as a test file and its helper
  `test_bash_vars` collected as a test; the helper is therefore named
  `suite_interpreter_vars`, with the reason recorded in its docstring.
- **`scripts/common/javascript.py` is new.** Both `hook_contract` (H2) and `workflows` (W1)
  compile JavaScript, so the V8 entry point is a generic helper in `common/` rather than a
  private function one area reaches into (SLF001 would refuse the alternative).
- **`validate` also uncomments the step-4 line.** `make validate` is specified in §A7 as
  running `validate_marketplace` **and** `validate_plugins`; the marketplace line was left
  commented at step 4, so the target would have run only half of what its help text claims.
- **T1 is listed, not run by `make validate`.** §A5 and plan B both place T1 in
  `test_templates.py`. `--list` prints it with the note `(templates test)`, the way Q1-Q3 and
  X1-X5 carry `(hygiene test, step 6)`. The test records the one family the templates still
  fire, R9 (the master template's eval table), as an exact pending set that step 11 closes:
  a new finding fails the test, and so does removing one without updating the set.
- **R12 checks structure, not verbatim wording.** A filled-in `{{PLACEHOLDER}}` re-wraps the
  paragraph around it, so a line-by-line comparison of `SECURITY.md` and `CODE_OF_CONDUCT.md`
  against their templates reports differences that are not drift (measured: 12 such findings,
  every one a re-wrap or a deliberate substitution). R12 therefore asserts every non-optional
  section of the template is present, in order, with no surviving placeholder; X5
  (`scripts/hygiene/test_legal_text.py`, step 6) keeps the verbatim check, which also keeps
  one home per rule (X1).
- **R14's collapse excludes cloud-session rows.** A row naming a deployment variant rather
  than a platform (`Claude Code cloud sessions`) never decides the catalog status on its own;
  with it included, `ruff-quality` and `shell-quality` would have to show ⚠️ where their rows
  read 🧪. Verified against all five plugins: the collapse reproduces every catalog cell.
- **The 33 documented hook events** were counted from the live `hooks.md` headings
  (`SessionStart` to `ElicitationResult`). Plan B says 32 and the step brief says 34; the
  measured number is recorded in `HOOK_EVENTS` with its docs date, and an undocumented event
  is a warning, never an error.
- **Skill frontmatter has 20 documented keys, subagents 18** (counted from the reference
  tables on 2026-09-21). `when_to_use` is one of the 20.
- **`SessionEnd` timeouts.** The reference documents a shared 1.5 s budget that a longer
  per-hook `timeout` raises, up to 60 s. H6 therefore warns between those two numbers and
  fails above 60 s, rather than refusing every documented configuration.
- **H5 does not resolve `$CLAUDE_PROJECT_DIR`.** That path names a file the plugin's own
  installer writes into a user's project later, so it cannot exist here;
  `block-no-verify`'s settings fragment relies on the exemption, and a test pins it.

### Tree at the end of step 5 (nothing committed)

```text
$ git status --short
## refactor/python-toolchain-and-governance
 M Makefile
 M docs/maintenance/pending-debt.md
 M docs/superpowers/specs/2026-09-21-refactor-migration-log.md
 M plugins/agent-self-knowledge/README.md
 M plugins/block-no-verify/CHANGELOG.md
 M plugins/block-no-verify/README.md
 M plugins/ruff-quality/CHANGELOG.md
 M plugins/ruff-quality/README.md
 M plugins/shell-quality/CHANGELOG.md
 M plugins/shell-quality/README.md
 M plugins/verify-completion/CHANGELOG.md
 M plugins/verify-completion/README.md
?? docs/audits/2026-09-20-agent-self-knowledge-eval.md
?? docs/audits/2026-09-20-block-no-verify-eval.md
?? docs/audits/2026-09-20-ruff-quality-eval.md
?? docs/audits/2026-09-20-shell-quality-eval.md
?? docs/audits/2026-09-20-verify-completion-eval.md
?? scripts/common/javascript.py
?? scripts/common/test_javascript.py
?? scripts/plugin_validation/claude_cli.py
?? scripts/plugin_validation/cli_coverage.py
?? scripts/plugin_validation/conftest.py
?? scripts/plugin_validation/evals.py
?? scripts/plugin_validation/frontmatter.py
?? scripts/plugin_validation/hook_contract.py
?? scripts/plugin_validation/kind.py
?? scripts/plugin_validation/readme_contract.py
?? scripts/plugin_validation/run_plugin_suites.py
?? scripts/plugin_validation/runtime_boundary.py
?? scripts/plugin_validation/script_env.py
?? scripts/plugin_validation/test_claude_cli.py
?? scripts/plugin_validation/test_cli_coverage.py
?? scripts/plugin_validation/test_evals.py
?? scripts/plugin_validation/test_frontmatter.py
?? scripts/plugin_validation/test_hook_contract.py
?? scripts/plugin_validation/test_kind.py
?? scripts/plugin_validation/test_readme_contract.py
?? scripts/plugin_validation/test_run_plugin_suites.py
?? scripts/plugin_validation/test_runtime_boundary.py
?? scripts/plugin_validation/test_script_env.py
?? scripts/plugin_validation/test_templates.py
?? scripts/plugin_validation/test_validate_claude.py
?? scripts/plugin_validation/test_validate_plugins.py
?? scripts/plugin_validation/test_workflows.py
?? scripts/plugin_validation/validate_claude.py
?? scripts/plugin_validation/validate_plugins.py
?? scripts/plugin_validation/workflows.py
```

```text
$ git diff --stat
 Makefile                                           |   8 +-
 docs/maintenance/pending-debt.md                   |  14 +
 .../specs/2026-09-21-refactor-migration-log.md     | 318 ++++++++++++++++++++-
 plugins/agent-self-knowledge/README.md             |  17 +-
 plugins/block-no-verify/CHANGELOG.md               |   2 +-
 plugins/block-no-verify/README.md                  |  10 +-
 plugins/ruff-quality/CHANGELOG.md                  |   2 +-
 plugins/ruff-quality/README.md                     |  15 +-
 plugins/shell-quality/CHANGELOG.md                 |   2 +-
 plugins/shell-quality/README.md                    |  20 +-
 plugins/verify-completion/CHANGELOG.md             |   2 +-
 plugins/verify-completion/README.md                |  25 +-
 12 files changed, 357 insertions(+), 78 deletions(-)
```

### Orchestrator verification of gate 5 (2026-09-21)

- Re-ran `make generate lint types test-fast` → clean, `0 errors, 0 warnings, 0 notes`, `544 passed, 122 deselected`; `pytest -m slow` → .................................................                        [100%]; `make validate` rc 0 with the two advisory warnings (B1 DEBT-0029 on `ccdocs.py`, G2 advisory until step 7); `make validate-cli` → `✔ Validation passed` on the marketplace and the five plugins; `--list` prints 67 IDs; the 14 negative probes plus the clean-fixture control pass (`test_probe_fires_and_then_stops[...]`).
- `make -s versions` → five `exempt` lines, `Computed label: bump: none`: the plugin edits (five READMEs: eval tables moved to `docs/audits/2026-09-20-<plugin>-eval.md`, R5 rows and symptoms added; four CHANGELOG footers to the `compare/` style) are exempt.
- Pytest emits two third-party `DeprecationWarning`s from `py_mini_racer` (ctypes `_pack_` layout, slated for Python 3.19); not silenced, tracked for the next mini-racer upgrade.
- Carried to step 11: one README sentence reads "**Behavioural evals** — Behavioural evals live in…" (duplicated opener) in the five READMEs; reword during README normalization.
- The agent's session was interrupted once by a network failure (ENOTFOUND) and resumed from its transcript; every file was re-read before completion.

---

## Gate 6 — `scripts/lint/`, `scripts/harness/`, `scripts/hygiene/` → full gate (2026-09-21)

Ported: `scripts/lint/` (`tools`, `shell_files`, `json_files`, `text_files`, `workflows_files`
and the `lint_files` entrypoint), `scripts/harness/` (`inventory` plus sixteen suites over
`.claude/`, `.vscode/` and the `Makefile`) and `scripts/hygiene/` (ten repository-wide
invariant suites), each with a sibling `test_*.py`. The `Makefile` lines marked
`# ported at step 6` are uncommented and every non-`setup` target now waits on a `.venv`
prerequisite that fails closed. Step 6 also delivers the commit guard step 8 had planned
(see the deviation below), because the Biome guard it replaces cannot coexist with canonical
JSON.

### Deviations from the plan, and why

| # | Deviation | Reason |
| --- | --- | --- |
| 1 | Both Biome halves of step 8 are delivered here: `.claude/hooks/guard-commit.sh` (with `guard-commit-biome.sh` as a three-line `exec` shim) and the text branch of `post-edit.sh` | The old guard runs Biome over every staged, modified and untracked JSON file and rejects `json.dumps(indent=2)` output, so **no canonical JSON could be committed while it was live**; the `PostToolUse` branch rewrote canonical JSON back to Biome's form after any call that touched it, so the churn could not survive its own verification either. `.claude/settings.json`'s hooks block is untouched; it still names the shim's path until the session restarts at step 8. See the addendum below |
| 2 | New module `scripts/common/environment.py` (`in_github_actions`), not in the §A5 file list | Measured on this machine: `~/.zshenv` line 127 exports `GITHUB_ACTIONS=true`, so reading that variable alone would have skipped **Q2 on the one machine Q2 exists for** and sent zizmor to the network locally. The helper requires the flag *and* a run identifier (`GITHUB_RUN_ID`, `GITHUB_WORKFLOW`, `GITHUB_EVENT_NAME`) |
| 3 | New helper `scripts.common.plugins.working_files` | `tracked_files` answers from the index, which is what a validator wants; a linter needs everything a commit could include, minus tracked paths deleted from the tree |
| 4 | Lint IDs are `L1`–`L6`, not `L1`–`L4` | The plan gives `--staged` the Ruff and basedpyright checks but no IDs for them. `L5` (Ruff) and `L6` (basedpyright) carry the tool's own output, so a denied commit names the finding |
| 5 | `validate_plugins --list` prints the lint registry too, and the `(hygiene test, step 6)` note becomes the test's path | One registry for every ID a maintainer can read out of gate output (P1). `LINT_INVARIANTS` lives in `lint_files.py`; `validate_plugins` renders it |
| 6 | `test_governance_map` lives inside `scripts/harness/test_scaffold_map.py` | §A5's file list has no `test_governance_map.py`; the two checks are added as functions so the list stays as written |
| 7 | `check` and `help` gained `##` comments | `make help` is built from those comments and must list every target; §A7's block leaves both undocumented |
| 8 | `test_checklists` requires `id` and `text`, not `id` and `title` | The committed checklists use `text`; the gate reads what the files carry |
| 9 | `Q3`'s shell sweep excludes `plugins/*/test-*.sh` and `plugins/*/tests/*.sh` | Their content is sample text for the guard under test (`shell-quality`'s suite writes `# shellcheck disable=all` to assert its hook denies it), and ADR-0003 already classes them as files Claude never loads. **Recorded defect**: three of them open with a file-wide `# shellcheck disable=SC2016`, which is real and belongs to the plugin follow-up, not to a tooling migration forbidden to touch plugin files |
| 10 | `P4`'s repository-wide sweep ignores placeholders inside backtick code spans, and covers `.claude/`, `.github/`, the root Markdown and the instruction files rather than everything | The contributing guide and the auditor have to be able to *name* `{{…}}`; `docs/` records historical plans and `scripts/` uses `{{` in f-strings |
| 11 | `X1` pins six signatures and records two the plan names but the tree does not carry yet | The push-route matrix and the registration contract are written at steps 11 and 10. `PENDING` names both so the list cannot look finished |
| 12 | `X4`'s sweep exempts `scripts/*/test_*.py` | Measured: five occurrences, each the check itself (two assertions that a deny text does **not** name `.mjs`/`npm run`, a fixture seeding `npx` for B1, one parametrised example of the `npm run validate` a checklist still carries, one docstring about the Biome branch) |
| 13 | `X5` records that `SECURITY.md`'s template pins **0** paragraphs | That template is placeholders throughout, so there is no shared wording; the count is recorded rather than hidden, and R12 covers its structure |

### Checklist

- [x] `time make check` exit 0, wall time recorded

  ```text
  $ time make check
  ...
  250 passed, 875 deselected, 2 warnings in 83.70s (0:01:23)
  .venv/bin/python -m scripts.plugin_validation.run_plugin_suites
  pass  plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh  [/opt/homebrew/bin/bash]  PASS
  pass  plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh  [/bin/bash]  PASS
  pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh  [/opt/homebrew/bin/bash]  PASS
  pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh  [/bin/bash]  PASS
  pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh  [/opt/homebrew/bin/bash]  PASS
  pass  plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh  [/bin/bash]  PASS
  pass  plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh  [/opt/homebrew/bin/bash]  PASS
  pass  plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh  [/bin/bash]  PASS
  pass  plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh  [/opt/homebrew/bin/bash]  PASS
  pass  plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh  [/bin/bash]  PASS
  pass  plugins/verify-completion/scripts/test-hooks.sh  [/opt/homebrew/bin/bash]  125 passed, 0 failed
  pass  plugins/verify-completion/scripts/test-hooks.sh  [/bin/bash]  125 passed, 0 failed
  DEBT-0029 advisory: uv python install 3.7 -> exit 2: error: No download found for request: cpython-3.7-macos-aarch64-none
  DEBT-0029 advisory: agent-self-knowledge: 3.7 is not downloadable; falling back to the lowest uv offers, 3.8
  DEBT-0029 advisory: agent-self-knowledge: interpreter .../cpython-3.8-macos-aarch64-none/bin/python3.8 (Python 3.8)
  DEBT-0029 advisory: plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py --help -> exit 0
  exit=0
  make check  192.59s user 175.62s system 98% cpu 6:12.24 total
  ```

- [x] `make help` lists every target (GNU Make 3.81, the macOS system make)

  ```text
  $ make --version | head -1
  GNU Make 3.81
  $ make help
  setup — create/refresh .venv from uv.lock (the only target that calls uv)
  check — the whole gate, in order
  generate — 10 regenerate catalog + issue forms, then fail on diff
  lint — 20 ruff format --check + ruff check (explicit .py list), shell, json, text bytes, actionlint, zizmor
  lint-staged — same checks, only on staged + modified + untracked files (guard-commit)
  types — 30 basedpyright, typeCheckingMode=all + failOnWarnings, venv interpreter, GitHub annotations in CI
  test-fast — 40 in-process tests
  validate — 50 catalog + plugin invariants (M P C S H R B W E G T Q X)
  validate-cli — 60 claude plugin validate --strict on marketplace + every plugin
  test-slow — 70 process-spawning tests + plugin suites under bash and /bin/bash + plugin Python under its floor
  versions — version-bump rules and route vs the latest tags / origin/main
  fix — writer: ruff format, ruff check --fix (safe), shfmt -w, canonical JSON
  fix-file — writer for one file (post-edit hook): make fix-file FILE=path
  clean — prune .claude/.cache/hooks stamps and stale state
  help — list every target with what it does
  ```

- [x] `make fix && make lint` idempotent; `git status --porcelain` identical before and after

  ```text
  $ git status --porcelain > /tmp/before.txt && make fix && git status --porcelain > /tmp/after.txt && diff /tmp/before.txt /tmp/after.txt
  .venv/bin/python -m scripts.lint.lint_files --fix
  lint --fix: 0 file(s)
  IDENTICAL: git status --porcelain unchanged by a second make fix
  $ make -s lint
  G2 .github/workflows: G2 advisory (step 7): zizmor --persona=auditor reports 24 findings (3 unsafe fixes): 6 informational, 9 low, 3 medium, 6 high
  lint: every file passes (1 warning(s))
  ```

- [x] collection count recorded; exactly one test skips inside the gate

  ```text
  $ .venv/bin/python -m pytest --collect-only -q | awk -F': ' '{s+=$2} END {print "total collected:", s, "in", NR, "files"}'
  total collected: 1125 in 70 files
  $ .venv/bin/python -m pytest -q -rs
  SKIPPED [1] scripts/harness/test_harness_index.py:25: enabled at step 10 when the index tables exist
  SKIPPED [1] scripts/plugin_validation/test_cli_coverage.py:65: CLAUDE_CODE_DOCS_DIR is not set
  ```

  The second skip carries `@pytest.mark.coverage_matrix`, so it is deselected by both halves
  of the gate (`make test-fast` runs `-m "not slow and not coverage_matrix"`, `make test-slow`
  runs `-m slow`) and the nightly job is what runs it. Inside `make check` the only skip is
  `test_harness_index`. **Q2 is not skipped on this machine**: `scripts/hygiene/test_rigor_floor.py`
  reports `11 passed`, which is what deviation 2 exists for.

- [x] Q1, Q2, Q3, X1–X5 and P4 each fail on their seeded defect and pass clean

  ```text
  probe                                                      | test                                            | seeded | clean
  Q1 a re-created ruff.toml                                  | test_quality_floor::test_no_competing_configuration_file_exists | FAILED | PASSED
  Q1 reportAny = false in [tool.basedpyright]                | test_quality_floor::test_only_the_pre_declared_rule_is_downgraded | FAILED | PASSED
  Q1 a disable= in .shellcheckrc                             | test_quality_floor::test_the_shellcheck_policy_disables_nothing | FAILED | PASSED
  Q2 an extra ignore this repository alone carries           | test_rigor_floor::test_this_repository_ignores_nothing_extra | FAILED | PASSED
  Q3 a # noqa in a maintainer module                         | test_suppressions.py                            | FAILED | PASSED
  Q3 a .basedpyright baseline directory                      | test_quality_floor::test_no_basedpyright_baseline_directory_exists | FAILED | PASSED
  X1 a second copy of the label taxonomy                     | test_single_home.py                             | FAILED | PASSED
  X2 an edited vendored schema                               | test_vendored_files.py                          | FAILED | PASSED
  X3 a line removed from an accepted ADR                     | test_adr_append_only.py                         | FAILED | PASSED
  X4 an npm instruction in the Makefile                      | test_tooling_alignment.py                       | FAILED | PASSED
  X5 a reformatted plugin LICENSE                            | test_legal_text::test_every_plugin_license_is_the_template_verbatim | FAILED | PASSED
  X5 a reworded paragraph in CODE_OF_CONDUCT.md              | test_legal_text::test_every_unparameterised_paragraph_survives_the_copy | FAILED | PASSED
  P4 a template placeholder in a live instruction file       | test_placeholders.py                            | FAILED | PASSED
  ```

  Two probes had to be rewritten before they fired, and both rewrites are about the probe,
  not the check: appending `reportAny = false` to the end of `pyproject.toml` lands in
  `[tool.pytest.ini_options]`, not `[tool.basedpyright]`; and the two pledge paragraphs of the
  Code of Conduct carry placeholders, so X5 compares the other eighteen.

- [x] `actionlint` clean; the zizmor advisory line; `test_workflow_pins` and `test_governance_map`

  ```text
  $ .venv/bin/actionlint -no-color .github/workflows/*.yml
  actionlint exit=0
  $ zizmor --persona=auditor --format plain (through scripts.lint.workflows_files)
  24 findings (3 unsafe fixes): 6 informational, 9 low, 3 medium, 6 high
  $ .venv/bin/python -m pytest scripts/hygiene/test_workflow_pins.py scripts/harness/test_scaffold_map.py -v
  scripts/hygiene/test_workflow_pins.py::test_this_repository_has_workflows_to_check PASSED
  scripts/hygiene/test_workflow_pins.py::test_every_action_reference_is_a_pinned_commit PASSED
  scripts/hygiene/test_workflow_pins.py::test_the_pin_check_reads_every_workflow PASSED
  scripts/harness/test_scaffold_map.py::test_the_map_names_every_area_on_disk PASSED
  scripts/harness/test_scaffold_map.py::test_the_map_names_no_area_that_is_gone PASSED
  scripts/harness/test_scaffold_map.py::test_the_tree_block_matches_the_areas PASSED
  scripts/harness/test_scaffold_map.py::test_governance_map_every_module_has_a_sibling_test PASSED
  scripts/harness/test_scaffold_map.py::test_governance_map_every_test_carries_at_most_one_marker PASSED
  scripts/harness/test_scaffold_map.py::test_every_marker_used_is_declared PASSED
  9 passed in 0.19s
  ```

  Zero zizmor ignore comments exist today, so the ignore policy passes trivially;
  `ZIZMOR_BLOCKING = False` is pinned by `test_zizmor_stays_advisory_until_the_workflows_are_rewritten`.

- [x] the three Gate 8 guard-commit payload smoke tests, run by hand

  ```text
  $ printf '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"},"cwd":"%s","session_id":"t"}' "$PWD" | .claude/hooks/guard-commit.sh; echo rc=$?
  rc=0
  $ ... | GUARD_COMMIT_LINT_CMD='echo bad; exit 1' .claude/hooks/guard-commit.sh
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Commit refused: the files this commit could include (staged, modified or untracked) fail `make lint-staged`. Fix them — `make fix` applies every safe rewrite — then commit again:\nbad"
    }
  }
  rc=0
  $ (in a working-tree copy with no .venv) ... | .../guard-commit.sh
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Commit refused: the project environment is missing (.../novenv/.venv/bin/python). The gate cannot run, so the commit is not checked. Run `make setup`, then commit again."
    }
  }
  rc=0
  $ time make -s lint-staged
  make -s lint-staged  2.98s user 0.23s system 180% cpu 1.779 total
  ```

  Both entry points behave identically: `scripts/harness/test_guard_commit.py` runs every case
  through `guard-commit.sh` and through the shim, under `bash` and `/bin/bash` (21 tests).

- [x] `.venv` prerequisite probe, in a working-tree copy with no environment

  ```text
  $ make versions
  error: .venv is missing; run `make setup`
  make: *** [.venv/bin/python] Error 2
  rc=2
  $ make types
  error: .venv is missing; run `make setup`
  make: *** [.venv/bin/python] Error 2
  rc=2
  ```

  The probe uses a copy of the working tree rather than `git clone`: the step-6 `Makefile` and
  `guard-commit.sh` are not committed yet, so a clone would test the step-5 file.

- [x] canonical-JSON churn measured, then applied; `make -s versions` still `bump: none`

  ```text
  $ .venv/bin/python -m scripts.lint.lint_files --fix --dry-run
  would rewrite .claude/settings.json
  would rewrite .github/labels.json
  would rewrite .vscode/launch.json
  would rewrite .vscode/settings.json
  would rewrite .vscode/tasks.json
  would rewrite plugins/verify-completion/.claude-plugin/plugin.json
  would rewrite templates/plugin-agent-only/.claude-plugin/plugin.json
  would rewrite templates/plugin-bundle/.claude-plugin/plugin.json
  would rewrite templates/plugin-skill-only/.claude-plugin/plugin.json
  lint --fix: 9 file(s)
  $ make -s versions
  agent-self-knowledge 0.1.0 exempt
  block-no-verify 0.1.2 exempt
  ruff-quality 0.1.1 exempt
  shell-quality 0.1.1 exempt
  verify-completion 0.1.1 exempt
  Computed label: bump: none
  ```

  Nine files, not the seven gate 2 predicted. `.vscode/launch.json` and `.vscode/tasks.json`
  were written after that measurement and were never canonical; `.vscode/settings.json` is
  canonical again after the step-6 edit, because the **legacy `post-edit.sh` Biome branch
  collapsed its short arrays** the moment a Bash call touched it. That is the same conflict
  deviation 1 is about: while Biome is still the `PostToolUse` writer, it re-collapses
  canonical JSON after every command that rewrites it, so `make fix` is followed by pruning
  the session's `bash-stamp-*` (which `make clean` prunes anyway, and which makes
  `post-edit.sh` exit early). `make lint` is what then proves the form held. The Node-era
  files (`package.json`, `package-lock.json`, `biome.json`, `knip.jsonc`, `tsconfig.json`,
  `.mcp.json`, `schemas/claude-code/**`, `schemas/*.schema.json`) and the vendored
  `schemas/github/**` are excluded by `JSON_EXCLUDED` and were not touched.

- [x] final state

  ```text
  $ git diff --stat
   .claude/hooks/guard-commit-biome.sh                | 72 +---------------------
   .claude/hooks/guard-marketplace-catalog.sh         |  2 +-
   .claude/settings.json                              |  4 +-
   .claude/skills/marketplace-governance/SKILL.md     | 68 +++++++-------------
   .github/labels.json                                | 12 +++-
   .vscode/launch.json                                |  4 +-
   .vscode/settings.json                              |  6 +-
   .vscode/tasks.json                                 | 66 +++++++++++++++-----
   Makefile                                           | 43 +++++++------
   .../verify-completion/.claude-plugin/plugin.json   |  6 +-
   scripts/common/plugins.py                          | 41 ++++++++++++
   scripts/common/test_plugins.py                     | 32 ++++++++++
   scripts/plugin_validation/validate_plugins.py      | 35 ++++++++---
   .../plugin-agent-only/.claude-plugin/plugin.json   | 12 +++-
   templates/plugin-bundle/.claude-plugin/plugin.json | 12 +++-
   .../plugin-skill-only/.claude-plugin/plugin.json   | 12 +++-
   16 files changed, 251 insertions(+), 176 deletions(-)
  ```

  Plus 46 new files: `.claude/hooks/guard-commit.sh`, `scripts/common/environment.py` and its
  test, and the `scripts/lint/`, `scripts/harness/` and `scripts/hygiene/` modules and suites.
  The churn is left in the working tree for the orchestrator to commit as a formatting-only
  commit before the step commit.

### Addendum — the `post-edit.sh` text branch (2026-09-21)

`lint_biome` and the `biome` file kind are gone. Everything that is not shell now goes through
`make -s fix-file FILE=<rel>`, which is the pipeline's own single-file writer, so the editor,
this hook and `make lint` cannot disagree about one file. The shell branch, the version-bump
reminder and the `MAX_BASH_FILES` logic are unchanged, and every `node_modules`, `Biome` and
`npm` reference is out of the hook (`test_the_hook_names_no_retired_tooling` pins that).

`make fix-file` gained the Python half it needed: `scripts/lint/lint_files.py` now has
`fix_python`, and `--fix --file` writes *and* reports, exiting non-zero on what it could not
repair, because the hook blocks on that output. `--fix` over the whole tree stays a writer,
since `make lint` follows it everywhere. **`ruff check --fix` runs before `ruff format`**,
which is Ruff's documented order and the only one that converges in a single pass: formatting
first leaves the blank lines an unused-import removal opens, so the hook would report a defect
it had just created. Measured before the fix, on a probe with an unused import and bad
spacing: the hook blocked with `L5 ... 1 file would be reformatted`; after it, the file
becomes `"""Probe."""\n\nx = 1\n` and nothing blocks.

A missing `.venv/bin/python` adds context naming `make setup` and never blocks: the edit
itself is fine, and refusing it would say nothing useful.

- [x] the four branch probes, run by hand and then pinned as tests

  ```text
  $ ...Edit payload for scripts/common/plugins.py            -> rc=0, no output
  $ ...Edit payload for a .json in Biome form                -> rc=0, rewritten to the canonical form
  $ ...Edit payload for a .md holding U+0007                 -> decision: block
  {
    "decision": "block",
    "reason": "`make fix-file FILE=.claude/.cache/hooks/_probe.md` reports what it could not rewrite (fix it in code; never silence it):\nlint --fix: 0 file(s)\nL3 .claude/.cache/hooks/_probe.md: line 1 holds U+0007\nmake: *** [fix-file] Error 1"
  }
  $ ...Edit payload for a .py under scripts/ with two defects -> rc=0, file repaired in one pass
  $ .venv/bin/shellcheck -x -f gcc .claude/hooks/post-edit.sh   ; echo $?   -> 0
  $ .venv/bin/shfmt -d .claude/hooks/post-edit.sh               ; echo $?   -> 0
  ```

- [x] the gate is still green with the new branch and its nine new tests

  ```text
  $ PATH=.venv/bin:$PATH .venv/bin/basedpyright --threads
  0 errors, 0 warnings, 0 notes
  $ time make check
  874 passed, 1 skipped, 265 deselected, 2 warnings in 17.45s      # make test-fast
  264 passed, 876 deselected, 2 warnings in 93.40s (0:01:33)       # make test-slow
  exit=0
  make check  199.21s user 190.91s system 99% cpu 6:32.69 total
  $ time make -s lint-staged
  make -s lint-staged  2.00s user 0.23s system 151% cpu 1.471 total
  $ make -s versions
  Computed label: bump: none
  ```

  1140 tests collected, 15 more than before this addendum. The one skip inside the gate is
  still `test_harness_index`. `git status --porcelain` lists 63 paths: the 62 of the gate-6
  checklist plus this log.

### Orchestrator verification of gate 6 (2026-09-22)

- `time make check` → exit 0 in 4:03 (log: all targets, `874 passed, 1 skipped` fast, 264 slow, `✔ Validation passed` on the marketplace and five plugins, plugin suites under `/opt/homebrew/bin/bash` and `/bin/bash`, DEBT-0029 advisory floor run under 3.8).
- `pytest -rs` → exactly one skip: `test_harness_index.py:25: enabled at step 10 when the index tables exist`.
- Commit guard smoke: allow → no output, rc 0; `GUARD_COMMIT_LINT_CMD='echo bad; exit 1'` → `deny` with the lint output. First live pass: commit `6b35fd1` (canonical JSON) went through the shim → `guard-commit.sh` → `make lint-staged`.
- `post-edit.sh`: a Biome-form JSON written through a Write payload came back canonical; the hook has no `biome`/`node_modules` reference left.
- JSON churn committed separately as `6b35fd1`; each file parses to the same content as before (`jq -S` comparison), `make -s versions` → `Computed label: bump: none`.
- Environment finding for the maintainer: `~/.zshenv:127` exports `GITHUB_ACTIONS=true` globally; `scripts/common/environment.py` requires the flag plus a run id before treating a process as CI.
