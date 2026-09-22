---
name: coherence-auditor
description: Audit one or more plugins of this marketplace for gaps, inconsistencies, broken references, ambiguities, discrepancies and gray areas that would make Claude Code reason or act differently than intended, each reported with its file, line and quoted text. Runs the read-only plugin-coherence-auditor subagent in its own context.
argument-hint: <plugin-id> [plugin-id ...]
disable-model-invocation: true
context: fork
agent: plugin-coherence-auditor
---

# Coherence audit

Plugins to audit: $ARGUMENTS

If that list is empty, audit every plugin under `plugins/` whose files differ from
`origin/main` (`git diff --name-only origin/main...HEAD -- plugins/`, plus uncommitted and
untracked files). If nothing differs, list the plugin ids under `plugins/` and stop.

For each plugin, in the order given:

1. Follow your instructions from start to finish: read every file the plugin ships and every
   repository document about it, end to end.
2. Return one report per plugin in the report shape your instructions define, with the
   plugin's version and the head SHA in its heading.

Audit and report only. Change no file, commit nothing, and push nothing.
