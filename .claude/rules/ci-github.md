---
paths:
  - ".github/**"
  - "scripts/check_pr.py"
  - "scripts/check_commit_msg.py"
---

# CI and GitHub

- The workflows are validate, pull-request, release, labels, labeler, claude-code-review and claude (ADR claude-github-action).
- `claude-code-review` reviews every push with a repository-specific prompt and re-checks earlier findings; `claude` answers `@claude` from users with write access only. Both use the `CLAUDE_CODE_OAUTH_TOKEN` secret.
- `claude-code-action` skips, with a green check, when the workflow file in a pull request differs from the default branch (observed 2026-10-04: "The workflow file must exist and have identical content to the version on the repository's default branch"); a pull request that changes these workflows is never reviewed by them.
- `claude-code-action` loads the repository's project settings by default (`settingSources` is user, project and local), including the base branch's `.claude/settings.json`. Its `permissions.ask` rules beat any `--allowedTools` entry, and an ask is denied when no user can answer, so `claude-code-review` passes `--setting-sources user` (reproduced locally on 2026-10-04 on Claude Code 2.1.289, the version the action installed in the CI run, with action v1.0.241: with project settings `gh pr comment` was denied, without them it ran; without a host, a call that would prompt is denied, per the headless docs). Excluding the project source also stops `CLAUDE.md` and `.claude/rules/` from loading, so the review prompt tells the model to Read them.
- The allowed-actions list also filters actions nested in other actions: `claude-code-action` v1.0.241 runs `oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6`, allowed by that exact SHA; re-check its `action.yml` files when updating the action.
- All of them set `permissions: {}` at the top level with minimal per-job grants, pin actions by SHA and set `persist-credentials: false` on every checkout (the labeler has none).
- The labeler runs on `pull_request_target` without checking out the PR's code.
- `check_pr.py` requires every changed existing plugin to be released in the same pull request: a single-step bump, the matching changelog section, an empty `[Unreleased]`, and a Migration section for majors; the pull request carries exactly one `semver:` label naming the highest bump among the plugins it releases.
- `check_pr.py` also requires a dated root `CHANGELOG.md` note when `marketplace.json` changes.
- Labels are defined as code with crazy-max (which deletes the ones not in the file), and `actions/labeler` applies them by path.
- The label prefixes are `type:`, `semver:`, `status:`, `priority:`, `category:` and `plugin:<name>`, plus `security-review`.
- Pinned action versions: checkout v7.0.1, setup-uv v10.2.0, setup-node v7.0.0, labeler v7.0.0, crazy-max/ghaction-github-labeler v6.0.0 and anthropics/claude-code-action v1.0.241.

## Repository Settings

- Applied 2026-10-04; the repository is public at `nerymurillohnd/claude-essentials`.
- Topics: `claude-code`, `plugin-marketplace`, `skills`, `mcp`, `agents`. Never use an official marketplace name, such as a reserved name from the marketplace reference, as a topic.
- Issues on; Wiki and Projects off.
- Squash merging only (title and body of the pull request), and head branches deleted automatically.
- Private vulnerability reporting, secret scanning and push protection on. Dependabot security updates are on by GitHub's default for public repositories; version updates stay deferred.
- "Reported content" to maintainers exists only for organization-owned repositories, so it does not apply here; the Code of Conduct sends reports to the maintainer's contact details.
- Interaction limits and code review limits stay off and can be turned on temporarily if a discussion gets out of hand.
- Actions allows GitHub-owned actions plus `astral-sh/setup-uv`, `crazy-max/ghaction-github-labeler` and `anthropics/claude-code-action@*` only, with SHA pinning required, read-only default `GITHUB_TOKEN` permissions, and Actions unable to approve pull requests.
- Ruleset `main: signed commits` on the default branch: signed commits, linear history, no force pushes, no deletion, no bypass.
- Ruleset `release tags` on `refs/tags/*--v*`: only admins create, update or delete them, and the tagged commit must be signed. Rulesets cannot require a signed tag object; `git tag -v` verifies it.
- Required pull request reviews and status checks (`Gates and isolated install test`, `Commit convention and release discipline`) stay off: the only collaborator is the maintainer, and Claude acts through that account (GitHub API, checked 2026-10-04). They would block direct pushes the release policy allows; enable them when a second collaborator joins.
- The remote labels equal `.github/labels.yml`; `gh workflow run labels.yml` syncs them and the GitHub defaults are gone.
- Community standards report 100 %: README, Code of Conduct, Contributing, License, Security policy and pull request template.
- Verify the published marketplace like a user only in a throwaway configuration, never in the maintainer's own: `export HOME="$(mktemp -d)" CLAUDE_CONFIG_DIR="$HOME/.claude"`, then `claude plugin marketplace add nerymurillohnd/claude-essentials`, `claude plugin install <plugin>@claude-essentials` and `claude plugin list --json`.
- `hello-example` 0.1.0 stays untagged; its first tag is `hello-example--v0.1.1`.
