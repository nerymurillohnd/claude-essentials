# Claude Code automation

How Claude Code is set up to maintain this repository: what runs on its own, what you start, and what each piece guarantees. Decisions: [ADR claude-code-automation](adr/decisions/ADR_2026-10-04_claude-code-automation.md), [ADR release-orchestration](adr/decisions/ADR_2026-10-04_release-orchestration.md). Everything here maintains the repository; none of it is shipped to plugin users.

**Contents:** [What runs on its own](#what-runs-on-its-own) · [Skills](#skills) · [On GitHub](#on-github) · [Agent](#agent) · [Workflows](#workflows) · [Gates](#gates) · [Scripts](#scripts) · [Limits](#limits) · [Change the automation](#change-the-automation)

## What runs on its own

Project settings in `.claude/settings.json` apply to every session in a folder you trust.

| Piece                    | When                                             | What it does                                                                                                                                                                                                                                                           |
| ------------------------ | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `permissions.ask`        | Before the tool runs                             | Asks before every `git push`, `git remote add` or `set-url`, pull request create, merge, edit, close, comment or review, release, repository or label change, workflow run, `claude plugin tag --push`, GitHub MCP write and Copilot review request, even in auto mode |
| `permissions.deny`       | Before the tool runs                             | Blocks commits with `--no-gpg-sign` or `--no-verify`, `git -c commit.gpgsign=false` or `tag.gpgsign=false`, and force pushes                                                                                                                                           |
| `guard-bash` hook        | Before every Bash call                           | Asks before pushes and GitHub writes the text rules miss (`git -C . push`, `bash -c '…'`, `xargs git push`); denies signing and hook bypasses written as an exact option token or a `-c` config value, so a commit message that mentions a flag passes                 |
| `guard-edit` hook        | Before Edit and Write                            | Denies hand edits of `version` in a plugin's `plugin.json` and of `BEGIN GENERATED` blocks                                                                                                                                                                             |
| `guard-sources` hook     | Before file, search, shell, web and GitHub tools | Denies reading or searching into the forbidden sources listed in the untracked `CLAUDE.local.md`                                                                                                                                                                       |
| `format` hook            | After Edit and Write                             | Runs prettier on edited Markdown, JSON, YAML and workflow scripts and tells Claude to re-read the file                                                                                                                                                                 |
| `session-status` hook    | Session start, resume, clear, compaction         | Prints the branch, changed files, a notice when Claude Code is newer than the pin, and a reminder to read files with the Read tool                                                                                                                                     |
| `worktree.baseRef: head` | New worktrees                                    | Worktrees start from your local `HEAD`, so unpushed commits are present                                                                                                                                                                                                |
| `verify` skill           | Before every commit                              | Claude runs `python3 scripts/check.py` before committing (Claude Code runs a project skill named `verify` before commits, except docs-only and tests-only ones)                                                                                                        |

Approving a prompt with "don't ask again" saves an allow rule in your local settings; it never overrides a project `ask` rule, so the next push asks again.

## Skills

Type `/<name>` or ask in plain words; `release-plugin` runs only when you type it.

| Skill                                         | Use it to                                                                                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `/new-plugin <name> <category>`               | Create a plugin: proposal, `new_plugin.py`, components, validation, a real session, pull request                                           |
| `/add-component <plugin> skill\|agent <name>` | Add a skill or agent to an existing plugin with the official generator                                                                     |
| `/release-plugin <plugin> <level> <topic>`    | Release: branch, notes, bump, behaviour check, signed commit, branch push and pull request; stops for `/github-ops:automatic-pr-lifecycle` |
| `/release-plugin <plugin> tag`                | After the merge: signed tag, `git tag -v`, tag push, GitHub Release check                                                                  |
| `/review-pr [number\|branch]`                 | Review with the `plugin-reviewer` agent: gates on a temporary checkout, quality bar, security, release rules                               |
| `/run-marketplace <plugin>`                   | Drive a plugin in a real headless session with only that plugin loaded                                                                     |
| `/sync-docs`                                  | Fix documentation drift after a change                                                                                                     |
| `/cc-currency`                                | Compare the repository with the current Claude Code release and update rules and the pin                                                   |
| `/verify`                                     | Run every gate                                                                                                                             |
| `plugin-versioning`                           | Loaded by Claude when it touches `plugins/` or the catalog: bump level, PR or direct push, branch names                                    |

## On GitHub

The Claude GitHub App runs two workflows ([ADR claude-github-action](adr/decisions/ADR_2026-10-04_claude-github-action.md)), authenticated with the `CLAUDE_CODE_OAUTH_TOKEN` repository secret and billed to the maintainer's Claude subscription:

- `claude-code-review.yml` reviews every push to a non-draft pull request. Each run re-checks whether Claude's earlier findings are fixed, reviews the current head for correctness and this repository's rules (CLAUDE.md, quality bar, security review, releasing, portability), posts new findings inline and posts one summary with a verdict and a fixed/open table. CI runs the gates; `/review-pr` additionally runs them on a checkout. The action skips (with a green check) a pull request whose copy of the workflow differs from `main`, so a change to these workflows is reviewed only locally.
- `claude.yml` answers `@claude` in an issue, a pull request comment or a review. Only users with write access can trigger it, so a third party's issue runs nothing until a maintainer comments `@claude <request>`. Claude may then push a `claude/` branch with the app's token; asking is the approval.

## Agent

For every pull request, run the bundled `/code-review high` for correctness bugs and `/review-pr` for this repository's own rules (release discipline, quality bar, security, portability, docs); neither replaces the other. For a plugin with hooks or MCP servers, `/code-review ultra` (cloud, billed after three free runs) is an optional extra pass before the merge.

`plugin-reviewer` (`.claude/agents/plugin-reviewer.md`) reviews a pull request or branch without editing anything. It checks out the head in a temporary worktree (prefix `claude-essentials-review-`), runs `python3 scripts/check.py` and `scripts/check_pr.py` there, reads the rules for each changed path, and returns a verdict and a findings table with `file:line` evidence. `/review-pr` runs it in the background; ask for it by name in any session.

## Workflows

Saved dynamic workflows in `.claude/workflows/` run many agents and cost more than a skill. Start them yourself with `/<name>`; each stays under ten agents and verifies every finding with a skeptic agent before reporting it.

| Workflow          | Use it for                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- |
| `/drift-audit`    | Meaning drift between guides, rules, CLAUDE.md, skills and the code, which the `docs` gate cannot see               |
| `/rules-currency` | Every fact in `.claude/rules/` checked against the official docs and changelog; pass the pin and the latest version |
| `/review-pr-deep` | Large or risky pull requests: release, quality, security and docs reviewed in parallel                              |

## Gates

`python3 scripts/check.py` runs the same gates locally and in CI ([testing](testing.md)). Two gates support the automation:

- `validate` also runs `claude plugin validate .claude --strict`, so a broken skill or agent frontmatter fails.
- `docs` (`scripts/check_docs.py`) fails when a copy of a pinned version, the gate list, a script or `check.py` target name, a rule's `paths`, a relative link or a `docs/*.md` reference no longer matches the repository, or when a project skill's `name` differs from its directory. When you reword a sentence that carries a pin, update `PIN_SITES` in that script.

## Scripts

| Script                     | Purpose                                                                      |
| -------------------------- | ---------------------------------------------------------------------------- |
| `scripts/claude_hooks.py`  | The hooks above; each decision is unit-tested in `tests/test_gates.py`       |
| `scripts/check_docs.py`    | The `docs` gate                                                              |
| `scripts/drive_plugin.py`  | Drives a plugin in a headless session ([testing](testing.md#drive-a-plugin)) |
| `scripts/add_component.py` | Adds a skill or agent to an existing plugin                                  |

## Limits

- Hooks parse shell commands on a best-effort basis: a command built at runtime (a variable holding `push`, a relative `cd` into a forbidden folder) can slip past them. The permission prompts and the review are the remaining layers.
- Skills and workflows guide Claude; the gates, `check_pr.py` and the permission prompts enforce.
- `drive_plugin.py` uses your login: the session sees your account email. For proof that holds for strangers, run `claude plugin eval plugins/<name> --no-publish`.
- Hooks run `python3` on every tool call for anyone who trusts the folder ([CONTRIBUTING](../CONTRIBUTING.md)).
- A new `.claude/agents/` directory or `.claude/workflows/` file may need `/reload-skills` or a new session before it appears.

## Change the automation

Edit the file, run `python3 scripts/check.py`, and record a changed decision in a new ADR. Settings and hooks: `.claude/settings.json` and `scripts/claude_hooks.py` with its tests. Skills: write them with the `skills-best-practices` skill when available and read back what loads (a `$0` in prose is an argument placeholder; escape it as `\$0`). Workflows: load `/workflow-authoring` first; keep `export const meta` a plain literal.
