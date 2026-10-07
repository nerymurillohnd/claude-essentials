---
paths:
  - "plugins/**/evals/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
---

# Plugin Evals

How to design and run `claude plugin eval` suites for this marketplace's plugins. Verified on Claude Code 2.1.289 on 2026-10-05 against https://code.claude.com/docs/en/plugin-evals and the CLI reference, while building the svelte-development suite.

## Before Any Run

- Never start a run until the maintainer agreed to that exact run. This includes one case or a load check.
- The agreement covers cases, model, runs per arm, cost ceiling and flags.
- Every run and every `llm` grader is a real model call on the maintainer's account.
- Order: `/code-review` of the branch first, evals after, so no money goes to a change review would reject.
- Validate case files without running them:
  - the YAML frontmatter parses
  - every grader regex compiles (`json.loads` the quoted value, then `re.compile`)
  - `prettier --check`
  - `shellcheck -o all` on scaffold scripts
  - `scripts/check.py`

## Design

- Cover four questions for every plugin.
  - Each skill loads when a task needs it and never for unrelated tasks. Use `tool_used` on `Skill` with `min: 0, max: 0` for negatives.
  - Each agent stays inside its role. A read-only agent changes no file even with `Write` and `Edit` available.
  - The plugin's guidance is followed, not skipped. Use `tool_order`, and `tool_used` on its MCP tools.
  - A task from the newest release is solved only by following the plugin. Declare a version newer than the one the fixture installs, so the changelog check is due.
- Prompts read like a user's request.
- Prompts never name the skill, the agent or the expected method.
- Give each case one grader on the result: a `regex` over the produced file, or an `llm` rubric for a short answer.
- Give each case one grader on the path: `tool_used`, `tool_order`.
- Mark path graders on plugin-only tools or skills `arm: both`. The baseline arm then scores 0 on them, so the delta measures what the plugin adds.
- `arm: with-only` turns a grader into an unscored indicator.
- A case whose graders are all `with-only` scores 0 in both arms (observed in the first CI run, 2026-10-05).
- Declare in `allowed_tools` every tool the case may use.
- Include the tools it must not use: the test is that it does not.
- Give the competing tools too, so choosing the right one is a real choice.
- Tighten regexes against false positives.
  - Use `\son:[a-z]` for the Svelte `on:` directive. Plain `on:` also matches `transition:`.
  - Use exact error positions rather than a word the answer would mention anyway.
- Quote frontmatter values that contain `{`, `:` or `[`. YAML reads `{ … }` as a map.
- After Prettier rewrites the frontmatter, re-parse every pattern to confirm it is unchanged.
- Use no MCP mocks in plugin suites. Mock files use `{{…}}` substitutions, which the `repo` gate rejects in plugin files.

## Scaffold Scripts

- Use one `scaffold.sh` per case directory, named in `case.yaml` (`context.scaffold_script`).
- Put shared helpers in a non-case directory such as `evals/shared/`.
- Start with `#!/usr/bin/env bash` and use mode 755, `set -euo pipefail`, braced variables and `[[ ]]`.
- The script must be `shellcheck -o all` clean.
- Resolve paths from the script's own location: `case_dir="$(cd "$(dirname "$0")" && pwd)"`, then `dirname`.
- Never use `../`. The `repo` gate rejects it.
- Never use an absolute or home path. Plugins are distributed.
- A scaffold runs outside the agent's sandbox, with a minimal environment and a 120-second limit, only with `--scaffold`.
- Do real setup in the scaffold.
  - Copy fixtures.
  - Drop `.example` suffixes.
  - Run `npm install --include=dev --ignore-scripts`, then `npx --no-install svelte-kit sync`.
  - A CI runner's npm may omit devDependencies.
  - The scaffold must fail loudly when a binary it needs is missing.
- Make real state changes in the scaffold, for example pinning a version in `package.json`. Never write a note that only claims a change.
- Test any non-trivial scaffold edit on a scratch copy before a paid run.

## Running

- Run from the plugin root (`claude plugin eval .`) or give the plugin path as the target.
- Put the target before `--tag`, `--allow-tools` and `--json`.
- Default ablation is `with-without`.
- The delta (with minus without, same model) is the number that matters. Zero or below means the plugin adds nothing.
- Use `--ablation none` only to check that cases load and graders work.
- Pass `--trust-plugin` with `--json`. A run that cannot ask is refused.
- Pass `--no-publish`.
- Pass `--scaffold` when cases have scaffolds.
- Pass `--allow-real-servers` for real MCP servers.
- Always pass `--max-cost-usd`.
- Pass no `--model` or `--judge-model`. Both are inherited and the run records the models it used (ADR inherited-eval-models-and-full-results, 2026-10-06).
- The docs recommend pinning `--model` in CI. Pin only for a comparison across runs, and say so.
- `--allow-tools` grants what `allowed_tools` asks for: `Write`, `Edit`, `Bash(...)`, `"mcp__plugin_<plugin>_<server>__*"`.
- Bash runs in a sandbox whose network reaches only domains granted as `WebFetch(domain:<host>)`.
- Read the "not granted" lines before trusting a score.
- On Ubuntu 24.04 runners the sandbox cannot start until `kernel.apparmor_restrict_unprivileged_userns` is 0.
  - Run 37409155173, 2026-10-06: every Bash call failed with `bwrap: loopback: Failed RTM_NEWADDR` in both arms.
  - `scripts/check.py ci-eval-tools` sets it and probes `bwrap` before any run.
  - A run whose answers mention `bwrap` is not evidence about the plugin.
- Write `--json` to the session scratchpad, never into the repository.
- The run also writes `evals/results/`. It is gitignored but holds the maintainer's paths.
- The `repo` gate scans the working tree, so delete `evals/results/` after the run.
- Isolation: each run has a temporary home, working directory and configuration.
- Only an allowlist of environment variables (including `PATH`) reaches the run.
- A plugin server binary must be on the user's `PATH`.
- To test without installing the binary on the maintainer's machine, run the suite against a scratch copy of the plugin.
- In that copy, set the `.lsp.json` `command` to the binary's absolute path.
- Say so in the evidence.
- Scores with real MCP servers are advisory unless the run is in an isolated environment such as a CI runner (docs, "Trust the plugin directory").
- Full runs go to CI: apply the `run-evals` label to the pull request (ADR plugin-evals-in-ci).
- Local runs are pilots.
- A plugin lists the npm packages its runs need in `evals/ci-packages.txt`.
- A plugin lists extra `--allow-tools` grants in `evals/ci-allow-tools.txt`.

## Evidence

- Report only numbers from a run that actually happened.
- Include the command, the CLI version, the models the run recorded, passed and total per arm, the delta per case, the cost, and any "not granted" or load errors.
- Put that record in the pull request (`evals: <plugin> <passed>/<total>, delta <with minus without>`), never in the plugin README.
- Open question, to settle from the first run whose full result is kept (the `evals-results` artifact): whether the trace graders see tool calls made inside a subagent.
- Subagents keep their own transcripts (`agent-<id>.jsonl`, sub-agents docs), so expect them not to.
- Analyse per grader, from the artifact.
  - Drop graders that pass in both arms on every run.
  - Fix graders that fail in both arms.
  - Explain the ones that pass only with the plugin.
  - Tighten skill wording where runs disagree.
- An `llm` grader with `focus: trace` sees only the first and last 12 messages. Never use it for a step in the middle of a long session.
