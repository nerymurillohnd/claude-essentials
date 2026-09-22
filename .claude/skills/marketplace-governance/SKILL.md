---
name: marketplace-governance
description: Map of this repository's maintainer tooling and its validation protocol, organized as one folder per governance area, each with a reference detailing what every entrypoint, module, and test executes.
when_to_use: Use when adding, moving, renaming, or reviewing any file under scripts/, when deciding which area a new maintainer script belongs to, when a restructure changes where governance tooling lives, or when authoring or running a plugin eval suite.
---

# Marketplace governance

Maintainer tooling only. Nothing here is distributed to users, and no plugin
loads any of it. The user-facing surface is `plugins/`.

## Placement rule

- A file's folder is its classification. One folder per area, eight areas, no `misc`.
- Entrypoints live at the root of their area and run as `python -m scripts.<area>.<name>`.
- Modules and their tests live side by side in the same area folder.
- A test that covers a shell hook or a schema belongs to the area it guards, not to the module that happens to call it.
- A new file that fits no area means the taxonomy is wrong. Add the area, then the file.
- Every area folder carries an `__init__.py`, as does `scripts/` itself, so imports are absolute and unambiguous.

> [!NOTE]
> The area headings and the tree below are hand-authored. Each area's `| File | Function |`
> table is generated from the first line of every module's own docstring
> (`python -m scripts.harness.governance_docs`, wired into `make generate`) — never edit a
> table directly; edit the docstring it came from and regenerate. [DEBT-0038](../../../docs/maintenance/resolved-debt.md)
> has the history of why these used to drift.

## 1. GitHub — API, Actions, and `.github/`

`scripts/github/` — what each file executes: [`references/github.md`](references/github.md)

<!-- governance-docs:github -->
| File | Function |
| --- | --- |
| `client.py` | A minimal GitHub REST client: stdlib only, read by default, injectable for tests. |
| `test_client.py` | Tests for the REST client: headers, pagination, dry-run writes and error handling. |
| `conftest.py` | A recording transport, so every API test runs offline and can assert what was sent. |
| `generate_issue_forms.py` | Rewrite the **Affected plugin** dropdown of every issue form, and nothing else. |
| `test_generate_issue_forms.py` | Tests for the dropdown generator: byte identity outside the block, and idempotence. |
| `install_claude_code.py` | Install one Claude Code CLI release on a CI runner, verified against Anthropic's signature. |
| `test_install_claude_code.py` | Tests for the verified Claude Code installer: what it refuses, and what it installs. |
| `issue_forms.py` | The issue forms: schema-valid, label-consistent, and carrying the generated dropdown (G1). |
| `test_issue_forms.py` | Tests for the issue forms: the real files against the real vendored schemas (G1). |
| `labels.py` | The label taxonomy as code: what it must contain, and how it is reconciled with GitHub. |
| `test_labels.py` | Tests for the label taxonomy: shape, completeness, and the diff against GitHub (G1). |
| `repo_metadata.py` | Cross-file pins: the CLI version, the tool versions, the workflow SHAs, the pipeline (G2, G3). |
| `test_repo_metadata.py` | Tests for the cross-file pins: the CLI version, the tool pins, the SHAs, the pipeline. |
| `sync_labels.py` | Reconcile the GitHub label taxonomy with `.github/labels.json`, dry run by default. |
| `test_sync_labels.py` | Tests for the label sync entrypoint: what it reads, what it sends, and what it refuses. |
| `triage.py` | Apply the triage rules to one GitHub event, dry run by default (ADR-0004). |
| `test_triage.py` | Tests for the triage entrypoint: narrowing, the dry run, and the base-checkout rule. |
| `triage_rules.py` | What labels an issue, a comment or a pull request earns — as pure functions (ADR-0004). |
| `test_triage_rules.py` | Tests for the triage rules: every path rule, the form answers, and the bump replacement. |
<!-- /governance-docs:github -->

## 2. Versioning and releases

`scripts/versioning/` — what each file executes: [`references/versioning.md`](references/versioning.md)

