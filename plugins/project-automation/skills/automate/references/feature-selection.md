# Feature selection

How to turn a signal found in the repository into the right Claude Code feature. Read it in phase 3, before writing the proposal.

**Contents:** [Native-first ladder](#native-first-ladder) · [Signal to feature](#signal-to-feature) · [Enforcement or guidance](#enforcement-or-guidance) · [Where it lives](#where-it-lives) · [Context cost](#context-cost) · [Rejecting an item](#rejecting-an-item) · [Sources](#sources)

## Native-first ladder

For each signal, take the first rung that does the job well:

1. **A setting or permission rule.** No code to maintain; Claude Code enforces it.
2. **A built-in feature or bundled skill** (for example `/verify`, `/run`, `/code-review`, `/loop`, the sandbox, auto memory). Check the commands reference for the installed version; the bundled set changes often.
3. **A Markdown component**: CLAUDE.md line, path-scoped rule, skill, subagent, output style.
4. **A hook running a short script** in a language the project already uses, or a tool already on the machine (`jq` only if present; otherwise the project's runtime).
5. **A new dependency, MCP server or external service.** Only when a signal demands it and the user agrees to the new requirement.

A rung lower on the ladder must beat the rung above it on a concrete criterion (enforcement, context cost, reliability), stated in the proposal.

## Signal to feature

| Signal in the repository or history                                                                                                          | Usual feature                                                                      | Notes                                                                                  |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| A convention Claude got wrong twice; build, test or lint commands Claude must know                                                           | CLAUDE.md line                                                                     | Short and imperative; one line per fact                                                |
| Guidance that applies only to some files (tests, migrations, a package)                                                                      | Path-scoped rule in `.claude/rules/` with `paths:`                                 | Loads only when matching files are read or edited                                      |
| The same prompt typed to start a task; a multi-step procedure (release, migration, deploy) done by hand                                      | Skill in `.claude/skills/<name>/`                                                  | Side effects: `disable-model-invocation: true`                                         |
| "Run the checks before committing" written in CLAUDE.md, CONTRIBUTING or review comments; fix-up commits after review (`fix lint`, `format`) | A project skill named `verify` that runs the project's checks                      | Claude Code runs it before each commit on recent versions; confirm the minimum version |
| A rule that must hold every time: protected files, forbidden commands, secrets                                                               | Permission deny rule; a `PreToolUse` hook when a rule pattern cannot express it    | Hooks and rules are enforcement; text is not                                           |
| A formatter or linter run by hand after edits                                                                                                | `PostToolUse` hook matching `Edit` and `Write`, scoped with `if` to the file types | Must fail open and finish fast                                                         |
| Commands approved again and again in permission prompts                                                                                      | Allow rules in project settings                                                    | Never allow broad patterns such as `Bash(*)`                                           |
| A side task that floods the conversation (log triage, dependency audit, broad search)                                                        | Subagent in `.claude/agents/` with read-only tools                                 | Returns a summary; isolated context                                                    |
| A review the team repeats with the same checklist                                                                                            | Skill (checklist) plus optional read-only reviewer subagent                        | `/code-review` may already cover generic correctness                                   |
| Work spread across many files with findings to cross-check                                                                                   | Dynamic workflow saved in `.claude/workflows/`                                     | Costs many agents; start it only on request                                            |
| A check that should run on a schedule (dependency drift, nightly report)                                                                     | `/loop` or cron tools in a session; Desktop scheduled tasks; a CI job              | Session-scoped tasks stop with the session                                             |
| Pull requests that need a first review or `@claude` help                                                                                     | Claude Code GitHub Actions                                                         | Needs a repository secret; outward-facing                                              |
| Data Claude keeps asking for from another system                                                                                             | MCP server                                                                         | New requirement for every user; ask first                                              |
| Answers in the wrong format or length, session after session                                                                                 | Output style                                                                       | Applies to every response while active                                                 |
| Broken or contradictory existing automation (missing hook script, invalid frontmatter, unreachable rule)                                     | Fix in place                                                                       | Rank first: it misleads Claude on every session                                        |

## Enforcement or guidance

- Instructions in CLAUDE.md, rules and skills are followed by judgment and can be skipped. If the user would be harmed when the instruction is skipped once, use a hook or a permission rule.
- Permission rules are evaluated deny, then ask, then allow; the first match wins. An allow rule cannot carve an exception out of a deny rule; a `!` negation listed after the broader rule in the same deny list can (for example `Read(*.env)`, then `Read(!sample.env)`). Otherwise write deny rules for the exact paths or commands.
- Read and Edit deny rules cover Claude's file tools, recognized Bash file commands and redirections. They do not cover a program that opens the file itself. For OS-level protection, propose the sandbox.
- A `PreToolUse` hook blocks only with exit code 2 or a JSON deny decision. Exit 1, a crash or a timeout lets the call through. A hook decision never overrides a deny or ask rule.

## Where it lives

| Scope                       | Files                                                                                                              | Use for                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| Project, shared through git | `CLAUDE.md`, `.claude/settings.json`, `.claude/rules/`, `.claude/skills/`, `.claude/agents/`, `.claude/workflows/` | Anything every contributor should get            |
| Project, only this user     | `CLAUDE.local.md`, `.claude/settings.local.json`                                                                   | Personal preferences and experiments             |
| User, every project         | Files under the user's home `.claude/` directory                                                                   | Only when the user asks; outside this repository |

Default to project-shared for team conventions and enforcement, and to project-local for anything that reflects one person's tools or habits. Ask when it is not obvious.

## Context cost

| Feature                                  | Cost per request                                                                                                     |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| CLAUDE.md, unscoped rules, output styles | Full text, every request                                                                                             |
| Path-scoped rules                        | Full text, only after matching files are touched                                                                     |
| Skills                                   | Name and description every request; full text when used; nothing with `disable-model-invocation: true` until invoked |
| Subagents                                | Isolated; only the summary returns                                                                                   |
| Hooks                                    | Zero, unless they print output for Claude                                                                            |
| MCP servers                              | Tool names; schemas deferred until used                                                                              |

State the cost of each row in the proposal. A large CLAUDE.md addition needs a stronger signal than a hook.

## Rejecting an item

Drop an item, and list it under "considered and rejected", when:

- no signal in the repository supports it;
- a built-in feature or an existing piece of automation already does it;
- it needs a tool, account or service the project does not have, and the user has not agreed to add one;
- its failure mode is worse than the problem (a slow hook on every edit, a broad allow rule);
- it duplicates CI: prefer making CI's commands easy for Claude to run over re-implementing them.

## Sources

- Choosing features and context cost: https://code.claude.com/docs/en/features-overview
- Permission rule order and Read deny scope: https://code.claude.com/docs/en/permissions
- Hook exit codes, `if` field, events: https://code.claude.com/docs/en/hooks
- Skills, the `verify` pre-commit behavior, frontmatter: https://code.claude.com/docs/en/skills
- Subagents: https://code.claude.com/docs/en/sub-agents
- Settings scopes and live reload: https://code.claude.com/docs/en/settings
- Scheduled tasks: https://code.claude.com/docs/en/scheduled-tasks
- Dynamic workflows: https://code.claude.com/docs/en/workflows
- Full index of pages: https://code.claude.com/docs/llms.txt
