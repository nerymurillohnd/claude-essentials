# Project identity and policies

- The marketplace is named `claude-essentials`, the owner is `nerymurillohnd` and the license is MIT.
- The notice of non-affiliation with Anthropic appears in the catalog, the root README and every plugin README.
- Only in-repo plugins are accepted, with `source` exactly `./plugins/<name>`.
- The plugin is the only unit of distribution.
- There are no standalone skills, agents, hooks or commands.
- Every component ships inside a plugin.
- There are 9 categories: workflows, agents, audits, code-review, documentation, development, best-practices, research and model-behavior.
- Clean-room policy: anything specific to Claude Code comes only from the official documentation and the changelog.
- Consult another marketplace or plugin collection only at my request.
- Consult only what I name, and only to observe, never to copy.
- The one exception is a plugin derived from a project's own official AI content that I name (ADR derived-third-party-content).
- The sourcing order is a generator, then an official template, then an open standard, and hand-writing last.
- The repository is public at `nerymurillohnd/claude-essentials` (`origin`).
- Every commit is signed.
- You need my explicit approval before any push, tag push or change to GitHub settings.
- The catalog holds `svelte-development`; `hello-example` was removed with a `renames` entry (its tag `hello-example--v0.1.1` stays).
