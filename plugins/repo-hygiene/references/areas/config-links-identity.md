# Links, configuration and identity

Areas: G11, G12, G13. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).
Run this area **before** any `git status`, `git diff` or `git log -p` in a repository you do
not trust: those commands can run the programs this area finds.

## Contents

1. What can go wrong
2. Routine checks (G11: 1-6, G12: 7-12, G13: 13-17)
3. Deep checks
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

G11, links and outside influence:

- A symbolic link (a file that only points to another path) is **dangling**: its target is
  gone. Or it points **outside the repository** (`/etc/hosts`, `../../secrets`), so tools
  that follow links read or write outside the project. Dependency folders (`node_modules`,
  `vendor/`) often hold hundreds of links.
- `url.<base>.insteadOf` silently rewrites every matching URL: fetches and pushes go to a
  different host than the one the remote shows in the project's docs.
- `include.path` / `includeIf.<cond>.path` pull settings from another file, so the local
  `.git/config` is not the whole story.
- Global and system settings act on this repository without living in it:
  `core.excludesFile` (a global ignore file), a global `core.hooksPath`, `init.templateDir`
  (hooks copied into every new clone), credential helpers, `maintenance.repo` (background
  maintenance registered for this path), and `fetch.prune` + `fetch.pruneTags` (the next
  fetch deletes local tags that the remote lacks).
