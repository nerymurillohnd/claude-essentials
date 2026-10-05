# Project identity and policies

- The marketplace is named `claude-essentials`, the owner is `nerymurillohnd` and the license is MIT.
- The notice of non-affiliation with Anthropic appears in the catalog, the root README and every plugin README.
- Only in-repo plugins are accepted, with `source` exactly `./plugins/<name>`.
- The plugin is the only unit of distribution: there are no standalone skills, agents, hooks or commands, and every component ships inside a plugin.
- There are 9 categories: workflows, agents, audits, code-review, documentation, development, best-practices, research and model-behavior.
- Clean-room policy: anything specific to Claude Code comes only from the official documentation and the changelog. Another marketplace or plugin collection is consulted only at my request, only what I name, and only to observe, never to copy.
- The sourcing order is a generator, then an official template, then an open standard, and hand-writing last.
- The repository is public at `nerymurillohnd/claude-essentials` (`origin`); every commit is signed, and you need my explicit approval before any push, tag push or change to GitHub settings.
- The first real plugin is `project-automation`; the example `hello-example` was retired in the same pull request with a `renames` entry mapping it to `null`.
