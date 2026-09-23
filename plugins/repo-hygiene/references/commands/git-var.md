# git var

Official: https://git-scm.com/docs/git-var · Areas: G1, G11, G12, G13 · Floor: any

## Purpose in an audit

Prints the values Git itself resolved for the editor, pager, shell, default branch,
identities, and the paths of the system and global config and attribute files. It answers
"which program would Git run" and "which global files apply" without running anything.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git var <VARIABLE>` | read | Prints one logical variable; exit 1 if it has no value `[doc]` |
| `git var -l` | read, prints config values | Also lists every configuration variable `[doc]`, credentials included (`remote.backup.url` with a token was in the list `[observed]`); redact or avoid |

## Options that matter

- `GIT_AUTHOR_IDENT`, `GIT_COMMITTER_IDENT`: name, email, timestamp, zone `[doc]`.
- `GIT_EDITOR`: `$GIT_EDITOR`, then `core.editor`, `$VISUAL`, `$EDITOR`, compile-time
  default `[doc]`. `GIT_SEQUENCE_EDITOR`: `$GIT_SEQUENCE_EDITOR`, `sequence.editor`,
  then `GIT_EDITOR` `[doc]`.
- `GIT_PAGER`: `$GIT_PAGER`, `core.pager`, `$PAGER`, default (usually `less`) `[doc]`.
- `GIT_DEFAULT_BRANCH`, `GIT_SHELL_PATH` `[doc]`.
- `GIT_ATTR_SYSTEM`, `GIT_ATTR_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_GLOBAL`: paths;
  some hold several lines, highest priority first; paths print even if the file does not
  exist `[doc]`.
- `-l`: the configuration listing part is deprecated in favor of `git config list`
  `[doc]`.

## Verified recipes

```sh
git var GIT_CONFIG_GLOBAL
git var GIT_CONFIG_SYSTEM
git var GIT_ATTR_GLOBAL
git var GIT_ATTR_SYSTEM
```

`[observed]`: two global config paths (`~/.config/git/config`, then `~/.gitconfig`), the
Homebrew system files `/opt/homebrew/etc/gitconfig` and `/opt/homebrew/etc/gitattributes`,
and `~/.config/git/attributes`.

```sh
git var GIT_EDITOR
git var GIT_PAGER
git var GIT_DEFAULT_BRANCH
git var GIT_SHELL_PATH
```

`[observed]`: `false` for the editor (the session set `GIT_EDITOR=false` in the
environment), `less`, `main`, `/bin/sh`.

```sh
git var GIT_AUTHOR_IDENT | sed -E 's/<[^>]*>/<email>/'
```

`[observed]`: `<name> <email> <epoch> <zone>`; redact the email in shared reports if
policy asks for it.

```sh
git var -l | wc -l
```

`[observed]`: 79 lines, including aliases and remote URLs; never print it unredacted.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- A value of `false` or `true` for `GIT_EDITOR` usually comes from an automation
  environment, not from config `[observed]`.
- `GIT_CONFIG_GLOBAL` lists several files; later lines have lower priority `[doc]`.
- A guard in this repository's tooling refused `git var` with a shell variable as the
  argument `[observed]`; write the variable name literally.
