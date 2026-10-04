---
paths:
  - "scripts/test_install.py"
  - "tests/**"
  - "docs/testing.md"
---

# Isolated install tests

- With a temporary `HOME` and `CLAUDE_CONFIG_DIR` the install is fully isolated; the fingerprints of the real configuration do not change.
- A marketplace added from a directory loads the plugin in place and ignores the version.
- Even so, `plugin list --json` reports a cache copy as `installPath`, so it does not tell you where the plugin loads from.
- The real user path is tested by cloning HEAD to a bare repo and using `git-subdir` entries with a `file://` URL.
- That test only covers HEAD, so commit before running it.
- Approaches that do not work and must not be retried: `marketplace add file://…git`, `extraKnownMarketplaces` from the CLI, and git over "dumb" HTTP.
- `scripts/test_install.py` runs three scenarios: in place, cache copy, and a session with `--plugin-dir`.
