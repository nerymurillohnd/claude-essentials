---
paths:
  - "README.md"
  - "plugins/**/README.md"
  - "templates/readme/**"
  - "scripts/sync_readmes.py"
  - "docs/readme-guide.md"
---

# Generated READMEs

- The root README is rendered from `templates/readme/root.md`.
- Plugin READMEs have `<!-- BEGIN GENERATED: x -->` blocks: header, requirements, installation, components, configuration, runtime, uninstall, documentation and license.
- Badges come from shields.io, built from manifest data, plus the native CI badge.
- Links leading out of a plugin are absolute GitHub URLs, because the plugin is copied alone into the cache.
- A plugin's sections and their emoji come from `repo.README_SECTIONS`: Overview, What it does, Prerequisites, Installation, Usage, Components, FAQ, Update and uninstall, Documentation and License, plus Configuration and Permissions when they apply (ADR plugin-readme-sections).
- Plugins support macOS, Linux (WSL included) and Windows with Git Bash (ADR supported-platforms): the generated `requirements` block lists the operating system before Claude Code, and the root Quick start lists platform, Claude Code and each plugin's own prerequisites in install order. A plugin's own tools follow in install order, every binary it starts with its install command, global or project-local, before Installation.
- A README is for a user deciding to install, not a second changelog: one paragraph in the whole file (the Overview description), and everything else as tables, labelled bullets, fenced blocks or `>` callouts, one fact per line. The rules and the fix order (template first, then the guide, then the plugin) are in `docs/readme-guide.md#readable-not-a-changelog`; author guidance lives in `templates/readme/plugin.md` and `PERMISSIONS_SECTION` in `scripts/new_plugin.py`.
- The FAQ holds 3 to 5 questions and opens with "Does installing this plugin modify my project?"; the `repo` gate checks both.
- Emoji headings put a leading hyphen in every anchor (`#-faq`); build links with `repo.readme_anchor`.
