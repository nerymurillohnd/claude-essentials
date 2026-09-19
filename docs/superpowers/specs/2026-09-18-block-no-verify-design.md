# block-no-verify plugin — design

- **Date:** 2026-09-18
- **Status:** approved (maintainer decisions confirmed in session)
- **Kind:** `skill-only` ([ADR-0001](../../decisions/adr-0001-marketplace-distribution-model.md))
- **References consulted, not copied:** the maintainer's earlier user-scope
  `block-no-verify.py` + `test-block-no-verify.sh`, `codex-essentials/plugins/block-no-verify`,
  `forestal-mt-plugins/plugins/block-no-verify`.

## Goal

A public plugin whose installation only makes a skill available. On request,
the skill assesses the repository, recommends a scope, and — after explicit
approval — installs a `PreToolUse` command hook that denies Git commands that
bypass local verification (hooks) or commit/tag signing when Claude runs them
through its shell tools. Nothing is wired at plugin install time.

## Verified constraints (live docs + changelog, 2026-09-18, Claude Code 2.1.277)

| Fact | Source | Design consequence |
| --- | --- | --- |
| Exit codes other than 0/2 are non-blocking: the tool call proceeds | [hooks](https://code.claude.com/docs/en/hooks) | A missing interpreter (exit 127) fails **open**. Bash is the interpreter hooks already run through, so it cannot silently vanish; `python3` can (macOS without CLT ships only a stub) |
| Exit 2 blocks regardless of stdout; JSON is still parsed | hooks | Deny = JSON `hookSpecificOutput` **and** exit 2, so a profile `echo` that corrupts stdout still blocks. Deliberate deviation from "exit 0 with JSON" |
| Shell-form hooks run via `sh -c` (macOS/Linux) or Git Bash (Windows), PowerShell when Git Bash is absent | hooks-guide | Command is `bash "<path>"` (never relies on the exec bit). Preflight refuses Windows without Git Bash |
| Matching hooks run in parallel; for `PreToolUse` the most restrictive decision wins (`deny` > `defer` > `ask` > `allow`) | hooks-guide | Our group coexists with any other hook; position in the array is irrelevant, so we append |
| `PreToolUse` fires before any permission-mode check; `deny` blocks even in `bypassPermissions` | hooks-guide | The policy holds in auto/bypass modes |
| A timed-out `PreToolUse` command hook does not block | hooks | Timeout 10 s; handler budget ≪ 100 ms; documented limitation |
| Identical handler definitions across settings files run once; different paths do not dedupe | hooks | Installing in two scopes runs twice — assess warns, never double-installs silently |
| Matcher `Bash\|PowerShell` is exact-match alternation | hooks | No `if` filter (it would miss wrapped/chained calls); filtering happens in the handler |
| `disableAllHooks` / `allowManagedHooksOnly` suppress non-managed hooks | hooks | Preflight stops when either would silence the policy |
| Cowork runs in a Linux sandbox and ignores `~/.claude/settings.json` and managed settings hooks; no `/hooks` there | [#40495](https://github.com/anthropics/claude-code/issues/40495) (open), [#63360](https://github.com/anthropics/claude-code/issues/63360) | **Cowork is out of scope**, stated once in the README; `SKILL.md` carries a one-line guard |
| Skill frontmatter outside the Agent Skills spec fails packaging on claude.ai surfaces | [skills](https://code.claude.com/docs/en/skills) | Frontmatter limited to `name`, `description`, `compatibility`, `license`, `metadata` |
| `git commit --no-verif` / `--no-veri` are accepted abbreviations and skip hooks (reproduced on git 2.55.0) | local repro | Long-option prefixes are matched, not just exact spellings |
| `-n` means `--no-verify` on `git commit` **and** `git am`; dry-run/no-stat/no-commit elsewhere | `git <cmd> -h`, git 2.55.0 | Short `-n` denied only for `commit` and `am` |

## Decisions

1. **Handler: Bash 3.2-compatible + `jq` ≥ 1.6** (maintainer choice). If `jq`
   disappears after install, the handler denies only payloads whose raw text
   contains `git` (case-insensitive) and passes everything else — it never
   bricks unrelated shell calls.
2. **Deterministic installer script**, not model-edited JSON:
   `scripts/manage.sh assess|preflight|install|status|uninstall|verify`.
   The model's job is the conversation and the gates; the merge, backup,
   idempotency, and rollback are code.
3. **Implicit trigger is quiet.** When the skill fires because the user is
   committing (not asking for protection), it runs `status` only and, if the
   policy is absent, makes a one-line offer once per session. The full
   assess → recommend → approve workflow runs on explicit request or accepted offer.
4. **Scope-owned copy.** The handler is copied to `.claude/hooks/` (project,
   local) or `~/.claude/hooks/` (user). The test suite stays in the plugin and
   is run *against the installed copy*.
5. **Local scope stays local.** `.claude/hooks/block-no-verify.sh` and
   (if not already ignored) `.claude/settings.local.json` are added to
   `.git/info/exclude` with a marker comment; uninstall removes exactly those lines.
6. **Group identity** = any handler whose `command` references
   `block-no-verify.sh`. Install is idempotent (replaces its own group in
   place on upgrade, never duplicates); uninstall removes only that group,
   and drops `PreToolUse`/`hooks` only when our removal emptied them.
7. **Backups** `<settings>.block-no-verify-<UTC timestamp>.bak` before every
   write; restored automatically if post-install verification fails.
8. **Formatting honesty:** `jq` preserves key order and values but normalizes
   whitespace to 2-space indentation. The skill reports this.

## Policy (what the handler denies)

A `git` invocation anywhere in the command (resolved by basename, `.exe`
stripped, case-insensitive) that:

- carries `--no-verify` or an accepted abbreviation (`--no-veri…`), on any subcommand;
- carries short `-n` (alone or bundled, e.g. `-anm`) on `commit` or `am`;
- carries `--no-gpg-sign` (or `--no-gp…`) on any subcommand; `--no-sign` (or `--no-si…`) on `tag`;
- sets via `-c`/`--config`/`--config=`/`-cKEY=VAL`/`--config-env`:
  `commit.gpgsign`/`tag.gpgsign` to a falsy value (`false|no|off|0`, numeric
  zero, empty), any `core.hooksPath`, any `gpg.program`/`gpg.<fmt>.program`,
  or an `alias.*` whose expansion contains a bypass;
- runs `git config` writes that do the same persistently (`set`, legacy
  `key value`, `--add`, `--replace-all`), `--unset`/`unset` of
  `core.hooksPath` or `*.gpgsign`, or `remove-section`/`rename-section` of
  `core`/`commit`/`tag`/`gpg`;
- runs `git rebase -x/--exec <cmd>` whose `<cmd>` contains a bypass;
- is preceded (leading assignment, `env`, `export`, or a bare assignment in
  another segment; `$env:` in PowerShell) by: `HUSKY=0`,
  `HUSKY_SKIP_HOOKS`, `SKIP`, `PRE_COMMIT_ALLOW_NO_CONFIG`, `LEFTHOOK=0|false`,
  `LEFTHOOK_EXCLUDE`, `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n`
  setting a protected key, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_GLOBAL`,
  `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `HOME`, `XDG_CONFIG_HOME`.

Parsing: top-level lists (`;`, `&&`, `||`, `|`, `|&`, `&`, newlines,
subshell parentheses), single/double quotes, backslash escapes, `$(…)` and
backticks kept inside their word, comments, heredoc bodies skipped,
redirections dropped, wrappers stripped with their value-taking options
(`sudo doas env nice nohup timeout xargs command builtin noglob watch time exec stdbuf`
and shell keywords), `bash|sh|zsh|dash|ksh -c` and `pwsh|powershell -Command`
inspected one level deep, deeper nesting checked by a conservative
text heuristic. Message values (`-m`, `--message`, `-F`, `--file`, `-C`,
`-c` on commit, `--author`, `--trailer`, …) are skipped, so their text never
triggers. PowerShell payloads use PowerShell quoting (`'…'` with `''`,
`"…"` with backtick escapes, `@'…'@` here-strings).

Fail closed: unparseable JSON, non-object payloads, unterminated quotes or
heredocs, and internal errors deny with a reason. Non-shell tools and
payloads without a string `command` pass through.

## Out of scope / documented limitations

Variables and indirection (`$FLAG`), aliases and functions, `eval`, command
substitution output, scripts executed from files, `git config --edit`,
`Start-Process`, `cmd /c`, anything outside Claude's tool calls (a human's
terminal, IDE Git UIs), Cowork, and server-side controls (branch protection,
CI) — which remain the real enforcement.

## Verification

- Handler test suite (≈200 cases) under `/bin/bash` 3.2 and current bash, wired
  into `npm test` so CI runs it.
- `npm run check` (ShellCheck, shfmt, Biome, validators, `claude plugin validate --strict`).
- Installer exercised end to end on throwaway repositories: fresh install,
  re-install (idempotent), install over existing hooks, uninstall, status.
- `claude plugin eval` suite: trigger on an explicit protection request, no
  trigger on a read-only Git question.

## Changes after independent review (2026-09-18)

Three reviewers ran without access to the design rationale: an adversarial
bypass hunt, the skill reviewer, and the plugin validator. Accepted changes:

- **Claude Code's own commit form was denied** (`-m "$(cat <<'EOF' ... don't ... EOF)"`):
  `$(...)` matching is now heredoc-, comment-, and quote-aware, and unquoted
  heredocs have their substitutions parsed instead of text-matched.
- **Real bypasses closed**, each reproduced as a landed commit: arguments built
  by expansions, brace expansion, zsh `=git`, `$'\u...'` on bash 3.2, hex/space
  falsy booleans (now "deny anything not clearly true"), `commit-tree`, editor
  and pager environment variables and config keys that run commands, aliases
  of `commit` with `-n` (resolved read-only from the repository's config),
  hook-file deletion/`chmod -x`/`mv`, and hook-manager `uninstall`.
- **Latency**: 50 KB inputs took up to 385 s on bash 3.2 (a timed-out hook does
  not block). Causes: O(m^2) assignment tracking, strings copied into
  functions, and bash 3.2's quadratic `${var%%pattern}`/`${var//pattern/}`.
  Fixed with a global scan string, windowed `regexec` scans, line-based
  heredoc skipping, and a work budget with a text-only fallback. Worst case
  measured about 200 ms; typical commands about 30 ms end to end.
- **Scope refinements**: persistent `core.hooksPath` inside the repository and
  persistent `include.path` are allowed (standard setup); environment
  isolation variables are checked only on hook-running or signing subcommands.
- **Installer**: symlinked settings are written through, `CLAUDE_CONFIG_DIR` is
  honored, backups live outside the working tree, group ownership matches the
  exact command shape, the rollback text never suggests deleting a pre-existing
  settings file, and Git exclusions are written only after verification.
- **Skill**: explicit gates (scope choice is the install approval; stop on
  "nothing to protect"; not-a-repo means user scope only), a quiet incidental
  path, no file-edit fallback when the script cannot run.

Declined: pre-approving `status` with `allowed-tools` or injecting it with
`` !`...` ``. In default permission mode an injected command that is not
pre-approved aborts the whole skill, and permission-rule matching on quoted
script paths is brittle; one read-only prompt per session is the safer cost.
