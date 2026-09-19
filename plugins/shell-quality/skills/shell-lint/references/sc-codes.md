# ShellCheck codes: correct fixes

Verified against ShellCheck 0.11.0 and the
[ShellCheck wiki](https://www.shellcheck.net/wiki/) on 2026-09-19. Each code
has a wiki page at `https://www.shellcheck.net/wiki/SC<code>`; read it before
fixing an unfamiliar code.

## Quoting and splitting

| Code | Problem | Fix |
| --- | --- | --- |
| SC2086 | `cmd $var` splits and globs | `cmd "${var}"`; for a deliberate list use an array `cmd "${args[@]}"` |
| SC2046 | `cmd $(other)` splits and globs | `cmd "$(other)"`; to split on purpose `read -r -a parts <<<"$(other)"` then `"${parts[@]}"` |
| SC2068 | `$@` unquoted | `"$@"` |
| SC2206 | `arr=($var)` | `read -r -a arr <<<"${var}"` (IFS decides the separator) |
| SC2207 | `arr=($(cmd))` | Bash 4+: `mapfile -t arr < <(cmd)`; Bash 3.2: `while IFS= read -r l; do arr+=("${l}"); done < <(cmd)` |
| SC2016 | `$` inside single quotes will not expand | Use double quotes if expansion is intended; if the literal is intended (jq, awk, a template), that is the user's call to annotate |
| SC2089/SC2090 | Quotes stored inside a string variable | Use an array for argument lists |

## Exit status and error handling

| Code | Problem | Fix |
| --- | --- | --- |
| SC2155 | `local x=$(cmd)` / `export x=$(cmd)` masks `cmd`'s status | `local x; x=$(cmd)` |
| SC2164 | `cd dir` unchecked | `cd dir \|\| exit 1`, or `\|\| return 1` in a function |
| SC2181 | `cmd; if [ $? -ne 0 ]` | `if ! cmd; then …` or `if ! out=$(cmd); then …` |
| SC2312 (optional) | `echo "$(cmd)"`: the substitution's failure is lost | `out=$(cmd)` first, then `echo "${out}"`; `\|\| true` only when ignoring the failure is intended |
| SC2311/SC2310 (optional, `check-set-e-suppressed`) | A function called where `set -e` is suspended | Handle the status explicitly |

## Variables

| Code | Problem | Fix |
| --- | --- | --- |
| SC2034 | Assigned but never used | Remove it, use it, or prefix a deliberate placeholder with `_` |
| SC2154 | Used but never assigned | Assign it, or document that the environment provides it (`: "${VAR:?must be set}"`) |
| SC2250 (optional) | `$var` without braces | `${var}` |
| SC2248 (optional) | Unquoted "safe" variable | Quote it anyway |
| SC2153 | Possible misspelling of a similar variable | Fix the name |

## Sourcing

| Code | Problem | Fix |
| --- | --- | --- |
| SC1090 | `source "$dir/x.sh"` cannot be followed | `# shellcheck source=lib/x.sh` naming the real file, or `source-path=SCRIPTDIR` |
| SC1091 | The sourced file is not in the input | Enable `external-sources=true` in the rc and set `source-path`, or pass the file together with the script |

`# shellcheck source=/dev/null` tells ShellCheck to skip the file; it hides
real findings in the sourced code, so it is a suppression.

## Tests and conditions

| Code | Problem | Fix |
| --- | --- | --- |
| SC2244 (optional `avoid-nullary-conditions`) | `[ "$x" ]` | `[ -n "${x}" ]` |
| SC2236/SC2237 (optional `avoid-negated-conditions` since 0.11) | `! [ -z "$x" ]` | `[ -n "${x}" ]` |
| SC2249 (optional `add-default-case`) | `case` without `*)` | Add `*)` that handles or reports the unexpected value |
| SC2166 | `[ a -a b ]` | `[ a ] && [ b ]` |
| SC2143 | `if [ "$(grep …)" ]` | `if grep -q …; then` |

## Portability (`#!/bin/sh`)

SC3xxx codes flag non-POSIX features in `sh` scripts: `[[ ]]` (SC3010),
arrays, `local` (SC3043), `function` keyword, `$'…'`, `==` in `[ ]` (SC3014),
`echo -e`/`-n` (SC3037). Fix with POSIX constructs, or change the shebang to
bash if the script really needs bash. ShellCheck 0.11 still reports
`set -o pipefail` (SC3040) even though POSIX.1-2024 standardized it.

## Optional checks worth enabling

From `shellcheck --list-optional` (0.11): `add-default-case`,
`avoid-negated-conditions`, `avoid-nullary-conditions`,
`check-extra-masked-returns` (SC2312), `check-set-e-suppressed`,
`check-unassigned-uppercase`, `deprecate-which`, `quote-safe-variables`,
`require-variable-braces` (SC2250), `useless-use-of-cat` (SC2002 moved here in
0.11). `require-double-brackets` fits bash-only codebases. Enable them by
name; `enable=all` turns on checks that conflict.

## Anti-patterns

- A `disable=` directive at the top of a file: before the first command it
  silences the whole file.
- `disable=` lines in `.shellcheckrc`, `disable=all`, `SHELLCHECK_OPTS="-e …"`.
- `shell=bash` in an rc file.
- `find … -exec shellcheck {} \;` in CI (always exits 0).
- Fixing SC2086 by removing the variable's contents' spaces instead of quoting.
- Silencing SC1091 globally instead of setting `source-path`.
- Treating `set -euo pipefail` as a substitute for checking statuses.
