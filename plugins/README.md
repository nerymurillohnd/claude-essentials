# 🧩 plugins

[← claude-essentials](../README.md)

> One directory per distributable plugin: `plugins/<plugin-id>/`.

| Rule | Why |
| --- | --- |
| The directory name equals `name` in `.claude-plugin/plugin.json` | The generator and validator fail the build otherwise |
| Each plugin is **self-contained** — no `../` references | An installed plugin is copied on its own into the user's plugin cache |
| Each plugin ships `README.md`, `CHANGELOG.md`, and `LICENSE` | Users judge, update, and reuse a plugin from these alone |

Claude never reads this folder directly: `npm run generate` scans it to build
[`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json), and that
catalog is what users install from.

➡️ To add one, see [docs/contributing/plugins.md](../docs/contributing/plugins.md).
