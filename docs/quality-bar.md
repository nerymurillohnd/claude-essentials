# Quality bar

What a plugin must meet to be accepted and to stay in the catalog. Items marked **gate** are enforced by `scripts/check.py` or CI; the rest are checked in review.

## Purpose and fit

- [ ] Solves a concrete, recurring problem for Claude Code users, described in the README Overview.
- [ ] Fits one category: workflows, agents, audits, code-review, documentation, development, best-practices, research or model-behavior. **gate**
- [ ] Does not duplicate a built-in Claude Code feature or another plugin in this catalog.
- [ ] Every component earns its place; a plugin with one excellent skill beats one with five weak ones.

## Correctness

- [ ] `claude plugin validate --strict` passes for the plugin and the marketplace. **gate**
- [ ] Installs and loads in a clean configuration, in place and from a cache copy. **gate** (`scripts/check.py test-install`)
- [ ] Skills trigger on the requests they describe and not on unrelated ones; the author tested this in real sessions.
- [ ] Hooks and servers handle missing tools, empty input and errors without blocking the user's work.

## Portability and self-containment

- [ ] No absolute, home or temporary paths; no user or machine names; no personal emails; no secrets. **gate**
- [ ] Nothing references files outside the plugin directory; no `../`; symlinks stay inside. **gate**
- [ ] Bundled files are referenced with `${CLAUDE_PLUGIN_ROOT}`, state with `${CLAUDE_PLUGIN_DATA}`. **gate** for hook and MCP commands
- [ ] Every bundled script has an unversioned `#!/usr/bin/env` shebang, is executable, and runs by path with no interpreter in front. **gate**
- [ ] Works on macOS and Linux; Windows behavior is stated in the README when it differs.

## Security

- [ ] Code that runs on the user's machine is listed and justified under Permissions. **gate** for the section
- [ ] Passes the [security review](security-review.md).
- [ ] Mods meet the extra requirements in [ADR security-posture](adr/decisions/ADR_2026-10-03_security-posture.md). **gate**

## Documentation

- [ ] README follows the template: Overview, What it does, Prerequisites, Installation, Usage, Components, FAQ, Update and uninstall, Documentation, License, plus Configuration and Permissions when they apply. **gate**
- [ ] The FAQ has 3 to 5 questions and opens with "Does installing this plugin modify my project?". **gate**
- [ ] Usage has at least one concrete example: what the user types and what happens.
- [ ] No placeholders left (`TODO`, `{{…}}`, `<your-…>`, `YYYY-MM-DD`). **gate**
- [ ] Generated README blocks are current. **gate**

## Versioning and maintenance

- [ ] SemVer version in `plugin.json` only, matching the newest changelog release. **gate**
- [ ] Changelog follows Keep a Changelog; majors have a Migration section. **gate**
- [ ] The author or a maintainer can respond to issues; unmaintained plugins are deprecated, then removed with a `renames` entry mapping the name to `null`.
