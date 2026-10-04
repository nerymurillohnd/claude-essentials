## Summary

Describe the change and why users need it. Link the issue it resolves (for example `Closes #12`).

## Type of change

- [ ] Plugin change with its release (fix, feature or breaking change to plugins under `plugins/`)
- [ ] New plugin (accepted proposal: #)
- [ ] Catalog change (`marketplace.json` entry or `renames`)
- [ ] Repository, tooling, CI or documentation only

## Checklist

Pull request title and commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), with the plugin name as scope for plugin changes, for example `fix(my-plugin): handle empty input`.

- [ ] `python3 scripts/check.py` passes locally; `python3 scripts/check.py test-install` passes for plugin changes.
- [ ] **Release:** every changed plugin was bumped with `scripts/bump_version.py` in this pull request, and its notes moved into the new `CHANGELOG.md` section.
- [ ] **Semver label:** exactly one `semver:` label, the highest bump among the released plugins (none for new plugins or non-plugin changes).
- [ ] **Catalog:** a change to `marketplace.json` has a dated note in the root `CHANGELOG.md`.
- [ ] **Breaking change:** the title uses `!`, the label is `semver:major`, and `### Migration` explains what broke, who is affected and the exact steps.
- [ ] **Portability:** no absolute or home paths, user or machine names, secrets or personal data; paths use `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`.
- [ ] **Self-containment:** nothing references files outside the plugin's own directory.
- [ ] **Security review:** hooks, MCP or LSP servers, executables and mods are listed in the README **Permissions** section and justified ([security review](https://github.com/nerymurillohnd/claude-essentials/blob/main/docs/security-review.md)).
- [ ] **Docs:** the plugin README explains every component with an example; generated README blocks were refreshed with `python3 scripts/sync_readmes.py`.
- [ ] **Sources:** any Claude Code behavior this change relies on was checked against the current official docs and changelog.

## How this was tested

List the sessions, prompts and commands you ran and what happened.
