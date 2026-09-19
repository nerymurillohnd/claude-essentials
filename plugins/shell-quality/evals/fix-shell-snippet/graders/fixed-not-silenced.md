---
type: llm
---

PASS if the corrected script quotes the expansions (`"$1"`/`"${dir}"`, `"$f"`), checks `cd` (for example `cd "${dir}" || exit 1`), replaces the `ls` output parsing with a glob loop, does not use `local` outside a function (or wraps the loop in a function), and replaces the `$?` test with a direct check, and the reply adds no `# shellcheck disable` directive.
FAIL if it silences any finding with a `# shellcheck disable` directive or an rc change, or leaves `cd $dir` unquoted and unchecked.
