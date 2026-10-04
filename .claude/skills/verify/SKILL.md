---
name: verify
description: Runs every repository gate for the claude-essentials marketplace with make check and reports the raw result. Use before every commit, and whenever asked to verify, validate or check the marketplace, a plugin or the tooling.
---

# Verify the repository

Run the same gates CI runs, from the repository root:

```bash
make check
```

When the change touches `plugins/`, `.claude-plugin/` or `scripts/test_install.py`, and the change is committed, also run:

```bash
make test-install
```

`make test-install` checks committed HEAD in its cache-copy scenario, so commit first or say that HEAD was tested.

## Rules

- Report the exact commands and the relevant raw output. Say which gate failed and why; never summarize a failure as success.
- Fix the root cause and re-run until every gate passes. Never weaken, skip or suppress a gate, and never edit a generated README block by hand: run `uv run scripts/sync_readmes.py` instead.
- If a tool is missing from PATH, name it and point to the setup table in CONTRIBUTING.md instead of installing anything.
