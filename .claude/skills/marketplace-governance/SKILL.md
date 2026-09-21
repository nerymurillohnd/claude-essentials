---
name: marketplace-governance
description: Map of this repository's maintainer tooling and its validation protocol, organized as one folder per governance area, each with a reference detailing what every entrypoint, module, and test executes.
when_to_use: Use when adding, moving, renaming, or reviewing any file under scripts/, when deciding which area a new maintainer script belongs to, when a restructure changes where governance tooling lives, or when authoring or running a plugin eval suite.
---

# Marketplace governance

Maintainer tooling only. Nothing here is distributed to users, and no plugin
loads any of it. The user-facing surface is `plugins/`.

## Placement rule

- A file's folder is its classification. One folder per area, ten areas, no `misc`.
- Entrypoints live at the root of their area and run as `python -m scripts.<area>.<name>`.
- Modules and their tests live side by side in the same area folder.
- A test that covers a shell hook or a schema belongs to the area it guards, not to the module that happens to call it.
- A new file that fits no area means the taxonomy is wrong. Add the area, then the file.
- Every area folder carries an `__init__.py`, as does `scripts/` itself, so imports are absolute and unambiguous.

## 1. GitHub — API, Actions, and `.github/`

`scripts/github/` — what each file executes: [`references/github.md`](references/github.md)

| File | Function |
| --- | --- |
| `client.py` | Minimal REST client over HTTP, with no retries; every response is treated as external data. Renamed from `github.py` to avoid `github.github`. |
| `test_client.py` | Covers the REST client. |
| `triage.py` | Entrypoint for `workflows/triage.yml`; reads the PR through the API and never executes it. |
| `triage_rules.py` | Pure rules defining which labels apply to an issue or PR (`ADR-0004`). Renamed from `triage.py`, which the entrypoint now holds. |
| `test_triage_rules.py` | Covers the labeling rules. |
| `sync_labels.py` | Synchronizes repository labels with the taxonomy; dry-run by default. |
| `labels.py` | Taxonomy from `.github/labels.json` plus `plugin: <name>` derived per plugin. |
| `test_labels.py` | Covers the taxonomy and the diff against the remote state. |
| `generate_issue_forms.py` | Regenerates the **Affected plugin** dropdown from `plugins/` on disk. |
| `issue_forms.py` | Contract for the issue forms parsed by the triage bot; it must not drift. |
| `test_issue_forms.py` | Covers the issue form contract. |
| `repo_metadata.py` | Validates issue forms against `schemas/github/` and validates the shape of `labels.json`. |
| `test_repo_metadata.py` | Covers repository metadata validation. |

## 2. Versioning and releases

`scripts/versioning/` — what each file executes: [`references/versioning.md`](references/versioning.md)

| File | Function |
| --- | --- |
| `check_versions.py` | Requires a SemVer bump and a dated `CHANGELOG` entry for each changed plugin. |
| `tag_versions.py` | Creates and pushes `{name}--v{version}` with `claude plugin tag --push`; idempotent. |
| `version_plan.py` | Pure `ADR-0003` rules defining which files are runtime files and which bump they require. |
| `test_version_plan.py` | Covers bump rules and the list of exempt files. |
| `changelog.py` | Detects `## [X.Y.Z] - YYYY-MM-DD` sections in a plugin's `CHANGELOG`. |
| `test_changelog.py` | Covers version-section parsing. |

## 3. Marketplace and catalog

`scripts/marketplace/` — what each file executes: [`references/marketplace.md`](references/marketplace.md)

| File | Function |
| --- | --- |
| `generate_marketplace.py` | Regenerates `plugins[]` in `marketplace.json` from each `plugin.json` on disk. |
| `validate_marketplace.py` | Validates manifests against the schemas and cross-checks disk ↔ catalog in both directions. |
| `catalog.py` | Builds and compares catalog entries; `category` and `tags` come from metadata. |
| `test_catalog.py` | Covers entry construction and drift detection. |

## 4. Static plugin validation

`scripts/plugin_validation/` — what each file executes: [`references/plugin-validation.md`](references/plugin-validation.md)