<!-- governance-docs:versioning -->
| File | Function |
| --- | --- |
| `changelog.py` | Parsing and the three CHANGELOG invariants: P3 (entry), C1 (links) and C2 (immutability). |
| `test_changelog.py` | Tests for CHANGELOG parsing and the P3, C1 and C2 checks. |
| `test_changelog_immutable.py` | C2 against this repository: every released section still reads as it did at its tag. |
| `check_versions.py` | The version-bump gate: what each plugin owes, which route the push takes, which label. |
| `test_check_versions.py` | Tests for the version gate: the golden last line, the JSON contract and the exit codes. |
| `conftest.py` | Builders for the temporary repositories the versioning tests run against. |
| `semver.py` | Canonical SemVer for plugin versions: parsing, ordering and the bump level (M5). |
| `test_semver.py` | Tests for canonical version parsing, ordering and the bump level (M5). |
| `tag_versions.py` | Create the `{name}--v{version}` tag of every plugin version that has none. |
| `test_tag_versions.py` | Tests for the tagging entrypoint, with the official CLI stubbed through `CLAUDE_BIN`. |
| `version_plan.py` | The one home of the runtime-vs-exempt rule, the bump plan and the push route (ADR-0003). |
| `test_version_plan.py` | Tests for the exempt rule, the bump plan and the §A11 route matrix. |
<!-- /governance-docs:versioning -->

## 3. Marketplace and catalog

`scripts/marketplace/` — what each file executes: [`references/marketplace.md`](references/marketplace.md)

<!-- governance-docs:marketplace -->
| File | Function |
| --- | --- |
| `catalog.py` | What a catalog entry contains, the field rules it obeys, and the catalog's own top level. |
| `test_catalog.py` | Tests for the catalog entry shape and the field rules M2, M3, M6, M9 and M10. |
| `conftest.py` | A minimal marketplace tree the catalog tests seed defects into. |
| `generate_marketplace.py` | Rewrite the generated `plugins` array of `.claude-plugin/marketplace.json` in place. |
| `test_generate_marketplace.py` | Tests for the catalog generator: what it owns, what it keeps, and what it removes. |
| `validate_marketplace.py` | The catalog gate: ten invariants over the manifests on disk and the generated catalog. |
| `test_validate_marketplace.py` | Tests for the catalog gate: the registry, a clean tree, and one seeded defect per ID. |
<!-- /governance-docs:marketplace -->

## 4. Static plugin validation

`scripts/plugin_validation/` — what each file executes: [`references/plugin-validation.md`](references/plugin-validation.md)

<!-- governance-docs:plugin_validation -->
| File | Function |
| --- | --- |
| `test_ccdocs.py` | agent-self-knowledge's `ccdocs.py`, run the way its skill runs it: as a process. |
| `claude_cli.py` | The official CLI, wrapped: `claude plugin validate --strict`. |
| `test_claude_cli.py` | The official CLI wrapper: what it runs, and what it does when the binary is gone. |
| `cli_coverage.py` | What the official CLI already checks, and the tool names this repository knows about. |
| `test_cli_coverage.py` | The dated tool list, and the nightly diff against the live documentation. |
| `conftest.py` | A scratch marketplace on disk, so a negative probe can be seeded and then removed. |
| `evals.py` | Eval-suite authoring invariants E1 to E4. |
| `test_evals.py` | E1 to E4: a suite that can measure something, and results that stay out of git. |
| `frontmatter.py` | Skill and subagent frontmatter: the six invariants S1 to S6. |
| `test_frontmatter.py` | Skill and subagent frontmatter: S1 to S6. |
| `hook_contract.py` | Hook wiring: the eight invariants H1 to H8, over `hooks.json` and settings fragments. |
| `test_hook_contract.py` | Hook wiring: H1 to H8, including the path H5 deliberately does not resolve. |
| `kind.py` | Plugin shape and the four file-level invariants that go with it (P1 to P5). |
| `test_kind.py` | Kind derivation and the file-level invariants P1, P2, P4 and P5. |
| `test_python_version_guard.py` | Shipped Python parses on an old interpreter, so its version check can speak. |
| `readme_contract.py` | The README contract: R1 to R14, over each plugin's README and the root catalog. |
| `test_readme_contract.py` | The README contract: the structure, the badges, and the status collapse. |
| `run_plugin_suites.py` | `make test-slow`, second half: every plugin's own suite, under every bash that matters. |
| `test_run_plugin_suites.py` | Every plugin suite, under every bash that matters, plus the Python smoke run and floor gate. |
| `runtime_boundary.py` | B1: the boundary between the maintainer's environment and a user's machine (§2.1). |
| `test_runtime_boundary.py` | B1: what a plugin may assume a user's machine already has (§2.1). |
| `script_env.py` | Which variables a shipped script reads; the `*_TEST_BASH` and `BNV_TEST_PYTHON` conventions. |
| `test_script_env.py` | Environment-variable extraction: what a script reads, not what it mentions. |
| `test_skill_supporting_files.py` | A skill's supporting files never carry `${CLAUDE_SKILL_DIR}`, which only SKILL.md gets filled in. |
| `test_templates.py` | T1: the shape templates under the same README and frontmatter rules, with `{{…}}` allowed. |
| `validate_claude.py` | `make validate-cli`: the official CLI's verdict on the marketplace and every plugin. |
| `test_validate_claude.py` | `make validate-cli`: the entrypoint's exit codes and its one-line error. |
| `validate_plugins.py` | `make validate`, second half: every invariant this repository adds to the official CLI. |
| `test_validate_plugins.py` | The negative probes: each defect fires with its own ID, and stops once it is removed. |
| `workflows.py` | Plugin workflows: W1, the one invariant over `plugins/*/workflows/*.js`. |
| `test_workflows.py` | W1: metadata purity, declared phases, compilation and a stub-runtime run. |
<!-- /governance-docs:plugin_validation -->

