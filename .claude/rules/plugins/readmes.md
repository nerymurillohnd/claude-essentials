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
- The FAQ holds 3 to 5 questions and opens with "Does installing this plugin modify my project?"; the `repo` gate checks both.
- Emoji headings put a leading hyphen in every anchor (`#-faq`); build links with `repo.readme_anchor`.
