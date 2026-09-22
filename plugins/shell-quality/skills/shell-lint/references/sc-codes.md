# ShellCheck codes: correct fixes

Verified on 2026-09-22 against ShellCheck 0.11.0 (each fix below was run
through the binary and exits `0`) and the
[ShellCheck wiki](https://www.shellcheck.net/wiki/). Every code has a page at
`https://www.shellcheck.net/wiki/SC<code>`; read it before fixing an
unfamiliar one. New codes and changed defaults arrive in releases: check the
[CHANGELOG](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md).

## Contents

- [Quoting and splitting](#quoting-and-splitting)
- [Exit status and error handling](#exit-status-and-error-handling)
- [Variables and functions](#variables-and-functions)
- [Sourcing](#sourcing)
- [Tests and conditions](#tests-and-conditions)
- [Portability](#portability)
- [Optional checks](#optional-checks)
- [Anti-patterns](#anti-patterns)

## Quoting and splitting

| Code | Problem | Fix |
| --- | --- | --- |
| SC2086 | `cmd $var` splits and globs | `cmd "${var}"`; a deliberate list is an array: `cmd "${args[@]}"` |
| SC2046 | `cmd $(other)` splits and globs | `cmd "$(other)"`; to split on purpose `read -r -a parts <<<"$(other)"`, then `"${parts[@]}"` |
| SC2068 | `$@` unquoted | `"$@"` |
| SC2206 | `arr=($var)` | `read -r -a arr <<<"${var}"` (IFS sets the separator) |
| SC2207 | `arr=($(cmd))` | bash 4+: `mapfile -t arr < <(cmd)`; bash 3.2: `while IFS= read -r l; do arr+=("${l}"); done < <(cmd)` |
| SC2016 | `$` inside single quotes will not expand | See below |
| SC2089/SC2090 | Quotes stored inside a string used as arguments | An array: `args=(-o "a b")`, then `cmd "${args[@]}"` |
| SC2064 | `trap "rm ${tmp}" EXIT` expands now | Single quotes: `trap 'rm -f -- "${tmp}"' EXIT` |

**SC2016.** Decide what the author meant. To expand, use double quotes. To
pass a literal `$` to a program, either hand the value over properly or escape
it inside double quotes:

```bash
jq --arg n "${name}" '.name == $n' data.json   # value passed as a jq variable
printf '%s\n' "\$HOME"                          # literal $HOME, no warning
```

ShellCheck already skips well-known commands that expect a literal `$` (the
wiki names `sh` and `perl`; `awk`, `jq`, and `sh -c` produced no SC2016 in
0.11.0), so the code usually fires on `echo`, `printf` arguments and
assignments, where the escape is the right change.

## Exit status and error handling

| Code | Problem | Fix |
| --- | --- | --- |
| SC2155 | `local x=$(cmd)` or `export x=$(cmd)` masks `cmd`'s status | `local x; x=$(cmd)` |
| SC2164 | `cd dir` unchecked | `cd dir \|\| exit 1`; `\|\| return 1` in a function |
| SC2181 | `cmd; if [ $? -ne 0 ]` | `if ! cmd; then …`, or `if ! out=$(cmd); then …` |
| SC2312 (optional) | `echo "$(cmd)"`, `done < <(cmd)`: the inner status is lost | Capture first, `out=$(cmd)`, then use `"${out}"`; `\|\| true` only when ignoring the failure is the intent |
| SC2310/SC2311 (optional `check-set-e-suppressed`) | A function runs where `set -e` is off | Check its status explicitly |
| SC2005 | `echo "$(cmd)"` | Just `cmd` |

## Variables and functions

| Code | Problem | Fix |
| --- | --- | --- |
| SC2034 | Assigned, never used | Delete it or use it; `_` is exempt (`read -r _ second`) |
| SC2154 | Used, never assigned | Assign it, or require it from the environment: `: "${VAR:?VAR must be set}"` |
| SC2153 | Possible misspelling of a similar name | Fix the name |
| SC2329 | Function never invoked before it goes out of scope | Call it, delete it, or inline a `trap` handler (below) |
| SC2250 (optional) | `$var` without braces | `${var}` |
| SC2248 (optional) | "Safe" variable unquoted | Quote it anyway |

SC2154 fires on lowercase names by default; uppercase names (assumed to come
from the environment) need the optional `check-unassigned-uppercase`.

SC2329 is new in 0.11.0. Per the [wiki](https://www.shellcheck.net/wiki/SC2329)
it is skipped when the script has no explicit `exit`, because another script
may source it and call the function. It fires on `trap` handlers: `cleanup()
{ …; }; trap cleanup EXIT; …; exit 0` reports SC2329. The wiki suggests a
directive; this skill does not. Put the command in the trap instead:

```bash
tmp=$(mktemp)
trap 'rm -f -- "${tmp}"' EXIT
```

If the handler is too long to inline, tell the user the finding is a known
false positive and let them decide.

## Sourcing

| Code | Problem | Fix |
| --- | --- | --- |
| SC1090 | `. "$1"`: a non-constant source | `# shellcheck source=lib/x.sh` naming the real file |
| SC1091 | The sourced file was not opened | `-x` plus `# shellcheck source-path=SCRIPTDIR` after the shebang (not a suppression); the same key in `.shellcheckrc` is a configuration change to propose |

Measured in 0.11.0: `. "$(dirname "$0")/lib/util.sh"` resolves to
`./lib/util.sh` relative to the **working directory**, so it passes only when
ShellCheck runs from the script's directory. `source-path=SCRIPTDIR` (a
file-wide directive or an rc line) plus `-x` made it pass from `/` as well.
`# shellcheck source=/dev/null` skips the file entirely, hides its findings,
and counts as a suppression.

## Tests and conditions

| Code | Problem | Fix |
| --- | --- | --- |
| SC2244 (optional `avoid-nullary-conditions`) | `[ "$x" ]` | `[ -n "${x}" ]` |
| SC2236/SC2237 (optional `avoid-negated-conditions` since 0.11.0) | `! [ -z "$x" ]` | `[ -n "${x}" ]` |
| SC2249 (optional `add-default-case`) | `case` without `*)` | Add a `*)` that handles or reports the value |
| SC2292 (optional `require-double-brackets`) | `[ ]` in bash | `[[ ]]` |
| SC2166 | `[ a -a b ]` | `[ a ] && [ b ]` |
| SC2143 | `if [ "$(grep …)" ]` | `if grep -q …; then` |

## Portability

`#!/bin/sh` scripts get SC3xxx codes for non-POSIX features. Measured in
0.11.0: `local` (SC3043), `[[ ]]` (SC3010), `echo -n` (SC3037), and
`set -o pipefail` (SC3040) is still reported although POSIX.1-2024 added it.
Other common ones: arrays, the `function` keyword, `==` in `[ ]` (SC3014).
Fix with POSIX constructs, or change the shebang to bash when the script
really needs bash. The unreleased `master` removes SC3003 (`$'…'`) for
POSIX.1-2024; check the changelog before relying on either.

**macOS `/bin/bash` 3.2.** ShellCheck does not check Bash versions: a bash
script using the features below passed `shellcheck -o all` with exit `0` and
then failed under `/bin/bash` 3.2.57 on macOS (verified 2026-09-22).

| Fails on 3.2 | Works on 3.2 |
| --- | --- |
| `declare -A m` | Parallel indexed arrays, or `case` lookups |
| `mapfile -t a < <(cmd)` | `while IFS= read -r l; do a+=("${l}"); done < <(cmd)` |
| `${x,,}` / `${x^^}` | `tr '[:upper:]' '[:lower:]' <<<"${x}"` |
| `[[ -v x ]]` | `[[ -n ${x+set} ]]` |
| `local -n ref=x` | Pass names and use `printf -v` or `eval` with care |
| `${x@Q}` | `printf '%q' "${x}"` |
| `set -u; "${a[@]}"` of an empty array | `${a[@]+"${a[@]}"}` |

Also avoid `wait -n` and `shopt -s inherit_errexit` (bash 4.3 and 4.4). Test
with `/bin/bash script.sh` when macOS support matters.

## Optional checks

`shellcheck --list-optional` in 0.11.0 prints eleven: `add-default-case`,
`avoid-negated-conditions`, `avoid-nullary-conditions`,
`check-extra-masked-returns` (SC2312), `check-set-e-suppressed`,
`check-unassigned-uppercase`, `deprecate-which`, `quote-safe-variables`,
`require-double-brackets`, `require-variable-braces` (SC2250),
`useless-use-of-cat` (SC2002, off by default since 0.11.0). Enable them by name
with `-o` or `enable=` in the rc. `-o all` is fine for a one-off audit, but in
a committed configuration it switches on checks that disagree with each other
(`require-double-brackets` is wrong for `sh`) and new ones on every upgrade.

## Anti-patterns

- Any directive, rc line, flag, or environment variable that suppresses a
  finding: see the rules in [SKILL.md](../SKILL.md#non-negotiable-rules).
- A `disable=` directive before the first command: it silences the whole file.
- `shell=bash` in an rc file: it overrides every shebang and hides POSIX
  findings in `sh` scripts.
- `find … -exec shellcheck {} \;` in CI: exits `0` whatever it finds.
- Fixing SC2086 by changing the data instead of quoting.
- Treating `set -euo pipefail` as a substitute for checking statuses.
- Accepting an editor's "disable this warning" quick fix
  (bash-language-server offers one).