## 5. Lint — file bytes, shell, JSON, workflows

`scripts/lint/` — the byte-level gate: ShellCheck and shfmt, the canonical JSON form,
UTF-8/LF/final-newline, actionlint and zizmor. Its entrypoint is `lint_files.py`, which
`make lint`, `make lint-staged`, `make fix` and `make fix-file` all call.

<!-- governance-docs:lint -->
| File | Function |
| --- | --- |
| `conftest.py` | A temporary tree that owns the same locked binaries and policy files as this repository. |
| `json_files.py` | L2: every tracked or new `.json` file is in the repository's one canonical form. |
| `test_json_files.py` | Tests for L2: the canonical form, the one exclusion list, and the JSONC carve-out. |
| `lint_files.py` | `make lint`, `make lint-staged`, `make fix` and `make fix-file`: one entrypoint, six IDs. |
| `test_lint_files.py` | Tests for the lint entrypoint: the registry, the three file sets, and the writer. |
| `shell_files.py` | L1: ShellCheck and shfmt over every shell file the working tree holds. |
| `test_shell_files.py` | Tests for L1: discovery by name or shebang, then the real ShellCheck and shfmt. |
| `text_files.py` | L3: the bytes of every text file, held to what `.editorconfig` already declares. |
| `test_text_files.py` | Tests for L3: the byte rules, and that they are read from `.editorconfig` rather than copied. |
| `tools.py` | The locked binaries the lint area shells out to, and one way to run them. |
| `test_tools.py` | Tests for the locked-binary helpers: resolution fails closed, PATH is the project's. |
| `workflows_files.py` | L4: GitHub Actions workflows, checked by actionlint and audited by zizmor. |
| `test_workflows_files.py` | Tests for L4 and G2: actionlint, the zizmor ignore policy, and zizmor itself all block. |
<!-- /governance-docs:lint -->

## 6. Harness — hooks, instruction files, editor wiring

`scripts/harness/` — tests for everything Claude loads rather than runs: `.claude/hooks/`,
`.claude/settings.json`, the skills' checklists, the `CLAUDE.md` index tables, `.vscode/`
and the `Makefile`. `inventory.py` reads that wiring and prunes stale hook state for
`make clean`; `governance_docs.py` is this file's own generator.

<!-- governance-docs:harness -->
| File | Function |
| --- | --- |
| `test_bash_stamp.py` | Smoke tests for the Bash stamp: `post-edit.sh` cannot work without it. |
| `test_checklist_gate.py` | Tests for the Stop gate: a skill cannot report a run as finished before it is. |
| `test_checklists.py` | The Stop-hook checklists are readable, complete, and their verifications can run. |
| `conftest.py` | Running this repository's own hooks the way Claude Code runs them. |
| `governance_docs.py` | Rewrite the per-file tables of `marketplace-governance/SKILL.md` in place. |
| `test_governance_docs.py` | Tests for the governance-docs generator: table order, markers, and drift on the real tree. |
| `test_guard_catalog.py` | Tests for the catalog guard: the generated array is refused, everything else is allowed. |
| `test_guard_commit.py` | Tests for the commit guard: it allows a clean commit and fails closed on everything else. |
| `test_harness_index.py` | P7: the index in `CLAUDE.md` lists exactly what the harness ships, both ways. |
| `test_hook_wiring.py` | P7 for hooks: every hook on disk is wired, tested, executable, and every wire resolves. |
| `inventory.py` | What the harness actually loads: index entries, hook bindings, agents, rules, stale state. |
| `test_inventory.py` | Tests for the harness reader: the wiring it reports, and the state it prunes. |
| `test_makefile.py` | The pipeline is the `Makefile`, so the `Makefile` itself is checked. |
| `test_plugin_paths.py` | Parity between the exempt rule's two homes: Python and the shell hook that mirrors it. |
| `test_post_edit.py` | Tests for the post-edit hook: the plugin version reminder, and nothing else. |
| `test_push_guard.py` | Tests for the push guard: the two pushes that must never happen. |
| `test_record_audit.py` | Tests for the audit recorder: `/pr-delivery` trusts this file instead of a hand-written note. |
| `test_repo_root.py` | Tests for the two-trees library: which checkout a hook acts on inside a worktree. |
| `test_scaffold_map.py` | The map of `scripts/` matches `scripts/`, and every module in it is covered by a test. |
| `test_session_start_smoke.py` | Smoke test for the session snapshot: it answers, and it answers in the documented shape. |
| `test_vscode.py` | §A16: the workspace is complete on its own and can never weaken the gate. |
<!-- /governance-docs:harness -->

