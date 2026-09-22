---
paths:
  - "plugins/**/*.sh"
  - "plugins/**/hooks/hooks.json"
  - ".claude/hooks/**/*.sh"
  - "scripts/plugin_validation/suites/**/*.sh"
---

# Shell scripts and hooks

- Scripts shipped in plugins run on whatever Bash the user has.
  `#!/usr/bin/env bash` picks the first `bash` on `PATH`, which on a stock Mac
  without Homebrew is `/bin/bash` 3.2, and hooks invoked as `bash script.sh` do
  the same. `make test-slow` runs every plugin suite under both `bash` and
  `/bin/bash`; keep it that way.
- Hooks sit in the hot path of every matching tool call. Time them against large
  adversarial inputs (long commands, heredocs, deep nesting) under `/bin/bash`
  3.2. Avoid constructs that go quadratic there: `${var%%pat}`, `${var//pat/}`,
  and `${var##*/}` on long strings, and passing large strings as function arguments.
- Test every degraded-mode claim ("if jq is missing, only X is denied") with the
  dependency removed and a realistic full hook payload (`cwd`, `transcript_path`,
  `session_id`), not only the field you expect to matter.
- A function that must exit the hook (deny, fail) can't run inside `$(...)`,
  because it only exits the subshell. Return through globals instead.
- Pass large test data through stdin or a file, never as one argument: Linux
  caps a single argument at 128 KB (`MAX_ARG_STRLEN`) and macOS doesn't, so a
  test that builds a 250 KB payload with `jq --arg` gets an empty payload on
  the CI runner and passes without testing anything. Assert that the payload
  was built before asserting on the hook's answer.
