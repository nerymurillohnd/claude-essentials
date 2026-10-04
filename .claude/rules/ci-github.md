---
paths:
  - ".github/**"
  - "scripts/check_pr.py"
  - "scripts/check_commit_msg.py"
---

# CI and GitHub

- The workflows are validate, pull-request, release, labels, labeler, claude-code-review and claude (ADR claude-github-action).
- `claude-code-review` reviews every push with a repository-specific prompt and re-checks earlier findings; `claude` answers `@claude` from users with write access only. Both use the `CLAUDE_CODE_OAUTH_TOKEN` secret.
- The allowed-actions list also filters actions nested in other actions: `claude-code-action` v1.0.241 runs `oven-sh/setup-bun@0c5077e51419868618aeaa5fe8019c62421857d6`, allowed by that exact SHA; re-check its `action.yml` files when updating the action.
- All of them use `permissions: {}`, actions pinned by SHA and `persist-credentials: false`.
- The labeler runs on `pull_request_target` without checking out the PR's code.
- `check_pr.py` requires every changed existing plugin to be released in the same pull request: a single-step bump, the matching changelog section, an empty `[Unreleased]`, and a Migration section for majors; the pull request carries exactly one `semver:` label naming the highest bump among the plugins it releases.
- `check_pr.py` also requires a dated root `CHANGELOG.md` note when `marketplace.json` changes.
- Labels are defined as code with crazy-max (which deletes the ones not in the file), and `actions/labeler` applies them by path.
- The label prefixes are `type:`, `semver:`, `status:`, `priority:`, `category:` and `plugin:<name>`, plus `security-review`.
- Pinned action versions: checkout v7.0.1, setup-uv v10.2.0, setup-node v7.0.0, labeler v7.0.0, crazy-max/ghaction-github-labeler v6.0.0 and anthropics/claude-code-action v1.0.241.
