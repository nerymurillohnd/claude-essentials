---
paths:
  - ".claude-plugin/**"
  - "scripts/check_repo.py"
  - "scripts/new_plugin.py"
---

# Marketplace file

- It requires `name`, `owner.name` and `plugins[]`.
- `metadata.pluginRoot` exists since 2.1.239 and `renames` since 2.1.193; `renames` is append-only and accepts `null` to retire a plugin.
- Entries natively accept free-form `category` and `tags`, `displayName`, `defaultEnabled`, `strict` and `metadata`.
- There is no marketplace-level `displayName`: it fails as an `Unknown field` under `--strict` (runtime-verified).
- Unknown keys are ignored at load time, but `validate --strict` turns them into a failure.
- Reserved names include `inline`, `builtin`, `skills-dir`, `synced`, `claude-plugin-test`, `npm`, `pip`, `uv`, `cargo`, `github`, `gh` and the `claudeai-` prefix.
- Since 2.1.280 other spellings of reserved names are refused, and a marketplace with an imitating name stops loading.
- `claude-essentials` passes `validate --strict` and the `marketplace add` name check.
- The file lives at `.claude-plugin/marketplace.json`; relative sources resolve from the marketplace root, start with `./` and never contain `..`.
- Other optional fields: `description` (validate warns if missing), `version` or `metadata.version` (never set here: the catalog is not versioned), `forceRemoveDeletedPlugins`, `$schema` (ignored at load time) and `allowCrossMarketplaceDependenciesOn`.
- `strict` defaults to `true`, and Claude Code ignores the free-form entry `metadata`.
- `displayName` exists only on plugin entries and in `plugin.json`; users see the marketplace by its `name`.
- Impersonating names (for example `official-claude-plugins`, `claude-plugins-v2`) and any non-ASCII name are also refused.
