---
paths:
  - ".claude/settings.json"
  - ".claude/skills/**"
  - ".claude/agents/**"
  - ".claude/workflows/**"
  - ".claude/rules/automation.md"
  - "scripts/claude_hooks.py"
  - ".github/workflows/claude*.yml"
---

# Claude Code Automation

- This is how Claude Code is set up to maintain this repository: what runs on its own, what the maintainer starts, and what each piece guarantees.
- Decisions: ADR claude-code-automation, ADR release-orchestration.
- Everything here maintains the repository; none of it is shipped to plugin users.

## What Runs on Its Own

- Project settings in `.claude/settings.json` apply to every session in a trusted folder.
- `permissions.ask` runs before the tool. It asks before every `git push`, `git remote add` or `set-url`, pull request create, merge, edit, close, comment or review, release, repository or label change, workflow run, `claude plugin tag --push`, GitHub MCP write and Copilot review request, even in auto mode.
- `permissions.deny` runs before the tool. It blocks commits with `--no-gpg-sign` or `--no-verify`, `git -c commit.gpgsign=false` or `tag.gpgsign=false`, and force pushes.
- The `guard-bash` hook runs before every Bash call. It asks before pushes and GitHub writes the text rules miss (`git -C . push`, `bash -c '…'`, `xargs git push`). It denies signing and hook bypasses written as an exact option token or a `-c` config value, so a commit message that mentions a flag passes, also when `git commit` or `git tag` reads it from a heredoc with `-F -`; every other heredoc is parsed as written.
- The `guard-edit` hook runs before Edit and Write. It denies hand edits of `version` in a plugin's `plugin.json` and of `BEGIN GENERATED` blocks.
- The `guard-sources` hook runs before file, search, shell, web and GitHub tools. It denies reading or searching into the forbidden sources listed in the untracked `CLAUDE.local.md`.
- The `format` hook runs after Edit and Write. It runs prettier on edited Markdown, JSON, YAML and workflow scripts and tells Claude to re-read the file.
- The `session-status` hook runs at session start, resume, clear and compaction. It prints the branch, changed files and a reminder to read files with the Read tool.
- `worktree.baseRef: head` makes new worktrees start from the local `HEAD`, so unpushed commits are present.
- The `verify` skill: Claude Code tells Claude to run it before each commit, and it runs `scripts/check.py`. The instruction applies when the skill loads from a project, personal, enterprise, additional-directory or `.claude/commands/` location, Claude may invoke it (no `disable-model-invocation: true`) and `includeGitInstructions` is not off. Docs-only and tests-only changes are excepted, and plugin skills do not count.
- Approving a prompt with "don't ask again" saves an allow rule in the local settings. It never overrides a project `ask` rule, so the next push asks again.

## Skills

- Run a skill with `/<name>` or in plain words; `release-plugin` runs only when typed.
- `/new-plugin <name> <category>` - Create a plugin: proposal, `scripts/new_plugin.py`, components, validation, a real session, pull request.
- `/add-component <plugin> skill|agent <name>` - Add a skill or agent to an existing plugin with the official generator.
- `/release-plugin <plugin> <level> <topic>` - Release: branch, notes, bump, behaviour check, signed commit, branch push and pull request. It stops for `/github-ops:automatic-pr-lifecycle`.
- `/release-plugin <plugin> tag` - After the merge: signed tag, `git tag -v`, tag push, GitHub Release check.
- `/review-pr [number|branch]` - Review with the `plugin-reviewer` agent: gates on a temporary checkout, quality bar, security, release rules.
- `/run-marketplace <plugin>` - Drive a plugin in a real headless session with only that plugin loaded.
- `/sync-docs` - Fix documentation drift after a change.
- `/cc-currency` - Compare the repository with the current Claude Code release, update the affected rules and record the last reviewed release.
- `/verify` - Run every gate.
- `plugin-versioning` - Claude loads it when it touches `plugins/` or the catalog: bump level, PR or direct push, branch names.

## On GitHub

