# Testing

Every gate runs locally with `scripts/check.py` and in CI with the same command. Scripts run by path, so their shebang chooses the interpreter, and every gate runs the tool found on PATH: no tool or Python version is pinned. Decisions: [ADR validation-stack](adr/decisions/ADR_2026-10-03_validation-stack.md), [ADR testing-approach](adr/decisions/ADR_2026-10-03_testing-approach.md), [ADR unpinned-tooling-and-shebang-interpreters](adr/decisions/ADR_2026-10-05_unpinned-tooling-and-shebang-interpreters.md).

## Targets

| Target                          | What it proves                                                                                                                                                                    |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/check.py validate`     | `claude plugin validate --strict` accepts the marketplace, the project's `.claude/` skills and agents, and each plugin                                                            |
| `scripts/check.py repo`         | Catalog, names, SemVer, changelogs, README sections, portability, self-containment, plugin scripts, mods, labels, the release tag pattern and local-only pre-commit hooks         |
| `scripts/check.py adrs`         | Every ADR record has a dated name, valid frontmatter, required sections, no placeholders and working links                                                                        |
| `scripts/check.py readmes`      | Generated README content matches manifests and plugin files                                                                                                                       |
| `scripts/check.py docs`         | Docs match the code: the minimum Claude Code version, gate list, script and `check.py` target names, rule `paths`, relative links, `docs/*.md` references and project skill names |
| `scripts/check.py tests`        | Each gate fails for the defect it targets (see below)                                                                                                                             |
| `scripts/check.py format`       | Prettier formatting of Markdown, JSON and YAML                                                                                                                                    |
| `scripts/check.py python`       | ruff and basedpyright with warnings as errors                                                                                                                                     |
| `scripts/check.py workflows`    | actionlint and the zizmor security audit                                                                                                                                          |
| `scripts/check.py schemas`      | Workflows and issue forms match GitHub's JSON Schemas                                                                                                                             |
| `scripts/check.py test-install` | Every plugin installs and loads like a user's install                                                                                                                             |

## Set up

The repository has no dependency manifest and nothing to install inside it. These tools must be on your PATH:

| Tool                                                                                                                                               | Used for                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [Claude Code](https://code.claude.com/docs/en/setup) 2.1.289 or later                                                                              | `claude plugin validate`, the scaffold, tags and install tests                        |
| [uv](https://docs.astral.sh/uv/)                                                                                                                   | Provides the `python3` that the scripts' shebang finds, and installs the Python tools |
| git                                                                                                                                                | Version control                                                                       |
| [Prettier](https://prettier.io/)                                                                                                                   | Formatting of Markdown, JSON and YAML                                                 |
| [ruff](https://docs.astral.sh/ruff/), [basedpyright](https://docs.basedpyright.com/)                                                               | Python lint, format and type checks                                                   |
| [actionlint](https://github.com/rhysd/actionlint), [zizmor](https://docs.zizmor.sh/), [check-jsonschema](https://check-jsonschema.readthedocs.io/) | Workflow and GitHub file checks                                                       |

`scripts/check.py` runs every gate that CI runs; `scripts/check.py --list` lists them. Install the local hooks once per clone, and optionally the commit message check:

```bash
uv tool install prek
prek install
cp scripts/git-hooks/commit-msg .git/hooks/commit-msg
```

## Local hooks

`.pre-commit-config.yaml` runs the installed ruff (`ruff check --fix`, then `ruff format`) and basedpyright (`--warnings`) as local `language: system` hooks on every commit, through [prek](https://github.com/j178/prek): `uv tool install prek`, then `prek install` once per clone; `prek run --all-files` checks the whole tree. The hooks are a fast local check; `scripts/check.py` remains the authority.

## Gate tests

`tests/test_gates.py` copies the repository into a temporary directory for each test, injects exactly one defect (a home path, a token, a `../` link, a symlink out of the plugin, a relative hook command, a plugin script without a shebang or executable bit, an interpreter in front of a plugin script, a version in the catalog entry, a wrong tag pattern, a mod without tests…) and asserts that the gate reports that defect and nothing else. A baseline test proves the unmodified copy passes. No defective content is ever committed.

## Isolated install test

`scripts/test_install.py` never touches the real Claude Code configuration. Each scenario uses a temporary `HOME` and `CLAUDE_CONFIG_DIR`:

1. **In place:** adds the repository as a directory marketplace, which also proves Claude Code accepts the marketplace name, then installs every plugin and runs `claude plugin details`.
2. **Cache copy:** clones HEAD to a bare repository and adds a temporary marketplace whose entries use `git-subdir` sources over `file://`, so each plugin is copied into the plugin cache exactly as users receive it. Commit before running it: it tests HEAD.
3. **Session:** loads all plugins with `claude --plugin-dir plugins plugin list --json` and fails on load errors or notes.

Outside CI, the script fingerprints `settings.json`, the plugin records, the plugin cache, the marketplaces directory and the skills directory of the real configuration before and after, and fails if any changed.

## Cleanup

Tests leave nothing behind: no directories, configurations, clones, caches or processes.

- Everything a script or test creates lives in a temporary directory with a known prefix (`claude-essentials-install-`, `claude-essentials-drive-`, `claude-essentials-review-`, `add-component-`, `new-plugin-`, `gate-fixture-`) and is removed when the script or test ends, including on failure.
- The cleanup is verified, not assumed: `tests/test_gates.py` asserts each fixture directory is gone after the test; `scripts/new_plugin.py` stops if its scaffold directory survives; `scripts/test_install.py` fails if its directory survives, if a directory with its prefix remains, or if any new entry containing `claude` appears in the system temporary directory during the run.
- `scripts/check.py clean` removes Python and ruff caches in the repository and any orphaned directory with the prefixes above, then confirms none remain.
- Tool caches (uv, prettier, ruff) are not test leftovers. Never delete them by hand; use the tool's own command (for uv, `uv cache prune` or `uv cache clean`).
- Never point a test at a real configuration or a permanent location. New scripts and tests follow the same rules and use the same prefixes, registered in `TEMP_PREFIXES` in `scripts/check.py`.

## Behavioral evaluation

`claude plugin eval` runs eval cases with and without a plugin and scores the difference ([plugin evals](https://code.claude.com/docs/en/plugin-evals)). It calls models and needs authentication, so it is not a CI gate; authors run it for plugins that shape Claude's behavior and attach the results to the pull request.
