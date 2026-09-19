# Plugin delivery

How a plugin change goes from idea to a tagged version on `main` without the
rework loops seen while shipping `block-no-verify` 0.1.0–0.1.1 (three review
rounds, stale eval numbers, a recreated merged branch, a stuck tag). These are
working rules; the mechanical parts are already enforced by `npm run check`,
the version-check job, and the hooks in `.claude/settings.json`: the push guard
denies pushes to a merged branch, and `/pr-delivery` enforces the definition of
done below with a checklist.

## Design before building

- Derive the component set (skills, agents, hooks, MCP, LSP, monitors, settings)
  from the goal and the live docs in CLAUDE.md's reference table. Propose it with
  a one-line justification per component and build only after the maintainer
  approves it.
- Write the plugin's non-goals and failure modes (missing dependency, timeout,
  unsupported surface) into the design before any code. They become the README's
  **What it does not do** and **Limitations**, not an afterthought.

## Review continuously, not at the end

- Run `/plugin-release-review <id>` on the first complete draft, not only before
  the PR. Re-run it after every change that touches runtime files, the README,
  or `plugin.json`. One review pass that finds everything beats three that find
  it in pieces.
- Run the plugin's own `test-*.sh` suite and `npm run check` after each change,
  not in a batch before committing.
- A finding is closed only when it is fixed **and** a gate exists that would
  catch it next time (validator rule, test, or a row in the review skill's
  references). Record the gap in `docs/maintenance/`.

## Shell scripts shipped in plugins

- They run on whatever Bash the user has. `#!/usr/bin/env bash` picks the first
  `bash` on `PATH`, which on a stock Mac without Homebrew is `/bin/bash` 3.2, and
  hooks invoked as `bash script.sh` do the same. `npm test` runs every suite under
  both `bash` and `/bin/bash`; keep it that way.
- Hooks sit in the hot path of every matching tool call. Time them against large
  adversarial inputs (long commands, heredocs, deep nesting) under `/bin/bash`
  3.2. Avoid constructs that go quadratic there: `${var%%pat}`, `${var//pat/}`,
  and `${var##*/}` on long strings, and passing large strings as function arguments.
- Test every degraded-mode claim ("if jq is missing, only X is denied") with the
  dependency removed and a realistic full hook payload (`cwd`, `transcript_path`,
  `session_id`), not only the field you expect to matter.
- A function that must exit the hook (deny, fail) can't run inside `$(...)`,
  because it only exits the subshell. Return through globals instead.
- Pass large test data through stdin or a file, never as one argument: Linux
  caps a single argument at 128 KB (`MAX_ARG_STRLEN`) and macOS doesn't, so a
  test that builds a 250 KB payload with `jq --arg` gets an empty payload on
  the CI runner and passes without testing anything. Assert that the payload
  was built before asserting on the hook's answer.

## Edits and evidence

- Prefer the Edit tool for exact replacements. After any scripted edit (`sed`,
  `perl`, `python`, heredoc), confirm it landed with `git diff` before moving on;
  a replacement that matches nothing fails silently.
- After writing files that contain escape sequences (`\u0000`, `\t`, regexes),
  check the bytes on disk. A tool may have turned an escape into a literal
  control character.
- Report something as done only with evidence from the current state: command
  output, a check run, or a GitHub read. Nothing is done because it was done
  earlier in the session.

## Numbers stay current

- Any change to a skill's `description`, its instructions, or `evals/` re-runs
  `claude plugin eval` in the **same branch**, and the README eval table is
  updated before the PR opens. The same applies to test counts and timings
  quoted in the README or CHANGELOG.

## Pull requests and branches

- Use the GitHub MCP server for every GitHub read and mutation it supports
  (PRs, checks, reviews, labels, tags, merge). Use `gh` only for what it lacks:
  Actions logs, runs and reruns, ruleset and merge-method policy, and deleting refs.
- Only a change that alters a plugin's behavior (a version bump) goes through a
  PR. Everything else (docs, READMEs, root files, tooling) is committed on
  `main` and pushed directly when the maintainer says "commit and push";
  `guard-push.sh` runs the checks before the push. Open a PR only when the change
  bumps a version or the maintainer says "PR".
- Once a PR is merged, its branch is closed. Never push to it again: pushing
  recreates the deleted remote branch with commits `main` doesn't have. Follow-up
  work starts from a fresh branch off the updated `main`.
- Everything that belongs to a change ships in its PR. If something is found
  after merge, it gets its own PR in the same session, not a push to the old branch.

## Tagging

- Tags `<id>--vX.Y.Z` come only from the `Tag plugin versions` workflow
  (ADR-0003). Never create or push them by hand.
- If the workflow fails pushing the tag with `remote: fatal error in commit_refs`,
  reruns repeat the failure. Dispatch a fresh run instead
  (`gh workflow run tag-versions.yml --ref main`); the script is idempotent.

## Definition of done

A plugin change is done only when all of these are verified, not assumed.
`/pr-delivery` holds them as a checklist whose Stop hook re-checks items 3, 5,
and 6 against the real remote:

1. The PR is merged, and GitHub reports the authorized head SHA as merged.
2. CI and `Tag plugin versions` are green on the merge commit in `main`.
3. For a runtime change, the new `<id>--vX.Y.Z` tag exists on the remote and
   points at the merge commit.
4. The README (eval table, numbers, Compatibility dates), CHANGELOG, root
   catalog row, and `marketplace.json` all match what shipped.
5. The feature branch is deleted locally and on the remote. `git branch -a` shows
   no leftover branches for the change.
6. Local `main` equals `origin/main`, and the working tree is clean.
