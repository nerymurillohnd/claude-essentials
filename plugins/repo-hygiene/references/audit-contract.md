# Audit contract

Both skills follow this contract. It defines what may run without approval, how commands are
written, how secrets are handled, what a finding and a recommendation contain, and how an
approved item is executed. The report layout is in `report-template.md`; the area checklists
are in `areas/`.

## Contents

1. Authority: read freely, mutate by approval
2. Audit safety
3. Command form
4. Secrets
5. Findings
6. Recommendations
7. The approval gate
8. Executing an approved item
9. False-positive catalogue
10. Evidence package
11. Transient errors

## 1. Authority: read freely, mutate by approval

- Every command that only reads is already authorized. Run it; asking before a read is a
  defect. Reads include `git ls-remote`, provider API and MCP reads, and listing files by name,
  size and type.
- A command needs an approved item ID when it changes a ref, the index, the working tree, the
  object store, Git config, a remote, the hosting provider, or anything outside the repository.
- These look like reads but write, so each is an item:
  - `git fetch` moves remote-tracking refs and can start auto-maintenance. Even
    `git fetch --dry-run` downloads objects (`[observed]`); use `git ls-remote` to compare.
  - `git push --dry-run` runs the `pre-push` hook (`[observed]`); never use it to inspect.
  - `git describe --dirty` rewrites `.git/index` even with `--no-optional-locks`
    (`[observed]`).
  - `git bisect start` checks out commits.
  - `git fsck --lost-found` writes `.git/lost-found/`.
  - `git stash` without a subcommand pushes a stash.
  - `git worktree prune` without `--dry-run`.
  - `git merge-tree --write-tree` and `git commit-tree` write objects. Run them only after
    the unreachable census (section 2).
- A general request ("clean it up", "límpialo", "fix everything") never approves a plan.
  Approval names item IDs.

## 2. Audit safety

- Run porcelain reads as `git -c core.fsmonitor=false --no-optional-locks --no-pager …`, in
  both skills. `--no-optional-locks` stops `git status` from refreshing the index, and
  `core.fsmonitor=false` stops it from running a configured FSMonitor hook program (`[doc]`
  git-config).
- In a partial clone (`git config --get remote.origin.promisor` is `true`, or
  `extensions.partialClone` is set), a read of a missing object downloads it. `[observed]`:
  `git ls-tree -r -l` fetched 2 missing blobs. Add `--no-lazy-fetch` (Git ≥ 2.45) to every
  read there. A missing object then shows as missing, and fetching it is an approved item.
- Pass `--no-ext-diff` to `git diff`, `git log -p` and `git show`, because `diff.external`
  runs a configured program for patch output (`[observed]`).
- Run every count, log and history walk as `git --no-replace-objects <command> …`. It is a
  **global option**: it goes before the subcommand. `git log --no-replace-objects` fails with
  "unrecognized argument" (`[observed]`). A replace ref changes what `log`, `rev-list`,
  `for-each-ref %(ahead-behind:…)` and `bisect` see. `[observed]`: with a replace ref active,
  `rev-list --left-right --count origin/main...main` reported `0 4` where the true value was
  `0 5`. For commands that start other Git processes (`git bisect run`), export
  `GIT_NO_REPLACE_OBJECTS=1` for that command instead.
- Pass `--no-textconv` to `git log` (`-p`, `-S`, `-G`, `-L`), `git show` and `git blame`, and
  `--no-ext-diff` wherever it applies. A configured `diff.<driver>.textconv` runs **by
  default** for these (`[observed]`).
- Check the command-executing config keys (`areas/config-links-identity.md`, G12) **before**
  the first `git status`: `git status` runs `filter.<driver>.clean` on changed tracked files,
  even with `--no-optional-locks` (`[observed]`). If a filter, fsmonitor or textconv driver is
  configured, say so, and keep every later command away from what would run it.
