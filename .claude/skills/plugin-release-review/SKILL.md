---
name: plugin-release-review
description: Release-readiness review for a plugin in the claude-essentials marketplace. Checks that its README, CHANGELOG, LICENSE, plugin.json, marketplace.json entry, root README catalog row, labels, and tags are complete, consistent with each other, faithful to what the plugin's files actually do, and written in the house style of the templates, then fixes the gaps and turns each new class of gap into a guard so it can't recur. Use it whenever a plugin is created or changed, before opening or merging a plugin PR, before calling a plugin "done" or "published", and whenever the user asks to review, audit, polish, or check a plugin, its README, its catalog entry, or its metadata, even if they only say "is this plugin ready?" or "revisa el plugin".
argument-hint: "[plugin-id]"
arguments: plugin_id
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"${CLAUDE_PROJECT_DIR}/.claude/hooks/checklist-gate.sh"'
          timeout: 600
---

# Plugin release review

A plugin's README is its storefront: the one page a developer reads before
deciding whether to trust the plugin with their shell, files, or credentials.
The metadata around it (manifest, catalog entry, root README row, CHANGELOG,
tags) is how the marketplace presents it. This review makes sure all of that is
**complete, consistent, true, and well written**, for every plugin, every time.

Two layers, and the review needs both:

1. **Mechanical floor.** `make validate` (part of `make check` and CI)
   enforces structure: schemas, kind, template sections and order,
   placeholders, alerts, code-block languages, badge catalog, install steps, and
   the root catalog row. If it fails, nothing else matters yet.
2. **Judgment.** Whether the README explains the plugin to a stranger, whether
   every claim is true of the shipped files, whether the voice and formatting
   match the templates, and whether the metadata tells one consistent story. No
   script can decide that; it takes reading the plugin and understanding it.

## Workflow

Work through the phases in order and keep notes as you go; the report at the
end is built from them.

### Checklist (enforced)

Start the checklist before phase 0, from the repository root:

```bash
.claude/hooks/lib/checklist.sh start .claude/skills/plugin-release-review/checklist.json "$plugin_id" "${CLAUDE_SESSION_ID}"
```

Mark each item as its phase ends, with the evidence that proves it (a command
summary, file:line references, counts):

```bash
.claude/hooks/lib/checklist.sh check <item-id> "<evidence>"
```

