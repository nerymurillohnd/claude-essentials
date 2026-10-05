---
name: automate
description: Audits the current repository and builds Claude Code automation for it (skills, subagents, hooks, permission rules, CLAUDE.md and rules, settings, scheduled tasks), choosing each piece from evidence in the repository, checking every configuration detail against the live Claude Code documentation for the installed version, and proving each piece works before handing it over. Use when the user asks to set up, audit, improve or automate Claude Code for a project; to add hooks, skills, subagents or permission rules to a repository; to fix Claude Code configuration that does not work; or to find recurring manual work Claude Code could take over.
argument-hint: "[focus, e.g. releases, hooks, docs; empty for the full scope]"
---

# Automate a project with Claude Code

Turn this repository's recurring work into Claude Code automation that is chosen from evidence, correct for the installed Claude Code version, and proven to work.

Focus requested by the user: $ARGUMENTS
(Empty means the full scope. With a focus, cover it first and still report anything else of high value.)

## Ground rules

These hold in every phase, including in auto mode, because the output changes how Claude behaves in this repository for everyone who works in it.

- **Nothing is written before the plan is approved.** Until the user approves the proposal in phase 3, only read files and run read-only commands. Approval covers the approved items only; anything new goes back to the user.
- **Never** commit, push, install packages, edit user-level files (the user's home `.claude/` directory) or managed settings, or remove existing automation unless the user asks for that exact action. Disabling or replacing a piece the user already has is a proposal item like any other.
- **Evidence or nothing.** Every proposed item cites a concrete signal from the repository, its history or the user. An item with no signal is dropped, however standard it is.
- **Native first.** Prefer a built-in Claude Code feature or a setting over a custom script, and a custom script over a new dependency. The ladder is in [feature-selection.md](references/feature-selection.md).
- **Verified syntax only.** Every field, event, rule pattern and path written to disk is checked against the live documentation page that defines it, for the installed version. Training knowledge of Claude Code is out of date by definition: features appear and change weekly.
- **Proven, not assumed.** An item is done when its positive test passes and its negative test fails for the intended reason, with the raw output shown.

## Workflow

Copy this checklist and tick it as you go:

```
- [ ] 1 Scope      version, repository state, focus, session-history consent
- [ ] 2 Discover   scout + researcher in parallel
- [ ] 3 Propose    evidence table, recommendation, decisions -> STOP for approval
- [ ] 4 Build      per item: criteria, verified syntax, write, test loop
- [ ] 5 Verify     independent verifier; fix and re-verify until clean
- [ ] 6 Hand over  guide, final report
```

### 1 Scope

Run `claude --version`, `git status --short --branch` and `git rev-parse --show-toplevel`. Work from the repository root. If the working tree has uncommitted changes, say so: the user may want the automation on its own branch. If the directory is not a git repository, continue without history signals and say so.

Ask the user one question before discovery, unless the session is non-interactive (then the answer is no): may the scout read the prompts from this project's past Claude Code sessions? Prompts typed again and again are the strongest signal for a skill, but transcripts are plaintext and can contain anything that passed through a tool. Only prompt text is used, and nothing from it is quoted beyond a short paraphrase.

### 2 Discover

Launch both agents in one message so they run in parallel:

- `project-automation:automation-scout`: pass the repository root, the focus, and whether session history is allowed. It returns the inventory, the recurring-work signals and the defects in existing automation, each with evidence.
- `project-automation:feature-researcher`: pass the installed version, the focus, the kinds of automation the repository is likely to need, and the Gotchas below with their source links, to confirm or correct for this version. It returns the Claude Code features relevant to this repository, the changelog entries since the installed version, and any conflict between the docs and existing project files, each with a source URL and quote.

The researcher runs on every repository, however small: it is the only source of Claude Code facts in this workflow, and a proposal that has not been checked against the docs is what the user would get without this skill. The scout may be replaced by your own reading only when the repository has fewer than about 50 tracked files; say so in the proposal.

Read both reports in full. A gotcha below that the researcher did not find stays in force unless the researcher read the linked section and quotes text that contradicts it; absence from a search is not evidence.

After reading, spot-check at least two of the scout's evidence lines yourself (open the file or rerun the command): a proposal built on a wrong inventory is worse than none.

If an agent is unavailable or fails, do its work yourself with the same output contract (see [templates.md](references/templates.md)), and say so. If no web access is available at all, say at the top of the proposal that its Claude Code facts are unverified.

### 3 Propose

1. Read [feature-selection.md](references/feature-selection.md) now, before choosing anything: it holds the native-first ladder, the signal-to-feature map and the rules for rejecting an item.
2. Map each signal to one feature. Fixes for broken or conflicting existing automation are their own rows and usually rank first. Keep only rows with a concrete signal; a short list of strong items beats a long list.
3. Confirm the Claude Code facts each row depends on (a minimum version, a rule's semantics, an event's behaviour) from the researcher's report, or send the researcher back with the exact questions. A question the docs answer is never left open in the proposal.
4. Present the proposal in exactly this shape, every column filled:

```markdown
## Findings

<three to six lines: what the repository is, what already exists, the strongest signals>

## Proposed automation

| #   | Signal and evidence | Automation | Feature and location | Confirmed by | Effort | Impact | Context cost | Risk |
| --- | ------------------- | ---------- | -------------------- | ------------ | ------ | ------ | ------------ | ---- |

## Recommendation

<which rows, in which order, and why; the one to build first if the user wants only one>

## Considered and rejected

- <item>: <reason>

## Decisions for you

1. <decision>: <options, recommended first, with the reason>

Nothing has been changed. Reply with the rows to build, or "all".
```

"Signal and evidence" cites a `path:line`, a command with its count, or the user's words. "Confirmed by" names the docs page and the fact it states, or says "unconfirmed". Effort is S, M or L; Impact and Risk name the concrete effect. A filled example is in [templates.md](references/templates.md).

Ask only the decisions that are the user's: scope (shared in the repository or local to them), anything with a trade-off (a commit-blocking hook costs seconds per commit), and where the guide goes (default: `claude-code-automation.md` in the project's existing documentation folder, or at the repository root when there is none).

