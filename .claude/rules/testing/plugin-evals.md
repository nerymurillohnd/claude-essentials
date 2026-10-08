---
paths:
  - "plugins/**/evals/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
---

# Plugin Evals

How to design and run `claude plugin eval` suites for this marketplace's plugins. Verified on Claude Code 2.1.289 on 2026-10-05 against https://code.claude.com/docs/en/plugin-evals and the CLI reference, and again on 2.1.293 and 2.1.294 on 2026-10-07 and 2026-10-08 while rebuilding the svelte-development suite (smoke and pilot runs).

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
- Mock every MCP tool a case can call (ADR pinned-eval-models-and-mocked-mcp).
  - Put suite-wide mocks in `evals/mocks/<server>/<tool>.md`, and a case's own in `<case>/mocks/`.
  - Use `fixed` mocks without `{{…}}` substitutions: the `repo` gate rejects them in plugin files.
  - Guard arguments the plugin must get right with `expect:`; a violation aborts the run with score 0.
  - Use `error: true` for an unavailable server.
  - Save the server's real `tools/list` result as `_tools.json`.
  - A mocked tool needs no `allowed_tools` entry and no grant; a tool without a mock does not exist in the run.
  - Make links in documentation excerpts absolute: the `docs` gate checks them.
  - The live server stays covered by `scripts/drive_plugin.py`.
- Grader syntax (docs, "Grader types"): a `regex` grader takes `pattern:` in the frontmatter, a JavaScript regex; case-insensitivity goes in `flags: i`, never `(?i)`.
- `tool_order` passes only when both tools were called. To require "no Grep before the first LSP call", use a `regex` over the trace: `^(?:(?!"name":\s*"LSP")[\s\S])*"name":\s*"(?:Grep|Glob)"` with `match: not_contains`.
- Never match the trace for words a loaded skill contains (`npm install -g`, `svelte-kit sync`): the trace holds the skill text. Use `tool_used` with `input_match` over the tool input instead.
- Graders that are `with-only` by default under ablation: `tool_used` on `Skill`, and every grader on `mock_calls` (observed 2026-10-08).
- A case that edits a file holding a deliberate fixture error must accept that error fixed: the plugin's Stop hook can lead Claude to fix errors in files it touched.

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
- Pass `--allow-real-servers` only for a server that has no mocks; a mocked server never starts.
- Always pass `--max-cost-usd`.
- Pass `--model claude-sonnet-5-5 --judge-model claude-opus-5-5`, full IDs, never aliases (ADR pinned-eval-models-and-mocked-mcp, 2026-10-08).
- Without `--judge-model` the judge is `haiku` (`claude plugin eval --help`, 2.1.293), not the agent's model: runs before 2026-10-08 were judged by Haiku.
- CI passes no `--runs`: each case runs the `runs` its `prompt.md` declares (3).
- `--allow-tools` grants what `allowed_tools` asks for: `Write`, `Edit`, `Bash(...)`, `"mcp__plugin_<plugin>_<server>__*"`.
- Bash runs in a sandbox whose network reaches only domains granted as `WebFetch(domain:<host>)`.
- The sandbox reads only the run's workspace and the directories on `PATH`, not the targets of symlinks in them (observed 2026-10-08, 2.1.294).
  - With nvm on macOS, `npm` and `npx` are symlinks into `lib/`, so every `npm` call in a run fails with `Cannot find module`.
  - A globally installed `svelteserver` is a symlink too, so `command -v svelteserver` prints nothing inside the run, while the LSP server (started by Claude Code outside the sandbox) answers.
  - Local pilots on such a machine therefore cannot measure project checks or the language-server probe.
  - Not yet checked on CI: `actions/setup-node` also links `npm` into `lib/`, so read the first CI trace before trusting a check grader there.
- Pass `--keep-temp` to read a run's trace at `<kept dir>/out/trace.jsonl`; the kept directory is read-only and its `home/` and `tmp/` are sealed.
- Pass `--output-dir` and `--report` into the session scratchpad, so no result lands in `evals/results/`.
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
- In that copy, set the `.lsp.json` `command` to the binary's absolute path, installed with `npm install --prefix <scratchpad>/eval-tools`.
- It works: `findReferences` answered in the 2026-10-08 pilot. Say so in the evidence.
- Scores with real MCP servers are advisory unless the run is in an isolated environment such as a CI runner (docs, "Trust the plugin directory").
- Full runs go to CI: apply the `run-evals` label to the pull request (ADR plugin-evals-in-ci).
- Local runs are pilots.
- A plugin lists the npm packages its runs need in `evals/ci-packages.txt`.
- A plugin lists extra `--allow-tools` grants in `evals/ci-allow-tools.txt`.

## Evidence

- Report only numbers from a run that actually happened.
- Include the command, the CLI version, the models the run recorded, passed and total per arm, the delta per case, the cost, and any "not granted" or load errors.
- Put that record in the pull request (`evals: <plugin> <passed>/<total>, delta <with minus without>`), never in the plugin README.
- The trace holds a subagent's tool calls, each with `parent_tool_use_id` and `agent_id` set, so trace and `tool_used` graders see them (pilot 2026-10-08, case `10-editor-delegation`).
- Analyse per grader, from the artifact.
  - Drop graders that pass in both arms on every run.
  - Fix graders that fail in both arms.
  - Explain the ones that pass only with the plugin.
  - Tighten skill wording where runs disagree.
- An `llm` grader with `focus: trace` sees only the first and last 12 messages. Never use it for a step in the middle of a long session.
