# Claude Essentials

{{badges}}

Community plugins for [Claude Code](https://code.claude.com/docs): workflows, agents, audits, code review, documentation, development practices, deep research and model behavior, distributed as a Claude Code plugin marketplace.

Claude Essentials is an independent community project. It is not affiliated with or endorsed by Anthropic.

**Contents:** [Quick start](#quick-start) · [Plugins](#plugins) · [Categories](#categories) · [Keep plugins updated](#keep-plugins-updated) · [Set up for a team](#set-up-for-a-team) · [Trust and security](#trust-and-security) · [Contributing](#contributing) · [Project documentation](#project-documentation) · [License](#license)

## Quick start

Requires Claude Code {{min_claude_code}} or later. Inside a Claude Code session, add the marketplace once and install the plugins you want:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install <plugin>@claude-essentials
```

The same from your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install <plugin>@claude-essentials
```

Each plugin's README lists its requirements, components and the exact commands to use it.

## Plugins

{{catalog}}

## Categories

{{categories}}

## Keep plugins updated

Claude Code does not update plugins from community marketplaces in the background unless you turn that on. Without it, you keep the version you installed, including any bug or security fix released later.

| To                    | Do this                                                                                            |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| Update automatically  | Run `/plugin`, open **Marketplaces**, select `claude-essentials` and choose **Enable auto-update** |
| Update one plugin now | `claude plugin update <plugin>@claude-essentials`                                                  |
| Refresh the catalog   | `/plugin marketplace update claude-essentials`                                                     |

## Set up for a team

Commit this to your repository's `.claude/settings.json` so everyone who trusts the folder gets the marketplace and the plugins you choose. Each person still installs the plugins once.

```json
{
  "extraKnownMarketplaces": {
    "claude-essentials": {
      "source": {
        "source": "github",
        "repo": "nerymurillohnd/claude-essentials"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "<plugin>@claude-essentials": true
  }
}
```

<details>
<summary>Pin a branch or tag, or clone only what Claude Code needs</summary>

Pin the catalog to a branch or tag by appending it to the source: `/plugin marketplace add nerymurillohnd/claude-essentials#<ref>`.

Clone only the catalog and the plugins, without documentation and tooling:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials --sparse .claude-plugin plugins
```

</details>

## Trust and security

A plugin runs with the permissions of the person who installs it. Every plugin here is reviewed against the [quality bar](docs/quality-bar.md), and plugins with hooks, MCP or LSP servers, executables or mods also pass the [security review](docs/security-review.md). Each plugin README has a **Permissions** section that states what it runs on your machine. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Contributing

This repository is developed and maintained only by its maintainer and Claude, so pull requests from others are not accepted. Bug reports and plugin proposals are welcome as issues: start with [CONTRIBUTING.md](CONTRIBUTING.md). We attend every issue and update the catalog ourselves.

## Project documentation

| Document                                     | What it covers                                                     |
| -------------------------------------------- | ------------------------------------------------------------------ |
| [Authoring guide](docs/authoring.md)         | How to build a plugin for this marketplace                         |
| [Quality bar](docs/quality-bar.md)           | What a plugin must meet to be accepted                             |
| [Security review](docs/security-review.md)   | Review policy for hooks, MCP and LSP servers, executables and mods |
| [Naming](docs/naming.md)                     | Plugin, skill, tag and label naming rules                          |
| [Releasing](docs/releasing.md)               | Versions, changelogs, tags and releases                            |
| [Testing](docs/testing.md)                   | Gates and isolated install tests                                   |
| [Architecture decisions](docs/adr/README.md) | Why the repository works the way it does                           |
| [Changelog](CHANGELOG.md)                    | Marketplace-level changes                                          |

## License

[MIT](LICENSE). Third-party material is listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
