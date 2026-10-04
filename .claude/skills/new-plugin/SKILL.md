---
name: new-plugin
description: Creates a new plugin for the claude-essentials marketplace from proposal to an open pull request - scaffold with the official generator, write the components, validate, drive it in a real session and release it at 0.1.0. Use when asked to create, scaffold, start or add a new plugin to the marketplace.
argument-hint: "<name> <category> <one-line description>"
arguments: [name, category]
---

# Create a plugin

Plugins are for the people who install them: write every component from their point of view, and never derive requirements from this machine. Read `docs/authoring.md`, `docs/naming.md` and `docs/quality-bar.md` before step 3; read `docs/security-review.md` too when the plugin has hooks, MCP or LSP servers, `bin/`, monitors or mods.

```
- [ ] 1 Proposal    scope, category, components, user value
- [ ] 2 Scaffold    new_plugin.py on a $name/initial branch
- [ ] 3 Components  replace every TODO; add more with add-component
- [ ] 4 Validate    validate --strict, check.py
- [ ] 5 Behaviour   drive_plugin.py; claude plugin eval for behaviour-shaping plugins
- [ ] 6 Release     signed commit, test-install, pull request (no semver label)
```

1. **Proposal.** State in a few lines what the plugin does for its users, its category (one of `repo.CATEGORIES`), its components and what each runs on the user's machine. A name must pass `docs/naming.md` (no `claude` or `anthropic` word, kebab-case, permanent once published). Confirm with the maintainer before scaffolding.
2. **Scaffold.** `git switch -c $name/initial`, then `python3 scripts/new_plugin.py $name --category $category --description "<one-line description>" --author "<author>" --with skills [agents ...]`. It runs `claude plugin init` in a throwaway config, adds the catalog entry, labels, labeler rules, catalog note, README, CHANGELOG and LICENSE.
3. **Components.** Replace every TODO. Write each skill with the `skills-best-practices` skill when it is available. Add a skill or agent with the `add-component` skill. Hooks run with exec form and `${CLAUDE_PLUGIN_ROOT}`; everything stays inside `plugins/$name/`.
4. **Validate.** `claude plugin validate plugins/$name --strict`, then `python3 scripts/check.py`; fix every failure at its cause (the `repo` gate names the file and rule).
5. **Behaviour.** `python3 scripts/drive_plugin.py $name --expect '<what it should do>'` for each skill (skill `run-marketplace`). For a plugin that shapes Claude's behaviour, build an eval suite with `claude plugin eval init` from `plugins/$name` and run `claude plugin eval plugins/$name --no-publish`; attach the result to the pull request. Never run evals without `--no-publish`: by default the report is also published to claude.ai when the account supports it.
6. **Release.** A new plugin starts at `0.1.0` and needs no bump and no `semver:` label. Run the `verify` skill, commit `feat($name): add $name plugin` (signed, message from a file, as `release-plugin` explains), `python3 scripts/check.py test-install`, then `git push -u origin $name/initial` and `gh pr create` with the template; both stop at an approval prompt. Hand off to `/github-ops:automatic-pr-lifecycle`; after the merge, ask the maintainer to run `/release-plugin $name tag` (only the maintainer can start it).

## Gotchas

- `new_plugin.py` leaves TODO placeholders on purpose; the `repo` gate rejects them until they are real content.
- The scaffold's `--with hooks` generates a Bun handler; never ship it: hooks may use only interpreters the plugin declares as requirements.
- Never install or enable the plugin in the maintainer's own configuration; `drive_plugin.py` and `test-install` use session-only or throwaway configurations.
- While `hello-example` is still in the catalog, the first real plugin's pull request also removes it: delete its entry and directory, add `"renames": {"hello-example": null}` and a dated catalog note.
