# Templates

Output shapes for each phase. The proposal table and the acceptance record are strict; the guide and the report are defaults to adapt. Write them in the language the user writes in; keep file paths, commands and identifiers as they are.

**Contents:** [Agent report contracts](#agent-report-contracts) · [Proposal](#proposal) · [Acceptance record](#acceptance-record) · [Final report](#final-report) · [Guide skeleton](#guide-skeleton)

## Agent report contracts

When an agent is unavailable and you do its work yourself, produce the same shape.

- **Scout:** environment; inventory of existing automation, each with its state (works, broken, conflicting, unused); recurring-work signals with evidence (`file:line`, a command and its count, or a commit subject pattern with its count); defects; what it could not check.
- **Researcher:** installed and latest version; features relevant to the focus, each with the minimum version, the source URL and a literal quote; changelog entries since the installed version that matter here; conflicts between the docs and the repository's files; pages it could not reach.
- **Verifier:** one row per item and test: item, test, command, observed result, verdict (`pass`, `fail`, `not verifiable here`), and for each failure the cause and the file to fix.

## Proposal

```markdown
## Findings

<three to six lines: what the repository is, what already exists, the strongest signals>

## Proposed automation

| #   | Signal and evidence                                                            | Automation                            | Feature and location                                      | Confirmed by                                                                                        | Effort | Impact                        | Context cost     | Risk |
| --- | ------------------------------------------------------------------------------ | ------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------ | ----------------------------- | ---------------- | ---- |
| 1   | `.claude/settings.json:6` runs `.claude/hooks/format.sh`, which does not exist | Restore the formatter hook            | Hook, `.claude/settings.json` + `.claude/hooks/format.sh` | hooks page: command hooks receive the event as JSON on stdin                                        | S      | High: every edit errors today | None             | Low  |
| 2   | 6 commits `style: fix lint errors after review` (`git log --grep`)             | `verify` skill running lint and tests | Skill, `.claude/skills/verify/`                           | skills page: a project skill named `verify` runs before each commit (minimum version from the page) | S      | High                          | Description only | Low  |

## Recommendation

<which rows, in which order, and why; what to do first if the user wants only one>

## Considered and rejected

- <item>: <reason (no signal / built-in covers it / cost exceeds value)>

## Decisions for you

1. <decision>: <options, with the recommended one first and why>

Nothing has been changed. Reply with the rows to build, or "all".
```

Effort: S (under an hour of work for Claude), M, L. Impact names the concrete effect, not "medium". Risk names what goes wrong if the item misbehaves.

## Acceptance record

One per approved item, written before building it and updated with results:

```markdown
### <#>. <automation>

- Files: <paths>
- Verified against: <doc URL> — "<quoted line>"
- Positive test: <command or action> → expected <result>
- Negative test: <command or action> → expected <result>
- Result: positive <pass/fail + raw output excerpt>; negative <pass/fail + raw output excerpt>
- After restart: <step, or "none">
```

## Final report

```markdown
## Built

| #   | Automation | Files | Positive | Negative | Verifier |
| --- | ---------- | ----- | -------- | -------- | -------- |

## Not built or not proven

- <item>: <why; what remains>

## Verify after restart

- <item>: <exact step>

## Decisions made

- <decision>: <reason>

## Guide

<path>
```

## Guide skeleton

```markdown
# Working with Claude Code in <project>

## What happens on its own

- <hook or rule>: <when it fires>, <what it does>, <what you see when it acts>

## What you start

- `/<skill> <args>`: <when to use it>, <what it does>, <where it stops for you>

## Agents Claude can delegate to

- `<agent>`: <what to ask for>

## How to tell it is working

- <observable sign per item; `/hooks`, `/permissions`, `/context` where useful>

## Turning something off

- <item>: <exact edit or command>

## Left out on purpose

- <item>: <reason>, <signal that would justify it later>
```
