# Contributing

Thanks for contributing to Claude Essentials. Plugins here are used by other people in their own Claude Code setups, so every change is held to the [quality bar](docs/quality-bar.md). Read the [authoring guide](docs/authoring.md) before adding or changing a plugin.

**Contents:** [Ways to contribute](#ways-to-contribute) · [Set up](#set-up) · [Add a plugin](#add-a-plugin) · [Change a plugin](#change-a-plugin) · [Pull requests](#pull-requests) · [Review](#review) · [Licensing](#licensing)

## Ways to contribute

| You want to                                  | Start here                                                                                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Report a bug                                 | [Bug report form](https://github.com/nerymurillohnd/claude-essentials/issues/new?template=bug_report.yml)                                   |
| Propose a new plugin or a significant change | [Plugin proposal form](https://github.com/nerymurillohnd/claude-essentials/issues/new?template=plugin_proposal.yml), before writing code    |
| Submit an accepted plugin                    | [Plugin submission form](https://github.com/nerymurillohnd/claude-essentials/issues/new?template=plugin_submission.yml) plus a pull request |
| Fix documentation or tooling                 | A pull request directly                                                                                                                     |
| Report a vulnerability                       | [Private report](SECURITY.md), never a public issue                                                                                         |

Search existing issues first. Be kind and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Set up

The repository has no dependency manifest and nothing to install inside it. You need these tools on your PATH:

| Tool                                                                                                            | Used for                                                                   |
| --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [Claude Code](https://code.claude.com/docs/en/setup) 2.1.289 or later                                           | `claude plugin validate`, the scaffold, tags and install tests             |
| [uv](https://docs.astral.sh/uv/)                                                                                | Runs the standard-library Python scripts (`uv run scripts/...`) and zizmor |
| git, make                                                                                                       | Version control and the `make` targets                                     |
| [Prettier](https://prettier.io/)                                                                                | Formatting of Markdown, JSON and YAML                                      |
| [ruff](https://docs.astral.sh/ruff/), [basedpyright](https://docs.basedpyright.com/)                            | Python lint, format and type checks                                        |
| [actionlint](https://github.com/rhysd/actionlint), [check-jsonschema](https://check-jsonschema.readthedocs.io/) | Workflow and GitHub file checks                                            |

`make check` runs every gate that CI runs; `make help` lists the targets. Optionally install the commit message hook in your clone:

```bash
cp scripts/git-hooks/commit-msg .git/hooks/commit-msg
```

Never install plugins from this repository into your own Claude Code configuration to test them: `make test-install` installs them in a throwaway configuration (see [testing](docs/testing.md)).

## Add a plugin

1. Open a plugin proposal and wait until it is accepted.
2. Create the plugin with the scaffold, never by hand:

   ```bash
   uv run scripts/new_plugin.py <name> --category <category> \
     --description "<one sentence>" --author "<your name>" [--with skills agents]
   ```

3. Replace every `TODO` with real content. `make check` fails until none is left.
4. Run `make check` and `make test-install` until both pass.
5. Commit with `feat(<name>): add <name> plugin` and open a pull request.

## Change a plugin

- Keep each pull request to one plugin or one repository concern.
- Add a user-facing note under `## [Unreleased]` in the plugin's `CHANGELOG.md`, using the change types `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` and, for breaking changes, `Migration`.
- Do not change `version` in `plugin.json`: maintainers do that when they release (see [releasing](docs/releasing.md)).
- Regenerate README blocks with `uv run scripts/sync_readmes.py` after changing manifests or components; never edit content between `BEGIN GENERATED` and `END GENERATED` by hand.
- For any change to plugin format, marketplace, skills, hooks, MCP or LSP servers, mods or distribution, re-read the relevant pages of the [official Claude Code documentation](https://code.claude.com/docs/llms.txt) and the [changelog](https://code.claude.com/docs/en/changelog), and mention in the pull request what you checked and when.

## Pull requests

- Title and commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `<type>(<scope>): <subject>`, where the scope is the plugin name for plugin changes. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer.
- Apply exactly one `semver:major`, `semver:minor` or `semver:patch` label to pull requests that change a plugin. Other labels are applied automatically.
- Describe the plugin's purpose, required permissions and external services, and the manual verification you did.
- Fill in the pull request checklist; CI runs `make check`, the install test and the release-discipline check.

## Review

Maintainers may request changes for correctness, security, portability, licensing or unclear instructions. Plugins with hooks, MCP or LSP servers, executables or mods also go through the [security review](docs/security-review.md). A merged change reaches users with the plugin's next release.

## Licensing

By contributing, you confirm you have the right to submit your work under the [MIT License](LICENSE), and you license it under those terms. Do not include secrets, private user data, or material you cannot redistribute; record third-party material in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
