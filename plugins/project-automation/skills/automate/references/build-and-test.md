# Build and test recipes

Where each kind of automation goes, the checks that prove it is well formed, and the positive and negative tests that prove it works. Read the section for each item in phase 4. The shapes here are orientation only: confirm every field on the live page linked in each section before writing it, because fields are added and changed between releases.

**Contents:** [Checks for every item](#checks-for-every-item) · [CLAUDE.md and rules](#claudemd-and-rules) · [Skills](#skills) · [Subagents](#subagents) · [Hooks](#hooks) · [Permission rules and settings](#permission-rules-and-settings) · [Output styles](#output-styles) · [Scheduled and recurring work](#scheduled-and-recurring-work) · [Dynamic workflows](#dynamic-workflows) · [GitHub Actions](#github-actions) · [Headless behaviour tests](#headless-behaviour-tests)

## Checks for every item

- JSON files parse: `python3 -m json.tool <file>` or `jq . <file>`, whichever the machine has.
- Skills, subagents and commands under `.claude/` pass `claude plugin validate .claude` (validating component files without a manifest needs Claude Code 2.1.233 or later). Treat warnings as failures.
- Scripts pass the project's own linters and formatters when it has them; otherwise `bash -n` for shell syntax and `shellcheck` when installed.
- No absolute paths into one person's home directory, no secrets, no machine names in shared files. Hook commands reference scripts through the project-directory placeholder.
- Run the negative test as carefully as the positive one: a guard that never blocks passes every positive test.

## CLAUDE.md and rules

- Project instructions: `CLAUDE.md` at the root (or `.claude/CLAUDE.md`). Personal ones: `CLAUDE.local.md`, kept out of git.
- File-specific guidance: `.claude/rules/<topic>.md` with a `paths:` list of globs in the frontmatter; without `paths:` the rule loads every session.
- Write facts and commands Claude cannot infer, one line each. Do not paste procedures: they become skills.
- **Positive test:** read a file that matches the rule's glob and confirm the rule's text arrives in context; for CLAUDE.md, start a new session and ask a question only the new line answers.
- **Negative test:** read a file outside the globs and confirm the rule does not load.
- Docs: https://code.claude.com/docs/en/memory

## Skills

- Path: `.claude/skills/<name>/SKILL.md`; the directory name is the command name. Supporting files sit next to it and are linked from SKILL.md.
- Frontmatter: `description` says what the skill does and when to use it, in the words a request would contain. Set `disable-model-invocation: true` when the skill has side effects (deploys, releases, migrations, pushes), so only the user starts it. `argument-hint` when it takes arguments.
- The body is rendered before Claude reads it: `$ARGUMENTS`, positional placeholders and the `CLAUDE_*` variables in braces are substituted, and an exclamation mark followed by a backticked command runs a shell command at load time. Keep literal examples of those in a supporting file.
- A skill that must stop for confirmation before an irreversible step says so explicitly; assume the user runs in auto mode.
- Skill edits load live in the current session.
- **Positive test:** run the skill on a safe target (a dry run, a temporary branch, a scratch directory) and compare the result with its acceptance criterion.
- **Negative test:** for a model-invoked skill, an unrelated request does not load it (see [Headless behaviour tests](#headless-behaviour-tests)); for a user-only skill, confirm it does not appear in Claude's skill list.
- Docs: https://code.claude.com/docs/en/skills

## Subagents

- Path: `.claude/agents/<name>.md`. Frontmatter needs `name` and `description`; restrict `tools` to what the job needs (a reviewer gets `Read, Grep, Glob` and maybe `Bash`, never `Edit` or `Write`).
- The body is the agent's whole system prompt: it does not receive the main conversation. State the input it gets, the steps, and the exact output shape.
- Claude Code watches `agents` directories that existed when the session started. A brand-new `.claude/agents/` directory needs a restart before the agent can be used.
- **Positive test:** spawn it with a small real task and check the output shape.
- **Negative test:** ask it for something outside its tools (an edit, for a read-only agent) and confirm it cannot.
- Docs: https://code.claude.com/docs/en/sub-agents

## Hooks

- Configuration: the `hooks` key of `.claude/settings.json` (shared) or `.claude/settings.local.json` (personal). Scripts: `.claude/hooks/<name>.<ext>`, executable.
- Reference scripts through the project-directory placeholder. Prefer exec form (`command` plus `args`), which passes each argument with no shell quoting; in shell form, wrap the placeholder in double quotes.
- Narrow with `matcher` (tool names, case-sensitive) and the `if` field (one permission rule such as `Bash(git commit *)` or `Edit(*.ts)`), so the script runs only when it matters. `if` works only on tool events.
- Decisions on `PreToolUse`: exit 2 blocks and shows stderr to Claude; JSON with a deny decision blocks; exit 0 allows; any other exit code is a non-blocking error and the call proceeds. A hook decision never overrides a deny or ask permission rule.
- Stderr from a hook that exits 0 goes only to the debug log; Claude never sees it. A `PostToolUse` linter hook that must show findings to Claude exits 2 (the tool has already run, so nothing is undone).
- Hooks that guard the user's work fail open on their own errors and finish within a second or two; a hook whose purpose is to block fails closed only on the condition it guards. Never start background processes from a hook.
- Settings edits, hooks included, reload live; `SessionStart` behaviour can only be observed in a new session.
- **Positive test:** pipe a realistic event to the script and check the exit code and output:
  ```bash
  echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m wip"}}' | ./.claude/hooks/check.sh; echo "exit=$?"
  ```
  Then trigger it for real with a harmless tool call in the session and confirm it fired.
- **Negative test:** pipe an event it must ignore (another tool, another command, an allowed path) and confirm exit 0 with no output; for a guard, also confirm the blocked case exits 2 and not 1.
- Docs: https://code.claude.com/docs/en/hooks-guide and https://code.claude.com/docs/en/hooks

## Permission rules and settings

- `permissions.allow`, `permissions.ask` and `permissions.deny` in `.claude/settings.json` or `.claude/settings.local.json`. Rules look like `Bash(npm test *)`, `Read(./.env)`, `Edit(./migrations/**)`, `WebFetch(domain:example.com)`.
- Order: deny, then ask, then allow; first match wins. An allow rule cannot make an exception to a deny rule. To exempt a path from a deny pattern, list a gitignore-style negation after it in the same `deny` list of the same file, such as `Read(*.env)` followed by `Read(!sample.env)`; a negation listed first, or in another settings file, carves nothing out, and it cannot reopen a file inside a directory denied as a whole. Otherwise deny exact paths.
- A `Read` deny rule also blocks Edit and Write on the same path, including creating the file; add an `Edit` deny for paths no tool may change, since NotebookEdit is not covered.
- Never propose broad allow rules (`Bash(*)`, `Bash(rm *)`, `Bash(git push *)`); allow the exact read-only or test commands the evidence shows.
- Claude Code keeps `.claude/settings.local.json` out of git when it creates the file; if you create it another way, add it to `.gitignore`.
- **Positive test:** attempt the allowed action and confirm it runs without a prompt; attempt the denied action and confirm Claude Code refuses it.
- **Negative test:** attempt a near miss (the sibling file, a similar command) and confirm it gets the intended treatment, not the rule's.
- Docs: https://code.claude.com/docs/en/permissions and https://code.claude.com/docs/en/settings

## Output styles

- Path: `.claude/output-styles/<name>.md`; the user selects it. It replaces part of the default system prompt, so propose one only for a clear, repeated format or role need.
- **Test:** select it in a session, ask a representative question, compare the answer's shape with the criterion; then switch back to the default.
- Docs: https://code.claude.com/docs/en/output-styles

## Scheduled and recurring work

- In a session: `/loop` and the cron tools; tasks end with the session. In the desktop app: scheduled tasks. For work that must run unattended and reliably, a CI job is usually the right home.
- A skill with `disable-model-invocation: true` does not run when a scheduled task fires with that skill as its prompt.
- **Test:** run the prompt once by hand and confirm its output; then confirm the schedule is listed.
- Docs: https://code.claude.com/docs/en/scheduled-tasks and https://code.claude.com/docs/en/desktop-scheduled-tasks

## Dynamic workflows

- Saved scripts in `.claude/workflows/`, started by name. They run many subagents and cost far more than a skill: propose one only for large, cross-checked jobs, and say the cost.
- Docs: https://code.claude.com/docs/en/workflows

## GitHub Actions

- Outward-facing: it needs a repository secret, runs on every matching event and spends the account's usage. Propose it only with a signal (pull requests that wait for review, repeated `@`-mentions) and leave installation (`/install-github-app` or the documented manual steps) to the user's explicit go-ahead.
- Docs: https://code.claude.com/docs/en/github-actions

## Headless behaviour tests

To check that a model-invoked skill triggers on the right requests and not on others, run a short non-interactive session from the repository root and look for a `Skill` tool call in the stream:

```bash
claude -p --output-format stream-json --verbose --max-budget-usd 0.50 \
  --permission-mode plan "<a request the skill should handle>" </dev/null | grep -c '"name":"Skill"'
```

Each run is a real model call billed to the user, so ask before running them, keep the budget cap, and use `--permission-mode plan` so the run cannot change files. Run the negative request the same way and expect zero.
