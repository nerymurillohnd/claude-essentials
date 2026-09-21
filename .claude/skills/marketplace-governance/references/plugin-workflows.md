# Plugin workflows

`scripts/plugin_workflows/`. The gate for `plugins/*/workflows/*.js`, which are
written in the dynamic workflow dialect and cannot be parsed by the repository's
JavaScript tooling.

## Ground rules

- Workflow scripts use top-level `return` and runtime globals such as `agent`, `parallel`, `pipeline`, `phase`, and `log`. That is not valid standalone JavaScript, so the formatter and linter exclude the path.
- Excluding a path from one gate means adding it to another. This test is the other one; without it these files would be the only unchecked code the repository ships.
- `meta` must be a pure literal. A computed value there cannot be read before the workflow runs, and the permission dialog shows it to the user.

## Tests

### `test_plugin_workflows.py`

- Parses each workflow and asserts `meta` is a pure literal object with `name`, `description`, and, when present, `phases`.
- Asserts every `phase()` call in the body has a matching declared phase title, and every declared title is used.
- Compiles the body to prove it parses in the dialect, catching a syntax error before a user's first run.
- Exercises the orchestration logic against a stub runtime, so the agent calls, the fan-out, and the result shaping are checked without spawning a real agent.