This skill registers a Stop hook (`checklist-gate.sh`). While the checklist is
in progress, it will not let the turn end: it lists what is still open, and
once every item is marked it re-runs each item's verify command (`make
validate`, `make versions`, tests) and reopens items whose verification fails.
That is the point: a review that skips a phase, or claims a green floor that
isn't green, cannot finish.

When an item needs a decision only the user can make (defer a fix, approve a
version bump), mark it `checklist.sh needs-user <item-id> "<question>"` and ask;
the turn can then end, and the item continues when they answer. Use
`checklist.sh abort "<their words>"` only when the user explicitly says to stop
the review. `checklist.sh status` shows where the review stands.

### 0. Coherence audit

Dispatch the `plugin-coherence-auditor` subagent on `$plugin_id` (one agent per
plugin) and read its report in full before anything else. It finds gaps,
inconsistencies, broken references, ambiguities, discrepancies, and weak
instructions that would make Claude Code itself reason or act differently —
that is its scope; a claim that would mislead a *human reader* of the README
or the catalog is this skill's own scope, covered in phases 4-5. Fold every
high/medium finding of its report into the fact sheet (phase 3), the
consistency check (phase 4), or the editorial review (phase 5), whichever it
matches; don't duplicate the finding, cite it once where it's fixed.

### 1. Scope

Plugin to review: `$plugin_id`. If that is empty, take the plugin the current
change touches (`git diff --name-only main...` under `plugins/`), and ask only
if it is still ambiguous. Identify what changed: a new plugin, a new
version, or docs only. Read the repository's `CLAUDE.md`, then
`templates/plugin-README-reusable-template.md` (the master; its header comment
holds the rules and conventions) and the plugin's shape template in
`templates/plugin-<shape>/`. Those two files are the standard you review
against, so read them fresh each time rather than from memory.

### 2. Mechanical floor

Run `make check` and `make versions` (CI runs the second as the
separate `version-check` job, so `check` alone can pass while CI fails). Fix
every failure before continuing. A failing floor means the structure is wrong,
and polishing prose on top of it wastes effort.

### 3. Ground truth

Build a **fact sheet** of what the plugin actually is, from its files, not from
its README. Read every runtime file: `plugin.json`, each `SKILL.md`, agent,
command, hook config, `.mcp.json`, and every bundled script. Record:

- components and the kind they imply;
- what it reads, writes, executes, and where (paths, scopes);
- network use and destinations; credentials and `userConfig`;
- external requirements with minimum versions, and where each is enforced;
- surfaces and anything that behaves differently on them (Cowork, Windows, cloud);
- the behaviors worth selling (what problem it solves, standout features);
- the true limits and failure modes.

This sheet is the reference for everything that follows. The most damaging
README errors are claims the code doesn't back up (a "no network" plugin that
calls `curl`, a requirement version the script doesn't check), and you can
only catch them by comparing against the files.

### 4. Consistency across artifacts

Read `references/consistency-matrix.md` and check every row. It lists which
facts (name, display name, description, version, kind, license, requirements,
surface status, dates) must agree across `plugin.json`, the
`marketplace.json` entry, the plugin README, the CHANGELOG, the LICENSE, the
root README catalog row, the issue-form dropdowns, labels, and tags.

Every row carries a `*(CI: ...)*` tag naming exactly what `make check` already
proved, seconds ago, in phase 2: cite that run as the evidence for that part
instead of re-deriving it by hand. The tag never covers the whole cell — read
the rest of the Notes, wherever it sits (before the tag, after a trailing
`;`, or both), as the claim no script makes and give that your own read. A
cell that is nothing but the tag needs no further read at all. Don't let a
word in the tag itself stand in for the claim: "structure" means row
presence and order, not that the prose is still accurate; a category
truly fitting, a minimum being really enforced, "Last verified" being
honest, and a released CHANGELOG entry never being rewritten are none of
them caught by any script, however the row is worded. Spend the manual
read there, not on what `make check` already proved.

### 5. Editorial review of the README

Read `references/readme-editorial-review.md` and review the README as a
first-time visitor would: can they tell in thirty seconds what this is, whom it
is for, what it solves, and what it will do to their machine? Then check
accuracy against the fact sheet, sell the real value without marketing
language, and hold the house style: section emojis, badge row, alert
semantics, tables, code-block languages, bold for the one fact a skimmer must
not miss.

Review the root README catalog row the same way: its one-line outcome is the
plugin's first impression in the catalog.

Compare the README with the other shipped plugins, not only the templates:
section order, emojis, badge row and order, tables, alert use, and voice must
match. A difference is a finding unless the template changed on purpose.

### 5b. Metadata fit

1. Read `plugin.json` against every field the live plugin manifest schema offers.
2. Each field the plugin's nature calls for is set (keywords for its problem space, `userConfig`, `dependencies`, `defaultEnabled`, component paths).
3. Read `plugin.json` `metadata.marketplace` (`category`, `tags`): `make generate` copies it into the `marketplace.json` entry, so fix it there, never in the entry.
4. A value a generator copied unchanged where the plugin needs more is a finding.

### 5c. Bundled reviews

1. Run `/code-review high` on the plugin's diff.
2. Run `/security-review` when the plugin ships scripts, hooks, MCP, or LSP.
3. Run `/claude-api prompt-audit` on its `SKILL.md` files, agents, and descriptions.
4. Skip a re-run and cite the earlier summaries instead when `plugin-design`
   Phase 10 already ran all three against this exact diff and the head SHA
   hasn't changed since (`git log -1 --format=%H`); any later commit means the
   diff changed and these run again.

### 6. Report

Present findings before changing anything substantial. Use this shape:

```markdown
## Plugin release review: <id> <version>

**Verdict:** ready | ready after fixes | not ready

| # | Severity | Area | Finding | Evidence | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | high | accuracy | README says "no network"; `scripts/sync.sh:14` calls curl | file:line | Declare the destination in Security and MCP, permissions, and network |

**Mechanical floor:** `make check` result.
**Consistency matrix:** rows checked, rows failing.
**Editorial:** strengths worth keeping, then the issues above.
**Prevention:** new guards added or proposed (see phase 7).
```

Severity: **high** = false or missing information a user relies on (security,
writes, network, requirements, install), or a metadata contradiction;
**medium** = unclear, incomplete, or off-template content; **low** = polish.

### 7. Fix and prevent

Fix the findings (docs-only fixes need no version bump; runtime changes do,
per `docs/contributing/versioning.md`). Then, for each finding, ask whether
it is a new *class* of gap. If it is, close the class, not just the instance:

- if a script can detect it reliably, add the check to
  `scripts/plugin_validation/readme_contract.py` (or the relevant validator) with a test;
- if it needs judgment, add it to the matching reference in this skill;
- update `docs/contributing/plugins.md` and the PR template if contributors
  would otherwise miss it;
- record it in `docs/maintenance/resolved-debt.md` (or `pending-debt.md` if not
  fixed now).

Rerun `make check` after fixing. Report what changed and which guards now
prevent each class of finding.

## Principles

- **Evidence over assertion.** Every finding cites a file and line or a command
  output; every "consistent" row was actually compared, not assumed.
- **The files win.** When the README and the code disagree, the README is wrong
  unless the code has a bug; say which, and fix the right one.
- **Honest status.** A surface is ✅ only after a dated install from the remote
  marketplace on that surface. Unverified is 🧪, and saying so is a feature.
- **Sell with facts.** The strongest pitch is a concrete scenario, an exact
  effect, and a stated limit. Adjectives ("powerful", "seamless") add nothing.
- **Independent re-derivation is intentional, not redundant.** `repo-auditor`
  (checks P2, P3) walks `consistency-matrix.md` and
  `readme-editorial-review.md` again on its own, rather than trusting this
  skill's checklist status. That is deliberate defense in depth against a
  checklist item marked `done` without real evidence — never "optimize away"
  either pass.
