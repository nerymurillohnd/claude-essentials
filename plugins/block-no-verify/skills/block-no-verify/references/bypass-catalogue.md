# Bypass catalogue

The handler inspects every shell command Claude runs through the `Bash` or
`PowerShell` tool. It finds each `git` invocation anywhere in the command (any
case, any path, `git.exe`, zsh `=git`, dashed forms such as `git-commit`) and
denies the ones below. Commit message text (`-m`, `--message`, `-F`, heredoc
bodies, including Claude Code's `-m "$(cat <<'EOF' ... EOF)"` form) and other
quoted data never trigger a deny.

## Denied

| Category | Examples |
| --- | --- |
| Skip hooks | `--no-verify` on any subcommand (`commit`, `push` with or without `--force`/`--force-with-lease`/`--mirror`, `merge`, `rebase`, `am`, `pull`, ...), the abbreviations Git accepts (`--no-verif`, `--no-veri`, `--no-v`), and brace forms (`--no-{verify,}`) |
| Short `-n` | `git commit -n`, `-anm "msg"`, `-nm`, `git am -n`, and the same through an alias of `commit` (`git ci -n`); not `push -n`, `merge -n`, `rebase -n`, `cherry-pick -n`, `revert -n`, `log -n`, where `-n` means something else |
| Skip signing | `--no-gpg-sign` (and `--no-gpg`, `--no-gp`) on any subcommand; `git tag --no-sign`; `git commit-tree`, which ignores both hooks and `commit.gpgsign` |
| One-off config | `-c`, `--config`, `--config=`, `-cKEY=VAL`, `--config-env` setting `commit.gpgsign`, `tag.gpgsign`, or `tag.forceSignAnnotated` to anything that is not clearly true (`false`, `no`, `off`, `0`, `0x0`, `" 0"`, empty, junk); any `core.hooksPath`; `gpg.program`/`gpg.<format>.program`; `include.path`/`includeIf.*` |
| Commands inside config | `core.editor`, `sequence.editor`, `core.pager`, `pager.*`, `core.sshCommand`, `core.fsmonitor`, `diff.external`, `credential.*helper`, `filter.*`, `merge.*.driver`, `diff.*.command`/`textconv`, and `alias.*` values are parsed as commands and denied if they contain a bypass |
| Persistent config | `git config` writes (`key value`, `set`, `--add`, `--replace-all`) that disable signing, set `gpg.program`, or point `core.hooksPath` outside the repository (absolute, `~`, `..`, empty, `NUL`); `--unset`/`unset` of those keys; `remove-section`/`rename-section` of `core`, `commit`, `tag`, `gpg`, `include*` |
| Environment | `HUSKY=0`, `HUSKY_SKIP_HOOKS`, `SKIP` (pre-commit), `PRE_COMMIT_ALLOW_NO_CONFIG`, `LEFTHOOK=0`/`false`, `LEFTHOOK_EXCLUDE`, `SKIP_SIMPLE_GIT_HOOKS`, `OVERCOMMIT_DISABLE`, `GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` for the keys above, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `HOME`, `XDG_CONFIG_HOME`, on a subcommand that runs hooks or signs (commit, merge, pull, rebase, am, cherry-pick, revert, tag, push, or an alias); `GIT_EDITOR`, `GIT_SEQUENCE_EDITOR`, `EDITOR`, `VISUAL`, `GIT_PAGER`, `PAGER`, `GIT_SSH_COMMAND`, `GIT_EXTERNAL_DIFF` values containing a bypass. Set as a leading assignment, via `env`/`sudo`, `export`/`declare -x`, a bare assignment earlier in the command, or `$env:NAME` in PowerShell |
| Arguments built by expansions | `git commit $(echo --no-verify)`, backticks, `F=--no-verify; git commit $F`, `set -- --no-verify; git commit "$@"`: an argument containing `$` or a backtick is checked together with the values the command sets elsewhere |
| Nested commands | `bash`/`sh`/`zsh`/`dash`/`ksh -c "..."`, `eval`, `env -S`, `watch`, `su -c`, `flock -c`, `pwsh -Command`, `Invoke-Expression`, a shell fed by a heredoc or here-string, `$(...)`, backticks, `<(...)`, substitutions inside unquoted heredocs, `git rebase -x/--exec`, `git submodule foreach`, `git bisect run`: parsed up to three levels deep, then checked conservatively |
| Wrappers | Any command before `git` (`sudo`, `env`, `nice`, `nohup`, `timeout`, `xargs`, `command`, `builtin`, `noglob`, `watch`, `time`, `exec`, `find -exec`, ...) |
| Hook files | `rm`/`unlink`/`truncate`/`shred` of `.git/hooks/*`, `.husky/*`, lefthook configs, `.pre-commit-config.yaml`, `.overcommit.yml`; `mv` of them away; `chmod` that removes the owner exec bit (`-x`, `a-x`, `644`); `pre-commit uninstall`, `lefthook uninstall`, `husky uninstall`. Creating, copying in, or `chmod +x`-ing hooks stays allowed |
| Fail closed | Invalid or non-object JSON, unterminated quotes or substitutions, internal errors |

Top-level lists are split on `;`, `&&`, `||`, `|`, `|&`, `&`, newlines,
parentheses, and braces. Single quotes, double quotes, backslash escapes,
`$'...'` (hex, octal, `\u`/`\U` escapes, also on bash 3.2), comments, and
redirections are handled. PowerShell payloads use PowerShell quoting (`''`,
backtick escapes, `@'...'@` here-strings, `<# #>` comments).

## Allowed on purpose

- `git push --force` and `--force-with-lease` without a bypass: the pre-push
  hook still runs. Preventing force pushes is a server-side policy (branch
  protection), not a local-verification bypass.
- `git config core.hooksPath .githooks` (or `.husky/_`) and
  `git config --global include.path ~/.gitconfig.local`: standard setup that
  keeps hooks and config in reviewable places.
- Environment overrides such as `HOME=/tmp git status` on subcommands that run
  no hooks and sign nothing.

## Conservative checks

When the command name comes from a variable (`$GIT commit`), a word splices
`git` with expansions (`git${IFS}commit`), arguments come from a pipe into
`xargs git`, or nesting exceeds three levels, the handler cannot resolve the
command. It then denies if that construct, together with the parts of the
command that invoke no `git`, mentions both `git` and a bypass marker
(`no-v`, `gpgsign`, `hookspath`, `husky`, `lefthook`, `skip=`, `GIT_CONFIG`,
...). Commit messages are not part of that text, so they do not cause false
positives there.

Parsing is metered. A pathological command (tens of kilobytes of tokens) that
exhausts the work budget gets a text-only check: denied if it mentions `git`
and a bypass marker, allowed otherwise. Measured worst case on 50 KB inputs:
about 200 ms on macOS bash 3.2; a typical commit takes about 30 ms end to end.

## Cannot see (documented limitations)

- Values that come from outside the command: shell functions and aliases
  defined earlier in the session, variables exported by a previous tool call,
  scripts executed from files (`bash ./release.sh`), and `source`d files.
- `git config --edit`, `Start-Process`, `cmd /c`, base64 `-EncodedCommand`.
- Writing hook files with redirections (`> .git/hooks/pre-commit`) or with a
  file-edit tool, and editing `.git/config` directly: pair this policy with
  file-edit permissions if that matters.
- Low-level history rewriting (`git update-ref`, `git replace`,
  `git filter-branch`) that does not itself create commits.
- Anything outside Claude's shell tools: a human's terminal, IDE Git
  integrations, CI. Server-side controls (branch protection, required checks,
  required signatures) remain the real enforcement.
