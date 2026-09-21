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
