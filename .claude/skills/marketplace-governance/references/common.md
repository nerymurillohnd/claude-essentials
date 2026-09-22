# Shared infrastructure

`scripts/common/`. The two modules every other area imports. Nothing here knows
about GitHub, versions, or the catalog; anything that does belongs in its own
area.

## Ground rules

- One definition of what a plugin is, shared by every script, so no two gates disagree about which directories count.
- A plugin's kind is derived from what it ships, never declared in `plugin.json`. Declaring it would fail `claude plugin validate --strict`, which is why `ADR-0001` was amended.
- External data is untyped until proven otherwise. Parse it, narrow it, then use it.

## `plugins.py`

- Exposes `root_dir` and `plugins_dir` so no caller computes a path from its own location.
- `list_plugin_dirs()` returns the plugin directories on disk; `manifest_path(name)` resolves one manifest.
- `read_json(path)` is the single reader, so a malformed manifest fails the same way everywhere.
- `plugin_components(dir, manifest)` enumerates what a plugin actually ships: skills, agents, and everything else.
- `plugin_kind(...)` derives `bundle`, `skill-only`, or `agent-only` from those components.
- A single-component plugin must use the default layout, such as `skills/<name>/SKILL.md`; a custom path in the manifest makes the kind underivable.
- `readme_kind(readme)` reads the `**Kind:**` line, and `check_plugin_kind(name, manifest, dir)` fails when the README and the files disagree.

## `errors.py`

- `has_error_code(error, code)` and `error_message(error)` narrow a caught exception, where anything can be raised and not everything carries the attributes code assumes.
- Every script reports failures through these rather than reaching for `.code` or `.message` directly, so a non-standard exception produces a readable message instead of a second exception inside the handler.

## Tests

- `test_plugins.py` — directory discovery, manifest reading, component enumeration, kind derivation per layout, and the README-versus-files mismatch.
- `test_errors.py` — narrowing a non-exception value, a missing code, and a message that is not a string.
