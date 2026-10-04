---
paths:
  - "scripts/**"
  - "tests/**"
  - ".github/workflows/**"
  - "docs/testing.md"
  - "docs/releasing.md"
---

# Official CLI

- `claude plugin validate` exits with 0, 1 or 2, and its `--json` mode prints the `hooks:` and `calls:` lines of mods.
- From the marketplace root it does not check the inside of the plugins, so validate each plugin separately.
- `validate` checks MCP since 2.1.281 and the paths of `outputStyles`, `themes`, `monitors` and `lspServers` since 2.1.283.
- `claude plugin init` only writes to `<config>/skills/<name>`, honors `CLAUDE_CONFIG_DIR` and generates a root `SKILL.md` plus `"skills": ["./"]`.
- `claude plugin eval` exists since 2.1.269 and may show as early access.
- `claude plugin test` runs the `.test.ts` tests of mods.
- `claude --plugin-dir <dir> plugin list --json` checks that a plugin loads without an API key and reports `errors` and `notes`.
- `--plugin-dir` pointed at a marketplace root does not load its plugins.
- `claude plugin tag [path] [--dry-run] [--push] [-m]` checks that `plugin.json` and the catalog entry agree, then runs `git tag -a <tag> -m "<name> <version>"`; it pushes as `refs/tags/<tag>`.
- `claude plugin init <name> --with skills agents hooks mcp lsp output-style channel` has no destination flag.
- Run `init` with a temporary `HOME` and `CLAUDE_CONFIG_DIR`, then move the output into `plugins/<name>/` and adapt the skills-directory layout (`scripts/new_plugin.py` does this).
- The `init --with hooks` scaffold runs `bun "${CLAUDE_PLUGIN_ROOT}/hooks-handlers/on-session-start.ts"`; never ship it unchanged, because hooks may only use interpreters the plugin declares as requirements.
- A folder of plugins passed to `--plugin-dir` loads each child with a manifest (2.1.265+), even when the folder also holds `marketplace.json` (2.1.281+).
