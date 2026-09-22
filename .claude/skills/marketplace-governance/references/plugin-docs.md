# Plugin documentation contracts

`scripts/plugin_docs/`. Checks that keep a plugin's README truthful about the
plugin's own behaviour. A README is not runtime, but an inaccurate one is a
defect that reaches every user who installs from the catalog.

## Ground rules

- A control the README does not mention is invisible. Nobody can use it, and nobody reviewing the plugin knows the behaviour can change underneath them.
- These checks compare documentation against code, in that direction. They never edit the README.
- Match whole words. A README naming `FOO_BAR` must not satisfy a script that reads `FOO`.
- Every gap found by hand becomes a check here, so the same gap cannot reappear in the next plugin.

## Tests

### `test_plugin_script_env.py`

- Collects every environment variable each plugin's scripts read.
- Fails when a variable is read by a script but never named in that plugin's README.
- Uses a whole-word match, because a substring match passes its own mutation test while letting a real gap through.
- Scoped per plugin: a variable documented in one plugin's README does not excuse another's.

### `test_readme_test_vars.py`

- Collects every `<PREFIX>_TEST_BASH` variable a plugin README tells maintainers to set.
- Fails when no `test-*.sh` suite in that plugin reads it.
- Without this, the documented command silently tests the wrong shell and the second interpreter is never exercised. That was `DEBT-0017`.
