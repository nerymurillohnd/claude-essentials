---
paths:
  - "README.md"
  - "plugins/**/README.md"
  - "templates/readme/**"
  - "scripts/sync_readmes.py"
  - "SECURITY.md"
  - "docs/publishing-checklist.md"
---

# Distribution and updates

- Background auto-update is off by default for third-party marketplaces, and `marketplace.json` has no field to turn it on.
- The user turns it on in `/plugin` → Marketplaces or with `"autoUpdate": true` in `extraKnownMarketplaces`.
- `extraKnownMarketplaces` in a repository's `.claude/settings.json` is honored only after the workspace trust dialog.
- Security fixes do not arrive on their own, so the README and advisories must ask users to update explicitly.
- An installed plugin is copied to `cache/<marketplace>/<plugin>/<version>/`, and the user only receives a new copy when the version changes.
- A published plugin is never renamed; if it is unavoidable, use `renames`.
- `/plugin install <plugin> --marketplace <repo>` installs in one step since 2.1.275.
- `marketplace add --sparse` clones only the given paths, with fixes for git < 2.39 in 2.1.284.
