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
- A plugin's required sections are Overview, Requirements, Installation, Usage, Components, Uninstall, Documentation and License, plus Permissions if it runs code.
