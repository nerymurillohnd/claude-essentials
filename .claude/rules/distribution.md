---
paths:
  - "README.md"
  - "plugins/**/README.md"
  - "templates/readme/**"
  - "scripts/sync_readmes.py"
  - "SECURITY.md"
---

# Distribution and updates

- Background auto-update is off by default for third-party marketplaces, and `marketplace.json` has no field to turn it on.
- The user turns it on in `/plugin` → Marketplaces or with `"autoUpdate": true` in `extraKnownMarketplaces`.
- `extraKnownMarketplaces` in a repository's `.claude/settings.json` is honored only after the workspace trust dialog.
- Security fixes do not arrive on their own, so the README and advisories must ask users to update explicitly.
- An installed plugin is copied to `cache/<marketplace>/<plugin>/<version>/`, and the user only receives a new copy when the computed version changes: the explicit `version`, or the commit when `version` is omitted. Local-path marketplaces load in place.
- A published plugin is never renamed; if it is unavoidable, use `renames`.
- `/plugin install <plugin> --marketplace <repo>` installs in one step since 2.1.275.
- `claude plugin install <plugin> --marketplace <source>` does the same from the shell since 2.1.292 (changelog and `claude plugin install --help` on 2.1.292, 2026-10-07): it adds a missing marketplace under the checks of `marketplace add`, and the plugin name is bare. The plugin CLI reference does not list the flag yet, so READMEs keep the two-step shell install until it does.
- `marketplace add --sparse` clones only the given paths, with fixes for git < 2.39 in 2.1.284.
- Users add the marketplace with `/plugin marketplace add nerymurillohnd/claude-essentials` and install with `claude plugin install <plugin>@claude-essentials`.
- Users update with `claude plugin update <plugin>@claude-essentials` or `/plugin marketplace update claude-essentials`.
- Teams pre-configure the marketplace with `extraKnownMarketplaces` plus `enabledPlugins` keyed `<plugin>@claude-essentials`.
- README install instructions always include the auto-update step.
- Use `displayName` for labels, and add `renames: { "<name>": null }` when removing a plugin.
