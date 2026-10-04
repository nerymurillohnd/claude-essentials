# Testing

Every gate runs locally with `make check` and in CI with the same command. Decisions: [ADR 0008](adr/0008-validation-stack.md), [ADR 0010](adr/0010-testing-approach.md).

## Targets

| Target              | What it proves                                                                                                               |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `make validate`     | `claude plugin validate --strict` accepts the marketplace and each plugin                                                    |
| `make repo`         | Catalog, names, SemVer, changelogs, README sections, portability, self-containment, mods, labels and the release tag pattern |
| `make readmes`      | Generated README content matches manifests and plugin files                                                                  |
| `make tests`        | Each gate fails for the defect it targets (see below)                                                                        |
| `make format`       | Prettier formatting of Markdown, JSON and YAML                                                                               |
| `make python`       | ruff and basedpyright with warnings as errors                                                                                |
| `make workflows`    | actionlint and the zizmor security audit                                                                                     |
| `make schemas`      | Workflows and issue forms match GitHub's JSON Schemas                                                                        |
| `make test-install` | Every plugin installs and loads like a user's install                                                                        |

## Gate tests

`tests/test_gates.py` copies the repository into a temporary directory for each test, injects exactly one defect (a home path, a token, a `../` link, a symlink out of the plugin, a relative hook command, a version in the catalog entry, a wrong tag pattern, a mod without tests…) and asserts that the gate reports that defect and nothing else. A baseline test proves the unmodified copy passes. No defective content is ever committed.

## Isolated install test

`scripts/test_install.py` never touches the real Claude Code configuration. Each scenario uses a temporary `HOME` and `CLAUDE_CONFIG_DIR`:

1. **In place:** adds the repository as a directory marketplace, which also proves Claude Code accepts the marketplace name, then installs every plugin and runs `claude plugin details`.
2. **Cache copy:** clones HEAD to a bare repository and adds a temporary marketplace whose entries use `git-subdir` sources over `file://`, so each plugin is copied into the plugin cache exactly as users receive it. Commit before running it: it tests HEAD.
3. **Session:** loads all plugins with `claude --plugin-dir plugins plugin list --json` and fails on load errors or notes.

Outside CI, the script fingerprints `settings.json`, the plugin records, the plugin cache and the skills directory of the real configuration before and after, and fails if any changed.

## Behavioral evaluation

`claude plugin eval` runs eval cases with and without a plugin and scores the difference ([plugin evals](https://code.claude.com/docs/en/plugin-evals)). It calls models and needs authentication, so it is not a CI gate; authors run it for plugins that shape Claude's behavior and attach the results to the pull request.