## 7. Shared infrastructure

`scripts/common/` — what each file executes: [`references/common.md`](references/common.md)

<!-- governance-docs:common -->
| File | Function |
| --- | --- |
| `environment.py` | Where the tooling is running: a maintainer's machine, or a GitHub Actions runner. |
| `test_environment.py` | Tests for CI detection, including the local `GITHUB_ACTIONS=true` that motivated it. |
| `errors.py` | Findings, exit codes and the exception types every maintainer module shares. |
| `test_errors.py` | Tests for the shared finding, exit-code and exception types. |
| `javascript.py` | V8 evaluation for the JavaScript this repository validates (P12). |
| `test_javascript.py` | V8 helper: a snippet's value, a thrown message, and a matcher's real semantics. |
| `jsontext.py` | Canonical JSON: the one serialisation every generated artifact in this repository uses. |
| `test_jsontext.py` | Tests for the canonical JSON serialisation shared by every generator. |
| `plugins.py` | Repository access: the git root, tracked files, plugin ids and JSON shape narrowing. |
| `test_plugins.py` | Tests for repository access: git root, tracked files, plugin ids and JSON narrowing. |
<!-- /governance-docs:common -->

## 8. File hygiene and tooling alignment

`scripts/hygiene/` — what each file executes: [`references/hygiene.md`](references/hygiene.md)

<!-- governance-docs:hygiene -->
| File | Function |
| --- | --- |
| `test_adr_append_only.py` | X3: an accepted decision record is appended to, never rewritten. |
| `conftest.py` | Shared readers for the repository-wide invariants. |
| `test_legal_text.py` | X5: the legal documents are their templates' text, not a paraphrase of it. |
| `test_placeholders.py` | P4, repository-wide: no template placeholder survives outside `templates/`. |
| `test_private_paths.py` | No tracked file names the maintainer's machine: this repository is published as it is. |
| `test_quality_floor.py` | Q1: the quality floor, everywhere. No second config, no downgraded rule, no escape hatch. |
| `test_rigor_floor.py` | Q2: the repository's policy is at least the maintainer's own, never less (P11). |
| `test_single_home.py` | X1: every policy table has exactly one home. |
| `test_suppressions.py` | Q3: a finding is fixed, never silenced. |
| `test_tooling_alignment.py` | X4: nothing in the swept tree still points at the toolchain this repository replaced. |
| `test_vendored_files.py` | X2: the vendored schemas are byte-pinned, because "unmodified" is the whole claim. |
| `test_workflow_pins.py` | G2 on the real tree: every action this repository runs is pinned to a commit. |
<!-- /governance-docs:hygiene -->

## 9. Behavioural validation

Evals are the only layer that measures behaviour instead of files. They cost
money, return different numbers for the same input, and therefore never gate a
merge. The protocol is [`references/plugin-eval-protocol.md`](references/plugin-eval-protocol.md).

- Suites live at `plugins/<id>/evals/`, beside the plugin, not under `scripts/`.
- Run one only when a plugin's runtime files change, never for a README or a manifest metadata edit.
- If a check is free and deterministic, it belongs in an area above, not in a suite.

## Tree

```
scripts/
├── __init__.py
├── common/              shared readers, error handling, environment detection
├── github/              REST client, triage, labels, issue forms
├── harness/             suites for .claude/, .vscode/ and the Makefile
├── hygiene/             repository-wide invariants: Q1-Q3, X1-X5, P4, G2
├── lint/                file bytes, shell, JSON, workflows
├── marketplace/         catalog generation and validation
├── plugin_validation/   the official CLI, frontmatter, hooks, README contract, evals
└── versioning/          bumps, CHANGELOG, tags
```

## Support files

| File | Function |
| --- | --- |
| `pyproject.toml` | Dependencies and configuration for pytest, Ruff, and Basedpyright. |
| `scripts/__init__.py` | Makes `scripts` a package so entrypoints run as `python -m scripts.<area>.<name>`. |
| `scripts/<area>/__init__.py` | One per area folder, so every import is absolute. |
