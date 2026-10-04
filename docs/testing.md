# Testing

Every gate runs locally with `python3 scripts/check.py` and in CI with the same command. Decisions: [ADR validation-stack](adr/decisions/ADR_2026-10-03_validation-stack.md), [ADR testing-approach](adr/decisions/ADR_2026-10-03_testing-approach.md).

## Targets

| Target                                  | What it proves                                                                                                                                                    |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python3 scripts/check.py validate`     | `claude plugin validate --strict` accepts the marketplace, the project's `.claude/` skills and agents, and each plugin                                            |
| `python3 scripts/check.py repo`         | Catalog, names, SemVer, changelogs, README sections, portability, self-containment, mods, labels, the release tag pattern and the local hook pins                 |
| `python3 scripts/check.py adrs`         | Every ADR record has a dated name, valid frontmatter, required sections, no placeholders and working links                                                        |
| `python3 scripts/check.py readmes`      | Generated README content matches manifests and plugin files                                                                                                       |
| `python3 scripts/check.py docs`         | Docs match the code: pinned versions, gate list, script and `check.py` target names, rule `paths`, relative links, `docs/*.md` references and project skill names |
| `python3 scripts/check.py tests`        | Each gate fails for the defect it targets (see below)                                                                                                             |
| `python3 scripts/check.py format`       | Prettier formatting of Markdown, JSON and YAML                                                                                                                    |
| `python3 scripts/check.py python`       | ruff and basedpyright with warnings as errors                                                                                                                     |
| `python3 scripts/check.py workflows`    | actionlint and the zizmor security audit                                                                                                                          |
| `python3 scripts/check.py schemas`      | Workflows and issue forms match GitHub's JSON Schemas                                                                                                             |
| `python3 scripts/check.py test-install` | Every plugin installs and loads like a user's install                                                                                                             |

## Local hooks

`.pre-commit-config.yaml` runs ruff (`ruff-check --fix`, then `ruff-format`) and basedpyright (`--warnings`) on the Python files of every commit, through [prek](https://github.com/j178/prek): `uv tool install prek`, then `prek install` once per clone; `prek run --all-files` checks the whole tree. The hooks follow the official [ruff](https://docs.astral.sh/ruff/integrations/#pre-commit) and [basedpyright](https://docs.basedpyright.com/latest/installation/prek-hook/) instructions. Their `rev` pins must equal `RUFF_VERSION` and `BASEDPYRIGHT_VERSION` in `scripts/check.py`; the `repo` gate fails otherwise. Before raising a pin, read the release notes of every version in between. The hooks are a fast local check; `python3 scripts/check.py` remains the authority.

## Gate tests

`tests/test_gates.py` copies the repository into a temporary directory for each test, injects exactly one defect (a home path, a token, a `../` link, a symlink out of the plugin, a relative hook command, a version in the catalog entry, a wrong tag pattern, a mod without tests…) and asserts that the gate reports that defect and nothing else. A baseline test proves the unmodified copy passes. No defective content is ever committed.

## Isolated install test

`scripts/test_install.py` never touches the real Claude Code configuration. Each scenario uses a temporary `HOME` and `CLAUDE_CONFIG_DIR`:

1. **In place:** adds the repository as a directory marketplace, which also proves Claude Code accepts the marketplace name, then installs every plugin and runs `claude plugin details`.
2. **Cache copy:** clones HEAD to a bare repository and adds a temporary marketplace whose entries use `git-subdir` sources over `file://`, so each plugin is copied into the plugin cache exactly as users receive it. Commit before running it: it tests HEAD.
3. **Session:** loads all plugins with `claude --plugin-dir plugins plugin list --json` and fails on load errors or notes.

Outside CI, the script fingerprints `settings.json`, the plugin records, the plugin cache, the marketplaces directory and the skills directory of the real configuration before and after, and fails if any changed.

## Drive a plugin

`python3 scripts/drive_plugin.py <plugin> [--prompt TEXT] [--source checkout|head] [--expect REGEX] [--model MODEL] [--budget USD] [--tools LIST] [--permission-mode MODE]` uses a plugin the way a user does: it sends a prompt (by default the plugin's first skill as a slash command) to a headless `claude -p` session with only that plugin loaded, and fails unless the plugin loaded alone, the session ended without error, every `--expect` regex matches the reply and the real configuration is unchanged. `--source head` drives the copy a user receives, installed from a bare clone of HEAD in a throwaway configuration. `--budget` caps the spend of the session (default \$0.50). `--tools` (default `default,Bash,WebFetch`) restores Bash and WebFetch, which `--restricted` drops. The project skill `run-marketplace` documents it.

The session runs with the maintainer's own login, because an isolated `CLAUDE_CONFIG_DIR` has no credentials, under `--restricted` (no user or project settings), `--strict-mcp-config` (no claude.ai connectors) and `--no-session-persistence` (no transcript), started in an empty temporary directory so neither the project `CLAUDE.md` nor the git snapshot reaches the model. It is a fast smoke test on the maintainer's login; `claude plugin eval` (below) is the clean-room check. Each run is a real model call (about \$0.01 with the default `haiku`), so it is not a CI gate; run it before a pull request that changes a plugin's behavior.

## Cleanup

Tests leave nothing behind: no directories, configurations, clones, caches or processes.

- Everything a script or test creates lives in a temporary directory with a known prefix (`claude-essentials-install-`, `claude-essentials-drive-`, `claude-essentials-review-`, `add-component-`, `new-plugin-`, `gate-fixture-`) and is removed when the script or test ends, including on failure.
- The cleanup is verified, not assumed: `tests/test_gates.py` asserts each fixture directory is gone after the test; `scripts/new_plugin.py` stops if its scaffold directory survives; `scripts/test_install.py` fails if its directory survives, if a directory with its prefix remains, or if any new entry containing `claude` appears in the system temporary directory during the run.
- `python3 scripts/check.py clean` removes Python and ruff caches in the repository and any orphaned directory with the prefixes above, then confirms none remain.
- Tool caches (uv, prettier, ruff) are not test leftovers. Never delete them by hand; use the tool's own command (for uv, `uv cache prune` or `uv cache clean`).
- Never point a test at a real configuration or a permanent location. New scripts and tests follow the same rules and use the same prefixes, registered in `TEMP_PREFIXES` in `scripts/check.py`.

## Behavioral evaluation

`claude plugin eval` runs eval cases with and without a plugin and scores the difference ([plugin evals](https://code.claude.com/docs/en/plugin-evals)). It calls models and needs authentication, so it is not a CI gate; authors run it for plugins that shape Claude's behavior and attach the results to the pull request.