| File | Function |
| --- | --- |
| `validate_claude.py` | Runs `claude plugin validate --strict` against the marketplace and every plugin. |
| `claude_cli.py` | Executes the CLI found on `PATH`; it is never a repository dependency. |
| `test_claude_cli.py` | Covers invocation and findings parsing. |
| `test_claude_code_schemas.py` | Ensures the `schemas/claude-code/` schema skeletons accept the documentation examples. |
| `test_skill_frontmatter.py` | Ensures frontmatter parses as YAML and fits within the 1,536-character budget. |
| `readme_contract.py` | Defines the plugin `README` contract and the catalog row in the root `README`. |
| `test_readme_contract.py` | Covers missing sections, template drift, and badges. |

## 5. Shell quality

`scripts/shell_quality/` — what each file executes: [`references/shell-quality.md`](references/shell-quality.md)

| File | Function |
| --- | --- |
| `lint_shell.py` | Runs ShellCheck with `.shellcheckrc` and formats all `.sh` files with `shfmt`. |
| `shell_files.py` | Discovers shell scripts using the same rule as the `PostToolUse` hook. |
| `test_shell_files.py` | Covers discovery by file extension and by shebang. |
| `test_plugin_shell_tests.py` | Runs every `plugins/**/test-*.sh` under both `bash` and `/bin/bash`. |

## 6. Plugin documentation contracts

`scripts/plugin_docs/` — what each file executes: [`references/plugin-docs.md`](references/plugin-docs.md)

| File | Function |
| --- | --- |
| `test_plugin_script_env.py` | Every environment variable read by a script must be named in that plugin's `README`. |
| `test_readme_test_vars.py` | Every documented `<PREFIX>_TEST_BASH` variable must be read by a plugin test suite. |

## 7. Plugin workflows

`scripts/plugin_workflows/` — what each file executes: [`references/plugin-workflows.md`](references/plugin-workflows.md)

| File | Function |
| --- | --- |
| `test_plugin_workflows.py` | Ensures `meta` is pure literal data, phases are declared, and the body compiles against a runtime stub. |

## 8. Repository hooks

`scripts/repo_hooks/` — what each file executes: [`references/repo-hooks.md`](references/repo-hooks.md)

| File | Function |
| --- | --- |
| `test_plugin_paths.py` | Verifies parity between `version_plan.py` and `.claude/hooks/lib/plugin-paths.sh`. |
| `test_checklist_gate.py` | Covers `checklist.sh` and the `Stop` hook that prevents completion when the checklist is incomplete. |
| `test_push_guard.py` | Tests `guard-push.sh` against a bare test origin; rejects pushes to a merged branch. |
| `test_record_audit.py` | Ensures `record-audit.sh` records the `repo-auditor` verdict for each audited head. |
| `test_repo_root.py` | Ensures `repo-root.sh` selects the correct tree inside a Git worktree. |

## 9. Shared infrastructure

`scripts/common/` — what each file executes: [`references/common.md`](references/common.md)

| File | Function |
| --- | --- |
| `plugins.py` | Paths and readers for `plugins/<name>/.claude-plugin/plugin.json`. |
| `test_plugins.py` | Covers plugin discovery and manifest reading. |
| `errors.py` | Normalizes exceptions so no code assumes attributes inside an `except` block. |
| `test_errors.py` | Covers error normalization. |

## 10. File hygiene and tooling alignment

`scripts/hygiene/` — what each file executes: [`references/hygiene.md`](references/hygiene.md)

| File | Function |
| --- | --- |
| `test_text_files.py` | Ensures no text file contains raw control characters. |
| `test_tooling_alignment.py` | Ensures the MCP server analyzes with the same version used by the local gate and CI. |

## 11. Behavioural validation

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
├── common/              shared readers and error handling
├── github/              REST client, triage, labels, issue forms
├── hygiene/             file bytes and tooling version alignment
├── marketplace/         catalog generation and validation
├── plugin_docs/         README and environment-variable contracts
├── plugin_validation/   the official CLI, schemas, frontmatter, README contract
├── plugin_workflows/    workflow dialect checks
├── repo_hooks/          suites for .claude/hooks/
├── shell_quality/       ShellCheck, shfmt, plugin shell suites
└── versioning/          bumps, CHANGELOG, tags
```

## Support files

| File | Function |
| --- | --- |
| `pyproject.toml` | Dependencies and configuration for pytest, Ruff, and Basedpyright. |
| `scripts/__init__.py` | Makes `scripts` a package so entrypoints run as `python -m scripts.<area>.<name>`. |
| `scripts/<area>/__init__.py` | One per area folder, so every import is absolute. |