- `GIT_*` environment variables override config for every command in the session:
  `GIT_AUTHOR_NAME`, `GIT_DIR`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_COUNT`.

G12, configuration that runs programs, aliases, hooks and tool footprints:

- A config key names a program that Git runs on its own: `core.fsmonitor`,
  `core.sshCommand`, `core.pager`, `core.editor`, `sequence.editor`, `credential.helper`
  starting with `!`, `diff.<driver>.textconv` and `.command`, `merge.<driver>.driver`,
  `filter.<driver>.clean`, `.smudge` and `.process`, `sendemail.*`, `gpg.program`,
  `hook.<name>.command`, `trailer.<key>.cmd`, `tar.<format>.command`,
  `core.alternateRefsCommand`, `remote.<name>.uploadpack`.
- A plaintext secret sits in config: `sendemail.smtpPass`, a token inside a URL, an inline
  `!` credential helper that echoes a password.
- An alias starting with `!` runs a shell command (`alias.nuke = !git clean -fdx`).
- Hooks: non-sample scripts in `.git/hooks`, or a `core.hooksPath` that moves hooks to a
  tracked folder (anyone who commits there changes what runs on your machine).
- Tool footprints: husky, pre-commit, lefthook, Git LFS, git-annex, git-town,
  git-branchless, rerere (`rr-cache`, recorded conflict resolutions replayed silently).

G13, identity and signing:

- `user.name` / `user.email` differ between scopes, or the session environment overrides
  them, so commits carry an identity nobody intended.
- One person appears under several names or emails, and no `.mailmap` joins them.
- Signing is configured (`commit.gpgSign`, `gpg.format`, `user.signingKey`) but recent
  commits are unsigned, or signed commits cannot be verified because
  `gpg.ssh.allowedSignersFile` is missing.
- `Signed-off-by` or `Co-authored-by` trailers name people who are neither author nor
  committer, or are missing where the project requires them.

## Routine checks

### G11

1. **Symbolic links: count, broken, outside.** Count first, then classify.

   ```sh
   find . -path ./.git -prune -o -type l -print 2>/dev/null | wc -l
   find ./node_modules ./vendor -type l 2>/dev/null | wc -l
   ```

   Then classify every link (bounded to 100 lines; the count above stays exact):

   ```sh
   bash -c 'root=$(git rev-parse --show-toplevel); cd "$root" || exit 1
   find . -path ./.git -prune -o -type l -print 2>/dev/null | while IFS= read -r l; do
     t=$(readlink "$l")
     case $t in /*) a=$t ;; *) a=$(dirname "$l")/$t ;; esac
     d=$(cd -P "$(dirname "$a")" 2>/dev/null && pwd -P) || d="?"
     case $d/ in "$root"/*) w=inside ;; "?/") w=unresolved ;; *) w=outside ;; esac
     if [ -e "$l" ]; then s=ok; else s=broken; fi
     printf "%s\t%s\t%s\t%s\n" "$s" "$w" "$l" "$t"
   done | sort | head -n 100'
   ```

   `[observed]` on the fixture: `broken outside ./broken-link ../does-not-exist`,
   `ok outside ./outside-link /etc/hosts`, `ok inside ./node_modules/.bin/tool ../pkg/f1.js`,
   `broken outside ./node_modules/pkg/esc ../../../outside`.
   Tracked links are mode `120000` in the index:
   `git --no-optional-locks --no-pager ls-files -s | awk '$1=="120000"' | wc -l`.
   Finding: "N links, B broken, O pointing outside the project (P of them in dependency
   folders)". Explain: "a link is a signpost to another file; a broken one points nowhere,
   and one pointing outside lets tools read or write files that are not part of this
   project". Never follow a link to read its target's content.

2. **URL rewriting.**

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp \
     '^url\..*\.(insteadof|pushinsteadof)$' | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
   git ls-remote --get-url https://github.com/example/example
   ```

   `[observed]`: `local file:.git/config url.https://mirror.example.com/.insteadof
   https://github.com/`; `git ls-remote --get-url` printed the rewritten URL without any
   network access; `git remote -v` and `git remote get-url` also print the **rewritten** URL,
   while `remote.<name>.url` keeps the original. Without `pushInsteadOf`, pushes follow the
   `insteadOf` rewrite too `[doc]`. Finding: "every GitHub URL is sent to mirror.example.com".

3. **Includes.**

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp '^include(if)?\.'
   ```

   Exit 1 with no output means none `[observed]`. `includeIf` conditions are `gitdir:`,
   `gitdir/i:`, `onbranch:` and `hasconfig:remote.*.url:` `[doc]`. Report the included path
   and whether it exists; the included file's keys appear in check 7 with their origin.

4. **Global and system settings acting on this repository.**

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp \
     '^(core\.(excludesfile|attributesfile|hookspath)|init\.templatedir|maintenance\.repo|fetch\.(prune|prunetags)|remote\..*\.(prune|prunetags)|safe\.directory|include\.path|includeif\..*\.path)'
   git --no-pager config --show-scope --show-origin --get-regexp '^credential\..*helper' \
     | sed -E -e 's#^(([^[:blank:]]+[[:blank:]]+){2}credential\.[^ ]*helper) !.*#\1 !<inline shell, redacted>#' \
              -e 's#(://)[^/@[:space:]]+@#\1***@#g'
   ```

   `[observed]` on this machine: `global core.excludesfile ~/.gitignore_global`,
   `global fetch.prune true`, `global fetch.prunetags true`, `system credential.helper
   osxkeychain`; an inline helper printed as `credential.https://example.com.helper !<inline
   shell, redacted>`. Findings:
   - `fetch.prune` + `fetch.pruneTags` both true: "the next `git fetch` deletes every local
     tag the remote does not have" (list local-only tags from the tags area first).
   - `maintenance.repo` listing this path: background jobs write to this repository.
   - A global `core.hooksPath`: hooks run from a folder outside the project in every repo.
   - `init.templateDir`: hooks and excludes are copied into every new clone.

5. **Session environment.** Names only, never values:

   ```sh
   env | grep '^GIT_' | cut -d= -f1 | sort
   type git
   ```

   `[observed]` inside a Claude Code Bash tool on this machine: `GIT_AUTHOR_NAME`,
   `GIT_AUTHOR_EMAIL`, `GIT_EDITOR`, `GIT_SEQUENCE_EDITOR`, and `git is a shell function`
   from the Claude Code shell snapshot. `GIT_AUTHOR_*` beat `user.name`/`user.email`: on the
   fixture, commits made with a local `user.name Dev` were authored as the global identity
   `[observed]`. Report each variable by name and what it overrides; `GIT_DIR`,
   `GIT_WORK_TREE`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`,
   `GIT_CONFIG_COUNT` change which repository or config is read `[doc]`.

6. **Alternates** (objects borrowed from another repository): owned by
   `areas/object-store.md`; note here only that `objects/info/alternates` is outside influence.

### G12

7. **Command-executing keys, names and origins only.**

   ```sh
   git --no-pager config --list --show-scope --show-origin --name-only \
     | grep -i -E '[[:blank:]](core\.(fsmonitor|sshcommand|pager|editor|hookspath|askpass|gitproxy|alternaterefscommand)|sequence\.editor|credential\..*helper|diff\.external|diff\..*\.(textconv|command)|merge\..*\.driver|filter\..*\.(clean|smudge|process)|sendemail\.|uploadpack\.packobjectshook|protocol\..*allow|pager\.|gpg\..*program|ssh\.variant|remote\..*\.(uploadpack|receivepack|vcs)|(merge|diff)tool\..*\.cmd|interactive\.difffilter|hook\..*\.command|tar\..*\.command|trailer\..*\.(cmd|command)|include(if)?\.)'
   ```

   `[observed]`: `system file:/opt/homebrew/etc/gitconfig credential.helper` and
   `local file:.git/config core.hookspath`. Keep this pattern without a `$` end anchor: the
   `block-no-verify` guard refused the anchored form as "a command built from variables"
   `[observed]`. For each hit, report scope, origin file and key. In `deep`, print values
   through the redaction `sed` of `audit-contract.md` section 4.
   Why it matters, by key `[doc]` / `[observed]`:
   - `filter.<d>.clean` runs during `git status` whenever a tracked file's timestamp changed
     `[observed]`, even with `--no-optional-locks`.
   - `diff.<d>.textconv` runs during `git log -S`, `-G`, `-L`, `-p`, `git show <commit>` and
     `git blame` unless `--no-textconv` is given `[observed]`.
   - `core.fsmonitor` runs on every index refresh; `core.sshCommand` on every SSH fetch.
   - `gpg.program`, `gpg.ssh.program` run on `%G?`, `--show-signature` and `verify-*`.
   - `uploadpack.packObjectsHook` is honored only from protected (system, global, command)
     config `[doc]`; in `.git/config` it is inert but still a red flag.
   - `sendemail.smtpPass` is a plaintext password.

8. **Aliases that run shell commands.** Names only:

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp '^alias\.' \
     | grep -E '^[^[:blank:]]+[[:blank:]]+[^[:blank:]]+[[:blank:]]+alias\.[^ ]+ !' \
     | sed -E 's/^([^[:blank:]]+[[:blank:]]+[^[:blank:]]+[[:blank:]]+alias\.[^ ]+) .*/\1/'
   ```

   `[observed]`: `local file:.git/config alias.nuke`. Git 2.55 also accepts
   `[alias "name"] command = …` (`alias.<name>.command`) `[doc]`; the pattern catches it.
   Never run an alias. In `deep`, show the value redacted; flag destructive verbs
   (`clean -f`, `reset --hard`, `push --force`, `rm -rf`, `branch -D`).

9. **Hooks: where they live and which are active.**

   ```sh
   git rev-parse --git-path hooks
   find "$(git rev-parse --git-path hooks)" "$(git rev-parse --git-common-dir)/hooks" \
     -maxdepth 1 -type f ! -name '*.sample' -exec ls -l {} + 2>/dev/null | head -n 50
   git hook list --show-scope pre-commit
   ```

   `[observed]`: with `core.hooksPath=.hooks-alt`, `--git-path hooks` printed `.hooks-alt`;
   `git hook list pre-commit` printed `hook from hookdir` for `.hooks-alt/pre-commit`, and
   `git hook list post-checkout` printed `warning: no hooks found` and exited 1 although
   `.git/hooks/post-checkout` existed: `core.hooksPath` makes `.git/hooks` inert. A
   config-defined hook printed `local<TAB>probe` with `--show-scope` `[observed]`. To cover every
   event, loop over the event names from githooks(5) (`pre-commit`, `commit-msg`,
   `post-checkout`, `post-merge`, `pre-push`, `pre-rebase`, `post-rewrite`,
   `reference-transaction`, `pre-auto-gc`, `post-index-change`, `sendemail-validate`, …) and
   print only events that answer. `git hook list` reads; `git hook run` executes — never run it.
   Fingerprint each non-sample hook: `shasum -a 256 <path>` and `wc -c`; do not open it in
   `routine`.

10. **Hook-manager and tool footprints.** Presence only:

    ```sh
    ls -d .husky .pre-commit-config.yaml .pre-commit-config.yml lefthook.yml lefthook.yaml \
      .lefthook.yml .lefthook lefthook-local.yml .lfsconfig 2>/dev/null
    ls -d "$(git rev-parse --git-common-dir)"/{annex,branchless,lfs,rr-cache} 2>/dev/null
    git --no-pager config --show-scope --get-regexp \
      '^(rerere\.|lfs\.|filter\.lfs\.|annex\.|git-town|branchless\.|hook\.)' | cut -d' ' -f1
    git --no-pager for-each-ref --format='%(refname)' 'refs/heads/git-annex' \
      'refs/remotes/*/git-annex' 'refs/branchless'
    find "$(git rev-parse --git-common-dir)/rr-cache" -mindepth 1 -maxdepth 1 -type d \
      2>/dev/null | wc -l
    ```

    `[observed]`: `global rerere.enabled`, `global rerere.autoupdate`, and one `rr-cache`
    entry. Git LFS: run `git lfs env` and `git lfs ls-files` only when
    `command -v git-lfs` succeeds (see `commands/git-lfs.md`). `rerere.autoUpdate=true`
    stages recorded resolutions without review; never `cat` an `rr-cache` preimage
    (`audit-contract.md` section 4).

11. **Plaintext secrets in config.** Key names only, from check 7 plus:

    ```sh
    git --no-pager config --list --show-scope --show-origin --name-only \
      | grep -i -E '(pass|token|secret|key|auth|cred)' | head -n 50
    git --no-pager config --list --show-scope --show-origin \
      | grep -c -E '://[^/@[:space:]]+@'
    ```

    The second command prints only a count of URLs with embedded credentials.

12. **Command-line guard interplay.** When a guard such as `block-no-verify` refuses a read,
    rewrite it without variables in `git` words; never bypass the guard.

### G13

13. **Configured identity per scope.**

    ```sh
    git --no-pager config --show-scope --show-origin --get-regexp \
      '^(user\.(name|email|signingkey|useconfigonly)|author\.|committer\.|gpg\.|commit\.gpgsign|tag\.gpgsign)' \
      | sed -E 's#^(([^[:blank:]]+[[:blank:]]+){2}user\.signingkey) .*#\1 <redacted>#I'
    ```

    `[observed]`: `global user.name Nery …` and `local user.name Dev` both present; the local
    one wins in config, but `GIT_AUTHOR_*` (check 5) beat both.

14. **Recent identities, raw and mapped.** Always pass a revision to `shortlog`:

    ```sh
    git --no-replace-objects --no-pager shortlog -s -n -e --all | head -n 30
    git --no-replace-objects --no-pager shortlog -s -n -e -c --all | head -n 30
    git --no-replace-objects --no-pager log --all --max-count=500 \
      --format='%an <%ae>|%cn <%ce>' | sort | uniq -c | sort -rn | head -n 30
    ```

    `[observed]`: `shortlog` with no revision and a non-terminal stdin reads stdin and prints
    nothing (a false "no authors"); `shortlog` always applies `.mailmap` and rejects
    `--no-mailmap`; `log --format=%an/%ae` shows the raw identity while `%aN/%aE` apply the
    mailmap. Finding: the same person under several emails, `Dev Old <dev@old.example>` vs
    `Dev <dev@example.com>`, or a config identity that no recent commit uses.

15. **Mailmap.**

    ```sh
    git --no-pager config --show-scope --get-regexp '^mailmap\.'
    git ls-files --error-unmatch .mailmap 2>/dev/null
    git check-mailmap 'Dev Old <dev@old.example>'
    ```

    `[observed]`: with `Dev <dev@example.com> Dev Old <dev@old.example>` in `.mailmap`,
    `check-mailmap` printed `Dev <dev@example.com>`; an unknown contact is echoed unchanged.

16. **Signature status of recent commits, without running any program.**

    ```sh
    git --no-replace-objects rev-list --max-count=50 --header HEAD \
      | tr '\0' '\n' | grep -c -E '^gpgsig'
    ```

    `[observed]` this counts signature headers (1 of 2 on a fixture with one SSH-signed
    commit) without calling `gpg` or `ssh-keygen`. Verifying (`%G?`, `verify-commit`) runs
    `gpg.program` / `gpg.ssh.program` `[doc]`: do it only after check 7 shows those keys unset
    or pointing at the standard binaries.

    ```sh
    git --no-replace-objects --no-pager log --max-count=50 --format='%G? %h %ae' \
      | cut -c1 | sort | uniq -c
    ```

    `[observed]`: an SSH-signed commit shows `N` (as if unsigned) plus
    `error: gpg.ssh.allowedSignersFile needs to be configured` when that file is missing, and
    `G` once it exists. `%G?` letters `[doc]`: `G` good, `B` bad, `U` good but unknown
    validity, `X` expired signature, `Y` good by expired key, `R` revoked key, `E` cannot be
    checked, `N` none.

17. **Trailers.**

    ```sh
    git --no-replace-objects --no-pager log --max-count=200 --format='%(trailers:only,unfold)' \
      | grep -v '^$' | sed -E 's/:.*//' | sort | uniq -c
    git --no-replace-objects --no-pager log --max-count=200 \
      --format='%h%x09%ae%x09%ce%x09%(trailers:key=Signed-off-by,valueonly,separator=%x2C)'
    ```

    `[observed]`: a commit committed by `Dev` carried `Signed-off-by: Someone Else …`.
    Finding: sign-offs that match neither author nor committer, or a mix of
    `Co-authored-by` spellings (`Co-Authored-By`). For one message,
    `git log -1 --format=%B <commit> | git interpret-trailers --parse` lists its trailers
    `[observed]`.

## Deep checks

1. **Every key in every scope, with provenance, redacted** (the contract's command):

   ```sh
   git --no-pager config --list --show-origin --show-scope \
     | sed -E -e 's#(://)[^/@[:space:]]+@#\1***@#g' \
              -e 's#^([^=]*(pass|token|secret|key|auth|cred)[^=]*=).*#\1***#I'
   ```

   Save the full output to the evidence package; report key counts per scope and every
   executing key's value. Read included files by path (they are config, not secrets) with
   `git config --file <path> --list --name-only`.
2. **Hook contents.** Read (never run) each non-sample hook and each `hook.<name>.command`
   target. Identify the manager by markers: `husky`, `pre-commit` ("File generated by
   pre-commit"), `lefthook`, `git lfs`, `gitleaks`, `talisman`. Report what each hook does in
   one sentence, and whether it calls the network, modifies files, or can be skipped.
3. **Tool state directories.** Sizes only: `du -sh "$(git rev-parse --git-common-dir)"/{lfs,annex,branchless,rr-cache} 2>/dev/null`.
   With `git-lfs` installed: `git lfs env | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'`,
   `git lfs ls-files --all --size | head -n 50`, `git lfs fsck --dry-run` when supported.
