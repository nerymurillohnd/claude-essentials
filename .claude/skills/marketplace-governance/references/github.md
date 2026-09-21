# GitHub — API, Actions, and `.github/`

`scripts/github/`. Everything that talks to the GitHub API or owns a file under
`.github/`. The taxonomy these files enforce is `ADR-0004`.

## Ground rules

- Use the GitHub MCP server for interactive work; this area is for automation that runs unattended in CI.
- Every caller is idempotent, so the client carries no retry logic. Re-running a workflow is always safe.
- Treat every API response as external data and narrow it before use. A renamed field must fail loudly, not silently.
- Labels are never authored in the GitHub UI. `.github/labels.json` is the source and the sync is one-directional.

## `client.py`

- Builds a minimal REST client over HTTP with `createClient()`; no retries, no pagination magic.
- Returns `None` for a `GET` on a missing resource and for a `DELETE` of something already gone — neither is an error.
- Guards a non-list response where a list is expected, so a shape change reports itself instead of throwing `not iterable`.
- Exposes `RAW` for the `application/vnd.github.raw+json` accept header used to read file contents at a ref.
- Resolves the target repository from `resolve_repo()` or from the git remote via `parse_repo_from_remote()`.
- Resolves credentials with `resolve_token()`, reading the environment and never a file on disk.

## `triage.py` — entrypoint

- Runs from `.github/workflows/triage.yml` on issue, issue-comment, and pull-request events.
- Reads the event payload from `GITHUB_EVENT_PATH` and fails fast when the variable is absent.
- **Security boundary**: it runs from a base-branch checkout. Pull-request content arrives through the API as data and is never executed.
- Dispatches on `GITHUB_EVENT_NAME` using own keys only, so an inherited name such as `toString` cannot resolve to a handler.
- Reads files at a ref through `raw_at()` and `json_at()` rather than checking the PR out.
- Ensures every label it is about to apply exists, creating missing derived labels first.
- Applies one reconciled change set per issue or PR and logs it as `#<n>: +[added] -[removed]`.
- Derives the release label for a PR from the changed files; a failure there is logged and skipped, never fatal.

## `triage_rules.py`

- Holds the pure rules: inputs in, label names out, no I/O.
- `area_labels(files)` maps changed paths to `area:` labels through `AREA_RULES`, with explicit sets for community and tooling files.
- `plugin_labels(files)` derives one `plugin: <name>` label per plugin touched.
- `is_valid_plugin_name()` mirrors the manifest's name pattern and 42-character cap, so a fork PR cannot inject an arbitrary label name.
- `issue_labels(body, plugin_names)` reads the rendered issue body; `form_field(body, label)` extracts one field from it.
- `author_reply_changes()` moves an issue out of the waiting state when the author, not a third party, replies.
- `reconcile(current, desired)` returns the add and remove sets, touching only the managed prefixes `area:`, `plugin:`, and `bump:`.

## `labels.py`

- Defines the taxonomy: `STATUS_LABELS`, `BUMP_LABELS`, `AREA_LABELS`, the `bump: deferred` escape hatch, and `REQUIRED_LABELS`.
- `REQUIRED_LABELS` lists every label a script, workflow, or issue form references by name. Removing one breaks automation, so it is checked, not assumed.
- Enforces GitHub's own limits: 50 characters for a name, 100 for a description.
- Derives one `plugin: <name>` label per plugin with a fixed color; derived labels are never authored by hand.
- `build_taxonomy(static_labels, manifests)` merges authored and derived labels into the desired state.
- `diff_labels(current, desired, prune=False)` returns create, update, and rename operations; deletions only when pruning.

## `sync_labels.py` — entrypoint

- Compares the repository's live labels against the taxonomy and prints one line per planned operation.
- Dry-run by default. `--apply` writes. `--prune` also deletes labels outside the taxonomy and is manual only, never wired into CI.
- Reports `already match the taxonomy` when there is nothing to do, so a clean run is unambiguous.

## `issue_forms.py`

- Owns the contract the triage bot depends on: `PLUGIN_FIELD_ID`, `PLUGIN_FIELD_LABEL`, and the `Marketplace catalog / installation` and `Not sure` options.
- The bot parses the rendered `### Affected plugin` section, so these strings and the generator must not drift apart.
- `plugin_dropdown_options()` and `with_plugin_options()` build the option list a form should carry.

## `generate_issue_forms.py` — entrypoint

- Rewrites the **Affected plugin** dropdown in every issue form from `plugins/` on disk.
- Generated output, never hand-edited; a form can then never offer a plugin that does not exist.
- Reports how many files changed and how many plugins were offered.

## `repo_metadata.py`

- Validates every issue form against the SchemaStore schemas vendored in `schemas/github/`, since GitHub publishes none.
- `check_labels()` verifies each label's own fields and that every required label and alias resolves.
- `check_issue_form()` cross-checks a form against the live label names and plugin names.
- `check_node_version_source()` requires every `setup-node` step to read `node-version-file` rather than a floating version, so CI runs the repository's own runtime.
- `check_claude_code_versions()` requires every workflow that installs the Claude Code CLI to pin the same canonical version.
- `validate_repo_metadata()` is the single entry the marketplace validator calls.

## Tests

- `test_client.py` — request shaping, the `None` paths for 404 and gone, and the non-list guard.
- `test_triage_rules.py` — area mapping, plugin-name rejection, form-field extraction, author-reply transitions, and reconciliation.
- `test_labels.py` — limits, derived-label shape, taxonomy assembly, and the diff including renames and prunes.
- `test_issue_forms.py` — the dropdown contract the bot parses.
- `test_repo_metadata.py` — schema failures, missing required labels, an unpinned Node version, and a drifting CLI pin.
