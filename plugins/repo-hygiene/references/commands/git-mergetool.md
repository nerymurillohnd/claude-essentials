# git mergetool

Official: https://git-scm.com/docs/git-mergetool · Areas: G2, G12 · Floor: any

## Purpose in an audit

Never run: it launches a configured program. The audit needs it only to explain the files
it leaves behind (`*.orig`, `*_BASE_*`, `*_LOCAL_*`, `*_REMOTE_*`, `*_BACKUP_*`) and the
config keys that decide them.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git mergetool …` | executes-config, mutates | Runs `merge.tool` / `mergetool.<tool>.cmd` and stages the result (contract section 2) |
| `git mergetool --tool-help` | read | Lists known tools `[doc]` |
| `git config --get-regexp '^mergetool\.'` | read | Inventory of the settings below |

## Options that matter

- `-t <tool>`/`--tool=<tool>`, `merge.tool`, `mergetool.<tool>.cmd`,
  `mergetool.<tool>.path` `[doc]`.
- `mergetool.<tool>.trustExitCode`: when false, Git decides success by the file's
  timestamp or by asking `[doc]`.
- `mergetool.keepBackup` (default true): keep `<file>.orig` with the conflict markers
  `[doc]`.
- `mergetool.keepTemporaries`: keep `BASE`/`LOCAL`/`REMOTE` temp files when the tool fails
  `[doc]`.
- `mergetool.writeToTemp`: write the temporaries in a temp directory instead of the
  working tree (default false) `[doc]`.
- `mergetool.hideResolved`, `mergetool.<tool>.hideResolved` `[doc]`.
- `-y`/`--no-prompt`, `-g`/`--gui` `[doc]`.

## Verified recipes

Only on a disposable fixture, never on an audited repository:

```sh
git config mergetool.fake.cmd 'cp "$REMOTE" "$MERGED"'
git config mergetool.fake.trustExitCode true
git mergetool -t fake --no-prompt
```

`[observed]`: `conf.txt` was resolved and staged (`1 M.` in porcelain v2) and
`conf.txt.orig` stayed as an untracked file (`? conf.txt.orig`).

Audit read for leftovers:

```sh
git --no-optional-locks --no-pager ls-files -o --exclude-standard -- '*.orig' '*_BACKUP_*' \
  '*_BASE_*' '*_LOCAL_*' '*_REMOTE_*'
```

`[observed]`: `conf.txt.orig`.

## Footprint it leaves when interrupted or misused

- `<file>.orig` after each merge while `mergetool.keepBackup` is true `[doc]`,
  `[observed]`.
- Temporaries named `<name>_BACKUP_<pid><ext>`, `<name>_BASE_<pid><ext>`,
  `<name>_LOCAL_<pid><ext>`, `<name>_REMOTE_<pid><ext>` (and `_LCONFL_`, `_RCONFL_`) in
  the working tree unless `mergetool.writeToTemp` is true (source:
  `git-mergetool.sh` in git/git); left behind when the tool fails and
  `keepTemporaries` is true, or when the session is killed.

## Gotchas

- The `.orig` extension is also used by `patch(1)` and other tools; an `.orig` file does
  not prove mergetool made it.
- "These are safe to remove once a file has been merged and its git mergetool session has
  completed" `[doc]`: check no merge is still in progress (G2) first.
- A custom `mergetool.<tool>.cmd` is a command-executing key for G12.