**Stop here and wait for approval.** Do not continue in the same turn. A non-interactive session ends at this phase with the proposal as its result.

### 4 Build

For each approved item, in the order of the table:

1. Write its acceptance criteria first: one positive test (it does the job) and one negative test (it rejects or ignores what it must not touch), using the record format in [templates.md](references/templates.md).
2. Open the live documentation page for the feature and confirm every field and value you are about to write. Quote the line you relied on in your notes. If the page and your plan disagree, the page wins; tell the user if that changes an approved item.
3. Read the item's section of [build-and-test.md](references/build-and-test.md), then write the files with the paths, shapes and checks it gives.
4. Run the checks and both tests. Fix and rerun until both pass for the intended reason. Exit after three failed attempts on the same item: stop, report what fails, and ask whether to drop or change it.
5. Run the repository's own formatters and linters on the files you created, if it has them, so the automation itself passes the project's gates.

### 5 Verify

Give `project-automation:automation-verifier` the list of built items with their acceptance criteria and file paths. It re-runs every test independently and tries to break each item. Fix every confirmed failure at its cause, rerun the affected tests, and send the fixed items back to the verifier until it reports no confirmed failures.

Some behaviour only shows in a new session (a SessionStart hook, a new `agents` directory, settings read once at start). Name those items in the hand-over as "verify after restart" with the exact step, rather than claiming them.

### 6 Hand over

Write the guide where the user chose, using the skeleton in [templates.md](references/templates.md): what now happens on its own, what the user starts and how, how to tell it is working, how to turn each piece off, and what was left out. Then give the final report from the same file. Report failures and skipped checks as plainly as successes.

## Gotchas

Each of these contradicts a reasonable assumption and has produced wrong configurations. They were checked against the linked docs on Claude Code 2.1.289; the researcher re-confirms them for the installed version.

- **An allow rule cannot carve an exception out of a deny rule.** Permission rules are evaluated deny, then ask, then allow; the first match wins regardless of specificity. To exempt a path, put a `!` negation after the broader rule in the same deny list of the same settings file (`Read(*.env)` then `Read(!sample.env)`), or deny exact paths. A `Read` deny also blocks Edit and Write on that path. (https://code.claude.com/docs/en/permissions#manage-permissions, https://code.claude.com/docs/en/permissions#read-and-edit)
- **Read and Edit deny rules do not stop a script from opening the file.** They cover Claude's file tools, recognized Bash file commands and redirects, not `node script.js` reading the file itself. OS-level protection needs the sandbox. (https://code.claude.com/docs/en/permissions#read-and-edit)
- **A guard hook that exits 1 lets the call through.** Only exit code 2 (or a JSON deny decision) blocks a `PreToolUse` call; any other non-zero exit is a non-blocking error. Test the block path, not just the allow path. (https://code.claude.com/docs/en/hooks#exit-code-output)
- **Use the hook `if` field instead of filtering inside the script.** It takes one permission rule, such as `Bash(git commit *)`, and keeps the script from spawning on every unrelated call. It works only on tool events. (https://code.claude.com/docs/en/hooks#common-fields)
- **A project skill named `verify` runs before every commit.** Since Claude Code 2.1.286, when a project (or personal) skill named `verify` or `simplify` exists at session start, Claude is told to run it right before each commit, except docs-only and tests-only commits. It must stay invocable by Claude (no `disable-model-invocation`), and the bundled `/verify` and plugin skills do not count. That is often a better fit than a commit-blocking hook: it costs no time on commits Claude does not make and runs the checks the skill lists (https://code.claude.com/docs/en/skills#run-your-checks-before-each-commit).
- **CLAUDE.md and skills are requests, hooks and permission rules are enforcement.** Anything that must hold every time goes in a hook or a rule. Keep CLAUDE.md under about 200 lines; move procedures to skills and file-specific guidance to path-scoped rules.
- **Some changes need a new session.** Edits to settings, hooks and existing skills reload live, but a brand-new `agents` directory, and keys read only at startup, need a restart. Check the page for the feature you changed. (https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/sub-agents#write-subagent-files)
- **Skills with side effects get `disable-model-invocation: true`**, which also means they cannot be preloaded into a subagent.
