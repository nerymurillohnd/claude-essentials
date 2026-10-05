# Contributing

Claude Essentials is developed and maintained only by its maintainer and Claude. Pull requests from anyone else are not accepted, so the way to take part is an issue. We attend every issue, resolve it and update the repository ourselves.

**Contents:** [Ways to take part](#ways-to-take-part) · [If you clone this repository](#if-you-clone-this-repository) · [Licensing](#licensing)

## Ways to take part

| You want to                                  | Start here                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Report a bug                                 | [Bug report form](https://github.com/nerymurillohnd/claude-essentials/issues/new?template=bug_report.yml)                            |
| Propose a new plugin or a significant change | [Plugin proposal form](https://github.com/nerymurillohnd/claude-essentials/issues/new?template=plugin_proposal.yml), before any code |
| Get help using a plugin                      | [SUPPORT.md](SUPPORT.md)                                                                                                             |
| Report a vulnerability                       | [Private report](SECURITY.md), never a public issue                                                                                  |

Search existing issues first. Be kind and follow the [Code of Conduct](CODE_OF_CONDUCT.md). We write, review and release all code ourselves; every plugin is held to the [quality bar](docs/quality-bar.md).

## If you clone this repository

If you open this repository in Claude Code and trust the folder, its project settings apply to your session: `.claude/settings.json` asks before every push, pull request, release or tag push, denies commits that skip signing or hooks, and registers hooks that run `scripts/claude_hooks.py` on tool calls (guards for versions, generated README blocks, pushes and GitHub writes; a guard for the forbidden sources listed in an untracked `CLAUDE.local.md`, which does nothing without that file; prettier on edited Markdown, JSON, YAML and JavaScript; and a session-start status that runs `git status` and `claude --version`). Read [Claude Code automation](.claude/rules/automation.md) to see what each one does before you trust the folder.

## Licensing

By submitting a proposal or any other content in an issue, you confirm you have the right to submit it under the [MIT License](LICENSE), and you license it under those terms. Do not include secrets, private user data, or material you cannot redistribute; third-party material is recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
