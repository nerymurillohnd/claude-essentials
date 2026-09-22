# Resolved Debt

Dated historical record of maintenance items resolved after this repo's
initial scaffold. Template: [`templates/resolved-debt-template.md`](../../templates/resolved-debt-template.md).

## Resolved Items

### DEBT-0040 — 2026-09-22 — Onboarding evidence-reader exposed gaps its external source never met

- **Original pending record:** none; found while bringing `evidence-reader` (written outside this repository) under `make check` on 2026-09-22.
- **Resolved debt:** (1) L3's `is_binary` needed a null byte in the first 8 KiB, so the plugin's two fixture PDFs, the first binary files this repository ever tracked, were read as text and failed as "not valid UTF-8". (2) The plugin declared Python 3.9, which no gate checks: `zip(..., strict=True)` passed Ruff and basedpyright (both at 3.14) and broke 7 of 58 extractor cases on `/usr/bin/python3` 3.9.6. (3) Four of its extractors carried `typing.cast` calls with no runtime check before them, the suppression-as-code Q-rule `test_every_cast_is_preceded_by_the_check_that_proves_it` forbids. (4) `image_tool.py` wrote converted pages and crops to a fixed `$TMPDIR/evidence-reader/<sha12>/`, created with the default mode and never checked for ownership or a symlink; on a shared `/tmp` another user could pre-create it and swap the images an agent views (the DEBT-0031 class, found by the release review). (5) The release review's coherence audit and code review found: an uncached formula that referred to another uncached formula corrupted the outer formula's parse (`A1 = B1+5` recomputed as 6), ROUND rounded halves to even and DATE ignored the 1904 date system; tracked changes inside Word table cells were dropped and tracked paragraph marks counted as empty changes; `find --column` searched every cell of a row missing that column; the report gate re-checked a spent handback copy and, with no retry state, could block past its two-retry cap; `${CLAUDE_SKILL_DIR}` in skill reference files, which Claude Code never fills in; untrusted images reached ImageMagick with no named decoder; and the repository had no `.gitattributes`, so git treated the PDFs as text.
- **Resolution:** (1) `scripts/lint/text_files.py` `BINARY_SIGNATURES` (`%PDF-`) is checked before the null-byte rule. (2) The maintainer set the floor to Python 3.14 (2026-09-22), as DEBT-0029 did for agent-self-knowledge: each extractor checks the version when it starts and exits 5 with a message, `check-requirements.sh` probes for 3.14, and the README, SKILL `compatibility` fields and root catalog say 3.14. (3) Each cast became a checked narrowing: typed aliases for `json.loads` and `ET.iterparse` (the repository's `_loads` pattern), `TypeIs` helpers, `isinstance` checks, `int.from_bytes` for the TIFF walk and `math.pow` for `^`. The only new per-file ignores are S314 on the three OOXML extractors, each of which refuses a DTD or entity before parsing; `ALLOWED_PER_FILE_IGNORES` in `scripts/hygiene/test_quality_floor.py` records them. (4) `_work_dir` uses `tempfile.mkdtemp`, which creates a new 0700 folder atomically for each run. (5) `evaluate` restores the caller's tokens and cursor; ROUND uses decimal half-up and DATE shifts by 1462 days under `date1904`; table cells record their tracked changes and `w:pPr` is skipped; a short row has no cell to match; the gate deletes the handback when it blocks and fails open when `stop_hook_active` is true with no retry state; references name scripts by file name, gated by `scripts/plugin_validation/test_skill_supporting_files.py` and a `plugin-authoring.md` rule; every ImageMagick input carries the `<format>:` prefix its magic bytes proved; `.gitattributes` marks the fixture formats binary. Each has a suite case that fails on the previous code, except the streaming `_sheet_layout` and the per-row `clear()`, whose output is unchanged (a case checks it) and whose memory saving no test measures. (6) The completion verifiers found that the suites ran shipped Python with CI's own `python3`, older than the declared 3.14: `run_plugin_suites` now exports `BNV_TEST_PYTHON` (its own interpreter, `scripts/plugin_validation/script_env.py`), tested by `test_a_suite_gets_the_repository_python`, and the evidence-reader suite prints a `skip` line for every case a missing tool skips. (7) The edge verifier found hostile inputs that ended in tracebacks (exit 1, undocumented) or wrong facts with exit 0: formulas with missing arguments, out-of-range DATE years, overflow and deep recursion; malformed sheet XML, styles and `--range`; a DTD or entity in a UTF-16 part, which passed the byte check; text inserted then deleted shown in the original view, and moves shown twice; an unterminated CSV quote that swallowed rows, an ambiguous duplicate column, an invalid `--pattern`; `²` accepted as a digit; file names starting with `-` read as tool options; and control characters that broke the gate's JSON. Each now ends in the documented exit code or the correct value, with a suite case that fails on the previous code.
- **Positive verification:** `make check` exits 0 (2026-09-22); the extractor suite passes 101 of 101 and the hook suite 21 of 21 on bash 3.2 and 5.x with Python 3.14, and `/usr/bin/python3` 3.9.6 gets `<script> needs Python 3.14 or later; this is python3 3.9.6 …` and exit 5 from all seven extractors.
- **Negative verification:** `test_is_binary_recognizes_a_pdf_with_no_null_byte` fails without the signature check. With `_require_python()` removed from `profile_csv.py`, the suite reports `FAIL python floor: profile_csv.py refuses 3.9 with a message` (exit 2 instead of 5). With the old `_work_dir` restored, the suite reports `FAIL image work dir: private and new per run` (`0o755`, reused).
- **Owner or responsible area:** `scripts/lint/text_files.py`, `plugins/evidence-reader/`, `scripts/plugin_validation/suites/evidence-reader/`
- **Residual risk / follow-up:** Users whose `python3` is older than 3.14 (the Xcode Command Line Tools' 3.9.6, Ubuntu 24.04's 3.12, Debian 13's 3.13) cannot use the extractors until they install 3.14. The maintainer accepted this on 2026-09-22 after reviewing the alternative (keep 3.9 and gate it in CI). The plugin README states it.
- **Related records:** [DEBT-0029](#debt-0029--2026-09-22--shipped-plugin-python-is-validated-only-advisorily)
- **Superseded by:** none

### DEBT-0022 — 2026-09-22 — `claude plugin validate --strict` accepts skill frontmatter that no YAML parser can read

- **Original pending record:** `pending-debt.md` DEBT-0022 (opened 2026-09-20): four `SKILL.md` files carried a `description` written as a plain scalar with a colon-space, which the repo's `yaml` dependency rejected while `claude plugin validate --strict` (2.1.278) accepted all four.
- **Resolved debt:** The repository's own gate had no check for this class of malformed frontmatter, so the only local validator that could catch it before publish didn't.
- **Resolution:** `scripts/plugin_validation/frontmatter.py` parses every skill's frontmatter with `yaml.safe_load` and raises invariant S1 on a `yaml.YAMLError`; `scripts/plugin_validation/test_frontmatter.py::test_a_plain_scalar_with_a_colon_breaks_the_parse` reproduces the exact defect (`description: a: b Check`) and asserts S1 fires. Wired into `make validate` (repo-verified 2026-09-22, resolution predates this audit).
- **Positive verification:** `.venv/bin/python -m pytest scripts/plugin_validation/test_frontmatter.py -q -k colon` passes (2026-09-22).
- **Negative verification:** The test itself is the reproduction: it feeds the frontmatter parser text with an unquoted colon-space in a plain scalar and asserts S1 (parse failure), not a pass — the same input class that `claude plugin validate --strict` was shown to accept in the original report.
- **Owner or responsible area:** `scripts/plugin_validation/frontmatter.py`, `scripts/plugin_validation/test_frontmatter.py`
- **Residual risk / follow-up:** The gap between this repo's gate and `claude plugin validate --strict` itself was never reported upstream (the original next action's first half); only the local-gate half was done. Not reopened as pending because the CLI behavior is now moot here — `make validate` fails the case regardless of what `--strict` does.
- **Related records:** [DEBT-0021](pending-debt.md#debt-0021--plugin-name-restrictions-are-undocumented-upstream), [plugin-authoring rule](../../.claude/rules/plugin-authoring.md)
- **Superseded by:** none

### DEBT-0009 — 2026-09-22 — Released CHANGELOG entries are checked against their tagged text

- **Original pending record:** `pending-debt.md` DEBT-0009 (opened 2026-09-18): a seeded-defect test showed a released `## [0.1.0]` entry could be rewritten (a false claim added) while `npm run check` and `npm run check:versions` still passed; only the review skill caught it.
- **Resolved debt:** Nothing in the automated gate compared a tagged CHANGELOG section's current text against what was published at its tag, so a maintained release note could drift from what actually shipped, silently.
- **Resolution:** `scripts/versioning/changelog.py` implements invariant C2 (`check_released_bodies`): for every plugin, every released section whose tag exists is re-read from git at that tag (`released_body_at_tag`) and compared verbatim to the working tree's copy; a mismatch is a finding. `scripts/versioning/test_changelog_immutable.py::test_every_released_section_equals_its_text_at_its_tag` runs C2 against every plugin's real CHANGELOG on the current tree, and its docstring states explicitly: "This is the check DEBT-0009 asked for." It is `@pytest.mark.slow`, so it runs under `make test-slow`, which `make check` includes.
- **Positive verification:** `.venv/bin/python -m pytest scripts/versioning/test_changelog_immutable.py -q` passes (2026-09-22); `make test-slow` is part of `make check`.
- **Negative verification:** `scripts/versioning/test_changelog.py::test_check_released_bodies_catches_a_rewritten_release` seeds a fixture repo with a released section edited after its tag and asserts `check_released_bodies` reports a finding — `.venv/bin/python -m pytest scripts/versioning/test_changelog.py -q -k released_bodies` passes (2026-09-22), reproducing the original seeded-defect failure this debt was opened from and showing it is now caught.
- **Owner or responsible area:** `scripts/versioning/changelog.py`, `scripts/versioning/test_changelog_immutable.py`
- **Residual risk / follow-up:** No override label (an "amend" mechanism for a deliberate typo fix) was added; a genuine correction to a released entry must go under `## [Unreleased]` instead, per C2's own design comment (`changelog.py:12`).
- **Related records:** DEBT-0008 (superseded reference removed; original mjs tooling this debt was filed against no longer exists — `scripts/lib/version-plan.mjs` and `scripts/check-versions.mjs` were replaced by the Python `scripts/versioning/` package during the toolchain migration)
- **Superseded by:** none

### DEBT-0006 — 2026-09-22 — The marketplace catalog accepts `renames: null` for a removed plugin

- **Original pending record:** `pending-debt.md` DEBT-0006 (opened 2026-09-18): `schemas/marketplace.schema.json` typed `renames.additionalProperties` as `{"type": "string"}`, so Ajv rejected `{"renames": {"old": null}}` even though Claude Code's own docs and this repo's `versioning.md` document `null` as the required value for a removed plugin.
- **Resolved debt:** The documented removal flow (map a removed plugin's name to `null` in `renames`) would fail this repo's own validator on the first real removal.
- **Resolution:** The repo's marketplace validation moved off the Ajv/`.mjs` schema entirely to a Python module (`scripts/marketplace/`, `scripts/versioning/version_plan.py`) during the toolchain migration; no `schemas/marketplace.schema.json` file remains in the repository (confirmed: `find . -iname "*.schema.json"` under the repo now returns only `.github/schemas/issue-forms.schema.json` and `.github/schemas/issue-config.schema.json`, neither of which is the marketplace schema). `version_plan.read_renames` is typed `dict[str, str | None]` and reads the map from JSON, where `null` deserializes to `None` natively; `check_renames` (`scripts/marketplace/catalog.py:299`) implements the check, and `scripts/marketplace/validate_marketplace.py:93` states the contract directly: "`renames` values are a string or null; no key still ships; a null has no README row," enforced as invariant M9.
- **Positive verification:** `.venv/bin/python -m pytest scripts/marketplace/test_validate_marketplace.py -q -k renames` and `scripts/marketplace/test_catalog.py -k renames` pass (2026-09-22); both suites build fixtures with `catalog["renames"] = {PLUGIN_ID: None}` (a `null` value) and assert on the *other* M9 conditions (a removed plugin must drop its README row, a still-shipping plugin must not appear in `renames`) rather than on the value's type — i.e. `null` is accepted as a normal case, never the thing under test as a rejection.
- **Negative verification:** `test_check_renames_refuses_a_key_that_still_ships` and `test_m9_fires_on_a_renames_key_that_still_ships` (the latter's docstring: "DEBT-0006: the catalog claimed a rename the tree had not made") confirm M9 still fires on the real defect class (a stale or fabricated rename claim) without rejecting a legitimate `null`.
- **Owner or responsible area:** `scripts/marketplace/catalog.py`, `scripts/versioning/version_plan.py`
- **Residual risk / follow-up:** None; the documented removal flow (`docs/contributing/versioning.md`) is unblocked. This resolution happened somewhere in the Python-toolchain migration (PR #19, merged 2026-09-22) and was not itself recorded in `resolved-debt.md` before this audit — recorded now for the first time.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** none

### DEBT-0038 — 2026-09-22 — `marketplace-governance`'s per-file tables were stale and nothing kept them honest

- **Original pending record:** `pending-debt.md` DEBT-0038 (opened 2026-09-22): the GitHub area table was missing six of its nineteen files, and the skill's own note admitted the tables predated the python-toolchain-and-governance migration (PR #19) with step 10 (rewrite them) explicitly deferred.
- **Resolved debt:** No generator derived the per-area `| File | Function |` tables from disk, so every module added, renamed or removed after the migration silently drifted. Two areas (Lint, Harness) had no table at all — Harness listed one of its nineteen files by name. The Placement Rule also still said "ten areas" against the eight real `scripts/` folders.
- **Resolution:** `scripts/harness/governance_docs.py` reads the first line of every governed module's own docstring (all 122+ non-`__init__.py` files already carried one) and rewrites each area's table between a `<!-- governance-docs:<area> -->` marker pair, module immediately followed by its own test, otherwise alphabetical; wired into `make generate` alongside the catalog and issue-form generators, with its own `git diff --exit-code` path. Lint and Harness got their first-ever tables. The Placement Rule now says "eight areas."
- **Positive verification:** `make check` exits 0 on this branch (`generate`, `lint`, `types`, `test-fast`, `validate`, `validate-cli`, `test-slow`); `scripts/harness/test_governance_docs.py` (14 cases, including `test_the_real_skill_file_is_current` and `test_every_real_area_has_exactly_one_marker_pair`) and the pre-existing `scripts/harness/test_scaffold_map.py` both pass.
- **Negative verification:** `module_rows` raises `MissingDocstringError`/`UnparsableModuleError` on a seeded module with no docstring or a syntax error; `render` raises `MissingMarkerError` when an area's marker pair is removed; reverting the GitHub table to its stale form and rerunning the generator restores the correct nineteen-row table.
- **Owner or responsible area:** `scripts/harness/governance_docs.py`, `.claude/skills/marketplace-governance/SKILL.md`, `Makefile`

### DEBT-0037 — 2026-09-22 — Post-merge audit findings: private paths, stale schema links, an undocumented upgrade

- **Original pending record:** none; `repo-auditor` returned `VERDICT: FAIL` on `a58e326`, and the pull request merged anyway, so these are fixed on a fresh branch per `.claude/rules/plugin-delivery.md`.
- **Resolved debt:**
  1. The migration log carried the maintainer's home directory and a private plan path.
  2. The root README, its template, the contributing guide and the governance skill linked `schemas/`, which moved to `.github/schemas/` or was deleted.
  3. `good first issue` was still documented after it left the taxonomy.
  4. ruff-quality and shell-quality 0.2.0 removed their installer skills without saying how to remove a 0.1.x settings gate.
  5. agent-self-knowledge carried two top alerts, and its catalog row omitted `curl`.
  6. Two READMEs claimed the `enabled` option needs 2.1.269, which the changelog does not back.
- **Resolution:** `scripts/hygiene/test_private_paths.py` refuses the home directory and any path into the private Claude plans folder in every shipped file; the links, label docs (plus an ADR-0004 amendment), upgrade notes, alert and catalog row are corrected; the unbacked version claim is removed. The released 0.2.0 CHANGELOG sections stay as tagged (C2), so the upgrade path lives in the READMEs.
- **Positive verification:** `make check` exits 0 on the fix branch.
- **Negative verification:** `test_private_paths.py` reports the migration log's lines when the unfixed log is restored.
- **Owner or responsible area:** `docs/`, `README.md`, `templates/`, `plugins/{ruff,shell}-quality/README.md`, `plugins/agent-self-knowledge/README.md`

### DEBT-0034 — 2026-09-22 — An eval scaffold counted as a plugin requirement, and a local green never saw it

- **Original pending record:** none; CI on `c5027fb` failed `test_the_binaries_each_plugin_invokes_are_the_ones_its_readme_lists` with `{'bash', 'git', 'jq'} != {'bash', 'jq'}` after `make check` had exited 0 locally.
- **Resolved debt:** Two defects:
  1. `invoked_binaries` (R5) and `env_var_sources` (R6) read every script under the plugin, `evals/` included, so verify-completion's case 02 scaffold (`git init`) made `git` a requirement users would have to install. Only `claude plugin eval` runs a scaffold, on the maintainer's machine.
  2. Every invariant reads the files git tracks, so the scaffold, still untracked when `make check` ran, was invisible locally; CI saw the committed file.
- **Resolution:** `runtime_scripts` in `scripts/plugin_validation/runtime_boundary.py` drops the paths `EXEMPT_FILE` exempts, the same rule that decides a version bump, and feeds R5 and R6; B1 still checks every shipped script. New invariant P6 (`check_untracked` in `validate_plugins.py`) fails on any untracked, non-ignored file under a plugin. Declaring `git` in the README was rejected: it would be false for users.
- **Positive verification:** `make validate` passes; `test_an_eval_scaffold_is_no_requirement_of_the_plugin` and `test_an_untracked_file_fires_p6_until_it_is_added` pass.
- **Negative verification:** the CI failure itself for (1); an untracked `plugins/verify-completion/evals/zz-untracked.md` makes `make validate` print P6 and fail, and removing it passes.
- **Owner or responsible area:** `scripts/plugin_validation/`

### DEBT-0033 — 2026-09-22 — Release-review findings on all five plugins, each class closed with a guard

- **Original pending record:** none; found by the release reviews of agent-self-knowledge 0.2.0, block-no-verify 0.1.3, ruff-quality 0.2.0, shell-quality 0.2.0 and verify-completion 0.1.2 on this branch.
- **Resolved debt:** Six classes of defect:
  1. A plugin script's old-Python version check could not run on 3.7: a walrus made the whole file a SyntaxError first.
  2. `test-*.sh` and `tests/**` were exempt from version bumps at any depth, yet block-no-verify's `manage.sh` runs its shipped `test-handler.sh`: a change to it would reach users without a bump.
  3. The README templates still prescribed an eval score table that R9 forbids in plugins; a test recorded it as pending instead of failing.
  4. CHANGELOG link style (C1) was checked against an allowance of four plugins that were already repaired, so a regression in those four could pass.
  5. shell-quality reported any shfmt failure, a file it could not write included, as a syntax error Claude must fix, and Stop kept Claude working on it.
  6. An eval grader demanded the opposite of the user's explicit request (verify-completion 02), another hard-coded the CI's Claude Code version (agent-self-knowledge 04), and three maintainer eval commands disagreed with their suites' own.
- **Resolution:** `scripts/plugin_validation/test_python_version_guard.py` (every shipped `.py` parses at the 3.7 grammar); `EXEMPT_FILE` and `.claude/hooks/lib/plugin-paths.sh` drop the test-file exemption (ADR-0003 amendment 2026-09-22) with parity and route tests; the four templates carry the eval sentence and `test_templates.py` requires zero findings; `test_changelog_immutable.py` fails on any C1 offender; `is_parse_error` in `shell-gate.sh` with a suite case for an unwritable directory; the grader rule in `.claude/skills/marketplace-governance/references/plugin-eval-protocol.md` already covers the eval class, and the plugin READMEs now copy each suite's own command. The `plugin-coherence-auditor` subagent (`/coherence-auditor`) reads a plugin end to end for this kind of drift before the next review.
- **Positive verification:** `make check` exits 0 (2026-09-22): 910 fast tests, every plugin invariant, `claude plugin validate --strict` on all nine targets, and the suites under both bashes (ruff-quality 81, shell-quality 67 with 1 skip, verify-completion 125, block-no-verify PASS).
- **Negative verification:** the version-guard test fails when the walrus is restored; the shell-quality suite reports 2 failures when `is_parse_error` is bypassed; the route test expects `pr` for a shipped test file.
- **Owner or responsible area:** `scripts/plugin_validation/`, `scripts/versioning/`, `.claude/hooks/lib/`, `templates/`, `plugins/*/`

### DEBT-0030 — 2026-09-22 — Gate-plugin defects the suites could not see, found by live runs, reviews and audits

- **Original pending record:** none; found and fixed in the same branch during the release review of ruff-quality 0.2.0 and shell-quality 0.2.0, and recorded here so each class keeps its guard.
- **Resolved debt:** Five classes of defect that every unit suite missed because the suites call the handler directly:
  1. A hook `if` of `Edit(P)` never matches the Write tool (live `claude -p --plugin-dir` run): a new file skipped the gate.
  2. Suppression checks netted counts across a batched Edit, ignored widened markers and repeated copies, and failed open when jq could not read the file (code review, plugin audits, cross-checked verification).
  3. The project tool search climbed above the project root and the TMPDIR state fallback trusted directories it did not own (security review).
  4. Stop looped on configuration errors and on findings only the user could settle, and restarted on every later turn (audits).
  5. Eval graders demanded fixes the pinned Ruff no longer reports by default (E711, E741) and used `file_exists` on scaffolded files (eval pilot).
- **Resolution:** invariant H7 in `scripts/plugin_validation/hook_contract.py`; regression cases in `scripts/plugin_validation/suites/{ruff,shell}-quality/test-gate.sh` (79 and 63), each failing before its fix; the grader rules in `.claude/skills/marketplace-governance/references/plugin-eval-protocol.md`; the `if`-twin rule in `.claude/rules/plugin-authoring.md`.
- **Positive verification:** `make check` exits 0 with both suites passing under `bash` and `/bin/bash` (2026-09-22).
- **Negative verification:** H7 reports 9 findings on the pre-fix `hooks.json`; each new suite case failed against the pre-fix handler (recorded per commit: a08b366, efbf5b1, fcb958e).
- **Owner or responsible area:** `plugins/ruff-quality/hooks/`, `plugins/shell-quality/hooks/`, `scripts/plugin_validation/`
- **Residual risk / follow-up:** The Bash guard stays textual (a write through `cp`, `mv` or a script is not caught); both READMEs state it under Limitations.
- **Related records:** [ADR-0007](../decisions/adr-0007-gates-ship-as-plugin-hooks.md), [DEBT-0029](#debt-0029--2026-09-22--shipped-plugin-python-is-validated-only-advisorily)
- **Superseded by:** none

### DEBT-0029 — 2026-09-22 — Shipped plugin Python is validated only advisorily

- **Original pending record:** DEBT-0029 in `pending-debt.md` (2026-09-21): `ccdocs.py`, the only Python any plugin ships, was outside `make lint` and `make types`; its smoke run printed `DEBT-0029 advisory:` lines and never failed; the README declared a 3.7 floor nothing exercised.
- **Resolved debt:** Every `.py` under `plugins/` is held by the same gates as `scripts/`: Ruff (`PY_FILES` in the `Makefile`, L5 in `make lint-staged`) and basedpyright (`include = ["scripts", "plugins"]`, L6). The maintainer set the plugin requirement to Python 3.14 (2026-09-22): the README says so in an IMPORTANT block, `ccdocs.py` checks the version when it starts and exits 2 with a message on an older `python3`, and `run_plugin_suites` fails a plugin whose README declares another floor and fails when the script does not start. `ccdocs.py` went from 110 Ruff findings and 271 basedpyright errors to none, with no suppression, and its commands print the same output. Its Ruff target stays `py39` so an older `python3` can still parse it and reach the version message.
- **Resolution:** `Makefile` (`PY_FILES`), `pyproject.toml` (`[tool.basedpyright] include`, `per-file-target-version`), `scripts/lint/lint_files.py` (`PYTHON_ROOTS`), `scripts/plugin_validation/run_plugin_suites.py` (`floor_problem`, `smoke_run`), `scripts/hygiene/test_suppressions.py` (Q3 sweeps `plugins/*.py`), agent-self-knowledge 0.2.0.
- **Positive verification:** `make lint` exits 0; the basedpyright language server reports 0 diagnostics across 125 workspace files including `ccdocs.py`; `test_a_python_floor_must_be_the_repository_interpreter` and `test_the_python_smoke_run_never_installs_an_interpreter` pass; `/usr/bin/python3` 3.9.6 running `ccdocs.py version` prints `ccdocs.py needs Python 3.14 or later; this is python3 3.9.6 …` and exits 2 (2026-09-22).
- **Negative verification:** a probe `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/_neg_probe.py` with `import os` and `X: int = "not an int"` made `make lint` exit 2 (F401, INP001) and the language server report `reportUnusedImport` and `reportAssignmentType`; removing it returned `make lint` to exit 0. `floor_problem("3.9", "3.14")`, `floor_problem("3.99", "3.14")` and `floor_problem(None, "3.14")` each return a problem.
- **Owner or responsible area:** `Makefile`, `pyproject.toml`, `scripts/lint/lint_files.py`, `scripts/plugin_validation/run_plugin_suites.py`
- **Residual risk / follow-up:** Users whose `python3` is older than 3.14 (the Xcode Command Line Tools' 3.9.6, Ubuntu 24.04's 3.12, Debian 13's 3.13) cannot use `claude-code-docs` until they install 3.14; accepted by the maintainer, 2026-09-22, and stated in the plugin README.
- **Related records:** [DEBT-0016](#debt-0016--2026-09-22--python-tests-and-repo-scripts-have-no-gates-yet), [DEBT-0019](pending-debt.md), [consolidated refactor migration log](../superpowers/specs/2026-09-21-refactor-migration-log.md)
- **Superseded by:** none

### DEBT-0016 — 2026-09-22 — Python tests and repo scripts have no gates yet

- **Original pending record:** DEBT-0016 in `pending-debt.md` (2026-09-19): the repository's gate ran only `node:test` and bash suites, and nothing linted, type-checked or tested Python.
- **Resolved debt:** The Node tooling is gone (package.json, Biome, Knip, tsconfig and every `.mjs` removed) and the repository is a uv-managed Python project for development. Every `.py` under `scripts/` is held by Ruff format and check, basedpyright in `all` mode with `failOnWarnings`, and pytest, locally through `make check` and in CI through the same `make` targets after `make setup`.
- **Resolution:** `Makefile` targets `lint`, `types`, `test-fast` and `test-slow`, all inside `make check`; `.github/workflows/ci.yml` runs `make setup` then `make check`. uv and every tool are pinned by `uv.lock`.
- **Positive verification:** `make lint` exits 0 on the tree (2026-09-22).
- **Negative verification:** adding `scripts/common/_neg_probe.py` containing only `import os` makes `make lint` exit 2 with ``F401 `os` imported but unused --> scripts/common/_neg_probe.py:1:8``; removing it returns exit 0.
- **Owner or responsible area:** `Makefile`, `pyproject.toml`, `.github/workflows/ci.yml`
- **Residual risk / follow-up:** The review condition also named Python under `plugins/`; that part was closed by [DEBT-0029](#debt-0029--2026-09-22--shipped-plugin-python-is-validated-only-advisorily).
- **Related records:** [DEBT-0029](#debt-0029--2026-09-22--shipped-plugin-python-is-validated-only-advisorily), [consolidated refactor migration log](../superpowers/specs/2026-09-21-refactor-migration-log.md)
- **Superseded by:** none

### DEBT-0025 — 2026-09-20 — A plugin README must document every environment variable its Python scripts read

- **Original pending record:** none. Found during `/plugin-release-review agent-self-knowledge` on 2026-09-20.
- **Resolved debt:** `ccdocs.py` reads `CCDOCS_CACHE_TTL`, `CCDOCS_CORPUS_TTL` and `CCDOCS_LANG` (lines 54, 61, 62). None appeared in the plugin README, so three user-facing controls — including the one that decides how stale a "live documentation" answer may be — were invisible to anyone deciding whether to install it. A full review by hand found two of the three and missed the last.
- **Resolution:** the README documents all three in a table under Requirements, and `scripts/lib/plugin-script-env.test.mjs` (part of `npm test`) fails when a plugin's Python scripts read an environment variable its README does not name. Ambient variables (`HOME`, `PATH`, `XDG_*`, `CLAUDE_*`, locale, CI) are exempt. Restricted to Python because `os.environ` names the variable unambiguously, while a shell `${VAR}` is more often a local.
- **Positive verification:** `node --test scripts/lib/plugin-script-env.test.mjs` passes for `agent-self-knowledge`, the only plugin shipping Python today.
- **Negative verification:** renaming `CCDOCS_CORPUS_TTL` to `CCDOCS_CORPUS_TTLX` in the README fails the test with `CCDOCS_CORPUS_TTL (read in skills/claude-code-docs/scripts/ccdocs.py)`. The first draft used a substring match and passed that mutation; the check now matches whole words.
- **Owner or responsible area:** `scripts/lib/plugin-script-env.test.mjs`
- **Residual risk / follow-up:** Shell scripts are not covered, and neither is a variable read indirectly. A plugin that reads configuration some other way still needs review to catch it.
- **Related records:** [plugin-release-review skill](../../.claude/skills/plugin-release-review/)
- **Superseded by:** none

### DEBT-0024 — 2026-09-20 — Every plugin README states its network posture in the badge row

- **Original pending record:** none. Found during `/plugin-release-review agent-self-knowledge` on 2026-09-20.
- **Resolved debt:** `checkNetworkClaim` in `scripts/lib/readme-contract.mjs` only fired when a README claimed `network-none` and shipped a script that called out. A README with **no** Network badge passed, which is the more misleading case: `agent-self-knowledge` — the only plugin here that reaches the network at all — shipped with no Network badge while all four others carry `network-none`, so the badge row implied the opposite of the truth.
- **Resolution:** `checkNetworkClaim` now reports a missing Network badge as a contract failure, so every plugin states `network-none`, `network-optional` or `network-required`. `agent-self-knowledge` carries `network-required`.
- **Positive verification:** `npm run validate` passes with the badge present; `node --test scripts/lib/readme-contract.test.mjs` passes 15 checks.
- **Negative verification:** `checkNetworkClaim(dir, new Map())` returns the missing-badge finding, asserted in the test; a plugin that declares `network-required` carries no obligation about its scripts, also asserted.
- **Owner or responsible area:** `scripts/lib/readme-contract.mjs`
- **Residual risk / follow-up:** The gate checks that a posture is declared and that `none` is truthful; it does not verify that `required` is truthful, which review covers.
- **Related records:** [plugin README template](../../templates/plugin-README-reusable-template.md)
### DEBT-0020 — 2026-09-20 — Skill descriptions are written from the skill's own files, and the repository states the contract

- **Original pending record:** none. Opened and closed inside the same change on 2026-09-20, so it never reached `pending-debt.md`; the measurement that opened it is preserved below.
- **Resolved debt:** Five of the six published skills opened their `description` with the `plugin-dev` formula `This skill should be used when…`, measured on 2026-09-20 across 71 installed `SKILL.md` files as 14 of 14 `plugin-dev` skills and 0 of the other 57. The catalog presented one plugin's dialect as the platform's convention, and nothing in the repository stated what a description should be, so the next plugin would inherit it by imitation.
- **Resolution:**
  - All seven descriptions — the six published plus `claude-code-docs` — rewritten from each skill's own `SKILL.md`, references and scripts rather than from the previous wording. Each opens with the instruction it gives Claude, and each names behaviour no earlier description carried (the installer lifecycle and Cowork guard of `block-no-verify`; the four hook events, three modes and self-protection of each quality gate; the six named gates, four record states and restart rule of `verify-completion`).
  - The triggering conditions moved into `when_to_use`, per the maintainer's decision on 2026-09-20; the docs define it as appended to `description` in the skill listing, so the two share one 1,536-character budget.
  - `.claude/rules/plugin-authoring.md` states the contract, and both plugin templates carry it in their placeholder frontmatter.
  - `scripts/lib/skill-frontmatter.test.mjs` (part of `npm test`) parses every plugin `SKILL.md` frontmatter with the repository's `yaml` dependency and enforces the budget.
- **Positive verification:** `node --test scripts/lib/skill-frontmatter.test.mjs` passes 15 checks; combined lengths are 1,082 / 1,003 / 1,025 / 1,016 / 1,072 / 989 / 976 characters, all inside 1,536. `npm run check` passes with the five plugins.
- **Negative verification:** Rewriting one description as a plain scalar containing a colon followed by a space fails the gate with `Nested mappings are not allowed in compact mappings`, while `claude plugin validate --strict` still passes it — the gap recorded as DEBT-0022.
- **Owner or responsible area:** `.claude/rules/plugin-authoring.md`, `scripts/lib/skill-frontmatter.test.mjs`, `templates/plugin-*/skills/skill-name/SKILL.md`
- **Residual risk / follow-up:** The gate checks that frontmatter parses and fits the budget; whether a description opens with an instruction rather than a self-introduction is caught by review, not by a gate. Whether the rewrite changes trigger behaviour is measured by the `claude plugin eval` re-run carried in each plugin's pull request.
- **Related records:** [ADR-0006](../decisions/adr-0006-changelog-scope-skill-declaration-and-release-tooling.md), [DEBT-0022](#debt-0022--2026-09-22--claude-plugin-validate---strict-accepts-skill-frontmatter-that-no-yaml-parser-can-read) (resolved 2026-09-22), global memory `bundled-skills-not-authoritative`
- **Superseded by:** none

### DEBT-0017 — 2026-09-19 — README test-shell variables are checked against the suites that read them

- **Original pending record:** none. Found by the repo-auditor on 2026-09-19: the ruff-quality and shell-quality READMEs had told maintainers to run their suites with `BNV_TEST_BASH`, which those suites read only as a fallback after their own `RQ_TEST_BASH` / `SQ_TEST_BASH`; the README fix had no gate.
- **Resolved debt:** A README could name a variable its suites don't read, so the documented command silently tested the default shell.
- **Resolution:** `scripts/lib/readme-test-vars.test.mjs` (part of `npm test`) fails when a plugin README names a `<PREFIX>_TEST_BASH` variable that none of that plugin's `test-*.sh` suites reads.
- **Positive verification:** the test passes for all four plugins.
- **Negative verification:** replacing `RQ_TEST_BASH` with `NOPE_TEST_BASH` in `plugins/ruff-quality/README.md` fails it with "names NOPE_TEST_BASH, but no test-*.sh in plugins/ruff-quality reads it".
- **Owner or responsible area:** `scripts/lib/readme-test-vars.test.mjs`
- **Residual risk / follow-up:** Only `*_TEST_BASH` variables are checked; other documented environment variables are reviewed by hand.

### DEBT-0015 — 2026-09-19 — Catalog category and tags come from `plugin.json` `metadata.marketplace`

- **Original pending record:** none. Raised by the maintainer on 2026-09-19: `plugin.json` has a `metadata` object Claude Code doesn't read, and the repo had no contract for it.
- **Resolved debt:** Marketplace entries support `category` and `tags` ([plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)), but `plugin.json` can't carry them, and `scripts/generate-marketplace.mjs` wrote only `name`, `source`, and `description`, so the catalog had no categories. `metadata` is documented as a free-form object Claude Code never reads ([plugins-reference](https://code.claude.com/docs/en/plugins-reference)), yet it was missing from `METADATA_KEYS` (`scripts/lib/version-plan.mjs`) and from the `jq del()` list in `.claude/hooks/lib/plugin-paths.sh`, so adding it to a manifest would have counted as a runtime change and forced a version bump. `schemas/marketplace.schema.json` (`additionalProperties: false` on entries) would also have rejected a `category`.
- **Resolution:**
  - Contract: `metadata.marketplace = { category, tags? }` in `plugin.json`. The allowed categories are defined once, in `schemas/plugin.schema.json#/definitions/marketplaceCategory` (a curated subset of the official Anthropic marketplace's categories, checked 2026-09-19; `location`, `math`, and `migration` are left out as outside this marketplace's scope); `marketplace.schema.json` entries reference that list and the tag definition.
  - `scripts/lib/catalog.mjs` builds each entry (`name`, `source`, `description`, then `category` and `tags` when set); `generate-marketplace.mjs` uses it. `validate-marketplace.mjs` compiles both schemas in one Ajv instance and fails when an entry differs from what the generator would write.
  - `metadata` is in `METADATA_KEYS` and in the `plugin-paths.sh` `jq del()` list.
  - Templates carry a `metadata.marketplace` placeholder whose `REPLACE-WITH-CATEGORY` fails the schema until replaced; [plugins.md](../contributing/plugins.md) and [versioning.md](../contributing/versioning.md) document the contract.
- **Positive verification:** `node --test scripts/lib/catalog.test.mjs scripts/lib/version-plan.test.mjs scripts/lib/plugin-paths.test.mjs` passes (generator order and omission, schema accept and reject cases, drift detection, metadata-only edit exempt in both the JS and bash implementations). `claude plugin validate --strict` 2.1.278 passes a plugin with `metadata.marketplace` and a marketplace entry with `category` and `tags`; CI pins 2.1.276, after 2.1.222, when `metadata` became a recognized field.
- **Negative verification:** the schema rejects an unknown category (`utilities`), a missing category, non-kebab, empty, or duplicate tags, and extra keys; the template's placeholder category fails with `/metadata/marketplace/category must be equal to one of the allowed values`. `npm run validate` reported a catalog entry whose description no longer matched its `plugin.json`.
- **Owner or responsible area:** `schemas/plugin.schema.json`, `schemas/marketplace.schema.json`, `scripts/lib/catalog.mjs`, `scripts/lib/version-plan.mjs`, `.claude/hooks/lib/plugin-paths.sh`
- **Residual risk / follow-up:** `metadata.marketplace` became required on 2026-09-19, once all four plugins declared it. Placeholder `tags` (`replace`, `with`, `tags`) pass the schema, as placeholder `keywords` already do; only review catches them. Editors resolve the marketplace schema's `$ref` against its `$id`, so editor-side category completion may not work.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** none

### DEBT-0014 — 2026-09-19 — Gate plugins enforce every stated minimum and test their installer and degraded modes

- **Original pending record:** none. Found by `/plugin-release-review` while building ruff-quality and shell-quality 0.1.0.
- **Resolved debt:** Four classes of gap, each caught before release:
  - The README stated Git ≥ 2.18 and Ruff ≥ 0.16, but `preflight` checked neither Git nor (outside the recommended mode) the Ruff version, although the Stop gate's `ruff format --check --output-format` needs 0.16.
  - Porting `manage.sh` from one plugin to the other silently dropped `os_kind`; `assess` and `preflight` printed `command not found` and still exited 0.
  - A test fixture built with `${4:-{\}}` produced an empty payload under `/bin/bash` 3.2 only, so the suite's post cases tested nothing there.
  - Without `jq`, the guard denies every `Write`/`Edit`/`Bash` call (intended fail-closed), but the message did not say how to recover.
- **Resolution:**
  - Both `manage.sh` preflights check Git ≥ 2.18; ruff-quality checks Ruff ≥ 0.16 in every mode.
  - Each plugin ships `scripts/test-manage.sh`: every command in a sandbox, failing on `command not found`, `unbound variable`, or `syntax error`, and asserting that preflight reports each minimum. `npm test` runs it under `bash` and `/bin/bash`.
  - Fixture builders abort the suite (`built_fail`) when jq cannot build a payload.
  - The guard's fail-closed message names the recovery (`! bash … manage.sh uninstall`), both READMEs list it under Limitations, and each `test-gate.sh` runs the guard with `PATH` lacking `jq` and a full realistic payload.
- **Positive verification:** `test-gate.sh` 99/99 (ruff-quality) and 82/82 (shell-quality), `test-manage.sh` all passing, on bash 3.2.57 and 5.3.20.
- **Negative verification:** with `os_kind` removed from the shell `manage.sh`, `test-manage.sh` reported 2 failures; with the old fixture, the ruff suite failed 23 post cases under `/bin/bash`.
- **Owner or responsible area:** `plugins/ruff-quality/skills/ruff-hooks/`, `plugins/shell-quality/skills/shell-hooks/`
- **Residual risk / follow-up:** the suites run with the local and CI runner's `jq`, Ruff, ShellCheck, and shfmt versions only (see DEBT-0012).
- **Related records:** DEBT-0012, DEBT-0013
- **Superseded by:** none

### DEBT-0013 — 2026-09-19 — A new plugin's shell suites and scripts are tested and linted before its first commit

- **Original pending record:** none. Found while building a new plugin on 2026-09-19.
- **Resolved debt:** `listShellFiles()` read `git ls-files`, so `npm test` and `lint:sh` skipped every script a new plugin adds until it was committed. A branch adding a plugin passed `npm run check` without running that plugin's 110-case suite; running it needed `git add -N`. The same listing kept tracked files that had been deleted.
- **Resolution:** `scripts/lib/shell-files.mjs` lists tracked files plus untracked files Git doesn't ignore (`--cached --others --exclude-standard`), and drops paths missing on disk. `scripts/lib/shell-files.test.mjs` builds a temporary repository with tracked, untracked, ignored, and deleted scripts and requires exactly the tracked and untracked ones. `.claude/skills/plugin-release-review/references/consistency-matrix.md` also gained a row for hook command form against the minimum Claude Code version, another class of gap found in the same review.
- **Positive verification:** with a new plugin still untracked, `npm test` ran its `test-*.sh` suite under `/opt/homebrew/bin/bash` and `/bin/bash`, and `lint:sh` picked up its scripts.
- **Negative verification:** before the fix the new test failed with `actual: [ 'deleted.sh', 'tracked.sh' ]` against `expected: [ 'tracked.sh', 'untracked.sh' ]`; the ignored script stays out.
- **Owner or responsible area:** `scripts/lib/shell-files.mjs`
- **Residual risk / follow-up:** plugin suites still run only with the local and CI runner's `jq`.
- **Related records:** DEBT-0003
- **Superseded by:** none

### DEBT-0011 — 2026-09-19 — Non-runtime changes are pushed directly to `main`; the checks run before the push

- **Original pending record:** none. The maintainer raised it on 2026-09-19 after a README-only commit was rejected by the required-checks ruleset.
- **Resolved debt:** DEBT-0005 removed every bypass from the required-checks ruleset, and `version-check` only ran on pull requests. So every change needed a PR, even a one-word README fix. The maintainer's rule was never that: only a change that alters a plugin's behavior needs a version bump and a PR. The requirement came from the repo-protocols plan's recommendation.
- **Resolution:**
  - The repository admin role is a bypass actor (mode *Always*) on ruleset 23655894. The maintainer made this change in the GitHub UI.
  - `.claude/hooks/guard-push.sh` denies a direct push to `main` unless the tree is clean, `check:versions` reports `bump: none`, and `npm run check` passes. A runtime change is sent to a PR.
  - `version-check` also runs on pushes to `main`, against the commit before the push.
  - `CLAUDE.md`, `docs/contributing/versioning.md`, `.claude/rules/plugin-delivery.md`, and `pr-delivery` describe the split: direct push for non-runtime changes, a PR for version bumps. (2026-09-19: `plugin-delivery.md` was split into path-scoped rules; the split is now stated in `CLAUDE.md` Conventions and `pr-delivery`.)
- **Positive verification:** `push-guard.test.mjs` allows a clean non-runtime push to `main`. The first direct push after this change went through the real gate.
- **Negative verification:** `push-guard.test.mjs` denies a runtime change, failing version rules, a failing check, and a dirty tree.
- **Owner or responsible area:** GitHub rulesets, `.claude/hooks/guard-push.sh`, `.github/workflows/ci.yml`
- **Residual risk / follow-up:** A push made outside Claude Code skips the local gate; CI's `check` and `version-check` on `main` catch it after the push, not before. The deletion, force-push, and tag rulesets keep no bypass.
- **Related records:** DEBT-0005 (superseded), [ADR-0003 amendment 2026-09-19](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0010 — 2026-09-19 — Delivery gaps from block-no-verify 0.1.x closed with a push guard, a delivery checklist, and project rules

- **Original pending record:** none. Found while shipping block-no-verify 0.1.0–0.1.1 and fixed in the following PR.
- **Resolved debt:** Shipping one plugin took three review rounds. The README eval table went stale after the skill description changed. A push after the #11 merge recreated the deleted branch `docs/block-no-verify-catalog` with a commit that never reached `main` (fixed in #12). The tag push failed server-side on reruns. "Done" was reported before every step was verified.
- **Resolution:**
  - `.claude/hooks/guard-push-merged-branch.sh` (PreToolUse, Bash) denies pushing a branch that was published before but no longer exists on the remote.
  - The repo skill `pr-delivery` starts a checklist that `checklist-gate.sh` enforces. Its verify commands prove that every plugin version is tagged on origin, the feature branch is gone locally and remotely, `main` equals `origin/main`, and the tree is clean.
  - `checklist.sh start` refuses while another checklist is unfinished. Verify commands receive `$CHECKLIST_SUBJECT`.
  - `.claude/rules/plugin-delivery.md` records the working rules: design first, continuous review, Bash 3.2 and degraded-mode testing, edit verification, current numbers, branch hygiene, tagging, and the definition of done. (2026-09-19: moved to `plugin-authoring.md`, `shell-scripts.md`, and `edits-and-evidence.md`, and into the `plugin-design`, `plugin-release-review`, and `pr-delivery` checklists.)
  - `scripts/lib/text-files.test.mjs` fails when a tracked or new text file holds a raw control character. A tool turned a written NUL escape into the byte twice, the second time in this change.
- **Positive verification:** `scripts/lib/push-guard.test.mjs` shows a deleted published branch is denied in eight spellings, under `bash` and `/bin/bash`. `checklist-gate.test.mjs` shows the subject reaches verify commands. The delivery verify commands pass against the real repository after #12.
- **Negative verification:** New branches, live branches, deletions, tag pushes, and non-push commands are allowed, and an unreachable remote fails open. A second checklist start is refused, and the delivery `branches` verify fails while the feature branch still exists.
- **Owner or responsible area:** `.claude/hooks/`, `.claude/skills/pr-delivery/`, `.claude/rules/`
- **Residual risk / follow-up:** Both are guardrails for Claude sessions, not controls. The push guard fails open offline and doesn't see pushes made outside Claude. The merge and CI items are evidence Claude records, not commands the gate re-runs, because re-running them would need GitHub credentials in the hook.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), DEBT-0008
- **Superseded by:** none

### DEBT-0008 — 2026-09-18 — Plugin README contract and root catalog row are enforced by `npm run validate`

- **Original pending record:** none — found and fixed in the same change (post-release review of `block-no-verify` 0.1.0).
- **Resolved debt:** Nothing enforced the plugin README template beyond the `**Kind:**` line, and the contributing guide never asked for a root README catalog row. `block-no-verify` 0.1.0 shipped with the root catalog still showing "No plugins published yet", the template's Cowork install and update steps replaced, and two requirement badges (Bash, jq) that were not in the template's badge catalog.
- **Resolution:**
  - `scripts/lib/readme-contract.mjs`, run by `npm run validate` (and so by `npm run check` and CI), derives the required sections, their order, and the allowed badges from `templates/plugin-README-reusable-template.md`. It rejects missing, unknown, or reordered sections, `{{placeholders}}`, more than one alert per section, unlabeled code blocks, badges outside the catalog, a Version badge that doesn't read the plugin's own `plugin.json`, and Installation without the Claude Code and Cowork steps. It also requires one root catalog row per plugin, sorted, whose link, kind, and surface statuses match the plugin.
  - `docs/contributing/plugins.md`, the PR template, and `CLAUDE.md` state the catalog-row step and what `validate` checks.
  - Bash and jq were added to the template's badge catalog; the root catalog and the plugin README were corrected.
  - Follow-up checks from a seeded-defect test of the review skill: each plugin `LICENSE` must match the canonical Apache-2.0 SHA-256 and `plugin.json` must declare `Apache-2.0`; "≥" requirement badges must match the Requirements table and the catalog row; a `network-none` plugin must not ship scripts that call network tools; every CHANGELOG heading needs a link definition. The three plugin-shape CHANGELOG templates were re-synced with the master (guidance sentence, compare links).
  - The judgment layer became the repo skill `.claude/skills/plugin-release-review/`, whose checklist is enforced by the `checklist-gate.sh` Stop hook (ADR-0002 amendment).
- **Positive verification:** `npm run check` passes; `scripts/lib/readme-contract.test.mjs` and `scripts/lib/checklist-gate.test.mjs` cover each rule with fixtures and check this repository's files. In a seeded-defect copy of the repo, the review skill found all six planted defects plus three real 0.1.0 bugs, and the extended validator now catches three of the six mechanically.
- **Negative verification:** Run against the tree before the fix, the validator reports all four gaps found by the manual review (badges Bash/jq, Cowork install steps, Cowork update line, placeholder catalog row).
- **Owner or responsible area:** `scripts/lib/`, `templates/`, `docs/contributing/`
- **Residual risk / follow-up:** Content quality (accuracy of claims, tone) still needs review; the validator checks structure and consistency only.
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md), [PR #10](https://github.com/nerymurillohnd/claude-essentials/pull/10)
- **Superseded by:** none

### DEBT-0001 — 2026-09-18 — `claude plugin validate --strict` runs in `npm run check` and CI

- **Original pending record:** DEBT-0001 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Only the repo's Ajv schemas gated manifests, so drift from Claude Code's own rules could go unnoticed. The open questions were whether CI can run the CLI without authentication, and whether `--strict` rejects `kind`.
- **Resolution:**
  - CI installs a pinned Claude Code CLI on the runner only (`CLAUDE_CODE_VERSION` in `ci.yml` and `tag-versions.yml`); locally the scripts use the maintainer's `claude` on `PATH`. It is not a repo dependency.
  - `npm run validate:claude` (`scripts/validate-claude.mjs`) runs `claude plugin validate --strict --json` on `.` and on every `plugins/<name>`, because the root run doesn't check plugin contents. It tolerates only the empty-marketplace warning while `plugins/` is empty.
  - The check runs in `npm run check` and the CI `check` job.
  - `kind` became derived ([ADR-0001 amendment](../decisions/adr-0001-marketplace-distribution-model.md)).
- **Positive verification:** Three fixture plugins copied from the templates pass `--strict` in a scratch clone (plan Task 2 Step 10). The CLI ran with a clean `HOME` and no credentials.
- **Negative verification:** A broken `SKILL.md` fails at `plugins/<name>` (exit 1). A skill-only plugin that gains an agent fails the README Kind check. Before the amendment, `kind` failed `--strict` on every plugin.
- **Owner or responsible area:** `scripts/`, `.github/workflows/ci.yml`, `.github/workflows/tag-versions.yml`
- **Residual risk / follow-up:** `CLAUDE_CODE_VERSION` must be bumped deliberately, and a newer local `claude` can disagree with CI until it is (DEBT-0004).
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md), [ADR-0002](../decisions/adr-0002-project-hooks.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** none

### DEBT-0002 — 2026-09-18 — Explicit semver adopted, enforced in CI, tagged by `claude plugin tag`

- **Original pending record:** DEBT-0002 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** The templates pinned `"version": "0.1.0"` without a stated strategy, the CHANGELOG template linked bare-version tags, and nothing required a version bump.
- **Resolution:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md).
  - `version` is required and must be canonical semver (schema).
  - `version-check` enforces a bump plus a dated CHANGELOG entry on every PR that changes a plugin's runtime files (a closed list exempts README/docs/LICENSE/CHANGELOG and `plugin.json` metadata), including `claude plugin tag --dry-run`.
  - The `Tag plugin versions` workflow runs `claude plugin tag --push` for every untagged version. There are no GitHub Releases: plugins reach users through the marketplace.
  - The templates and [versioning.md](../contributing/versioning.md) document the rule.
- **Positive verification:** `npm test` passes the version-plan and changelog suites. In the scratch-clone scenario, `check-versions` exits 0 for a new plugin and a committed bump, and `tag-versions --dry-run` selects only untagged versions.
- **Negative verification:** In the same scenario, an unbumped change exits 1 with "still 0.1.0", a missing CHANGELOG entry exits 1, `--verify-tag` on a dirty tree exits 1, and the schema rejects a missing, `v`-prefixed, or build-metadata version.
- **Owner or responsible area:** `schemas/`, `scripts/`, `.github/workflows/`, `templates/`
- **Residual risk / follow-up:** The live tagging workflow and tag ruleset stay unverified until the first plugin version (ADR-0003 Confirmation).
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0003 — 2026-09-18 — Shell scripts are linted by `npm run check` and CI

- **Original pending record:** DEBT-0003 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Only Claude's own edits were linted, by the PostToolUse hook. `npm run check` and CI had no shell linter, so edits by a person, another program, or a merge could regress the hooks unnoticed.
- **Resolution:**
  - A repo-local `.shellcheckrc` mirrors the maintainer's policy: the same ten optional checks, and no global disables.
  - `npm run lint:sh` (`scripts/lint-shell.mjs`) runs `shellcheck -x` and `shfmt -d` on every tracked shell script. It finds them with the hook's rule: `.sh` files, plus files with an `sh`/`bash` shebang (`scripts/lib/shell-files.mjs`).
  - `lint:sh` is part of `npm run check`.
  - The CI `check` job installs ShellCheck 0.11.0 and shfmt 3.14.1 from their official releases, verifies each download with `sha256sum --check`, and then runs `lint:sh`.
- **Positive verification:** All 5 hook scripts pass under the repo rc. Unit tests cover shell-script detection (`shell-files.test.mjs`). The SHA-256 of both downloads was verified locally against GitHub's asset digests.
- **Negative verification:** A tracked script containing `echo $1` makes `lint:sh` fail with SC2086.
- **Owner or responsible area:** `.shellcheckrc`, `scripts/lint-shell.mjs`, `.github/workflows/ci.yml`
- **Residual risk / follow-up:** The tool versions in CI are bumped by hand, together with their checksums. Contributors need ShellCheck and shfmt installed locally.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0004 — 2026-09-18 — Actions pinned by SHA, Dependabot enabled, Claude Code CLI pin kept consistent

- **Original pending record:** DEBT-0004 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Workflows that hold write tokens referenced actions by mutable major tags. Nothing updated the actions or the npm dev dependencies. The `CLAUDE_CODE_VERSION` pins could drift apart between workflows, and from the maintainer's local CLI, without anyone noticing.
- **Resolution:**
  - Every `uses:` in `.github/workflows/` is pinned to a full commit SHA, with a version comment: `actions/checkout` v7.0.1, `actions/setup-node` v7.0.0, `actions/stale` v11.0.0.
  - `.github/dependabot.yml` updates `npm` and `github-actions` weekly. Dependabot also maintains SHA pins that carry a version comment. Alerts and security updates are enabled.
  - `npm run validate` fails if two workflows that install Claude Code set different values of `CLAUDE_CODE_VERSION`, if one sets none, or if a value isn't canonical semver.
  - `npm run validate:claude` prints a note when the local `claude` differs from CI's pin.
- **Positive verification:** `actionlint` is clean. `npm run validate` passes on the real workflows (both at 2.1.276). The unit tests for `checkClaudeCodeVersions` pass.
- **Negative verification:** The unit tests confirm a missing pin, a `v`-prefixed pin, and diverging pins are each reported.
- **Owner or responsible area:** `.github/workflows/`, `.github/dependabot.yml`, `scripts/lib/repo-metadata.mjs`
- **Residual risk / follow-up:** Dependabot can't bump `CLAUDE_CODE_VERSION`, because it's an env value, so it's bumped by hand in both workflows at once; validation enforces that they match.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0004](../decisions/adr-0004-issue-and-label-protocol.md)
- **Superseded by:** none

### DEBT-0005 — 2026-09-18 — The `main` status-check ruleset no longer lets admins bypass it

- **Original pending record:** none. Found and fixed the same day, so it never had a pending entry.
- **Resolved debt:** The repo-protocols plan specified "no bypass actors" for `main`. The live ruleset "Require green checks to merge into main" (id 23655894) was created with the repository admin role as a bypass actor in mode `always`. That let the only maintainer push straight to `main`, or merge a red PR, without `check` or `version-check`. `version-check` runs only on `pull_request` events, so any direct push to `main` needed that bypass.
- **Resolution:** On 2026-09-18, `bypass_actors` was set to `[]` with `gh api -X PUT repos/nerymurillohnd/claude-essentials/rulesets/23655894`. The ruleset's name, target, enforcement, conditions, and rules are unchanged; a diff before the change confirmed that only `bypass_actors` would differ. All three rulesets now have no bypass actors.
- **Positive verification:** The ruleset reads back `enforcement=active`, `bypass=[]`, `current_user_can_bypass=never`. `gh api repos/nerymurillohnd/claude-essentials/rules/branches/main` returns `deletion`, `non_fast_forward`, `required_status_checks`.
- **Negative verification:** The maintainer's `current_user_can_bypass` is `never`. A direct push to `main` was not attempted: it would be rejected now, and attempting it would itself be the prohibited action.
- **Owner or responsible area:** GitHub repository rulesets
- **Residual risk / follow-up:** If GitHub Actions can't run, nothing can merge. The remedy is a deliberate, audited, temporary ruleset edit — never a standing bypass. Every change to `main` goes through a PR, including docs-only changes.
- **Related records:** [repo-protocols plan](../superpowers/plans/2026-09-18-repo-protocols.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** DEBT-0011 (2026-09-19): the maintainer allows direct pushes to `main` for non-runtime changes, gated locally.