4. **Full identity history.** Checks 14 and 17 without `--max-count`, grouped by year:
   `git --no-replace-objects --no-pager log --all --format='%ad %ae' --date=format:%Y | sort | uniq -c`.
5. **Signing coverage per protected branch.** For the default branch and each release tag:
   the `gpgsig` count vs commit count (check 16 without `--max-count`), then `%G?` only when
   check 7 cleared the signing programs.
6. **Links in history.** Links committed then deleted:
   `git --no-replace-objects --no-pager log --all --no-textconv --diff-filter=A --format='%h' --raw | grep -c ' 120000 '`.

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| Broken link in the working tree, untracked | `rm -- broken-link` | Recreate: `ln -s ../does-not-exist broken-link` | That one path |
| Tracked link pointing outside | `git rm -- outside-link` then commit | `git revert <commit>` | Index and one commit |
| Unwanted `insteadOf` rewrite | `git config --local --unset url.https://mirror.example.com/.insteadof` | `git config --local url.https://mirror.example.com/.insteadOf https://github.com/` | Local scope only; global scope is a separate item |
| `fetch.prune`+`fetch.pruneTags` would drop local tags | Push or archive local-only tags first, then `git config --local fetch.pruneTags false` | `git config --local --unset fetch.pruneTags` | Local scope only; never edits the user's global config unless named |
| Dangerous alias | `git config --local --unset alias.nuke` | `git config --local alias.nuke '!git clean -fdx'` | That alias only |
| `core.hooksPath` to an unexpected folder | `git config --local --unset core.hookspath` | `git config --local core.hooksPath .hooks-alt` | Local key only; hook files untouched |
| Non-sample hook not wanted | `mv .git/hooks/post-checkout <evidence-dir>/post-checkout` | `mv <evidence-dir>/post-checkout .git/hooks/post-checkout` | That file |
| Plaintext `sendemail.smtpPass` | Rotate the password first, then `git config --global --unset sendemail.smtppass` | irreversible for the old secret (rotation) | Named scope and key |
| Repository registered for maintenance by mistake | `git maintenance unregister` | `git maintenance register` | This repository's registration |
| Inconsistent identity | `git config --local user.email dev@example.com` | `git config --local --unset user.email` | Local scope; history untouched |
| Several identities per person | Add a `.mailmap` line and commit it | `git revert <commit>` | One new tracked file |
| SSH signatures show `N` | `git config --local gpg.ssh.allowedSignersFile .github/allowed_signers` (file must exist) | `git config --local --unset gpg.ssh.allowedSignersFile` | Local key only |

