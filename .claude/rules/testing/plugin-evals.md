---
paths:
  - "plugins/**/evals/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
---

# Plugin evals

How to design and run `claude plugin eval` suites for this marketplace's plugins. Verified on Claude Code 2.1.289 on 2026-10-05 against https://code.claude.com/docs/en/plugin-evals and the CLI reference, while building the svelte-development suite.

## Before any run

- Never start a run, not even one case or a load check, until the maintainer agreed to that exact run: cases, model, runs per arm, cost ceiling and flags. Every run and every `llm` grader is a real model call on the maintainer's account.
- Order: `/code-review` of the branch first, evals after, so no money goes to a change review would reject.
- Validate case files without running them: YAML frontmatter parses, every grader regex compiles (`json.loads` the quoted value, then `re.compile`), `prettier --check`, `shellcheck -o all` on scaffold scripts, and `scripts/check.py`.

## Design

- Cover four questions for every plugin: each skill loads when a task needs it and never for unrelated tasks (`tool_used` on `Skill` with `min: 0, max: 0` for negatives); each agent stays inside its role (a read-only agent changes no file even with `Write` and `Edit` available); the plugin's guidance is followed, not skipped (`tool_order`, `tool_used` on its MCP tools); and a task from the newest release is solved only by following the plugin (pin a version newer than the references' "Verified against" line so the changelog check is due).
- Prompts read like a user's request and never name the skill, the agent or the expected method.
- Give each case one grader on the result (a `regex` over the produced file, or an `llm` rubric for a short answer) and one on the path (`tool_used`, `tool_order`). Mark path graders on plugin-only tools or skills `arm: both`: the baseline arm then scores 0 on them, so the delta measures what the plugin adds. `arm: with-only` turns a grader into an unscored indicator, and a case whose graders are all `with-only` scores 0 in both arms (observed in the first CI run, 2026-10-05).
- Declare in `allowed_tools` every tool the case may use, including the ones it must not use (the test is that it does not), and give the competing tools too, so choosing the right one is a real choice.
- Tighten regexes against false positives: `\son:[a-z]` for the Svelte `on:` directive (plain `on:` also matches `transition:`); exact error positions rather than a word the answer would mention anyway.
- Quote frontmatter values that contain `{`, `:` or `[` (YAML reads `{ … }` as a map). After Prettier rewrites the frontmatter, re-parse every pattern to confirm it is unchanged.
- No MCP mocks in plugin suites: mock files use `{{…}}` substitutions, which the `repo` gate rejects in plugin files.

## Scaffold scripts

- One `scaffold.sh` per case directory, named in `case.yaml` (`context.scaffold_script`); shared helpers live in a non-case directory such as `evals/shared/`.
- `#!/usr/bin/env bash`, mode 755, `set -euo pipefail`, braced variables, `[[ ]]`: `shellcheck -o all` clean.
- Resolve paths from the script's own location (`case_dir="$(cd "$(dirname "$0")" && pwd)"`, then `dirname`), never with `../` (the `repo` gate rejects it) and never with an absolute or home path: plugins are distributed.
- A scaffold runs outside the agent's sandbox with a minimal environment and a 120-second limit, only with `--scaffold`. Do real setup there (copy fixtures, drop `.example` suffixes, `npm install --include=dev --ignore-scripts`, then `npx --no-install svelte-kit sync`; a CI runner's npm may omit devDependencies, and the scaffold must fail loudly when a binary it needs is missing) and real state changes (for example pinning a version in `package.json`); never a note that only claims a change.
- Test any non-trivial scaffold edit on a scratch copy before a paid run.

## Running

- Run from the plugin root (`claude plugin eval .`) or give the plugin path as the target; put the target before `--tag`, `--allow-tools` and `--json`.
- Default ablation `with-without`: the delta (with minus without, same model) is the number that matters; zero or below means the plugin adds nothing. Use `--ablation none` only to check that cases load and graders work.
- Pass `--trust-plugin` with `--json` (a run that cannot ask is refused), `--no-publish`, `--scaffold` when cases have scaffolds, `--allow-real-servers` for real MCP servers, `--max-cost-usd` always, `--model` and `--judge-model` pinned.
- `--allow-tools` grants what `allowed_tools` asks for: `Write`, `Edit`, `Bash(...)`, `"mcp__plugin_<plugin>_<server>__*"`. Bash runs in a sandbox whose network reaches only domains granted as `WebFetch(domain:<host>)`. Read the "not granted" lines before trusting a score.
- Write `--json` to the session scratchpad, never into the repository. The run also writes `evals/results/`, which is gitignored but holds the maintainer's paths; the `repo` gate scans the working tree, so delete it after the run.
- Isolation: each run has a temporary home, working directory and configuration; only an allowlist of environment variables (including `PATH`) reaches it. A plugin server binary must be on the user's `PATH`; to test without installing it on the maintainer's machine, run the suite against a scratch copy of the plugin whose `.lsp.json` `command` is the binary's absolute path, and say so in the evidence.
- Scores with real MCP servers are advisory unless the run is in an isolated environment such as a CI runner (docs, "Trust the plugin directory"). Full runs go to CI: apply the `run-evals` label to the pull request (ADR plugin-evals-in-ci); local runs are pilots. A plugin lists the npm packages its runs need in `evals/ci-packages.txt` and extra `--allow-tools` grants in `evals/ci-allow-tools.txt`.

## Evidence

- Report only numbers from a run that actually happened: the command, the CLI version, both models, passed and total per arm, the delta per case, the cost, and any "not granted" or load errors.
- Put that record in the pull request (`evals: <plugin> <passed>/<total>, delta <with minus without>`), never in the plugin README.
- Open question, to settle on the first run that delegates to an agent: whether the trace graders see tool calls made inside a subagent.
