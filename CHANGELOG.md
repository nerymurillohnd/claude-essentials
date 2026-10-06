# Changelog

Changes to the Claude Essentials catalog: plugins added, deprecated, removed or renamed, and changes to how the catalog is distributed. Each plugin keeps its own versioned changelog in `plugins/<name>/CHANGELOG.md`.

The catalog has no version: users always receive the latest catalog, and only plugins are versioned ([Semantic Versioning](https://semver.org/spec/v2.0.0.html)). Entries are grouped by date (UTC), newest first, using the change types of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 2026-10-06

### Changed

- The root README is laid out as a page for someone deciding what to install: section icons, GitHub callouts for the install prerequisites, the update warning and the permissions caution, and a Contents line with icons. Its anchors follow the new headings, and the wording of the affiliation notice, install commands and Claude Tag guidance is unchanged.
- Plugin evals run only when a pull request changes a file under `plugins/`. A labelled pull request that changes no plugin skips the eval job, so it starts no runner and makes no model call.
- Plugin READMEs are written as a page for the user who is deciding to install, not as a second changelog: one paragraph in the whole file, and tables, labelled bullets, callouts and `<details>` blocks everywhere else. The rule and its fix order are in `docs/readme-guide.md`, and the scaffold's own TODO text asks for that shape, so every new plugin starts from it.
- Every plugin supports macOS, Linux (WSL included) and Windows with Git Bash; the READMEs list the platform first among the prerequisites, and the root Quick start lists what to install, in order, before a plugin.
- `svelte-development`: the catalog description now names SvelteKit 2 support, language-server navigation with renames proven by the project check, and a svelte-check of your changes before Claude stops.

## 2026-10-05

### Added

- `svelte-development`: Svelte 5 and SvelteKit 3 development with best-practice, docs-and-autofixer and code-navigation skills, an editor and an auditor agent, and the Svelte MCP and language servers, built on the Svelte team's AI tools.

### Removed

- `hello-example`: the example plugin, removed now that a real plugin covers the release pipeline. Installs migrate through the catalog's `renames` entry; its tag `hello-example--v0.1.1` and GitHub Release remain.

## 2026-10-03

### Added

- Marketplace catalog `claude-essentials` with its category taxonomy and the non-affiliation disclaimer.
- `hello-example`, an example plugin that proves the pipeline end to end and will be removed once real plugins cover it.
- Repository gates, the plugin scaffold, the version bump script, the isolated install test, CI workflows, labels and contribution templates.
