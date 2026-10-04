# Publishing checklist

The repository was published on 2026-10-04 at https://github.com/nerymurillohnd/claude-essentials. This file records how each setting was applied, so it can be checked or repeated; unchecked items are still open.

## 1. Create the remote and push

- [x] Public repository created with `gh repo create nerymurillohnd/claude-essentials --public --description "…"`, `origin` added and `main` pushed.

## 2. Repository settings

- [x] Topics: `claude-code`, `plugin-marketplace`, `skills`, `mcp`, `agents`. Never use an official marketplace name, such as a reserved name from the marketplace reference, as a topic.
- [x] Features: Issues on; Wiki and Projects off.
- [x] Pull requests: squash merging only (title and body of the pull request), delete head branches automatically.
- [x] Security: private vulnerability reporting, secret scanning and push protection on. Dependabot security updates are on by GitHub's default for public repositories; Dependabot version updates stay deferred.
- [x] Moderation: "Reported content" to maintainers exists only for organization-owned repositories, so it does not apply here; the Code of Conduct sends reports to the maintainer's contact details. Interaction limits and code review limits stay off and can be turned on temporarily if a discussion gets out of hand.
- [x] Actions: GitHub-owned actions plus `astral-sh/setup-uv` and `crazy-max/ghaction-github-labeler` only, SHA pinning required, default `GITHUB_TOKEN` permissions read-only, Actions cannot approve pull requests.

## 3. Protect `main`

- [x] Ruleset `main: signed commits` on the default branch: signed commits, linear history, no force pushes, no deletion. No bypass.
- [x] Ruleset `release tags` on `refs/tags/*--v*`: only admins create, update or delete them, and the tagged commit must be signed. Rulesets cannot require a signed tag object; `git tag -v` verifies it.
- [ ] Required pull request reviews and status checks (`Gates and isolated install test`, `Commit convention and release discipline`) once there are other contributors; with a single maintainer they would block direct pushes the release policy allows.

## 4. Labels

- [x] `gh workflow run labels.yml` synced the labels; the remote labels equal `.github/labels.yml` and the GitHub defaults are gone. Labels used by the issue forms were checked on a test issue, which was then deleted.

## 5. Community profile

- [x] **Insights → Community standards** reports 100 %: README, Code of Conduct, Contributing, License, Security policy and pull request template.
- [ ] Confirm in the browser that `/issues/new/choose` lists the three issue forms and the three contact links (the API reported the contact links; forms are only visible signed in).

## 6. Verify the published marketplace like a user

- [x] In a throwaway configuration, never in the maintainer's own, `claude plugin marketplace add nerymurillohnd/claude-essentials` and `claude plugin install hello-example@claude-essentials` installed version 0.1.0; the real configuration was unchanged.

```bash
export HOME="$(mktemp -d)" CLAUDE_CONFIG_DIR="$HOME/.claude"
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install hello-example@claude-essentials
claude plugin list --json
```

## 7. First release

- [x] Pull request #2 released `hello-example` 0.1.1 (its own `LICENSE`); after the squash merge, `claude plugin tag plugins/hello-example` created the signed `hello-example--v0.1.1`, and the release workflow published the GitHub Release from its changelog section. 0.1.0 stays untagged. The catalog has no version and no tag.

## 8. After publishing

- [ ] Decide the scheduled Claude Code release watcher (deferred in the sourcing log).
- [ ] Reconsider Dependabot version updates for GitHub Actions, so SHA pins stay current.
- [ ] Plan the first real plugin and the removal of `hello-example`.
