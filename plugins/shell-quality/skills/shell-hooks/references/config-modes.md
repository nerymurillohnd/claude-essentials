# Configuration modes

The user chooses one. Show them the exact configuration with
`manage.sh show-config --config-mode <mode>` before they choose, and explain it
using `assess`'s baseline ("with this mode, N findings today, mostly SC2086 and
SC2250, and M scripts shfmt would reformat").

ShellCheck and shfmt are configured separately: ShellCheck by an rc file,
shfmt by EditorConfig. Each mode sets both.

| Mode | ShellCheck | shfmt | Files written | Best for |
| --- | --- | --- | --- | --- |
| `recommended` | Native discovery, after the bundled rc is written where ShellCheck finds it | EditorConfig, after the bundled `[[shell]]` block is appended (project/local), or the recommended flags for scripts no `.editorconfig` governs (user scope) | Project/local: `<repo>/.shellcheckrc` if no rc exists there; the marked block in `<repo>/.editorconfig` if it sets no shell style. User: `$XDG_CONFIG_HOME/shellcheckrc` (usually `~/.config/shellcheckrc`) if neither it nor `~/.shellcheckrc` exists | Projects without a shell lint policy |
| `own` | Native discovery (closest `.shellcheckrc`/`shellcheckrc`, then `~/.shellcheckrc`, then the XDG file) | EditorConfig | Nothing | Projects that already have a policy |
| `own` + `--config-path FILE` | `--rcfile FILE` for every script | EditorConfig | Nothing | A shared rc kept outside the usual places |
| `defaults` | `--norc` | `-i 0` (tabs, dialect from the script; EditorConfig ignored) | Nothing | A zero-configuration gate; it also ignores the project's policy |

## How to explain each one

- **recommended** — "ShellCheck follows sourced files and turns on ten
  optional checks: masked return values (SC2312), `set -e` traps, missing
  default `case` branches, `${braces}`, nullary and negated tests, `which`,
  useless `cat`, unassigned uppercase variables, unquoted safe variables. No
  `shell=`, no `enable=all`, no disables. shfmt formats every shell script
  (including extensionless ones and `.bats`) in Google style: 2 spaces,
  indented `case` branches, `&&`/`|` at the start of continued lines,
  simplified syntax. Both are real files, so your editor, pre-commit, and CI
  follow them too; neither is ever written over your own." Show both files and
  point out the checks most likely to fire from the baseline.
- **own** — "The gate uses what you already have." Show the rc file and the
  EditorConfig lines in use. If there is no rc, say ShellCheck uses defaults; if
  EditorConfig sets nothing for shell, shfmt uses tabs.
- **defaults** — "ShellCheck's default checks only and shfmt's default style
  (tabs), ignoring every configuration file, including the project's. It will
  disagree with a project whose EditorConfig uses spaces."

## Scope interactions

- User scope + `recommended`: the rc goes to the user-level location, which
  ShellCheck uses **only when a project has no rc of its own**. For shfmt the
  gate adds `--style-fallback`: scripts under an `.editorconfig` keep that
  style; scripts with none get the recommended style. No `.editorconfig` is
  written outside a project.
- User scope + `defaults`: every project on the machine is checked with
  defaults and formatted with tabs, ignoring each project's policy. Say this
  explicitly.
- Project scope + `own --config-path`: the rc must live inside the repository
  (referenced as `$CLAUDE_PROJECT_DIR/<path>` so teammates have it).

## The max-blocks setting

`--max-blocks N` (1–7, default 5) is how many consecutive times the Stop gate
may block one turn. After that the turn ends with a visible warning listing
what is unresolved. Claude Code itself stops honoring a Stop hook after 8
consecutive blocks, without a message; the limit keeps the warning visible.
