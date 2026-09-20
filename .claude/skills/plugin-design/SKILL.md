---
name: plugin-design
description: The end-to-end procedure for creating a plugin, or making a major change to one, in the claude-essentials marketplace, from the user's idea to a merged, tagged release. Enforces the design phase with a Stop-hook checklist and hands review and delivery to plugin-release-review and pr-delivery. Use it whenever the user brings a plugin idea, goal, or references ("quiero un plugin para…", "diseña", "blueprint", "propuesta"), and before writing any plugin file.
argument-hint: "[plugin-id]"
arguments: plugin_id
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"${CLAUDE_PROJECT_DIR}/.claude/hooks/checklist-gate.sh"'
          timeout: 300
---

# Plugin design

We build the reference standard for the community: one marketplace where an
advanced developer finds each plugin complete, correct, and well wired, instead
of assembling it from many repositories. The user gives the goal and
references. You own the research, the decisions, and their justification.

Think systemically: map dependencies, second- and third-order effects, and
risks per scenario before deciding. Live, current sources win over memory.

## Phase 0: Start

1. Start the checklist: `.claude/hooks/lib/checklist.sh start .claude/skills/plugin-design/checklist.json "$plugin_id" "${CLAUDE_SESSION_ID}"`.
2. Record each item with `checklist.sh check <id> "<evidence>"`.
3. Invoke `superpowers:brainstorming`.
4. Invoke every `plugin-dev:*` skill that matches the components in play.

## Phase 1: Goal

1. Restate the goal in one sentence and confirm it.
2. Ask only what is the user's call: scope, priorities, trade-offs with no evidence edge.
3. Mark those `checklist.sh needs-user <id> "<question>"`.
4. Decide everything else yourself, with justification.

## Phase 2: Research

1. Read yourself the primary docs the design touches (CLAUDE.md reference table).
2. Read the last 6 months of the Claude Code changelog.
3. Read every source the user gave.
4. Search for comparable plugins, skills, hooks, and marketplaces yourself.
5. Record one verdict per source: adopt, reject, why.
6. Flag every repo doc that contradicts live docs.

## Phase 3: Evidence

1. Use the real installed tool or service.
2. Run its commands and capture real output.
3. Test edge cases: broken config, missing binary, excludes, CI, odd paths.
4. For LSP, MCP, or hooks, capture live what Claude Code sends and answers.
5. Tag each fact `[observed]` or `[doc]` with its version.

## Phase 4: Design decisions

1. Decide every surface in [`references/surfaces.md`](references/surfaces.md): used or rejected, one line why.
2. Decide how many skills and where each boundary falls.
3. Split skills by purpose so none loads another's context.
4. Decide agents, subagents, teams, orchestrator, auditor, workflows.
5. Justify each piece against the simpler alternative.
6. Context-dependent work is instructions and checklists.
7. Fragile, deterministic work is a script.
8. Pick each component's language: Bash + jq by default for shipped hooks; Python (stdlib, `#!/usr/bin/env python3`) when the logic needs it and the audience already has it, declared in Requirements.
9. Repo tests today are `node:test` (`scripts/**/*.test.mjs`) and bash suites (`plugins/**/test-*.sh`). Python tests via `uv run --script` need DEBT-0016 closed first (uv, pytest, Ruff, and Basedpyright gates in `npm run check` and CI).
10. Never `uv run` in a hook's hot path: it can download an interpreter or packages.

## Phase 5: Requirements and environments

1. Fill the 📋 Requirements table: minimum, check, why.
2. Define supported platforms: macOS, Linux, WSL, Windows with Git Bash, or as decided.
3. Design for any user installing from the plugin cache, never for the maintainer's machine.
4. State where it doesn't apply: Cowork, cloud, `-p`, IDE.

## Phase 6: Limits and failures

1. Write the non-goals.
2. List every failure mode with its defined behavior.
3. Decide fail-closed or fail-open per event.

## Phase 7: Verification plan

1. Test suites with realistic payloads, under `bash` and `/bin/bash`.
2. At least 3 evals: positive and negative triggers, with and without the plugin.
3. List the live checks still open.

## Phase 8: Spec and approval

1. Write `docs/superpowers/specs/YYYY-MM-DD-<id>-design.md` with one canonical section.
2. The checklist verifies the required sections.
3. Present it concisely.
4. The user approves or adjusts.
5. Build nothing before approval.

## Phase 9: Build

1. Branch from an updated `main`.
2. Read `.claude/rules/plugin-authoring.md` and `.claude/rules/shell-scripts.md` first: path-scoped rules load only when a matching file is read, not written.
3. Copy the template for the plugin's kind.
4. Write skills as contracts: short, clear, verifiable steps.
5. Keep references one level deep, with a table of contents over 100 lines.
6. Write the scripts, hooks, LSP, MCP, and agents decided.
7. Format and lint each file as you edit it.
8. Run the tests after each change.

## Phase 10: Verify

1. Run the suites under both bash.
2. Run `claude plugin eval` and update the README eval table in the same branch.
3. Run live checks with `claude -p --plugin-dir`.
4. Run `/code-review high` on the branch diff.
5. Run `/simplify` on the changed code.
6. Run `/security-review` when the plugin ships scripts, hooks, MCP, or LSP.
7. Run `/claude-api prompt-audit` on every `SKILL.md`, agent, and description.
8. Ask the user to run `/skill-doctor` to see the plugin's context cost (Claude can't invoke it).
9. Run `npm run check`.
10. Close each finding with its fix and a gate that catches it next time.

## Phase 11: Review

1. Run `/plugin-release-review <id>` on the first complete draft.
2. Re-run it after every change to runtime files, README, or `plugin.json`.

## Phase 12: Deliver

1. Run `/pr-delivery` and follow its checklist to merged, tagged, and clean.

## Phase 13: Close

1. Record debt and misalignments in `docs/maintenance/`.
2. Save to memory only what the repo doesn't record.
3. Report the outcome with evidence.
