# README editorial review

The README is written for one person: a developer who found the marketplace,
has never seen this plugin, and must decide whether to let it act on their
machine. Review it as that person, then as a maintainer checking the facts.

## 1. The thirty-second read

Read only the title, badges, blockquote, `**Kind:**` line, intro paragraph,
and the CAUTION alert. A stranger should be able to answer:

- What is this, and what problem does it solve for me?
- Is it for my situation (tools, surface, team or solo)?
- What will it do to my machine or repository, and what will it never do?
- What do I need installed?

If any answer needs scrolling, the top is doing too little. The blockquote is
an outcome in the user's words ("Stop Claude from skipping your Git hooks…"),
not a component list ("A skill that installs a hook…").

## 2. Does it sell the real value?

The template has no "Features" heading on purpose: features live in
**What it does** (scenario → how it helps → observable result) and
**Examples**. Check that:

- the scenarios are real situations users recognize, not restatements of the
  mechanism;
- the standout capabilities from the fact sheet appear somewhere a skimmer
  will see them (What it does, the Skills table, Examples);
- Examples show a realistic prompt and what the user then sees, including at
  least one case that shows the plugin's distinctive value;
- claims are concrete (numbers, exact effects) and every number is current.

"Selling" here means making the true value obvious. Superlatives, vague
benefits ("streamlines your workflow"), and claims the fact sheet can't back
are defects, not marketing.

## 3. Accuracy against the fact sheet

Go section by section and compare each claim to the files:

| Section | Verify |
| --- | --- |
| What it does not do | Every non-goal is true; the most common wrong assumption is addressed |
| Installation / What installing changes | Exactly what plugin installation touches; nothing more happens until a component runs |
| Skills / Agents / Hooks / MCP | Every component listed with correct invoke names, triggers, and invocation mode; "None" means none |
| Requirements | Every tool the scripts call, with the minimum version they actually need; check commands work |
| Verification | The smoke test and maintainer commands run as written; eval numbers match the last recorded run |
| Compatibility | Status per surface is honest; notes explain what differs |
| Security | Reads, writes, processes, network, credentials match the fact sheet line by line |
| Limitations | Real failure modes with symptoms and a safe recovery; nothing the fact sheet shows is missing |

### Claims worth testing, not just reading

- Fail-closed and degraded-mode claims ("if jq is missing, only git commands
  are denied"): test them with the dependency removed and a **realistic full
  payload** (working directory, transcript path), not only the field you
  expect to matter.
- "Nothing happens until…" claims: check what the auto-invoked path actually
  runs before any approval.
- The catalog cell and descriptions never claim what the non-goals,
  Limitations, or bypass catalogue say the plugin does not do.

## 4. House style (from the master template's conventions)

- **Title**: `# <emoji> <Display Name>`; section headings keep the template's emojis and exact titles.
- **Badge row**: version (dynamic, never hardcoded), license, kind, Claude Code, Claude Cowork, then one badge per external requirement from the template's catalog.
- **Nav line** under the badges and the footer `<sub>` line as in the template.
- **Alerts**: NOTE = context, TIP = shortcut, IMPORTANT = must know before installing, WARNING = risky default, CAUTION = irreversible or data-affecting. At most one per section, and the type must match the content.
- **Tables** for anything with more than two attributes; lists for simple enumerations.
- **Code**: `text` blocks for prompts and slash commands typed inside Claude, `bash` for shell commands; inline code for names, paths, commands.
- **Emphasis**: bold for the one fact a skimmer must not miss per section; italics rarely.
- **Voice**: second person to the reader, present tense, active voice, short sentences, no filler, no marketing adjectives. Match the tone of the existing root README.
- **Links**: relative for repo files, descriptive link text (never "here").

## 5. Root catalog row

The row is the plugin's first impression. Its description is the README
blockquote outcome (or a faithful shortening), its requirements cell lists the
same tools as the Requirements table, and its statuses match the badges.

## 6. Writing fixes

When rewriting, keep what already works, change only what fails the checks
above, and keep every section's template shape. Re-read the changed README
top to bottom once more as the stranger from step 1.