- The Claude GitHub App runs one workflow (ADR claude-github-action; `claude.yml` was removed by ADR remove-claude-mention-workflow, so `@claude` mentions run nothing). It authenticates with the `CLAUDE_CODE_OAUTH_TOKEN` repository secret and is billed to the maintainer's Claude subscription.
- `.github/workflows/claude-code-review.yml` reviews every push to a non-draft pull request.
  - Each run re-checks whether Claude's earlier findings are fixed.
  - It reviews the current head for correctness and this repository's rules (CLAUDE.md, quality bar, security review, releasing, portability).
  - It posts new findings inline and one summary with a verdict and a fixed/open table.
  - CI runs the gates; `/review-pr` additionally runs them on a checkout.
  - The action skips, with a green check, a pull request whose copy of the workflow differs from `main`, so a change to these workflows is reviewed only locally (observed 2026-10-04; the action's docs do not state it).

## Review and Agent

- For every pull request, run the bundled `/code-review high` for correctness bugs and `/review-pr` for this repository's own rules (release discipline, quality bar, security, portability, docs). Neither replaces the other.
- For a plugin with hooks or MCP servers, `/code-review ultra` (cloud research preview; Pro and Max accounts get three one-time free runs, then it bills as usage credits, about $5 to $25 per review; on Bedrock, Agent Platform, Foundry and Zero Data Retention organizations it runs a local review instead) is an optional extra pass before the merge.
- `plugin-reviewer` (`.claude/agents/plugin-reviewer.md`) reviews a pull request or branch without editing anything.
  - It checks out the head in a temporary worktree (prefix `claude-essentials-review-`).
  - It runs `scripts/check.py` and `scripts/check_pr.py` there and reads the rules for each changed path.
  - It returns a verdict and a findings table with `file:line` evidence.
  - `/review-pr` runs it in the background; ask for it by name in any session.

## Workflows

- Saved dynamic workflows in `.claude/workflows/` run many agents and cost more than a skill.
- Start them with `/<name>`. Each stays under ten agents and verifies every finding with a skeptic agent before reporting it.
- `/drift-audit` - Meaning drift between guides, rules, CLAUDE.md, skills and the code, which the `docs` gate cannot see.
- `/rules-currency` - Every fact in `.claude/rules/` checked against the official docs and changelog; pass the last reviewed release as `pin` and the latest version.
- `/review-pr-deep` - Large or risky pull requests: release, quality, security and docs reviewed in parallel.

## Gates

- `scripts/check.py` runs the same gates locally and in CI; their behaviour is in `.claude/rules/testing/gates.md`. The `validate` and `docs` gates also cover this automation.

## Scripts

- `scripts/claude_hooks.py` - The hooks above; each decision is unit-tested in `tests/test_gates.py`.
- `scripts/check_docs.py` - The `docs` gate.
- `scripts/drive_plugin.py` - Drives a plugin in a headless session (`.claude/rules/testing/drive-plugin.md`).
- `scripts/add_component.py` - Adds a skill or agent to an existing plugin.

## Limits

- Hooks parse shell commands on a best-effort basis. A command built at runtime (a variable holding `push`, a relative `cd` into a forbidden folder) can slip past them. The permission prompts and the review are the remaining layers.
- Skills and workflows guide Claude; the gates, `scripts/check_pr.py` and the permission prompts enforce.
- `scripts/drive_plugin.py` uses the maintainer's login, so the session sees the account email. For proof that holds for strangers, run `claude plugin eval plugins/<name> --no-publish`.
- Hooks run `scripts/claude_hooks.py` by path (exec form; its shebang finds `python3`) on every tool call for anyone who trusts the folder (`CONTRIBUTING.md`).
- A new or edited `.claude/workflows/` file needs `/reload-skills` or a new session. The sub-agents docs say a newly created agents directory needs a new session (when `~/.claude/agents/` did not exist at session start); one created mid-session was also observed to load without a restart (`.claude/rules/claude-code-features.md`).

## Change the Automation

- Edit the file, run `scripts/check.py`, and record a changed decision in a new ADR.
- Settings and hooks: `.claude/settings.json` and `scripts/claude_hooks.py` with its tests.
- Skills: write them with the `skills-best-practices` skill when available and read back what loads. A `$0` in prose is an argument placeholder; escape it as `\$0`.
- Workflows: load `/workflow-authoring` first; keep `export const meta` a plain literal.
