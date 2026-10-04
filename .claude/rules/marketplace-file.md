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