Rewriting identities or sign-offs in existing commits is a history rewrite: route it to the
runbook in `areas/history-and-secrets.md` and never bundle it with the items above.

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| A link pointing outside | A problem: `node_modules/.bin` links, pnpm stores and monorepo workspaces do this by design; classify, do not delete |
| A broken link in `node_modules` | A repository defect: dependency folders are regenerated |
| A `.git/hooks/<name>` file without `.sample` | An active hook: with `core.hooksPath` set, `.git/hooks` is ignored `[observed]` |
| `credential.helper` in system scope | A leak: `osxkeychain` from Homebrew's `gitconfig` is normal |
| `%G?` = `N` | Unsigned: an SSH signature shows `N` when `allowedSignersFile` is missing `[observed]` |
| Empty `shortlog` output | No authors: `shortlog` read stdin because no revision was given `[observed]` |
| `GIT_AUTHOR_NAME` in the session | A repository setting: it comes from the shell or the agent harness |
| `git remote -v` URL | The configured URL: `insteadOf` rewrites what it shows `[observed]` |

## Version floors

| Feature | Floor |
| --- | --- |
| `config --show-origin` | 2.8 `[doc]` RelNotes 2.8.0 |
| `config --show-scope` | 2.26 `[doc]` RelNotes 2.26.0 |
| `includeIf` | 2.13 `[doc]` RelNotes 2.13.0 |
| `fetch.pruneTags` | 2.17 `[doc]` RelNotes 2.17.0 |
| `git maintenance` (`maintenance.repo`) | 2.29 `[doc]` RelNotes 2.29.0 |
| SSH signing (`gpg.format ssh`) | 2.34 `[doc]` RelNotes 2.34.0 |
| `git config list/get/set` subcommands | 2.46 `[doc]` (older Git: `--list`, `--get`) |
| Config-defined hooks (`hook.<name>.command`) | 2.54 `[doc]` RelNotes 2.54.0 |
| `git hook list --show-scope`, `alias.<name>.command` | present in 2.55 `[observed]`/`[doc]` |
| `git check-mailmap` | 1.8.4 `[doc]` RelNotes 1.8.4 |
| `interpret-trailers --parse` | 2.15 `[doc]` RelNotes 2.15.0 |

## Sources

- https://git-scm.com/docs/git-config (scopes, protected configuration, conditional
  includes, `url.<base>.insteadOf`, `alias.*`, every executing key)
- https://git-scm.com/docs/git#_security and https://git-scm.com/docs/git#_environment_variables
- https://git-scm.com/docs/git-hook and https://git-scm.com/docs/githooks
- https://git-scm.com/docs/git-credential and https://git-scm.com/doc/credential-helpers
- https://git-scm.com/docs/git-check-mailmap and https://git-scm.com/docs/gitmailmap
- https://git-scm.com/docs/git-shortlog, https://git-scm.com/docs/git-log (`%G?`, trailers)
- https://git-scm.com/docs/git-interpret-trailers, https://git-scm.com/docs/git-verify-commit
- Git release notes, `Documentation/RelNotes/*.adoc` in https://github.com/git/git
- Corpus: `commands/git-config.md`, `commands/git-hook.md`, `commands/git-credential.md`,
  `commands/git-check-mailmap.md`, `commands/git-shortlog.md`,
  `commands/git-interpret-trailers.md`, `commands/git-verify-commit.md`, `commands/git-lfs.md`
