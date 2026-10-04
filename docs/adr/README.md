# Architecture decision records

Decisions that shape this repository, in the format defined by [ADR 0001](0001-record-architecture-decisions.md). Start a new record from [the template](../../templates/adr/adr-template.md), number it after the last one, and add it to this index in the same pull request; `uv run scripts/check.py` fails otherwise. To change a decision, write a new record that supersedes the old one and set the old one's `status` to `superseded by NNNN`.

| ADR                                             | Decision                                                                          | Status   |
| ----------------------------------------------- | --------------------------------------------------------------------------------- | -------- |
| [0001](0001-record-architecture-decisions.md)   | Record architecture decisions as MADR-based ADRs                                  | Accepted |
| [0002](0002-marketplace-name-and-disclaimer.md) | Marketplace name `claude-essentials` with a non-affiliation disclaimer            | Accepted |
| [0003](0003-clean-room-policy.md)               | Clean-room policy for Claude Code content                                         | Accepted |
| [0004](0004-sourcing-policy.md)                 | Sourcing policy: automate and source first, hand-write last                       | Accepted |
| [0005](0005-in-repo-plugins-only.md)            | In-repository plugins only                                                        | Accepted |
| [0006](0006-per-plugin-versioning.md)           | Independent SemVer per plugin, version only in `plugin.json`, official tags       | Accepted |
| [0007](0007-release-automation.md)              | Release automation: hand-written changelogs, local release script, CI publication | Accepted |
| [0008](0008-validation-stack.md)                | Validation stack with zero repository dependencies                                | Accepted |
| [0009](0009-security-posture.md)                | Security posture for code that runs on users' machines                            | Accepted |
| [0010](0010-testing-approach.md)                | Testing approach: isolated install tests and gates proven by injected defects     | Accepted |
| [0011](0011-labels-and-pr-automation.md)        | Labels and pull request automation as code                                        | Accepted |
| [0012](0012-generated-readme-content.md)        | Generated README content that cannot drift from the plugins                       | Accepted |
| [0013](0013-minimum-claude-code-version.md)     | Minimum Claude Code version 2.1.289 for tooling and new plugins                   | Accepted |
| [0014](0014-editor-json-schemas-not-adopted.md) | Hand-written JSON Schemas for Claude Code files are not adopted yet               | Accepted |