- Never run a command that executes configured programs while auditing:
  - `git grep --textconv`, `git grep -O`, `git diff --ext-diff`, `git difftool`,
    `git mergetool`;
  - any alias;
  - any hook.

  Git's documentation warns that an untrusted repository's config and hooks run arbitrary
  commands (https://git-scm.com/docs/git#_security).
- In `deep`, before anything else, check trust. Run `stat -f %Su .git 2>/dev/null ||
  stat -c %U .git` and compare the owner with `id -un`, then list the command-executing
  config keys (see `areas/config-links-identity.md`). For a repository that is not the user's
  own, stop and recommend `git clone --no-local <path> <new-path>` first.
- Never add `-c safe.directory=…`. It disables the ownership protection.
- In `deep`, also add `-c gc.auto=0 -c maintenance.auto=false` to every inspection.
- Order in `deep`, because later steps write objects:
  1. ref snapshot to the evidence package;
  2. reflogs;
  3. the unreachable census, with and without reflog roots;
  4. integrity;
  5. anything that writes objects.
- Bound every listing so the context never floods:
  - `--directory` on ignored and untracked listings;
  - counts before lists;
  - `head -n N` on long output.

  Totals are always exact, even when a listing is cut, and the report says when output was
  cut.

## 3. Command form

These rules follow https://git-scm.com/docs/gitcli.

- Put revisions before paths, and `--` after revisions: `git log -1 main --`.
- Put `--end-of-options` before any revision taken from repository data or user input
  (Git ≥ 2.24): `git rev-parse --verify --end-of-options "$name^{commit}"`.
- Split short options (`-a -b`, never `-ab`). Use the stuck form for option arguments
  (`--format=…`). Spell long options out in full.
- Quote pathspec globs so Git expands them, not the shell.
- Parse only stable machine formats: `--porcelain`, `for-each-ref --format=…`, `-z`. Never
  parse human output.
- Write every mutating command literally, one per call, with the exact ref, SHA or path. No
  `$(…)`, no variables, no loops. The user's permission prompt and guards such as
  `block-no-verify` must be able to read it.
- Prefer literal commands for reads too. Guards such as `block-no-verify` also refuse
  read-only Git commands built from variables (`[observed]`: `git var $v` and a
  `-c core.hooksPath` probe were refused). When a read loop is refused, run the reads one by
  one with literal arguments. Never rephrase the command to get past the guard.

## 4. Secrets

- Never read a secret-shaped file with `cat`, `grep`, `diff`, `--textconv`, `git show`,
  `git grep` or a pager. Secret-shaped means:
  - `.env*` (except `*.example`, `*.sample`, `*.template`);
  - `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_*`;
  - `credentials*`, `.npmrc`, `.pypirc`, `.netrc`, `*.tfvars`, `.dev.vars`.

  Report path, size, ignore rule, and whether it is tracked.
- Redact in the same command that prints. Never print raw and redact later: the tool output
  already holds the secret.

  ```sh
  git --no-pager remote -v | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
  git --no-pager config --list --show-origin --show-scope \
    | sed -E -e 's#(://)[^/@[:space:]]+@#\1***@#g' \
             -e 's#^([^=]*(pass|token|secret|key|auth|cred)[^=]*=).*#\1***#I'
  ```

  `[observed]`: without the `sed`, `git remote -v` printed a URL of the form `https://user:<token>@…` with the token in clear.
- History searches print the commit and path (`--name-only`), never patch lines. Report a
  secret as: commit, path, pattern class, and whether it is still in the current tree.
- Always pass `--name-status` (or `--stat`) to `git stash show`. With `stash.showPatch=true`
  a bare `git stash show` prints file contents (`[observed]`).
- Fingerprint files with `git hash-object --stdin <file`, or add `--no-filters` to the path
  form. `git hash-object -- <path>` applies the path's clean filter, which runs a configured
  program.
- Never `cat` an unknown payload: `lost-found` files, `rr-cache` preimages, dangling blobs.
  Fingerprint it instead with `git hash-object --stdin <file` (no `-w`), `wc -c`, and
  `file -b`.
- Protect secret-shaped paths in `git clean -X` with a **negated** exclude:
  `-e '!.env'`. `[observed]`: `-e '!.env'` keeps `.env`, while `-e .env` does not, because
  under `-X` an `-e` pattern adds an ignore rule.
- Run scanners with redaction and no live verification:
  - `gitleaks git --redact`;
  - `trufflehog git file://. --no-verification --json`, piped through `jq` so that only the
    detector name, file, commit and line leave the command. trufflehog has no redaction flag
    and prints the raw secret otherwise. Without `jq`, do not run it.

## 5. Findings

Every finding has:

- a stable ID (`F1`, `F2`, …);
- what it is, in plain words;
- why it matters for this repository;
- evidence: the command and its trimmed output;
- confidence: `proven`, `likely` or `unknown`;
- the consequence of doing nothing;
- the **root cause** when a setting, rule or habit produces it. Findings with one root cause
  are grouped under it.

Explain every Git term in plain words the first time it appears: upstream, reflog, dangling
commit, squash merge, worktree, replace ref. Commands and SHAs are evidence, never the
explanation.

## 6. Recommendations

Write every recommendation in full sentences, never as a bare command. Each one states:

1. the ID (`R1`, `R2`, …) and the findings it closes;
2. what was found and where, and why it is a problem here;
3. what the action does, step by step;
4. what changes, and what stays exactly as it is;
5. the risk, and who else it affects (collaborators, open PRs, CI, forks, deployments);
6. the preconditions, re-checked right before execution;
7. the literal command(s);
8. how to undo it, with the exact recovery command, or the word **irreversible**;
9. what happens if the user does nothing;
10. the approval scope: what approving this ID authorizes, and what it does not ("R3
    authorizes only the tag `archive/naming-wip`; no stash `pop`, `apply` or `drop`").

When more than one reasonable action exists, list the alternatives with the recommended one
first and why.

Order the recommendations by priority:

1. protect work;
2. remove risk;
3. fix the root cause;
4. fix drift;
5. reduce noise.

Preservation items (archive tags, recovery refs, verified backups) come before any removal
that depends on them. Items kept on purpose go to "Retain", each with its **exit condition**:
the evidence that would make removal safe.

## 7. The approval gate

- Present the whole report once, after the coverage is complete: every finding, every
  recommendation, and one approval request ("Approve R2 and R5; keep R3?").
- Never drip-feed recommendations across turns, and never cut a list with "and more".
- Discussing and changing the plan before approval is part of the cycle.
- A rejected item stays untouched, and so does any item that depends on it.

## 8. Executing an approved item

For each approved ID, in the order given:

1. Re-run its evidence command. If the target, SHA or path changed, stop that item, report
   the drift, and ask again.
2. Record the pre-state: `git rev-parse` of every ref it touches, or the path list.
3. Run the literal command.
4. Verify the result with a read.
5. Report the command, its output, the new state, and the recovery command.

If a permission prompt is denied, mark the item `declined` and skip everything that depends
on it.

## 9. False-positive catalogue

Check every finding against this list before writing it:

| It looks like | It is not proof of |
| --- | --- |
| Clean checkout | No stash, no unreachable work |
| Clean `git status` | No local edits (assume-unchanged, skip-worktree and broken `.git` files hide them) |
| `git check-ignore -v` exits 0 | The path is ignored (a negated rule matches with exit 0) |
| No open PR | No unresolved review conversation |
| Closed without merge | Missing or lost source |
| Unreachable object | Garbage |
| Review thread marked outdated | Fixed |
| Access denied, 403, 404 | Absence |
| A `lost-found` file name | A recoverable object |
| `[gone]` upstream | Merged |
| Empty three-dot diff | Equal endpoints |
| Ignored path | Disposable path |
| `garbage: 0` in `count-objects` | Nothing unreachable |
| Provider state "fixed" | Independently verified fix |
| Branch not an ancestor of main | Unmerged content (it may be squash-merged) |
| `git cherry` shows `+` | Content missing from main |
| Commit subject "WIP on …" | Proof of which tool made it |

## 10. Evidence package

- Full enumerations go to files, never truncated: every PR, thread ID, alert, ref,
  unreachable ID, lost-found name and stash path.
- Default location: `${TMPDIR:-/tmp}/repo-hygiene/<repository-name>-<UTC timestamp>/`,
  created with `mkdir -m 700`. Announce it in the report.
- Copying records into the repository is an approved item, unless the project's CLAUDE.md or
  AGENTS.md defines where audit records go. In that case, follow that convention and say so.
- Save each command's exit code with its output.
- When the audit corrects itself, add a dated verification amendment at the top of the
  report.

## 11. Transient errors

Retry timeouts and rate limits up to three times, with increasing waits, and report each
retry. After the last failure, mark the row `blocked` with the command and the error.
