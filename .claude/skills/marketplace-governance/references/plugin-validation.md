# Static plugin validation

`scripts/plugin_validation/`. Deterministic, free checks that read a plugin's
files without running a model. Behavioural checks cost money and live in the
eval protocol; if a check can be static, it is not an eval.

## Ground rules

- `claude plugin validate --strict` is the source of truth for manifest and hook shape. Never reimplement what it already checks.
- It is a necessary gate, not a sufficient one. A green run is not proof that a plugin works.
- Always pass `--strict`. Two classes of broken hook are warnings without it, and the runtime ignores them in silence.
- Every check this area adds exists because a probe showed the official validator does not cover it. Record the binary version and the date with the probe.
- When the CLI starts covering one of them, keep the local check as defence in depth and note the overlap.

## What the official validator covers

Verified against Claude Code `2.1.278` on 2026-09-20, one defect per probe.

| Defect | Result |
| --- | --- |
| Hook entries declared outside the `hooks` object | Hard error |
| `timeout` not a number | Hard error |
| `command` key absent on a `type: command` handler | Hard error |
| Known manifest field with the wrong type | Hard error |
| Unknown manifest field | Warning, fails under `--strict` |
| Unknown hook event name | Warning, fails under `--strict`; the entry is ignored at runtime |
| Unknown hook type | Warning, fails under `--strict`; the entry is ignored at runtime |
| `command` present but an empty string | **Not detected** |
| `matcher` that does not compile as a regex | **Not detected** |
| `matcher` naming a tool that does not exist | **Not detected** |
| `command` pointing at a script that does not exist | **Not detected** |
| `version` that is not SemVer | **Not detected** |
| Skill frontmatter that is not parseable YAML | **Not detected**, exits 0 |
| Unknown key in skill frontmatter | **Not detected** |
| Malformed `allowed-tools` | **Not detected** |

A hook that fails to load is worst in a plugin whose purpose is to block. The
lock never closes and nothing says so, which is why the warning rows are treated
as errors here rather than left to `--strict` alone.

## `claude_cli.py`

- `run_claude(args, cwd)` executes the CLI found on `PATH`, never a bundled copy. Claude Code is not a repository dependency.
- Locally that is the maintainer's own install; in CI it is the version the workflows pin.
- `collect_findings(report)` parses the validator's report into structured findings so a caller can filter rather than grep.
- `EMPTY_MARKETPLACE_WARNING` is the one finding tolerated while `plugins/` is empty.

## `validate_claude.py` — entrypoint

- Runs `claude plugin validate --strict` on the marketplace manifest **and** on every plugin directory.
- Both targets are required: validating the marketplace root does not check plugin contents. That gap was `DEBT-0001`.
- Reports the local CLI version against the version CI pins. A mismatch is not an error, but results may differ, so it is stated rather than hidden.

## `readme_contract.py`

- Enforces the plugin README against `templates/plugin-README-reusable-template.md` and the root README catalog row against its own template, so a published plugin cannot ship with missing sections, template drift, or no catalog row.
- `read_contract(template)` derives the required section list from the template itself, so the template stays the single source.
- `section_titles()` and `section_bodies()` split a README into comparable parts; `heading_title()` normalizes one heading.
- `OPTIONAL_SECTIONS` marks the sections a plugin may omit. Everything else is required.
- `header_badges()` reads the badge row; `CORE_BADGES` requires Version, License, Kind, Claude Code, and Claude Cowork.
- `surface_status()` maps a surface URL to its status emoji, so support tables cannot claim a state the badge contradicts.
- `badge_minimums()` and `check_requirement_minimums()` cross-check the versions a badge advertises against the Requirements table body.
- A README that ships a script or names a network tool must carry the matching Network badge. A missing badge fails, not only a false one.
- `check_plugin_readme(id, readme, contract)` is the single entry the marketplace validator calls.

## Tests

- `test_claude_cli.py` — invocation shaping and findings parsing, including the tolerated empty-marketplace warning.
- `test_claude_code_schemas.py` — every skeleton in `schemas/claude-code/` compiles, accepts the complete examples from the official docs, and rejects known mistakes. The fixtures are the docs' own examples, so a failure means the docs moved.
- `test_skill_frontmatter.py` — every `plugins/*/skills/*/SKILL.md` frontmatter parses as YAML and `description` plus `when_to_use` fit the 1,536-character budget. Both failures are silent under the official validator, and an unparseable description is the defect that reaches users.
- `test_readme_contract.py` — missing sections, template drift, badge mismatches, and the missing-Network-badge case.
