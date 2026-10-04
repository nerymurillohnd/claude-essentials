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
- `init --with hooks` generates a hook that requires `bun`.
- `claude plugin eval` exists since 2.1.269 and may show as early access.
- `claude plugin test` runs the `.test.ts` tests of mods.
- `claude --plugin-dir <dir> plugin list --json` checks that a plugin loads without an API key and reports `errors` and `notes`.
- `--plugin-dir` pointed at a marketplace root does not load its plugins.
