# Marketplace and catalog

`scripts/marketplace/`. The catalog Claude Code reads, and the checks that keep
it identical to what is on disk. The distribution model is `ADR-0001`.

## Ground rules

- The `plugins` array in `.claude-plugin/marketplace.json` is generated. Hand-editing it is the defect this area exists to prevent, and a `PreToolUse` hook denies the edit.
- A plugin's manifest `name` must equal its directory name under `plugins/`. Both the generator and the validator enforce it.
- Catalog-only fields live in `plugin.json` under `metadata.marketplace`. Claude Code never reads `metadata`, which is why the catalog can carry `category` and `tags` without polluting the runtime manifest.
- The repository's own schemas encode this repository's policy. The official CLI remains the source of truth for the manifest shape; see the plugin validation reference.

## `catalog.py`

- `catalog_entry(name, source, manifest)` builds one catalog entry from a plugin manifest.
- `catalog_entry_drift(entries, manifests)` compares the committed catalog against what the manifests would generate, field by field, and names each difference.
- `compile_schemas(root)` loads and compiles the repository schemas once, so the generator and the validator judge by the same rules.

## `generate_marketplace.py` — entrypoint

- Regenerates the `plugins` array from every `plugins/<name>/.claude-plugin/plugin.json` on disk.
- Copies `category` and `tags` from `metadata.marketplace` into each entry.
- Leaves every other top-level field of `marketplace.json` untouched; only the generated array is rewritten.
- CI fails when running it produces a diff that was not committed, which is what makes "generated" enforceable rather than aspirational.

## `validate_marketplace.py` — entrypoint

- Validates `marketplace.json` and every `plugins/*/.claude-plugin/plugin.json` against the repository schemas.
- Cross-checks disk against catalog in both directions: a plugin on disk missing from the catalog, and a catalog entry with no directory.
- Verifies that each manifest `name` matches its directory.
- Runs the repository-metadata checks: issue forms, labels, the Node version source, and the pinned CLI version.
- Runs the README contract: plugin README sections and the root README catalog row.
- This is `npm run validate`'s successor and the cheapest full check available. Run it alone after editing a single manifest.

## Tests

- `test_catalog.py` — entry construction from a manifest, drift detection per field, and schema compilation.
