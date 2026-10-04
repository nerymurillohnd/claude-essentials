## Summary

Describe the change and why users need it. Link the issue it resolves (for example `Closes #12`).

## Type of change

- [ ] Plugin change (fix, feature or breaking change to a plugin under `plugins/`)
- [ ] New plugin (accepted proposal: #)
- [ ] Plugin release made with `scripts/release.py`
- [ ] Repository, tooling, CI or documentation only

## Checklist

Pull request title and commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), with the plugin name as scope for plugin changes, for example `fix(my-plugin): handle empty input`.

- [ ] `uv run scripts/check.py` passes locally; `uv run scripts/check.py test-install` passes for plugin changes.
- [ ] **Changelog:** each changed plugin has a user-facing note under `## [Unreleased]` in its `CHANGELOG.md` (not needed for release pull requests).
- [ ] **Version:** `version` in `plugin.json` is unchanged, unless this is a release made with `scripts/release.py`.
- [ ] **Semver label:** exactly one of `semver:major`, `semver:minor`, `semver:patch` is applied for plugin changes.
- [ ] **Breaking change:** the title uses `!`, the label is `semver:major`, and `### Migration` explains what broke, who is affected and the exact steps.
- [ ] **Portability:** no absolute or home paths, user or machine names, secrets or personal data; paths use `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`.
- [ ] **Self-containment:** nothing references files outside the plugin's own directory.
- [ ] **Security review:** hooks, MCP or LSP servers, executables and mods are listed in the README **Permissions** section and justified ([security review](https://github.com/nerymurillohnd/claude-essentials/blob/main/docs/security-review.md)).
- [ ] **Docs:** the plugin README explains every component with an example; generated README blocks were refreshed with `uv run scripts/sync_readmes.py`.
- [ ] **Sources:** any Claude Code behavior this change relies on was checked against the current official docs and changelog.

## How this was tested

List the sessions, prompts and commands you ran and what happened.
