# Repository hooks

`scripts/repo_hooks/`. Test suites for the hooks in `.claude/hooks/`, which run
on every session in this repository. A hook that silently stops working removes
a gate without removing the belief that the gate exists, so each one is executed
against a real fixture rather than read.

## The hooks under test

| Event | Hook | Role |
| --- | --- | --- |
| `SessionStart` | `session-start.sh` | Reports repository state, including a marketplace validation run |
| `PreToolUse` | `guard-marketplace-catalog.sh` | Denies hand-edits to the generated `plugins` array |
| `PreToolUse` | `bash-stamp.sh` | Records shell invocations for later evidence |
| `PreToolUse` | `guard-commit.sh` | Denies a `git commit` when `make lint-staged` fails |
| `PreToolUse` | `guard-push.sh` | Denies a push to a branch the remote no longer has |
| `PostToolUse` | `post-edit.sh` | Reminds once per session that a plugin runtime change needs a version bump |
| `SubagentStop` | `record-audit.sh` | Records the `repo-auditor` verdict per audited head |

## Ground rules

- Hook edits apply immediately. There is no reload step, so a broken hook affects the next tool call, not the next session.
- A new hook script needs the exec bit (`100755`) and is tested by executing its path.
- Shared logic lives in `.claude/hooks/lib/`. A hook that duplicates a rule instead of sourcing it becomes the second source of truth this area exists to catch.

## Tests

### `test_plugin_paths.py`

- Executes the bash functions in `.claude/hooks/lib/plugin-paths.sh` and compares them against `versioning/version_plan.py`.
- The runtime-versus-exempt rule exists twice by necessity: CI reads it in Python, the hooks read it in bash. This test is what keeps the two identical.
- A change to one without the other fails here rather than in a release.

### `test_checklist_gate.py`

- Exercises `.claude/hooks/lib/checklist.sh` and the `Stop` hook `checklist-gate.sh`.
- Proves the gate refuses to end a turn while a maintenance skill's checklist has unchecked items, and releases once they are recorded.

### `test_push_guard.py`

- Builds a throwaway clone against a local bare `origin` and runs `guard-push.sh` against it.
- Asserts that pushing a published branch the remote no longer has is denied, and that new branches, existing branches, deletions, and non-push commands pass.
- The denied case is the one that matters: a merged branch must never receive another push.

### `test_record_audit.py`

- Exercises `record-audit.sh`, the `SubagentStop` hook that records the `repo-auditor` verdict keyed by the head SHA it audited.
- Delivery requires a `VERDICT: PASS` for the exact head, so a verdict recorded against a stale SHA must not satisfy it.

### `test_repo_root.py`

- Exercises `.claude/hooks/lib/repo-root.sh`, which decides whether a hook acts on the tree Claude is working in or on the checkout the session started from.
- The two diverge inside a git worktree, and picking the wrong one makes a gate inspect the wrong files while still reporting success.
