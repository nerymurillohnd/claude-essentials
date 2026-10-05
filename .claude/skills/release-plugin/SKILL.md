---
name: release-plugin
description: Releases one plugin end to end - branch, changelog notes, version bump, behaviour check, signed commit, branch push and pull request, then after the merge the signed tag, its push and the GitHub Release check. Use when the maintainer asks to release, publish, bump or tag a plugin.
argument-hint: "<plugin> <major|minor|patch> <topic>  |  <plugin> tag"
arguments: [plugin, level, topic]
disable-model-invocation: true
---

# Release a plugin

`.claude/rules/releasing.md` (tag, publish, roll back) and `docs/releasing.md` (notes, bump, pull request) are the procedure and win if this skill ever differs; `plugin-versioning` decides the level. Every push, pull request and tag push stops at a permission prompt (project `permissions.ask` and the `guard-bash` hook): that prompt is the maintainer's approval for that exact action, so never route around it. This skill never merges: reviews, CI repairs and the merge belong to `/github-ops:automatic-pr-lifecycle`.

Invoked with `$plugin $level $topic`. When the second argument is `tag`, skip to Part 2.

## Part 1: prepare and open the pull request

```
- [ ] 1 Preflight     clean tree on main (or work in progress on $plugin/<topic>), gates green
- [ ] 2 Branch        $plugin/$topic from main, unless already on it
- [ ] 3 Notes         user-facing notes under ## [Unreleased]
- [ ] 4 Bump          dry run, then the bump; review git diff
- [ ] 5 Behaviour     drive the plugin in a real session
- [ ] 6 Commit        verify, signed Conventional Commit, test-install
- [ ] 7 Push branch   approval prompt
- [ ] 8 Pull request  approval prompt, semver label, then hand off
```

1. **Preflight.** If the current branch already is `$plugin/<topic>` and every uncommitted change in `git status --short` is under `plugins/$plugin/` (as `add-component` leaves it), keep that tree: skip `git switch main` and step 2, run `git fetch --prune`, and use that branch's topic. Otherwise `git status --short` must be empty; `git switch main && git pull --ff-only && git fetch --prune`. In both cases `scripts/check.py` must pass. Stop and report on any failure.
2. **Branch.** `git switch -c $plugin/$topic` (short-lived `<plugin>/<topic>` branches, deleted on merge); skipped when preflight kept an existing `$plugin/<topic>` branch.
3. **Notes.** Read `plugins/$plugin/CHANGELOG.md`. `## [Unreleased]` must describe every user-visible change in Keep a Changelog types; a MAJOR needs `### Migration`. If notes are missing, draft them from `git log main..HEAD -- plugins/$plugin` (optionally `uvx git-cliff@2.14.2 --include-path "plugins/$plugin/**" --tag-pattern "^$plugin--v" --unreleased`), rewrite them for users, and show them to the maintainer before continuing.
4. **Bump.** `scripts/bump_version.py plugin $plugin $level --dry-run`, then without `--dry-run`. Review `git diff`: the new section matches `plugin.json`, `[Unreleased]` is empty, the README badge moved.
5. **Behaviour.** `scripts/drive_plugin.py $plugin --expect '<what the change adds>'` (skill `run-marketplace`). A failure stops the release.
6. **Commit.** Run the `verify` skill, then commit with a message written to a file (a hook that parses the command line can reject multi-line quoted text, such as a heredoc with a stray apostrophe or a `<<'EOF'` inside the message): `git add plugins/$plugin README.md` and `git commit -F <file>` using `feat($plugin): …` for minor, `fix($plugin): …` for patch, `feat($plugin)!: …` with a `BREAKING CHANGE:` footer for major. Then `scripts/check.py test-install` (it tests HEAD).
7. **Push the branch.** `git push -u origin $plugin/$topic` and wait for the approval prompt.
8. **Pull request.** Fill `.github/PULL_REQUEST_TEMPLATE.md` into a body file, then `gh pr create --title "<commit subject>" --body-file <file> --label semver:$level`. After the approval, print the URL and stop with: _Run `/github-ops:automatic-pr-lifecycle <number>` to work through reviews and merge; then `/release-plugin $plugin tag`._

## Part 2: tag the merged release (`/release-plugin <plugin> tag`)

1. `git switch main && git pull --ff-only && git fetch --prune`; confirm the release commit is on `main` with `git log -1 -- plugins/$plugin`.
2. `claude plugin tag plugins/$plugin --dry-run`, then `claude plugin tag plugins/$plugin`.
3. `git tag -v $plugin--v<version>` must report a good signature; stop otherwise.
4. `git push origin $plugin--v<version>` and wait for the approval prompt.
5. `gh run watch` on the release workflow run, then `gh release view $plugin--v<version>`; report the release URL.
6. `git branch -d $plugin/<topic>` if it still exists locally.

## Roll back

Never delete, move or re-push a published tag: users may have installed it. Fix forward: revert or correct in a new `$plugin/<topic>` branch and release a PATCH (or a MAJOR with `### Migration` if users must act). To withdraw a whole plugin, follow "Deprecate or remove a plugin" in `docs/releasing.md`. The roll-back details are in `.claude/rules/releasing.md`.

## Gotchas

- `bump_version.py` refuses an empty `[Unreleased]` and a skipped version; never edit `version` by hand (the `guard-edit` hook denies it).
- A pull request carries exactly one `semver:` label, the highest bump among the plugins it releases; a new plugin needs none.
- `claude plugin tag` refuses uncommitted changes under the plugin directory and an existing tag; never pass `--force`, which skips both checks.
- Squash merges are signed by GitHub's key, so `git log --show-signature` shows them unverified locally; check with `gh api repos/nerymurillohnd/claude-essentials/commits/<sha> --jq .commit.verification`.
