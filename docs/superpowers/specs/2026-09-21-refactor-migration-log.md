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
