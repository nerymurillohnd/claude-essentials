# Publishing checklist

Run these steps **only after the maintainer explicitly approves publication**. Until then the repository stays local with no remote.

## 1. Create the remote and push

```bash
gh repo create nerymurillohnd/claude-essentials --public \
  --description "Community plugins for Claude Code. Not affiliated with or endorsed by Anthropic." \
  --homepage "https://github.com/nerymurillohnd/claude-essentials"
git remote add origin https://github.com/nerymurillohnd/claude-essentials.git
git push -u origin main
```

## 2. Repository settings

- [ ] Topics: `claude-code`, `plugin-marketplace`, `skills`, `mcp`, `agents`. Never use an official marketplace name, such as a reserved name from the marketplace reference, as a topic.
- [ ] Features: Issues on; Wiki off; Discussions optional.
- [ ] Pull requests: squash merging only, default commit message "Pull request title", delete head branches automatically.
- [ ] Security: enable private vulnerability reporting, secret scanning and push protection.
- [ ] Moderation: enable content reporting to repository maintainers (the Code of Conduct relies on it).
- [ ] Actions: allow GitHub-owned actions plus `astral-sh/setup-uv`, `crazy-max/ghaction-github-labeler`; require SHA pinning if the setting is available; default `GITHUB_TOKEN` permissions read-only.

## 3. Protect `main`

Ruleset for `main`:

- [ ] Require a pull request with one approval and code owner review.
- [ ] Require status checks: `Gates and isolated install test` and `Commit convention and release discipline`.
- [ ] Require signed commits and linear history; block force pushes and deletion.
- [ ] Tag ruleset for `*--v*`: restrict creation to maintainers and require signed tags.

## 4. Labels

```bash
gh workflow run labels.yml
```

Then confirm the labels match `.github/labels.yml` and the default GitHub labels are gone.

## 5. Community profile

- [ ] Open **Insights → Community standards** and confirm README, Code of Conduct, Contributing, License, Security policy, issue templates and pull request template are detected.

## 6. Verify the published marketplace like a user

In a throwaway configuration, never in the maintainer's own:

```bash
export HOME="$(mktemp -d)" CLAUDE_CONFIG_DIR="$HOME/.claude"
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install hello-example@claude-essentials
claude plugin list --json
```

## 7. First release dry run

```bash
python3 scripts/bump_version.py plugin hello-example patch --dry-run
python3 scripts/bump_version.py marketplace patch --dry-run
```

Confirm the previewed changelogs, then decide whether to tag `marketplace--v0.1.0` and `hello-example--v0.1.0` for the initial versions with `git tag -a` and `claude plugin tag plugins/hello-example`, and push the tags. The release workflow publishes the GitHub Releases.

## 8. After publishing

- [ ] Decide the scheduled Claude Code release watcher (deferred in the sourcing log).
- [ ] Reconsider Dependabot for GitHub Actions, so SHA pins stay current.
- [ ] Plan the first real plugin and the removal of `hello-example`.
