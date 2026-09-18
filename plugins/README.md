# plugins

One directory per distributable plugin: `plugins/<plugin-name>/`.

This directory is scanned by `npm run generate` to build
`.claude-plugin/marketplace.json` — nothing here is installed or read directly
by Claude Code except through that generated catalog.

See [docs/contributing/plugins.md](../docs/contributing/plugins.md) to add one.
