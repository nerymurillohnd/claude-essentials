---
paths:
  - "scripts/test_install.py"
  - "tests/**"
  - "docs/testing.md"
---

# Isolated Install Tests

- With a temporary `HOME` and `CLAUDE_CONFIG_DIR` the install is fully isolated.
- The fingerprints of the real configuration do not change.
- A marketplace added from a directory loads the plugin in place and ignores the version.
- Even so, `plugin list --json` reports a cache copy as `installPath`, which is not the load location.
- Since 2.1.289, `readFromFolder` holds the real source directory and `folderVersion` its version (observed 2026-10-04).
- The real user path is tested by cloning HEAD to a bare repo and using `git-subdir` entries with a `file://` URL.
- That test only covers HEAD, so commit before running it.
- Approaches that do not work and must not be retried:
  - `marketplace add file://…git`
  - `extraKnownMarketplaces` from the CLI
  - git over "dumb" HTTP
- `scripts/test_install.py` runs three scenarios: in place, cache copy, and a session with `--plugin-dir`.
- The isolated sequence is `HOME=<tmp> CLAUDE_CONFIG_DIR=<tmp>/.claude claude plugin marketplace add <repo-path>`, then `claude plugin install <plugin>@claude-essentials`.
- The fingerprinted real files are `settings.json`, `plugins/known_marketplaces.json` and `plugins/installed_plugins.json`.
- The fingerprinted real listings are `plugins/cache`, `plugins/marketplaces` and `skills`.
- The text output of `claude plugin list` shows `Read from: <source dir>`, which is the real load location.
- The cache-copy entry shape is `{"source": "git-subdir", "url": "file://<bare>.git", "path": "plugins/<name>"}`.
- The plugin lands in `<config>/plugins/cache/claude-essentials/<name>/<version>/`.
- The failures you will see if you retry:
  - "Invalid marketplace source format"
  - the marketplace reported as not found
  - "dumb http transport does not support shallow capabilities"
