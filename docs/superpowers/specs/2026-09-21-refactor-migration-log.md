# Migration log — Python toolchain and governance refactor

Evidence for every phase gate of `~/.claude/plans/consolidated-governance-refactor.md`
Part B. One heading per gate; each box is checked only with output from the current
tree. This file is committed with step 7 and re-read by `repo-auditor` at step 12.

## Gate 0 — pre-flight (2026-09-21)

- [x] branch `refactor/python-toolchain-and-governance` created from `13d345c`
- [x] first commit `a19bc6d` holds the demolition and the carried trees; tree clean; not pushed
- [x] parent check after `git fetch --prune origin`:

  ```text
  HEAD~1=13d345cd4e956578db136f139d34a4813b32beae origin/main=13d345cd4e956578db136f139d34a4813b32beae
  PARENT_OK
  porcelain=0
  ```

- [x] tool versions:

  ```text
  uv: uv 0.12.17 (635500036 2026-09-18 aarch64-apple-darwin)
  make: GNU Make 3.81
  claude: 2.1.278 (Claude Code)
  shellcheck: version: 0.11.0
  shfmt: 3.14.1
  jq: jq-1.8.2
  ```

- [x] `uv python list --only-installed | grep 3.14`: `cpython-3.14.7-macos-aarch64-none` present
- [x] `.claude/hooks/lib/checklist.sh abort "superseded by the toolchain refactor"` → see below
- [x] `.claude/state/audits/` and `.claude/.cache/hooks/bash-stamp-*` cleared (`audits=0 stamps=0`)
- [x] `sha256sum schemas/github/*.json` (compared again at gate 9 after the move):

  ```text
  0988613c0ace111998e94d1883ad1a6110fbd8525385e1bff88ccb102e851e60  schemas/github/issue-config.schema.json
  31ed735665dfe33739dc41a2342871d32199154ea8a1dd7411ca6303a0e868c5  schemas/github/issue-forms.schema.json
  ```

  ```text
  $ .claude/hooks/lib/checklist.sh abort "superseded by the toolchain refactor"
  aborted
  abort rc=0                       # .claude/state/checklists/.active is gone
  ```

## Gate 1 — `evals/**` and tests exempt (2026-09-21)

- [x] `git ls-files 'scripts/*.mjs' 'scripts/**/*.mjs' | wc -l` is 0 (in `a19bc6d`)
- [x] no `evals/results/` file tracked; `git check-ignore -v plugins/block-no-verify/evals/results/x.json` → `.gitignore:57:**/evals/results/`
- [x] `plugin_path_is_exempt` table, run under `bash` (5.x) and `/bin/bash` (3.2):

  ```text
  exempt  evals/a/b.md          exempt  test-x.sh           exempt  scripts/test-hooks.sh
  exempt  tests/a.sh            exempt  skills/x/tests/a.sh exempt  LICENSE.md
  exempt  docs/a.md             exempt  README.md
  RUNTIME evalsx/b.md           RUNTIME skills/x/evals/y    RUNTIME test-x/y.sh
  RUNTIME tests                 RUNTIME hooks/hooks.json    RUNTIME LICENSE.x/y
  RUNTIME skills/test-a.sh.bak  RUNTIME testsuite/a
  /bin/bash: exempt / runtime / exempt
  ```

  `shellcheck` and `shfmt -d` on `plugin-paths.sh`: clean (`SHELL_OK`).
- [x] `git diff origin/main -- docs/decisions | grep -E '^-[^-]' | wc -l` → 0 (ADR-0003 amendment appended only)
- [x] `git ls-files 'plugins/*/evals/*' | wc -l` → 105 before this step (29 + 18 + 19 + 19 + 20, incl. the five `.gitignore`); decision: the five per-suite `evals/.gitignore` are removed and the root `.gitignore` keeps the single rule `**/evals/results/` (plan Part F)
- [x] `grep -c '|||||||' docs/maintenance/resolved-debt.md` → 0
- [x] the five `evals/README.md` "CI policy" sections rewritten to D2 (runtime classification selects; `evals/**` never does)
- [ ] `git status --porcelain` empty after this step's commit (filled below)
