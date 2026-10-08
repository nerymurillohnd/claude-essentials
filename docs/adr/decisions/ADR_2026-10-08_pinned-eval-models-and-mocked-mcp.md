---
status: accepted
date: 2026-10-08
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
supersedes: ADR_2026-10-06_inherited-eval-models-and-full-results.md
superseded-by: none
---

# Eval runs pin their models, mock MCP servers and run every case three times

## Purpose

Record that plugin eval runs pin the agent and the judge model, answer a plugin's MCP tools from mocks instead of the real servers, and run each case the number of times the case declares, in CI too.

## Scope

`.github/workflows/plugin-evals.yml`, `.claude/rules/testing/plugin-evals.md` and every plugin eval suite (first applied to `plugins/svelte-development/evals/`). It supersedes [ADR inherited-eval-models-and-full-results](ADR_2026-10-06_inherited-eval-models-and-full-results.md); the full results it keeps as an artifact stay. It replaces the `--runs 1` part of [ADR plugin-evals-in-ci](ADR_2026-10-05_plugin-evals-in-ci.md); the label trigger, the grants and the informative threshold stay.

## Context and problem statement

The `svelte-development` suite was rebuilt from 20 overlapping cases to 11 in the session of 2026-10-07 and 2026-10-08. Three facts found while rebuilding it changed the earlier decisions:

- The judge was never inherited. `claude plugin eval --help` on 2.1.293 says `--judge-model` defaults to `haiku`, and the docs say the default judge is "the model Claude Code uses for background tasks". The earlier runs were judged by Haiku, a smaller model than the agent, and an inherited agent model would be judged by itself when both are the same.
- `claude plugin eval` never starts a plugin's real MCP servers unless asked, and answers mocked tools from `evals/mocks/<server>/<tool>.md` with no grant. The rule against mocks rested on `{{…}}` substitutions, which the `repo` gate rejects in plugin files; a mock without substitutions passes the gate.
- A real MCP server makes a score depend on the machine, the network and the server's current answers, and the docs call such scores advisory outside an isolated environment. Plugins are installed by third parties, so a result must not depend on the maintainer's machine.

The maintainer decided in that session: the agent is Sonnet 5.5 and the judge Opus 5.5, reversing the inherited models; MCP tools are mocked; a local run is a pilot and the full run happens in CI.

## Decision drivers

- A result must be the same on any machine.
- The judge must not be the agent's model and must be at least as capable.
- Runs must be comparable across pull requests.
- A case needs at least three runs per arm to tell an effect from luck.

## Considered options

- Pin both models, mock MCP servers, three runs per case
- Keep inherited models and real MCP servers

## Decision outcome

Chosen option: **Pin both models, mock MCP servers, three runs per case**, because it removes the machine, the network and model rollouts from the score, and gives a judge stronger than the agent.

- Every run passes `--model claude-sonnet-5-5 --judge-model claude-opus-5-5`, full model IDs rather than aliases, because an alias can move to another model between runs.
- Plugin suites mock every MCP tool their cases can call: `fixed` mocks without `{{…}}` substitutions, `expect:` guards for arguments the plugin must get right, `error: true` for an unavailable server, and the server's real `tools/list` saved as `_tools.json`. The live integration stays covered by `scripts/drive_plugin.py`.
- CI no longer passes `--runs`, so each case runs the `runs` its `prompt.md` declares (3).

### Consequences

- Good, because the delta compares the same pinned agent across pull requests.
- Good, because a mocked tool returns the same answer everywhere and no code leaves the runner.
- Good, because an `expect:` guard turns a wrong argument (a file path passed as code) into an aborted run, a regression signal.
- Bad, because a mock cannot judge code, so a suite measures whether the plugin uses the tool correctly, not what the real tool would answer.
- Bad, because three runs triple the cost of a full run: the local pilot of the 11-case `svelte-development` suite cost 2.61 USD for one run per arm (22 runs), so a full run is about 7.85 USD, and the CI ceiling per plugin rises from 10 to 15 USD.
- Bad, because a new default model is not measured until the pinned IDs are changed on purpose.

### Risks and mitigations

| Risk                                | Likelihood or condition  | Impact                             | Mitigation or response                                                                              | Owner      |
| ----------------------------------- | ------------------------ | ---------------------------------- | --------------------------------------------------------------------------------------------------- | ---------- |
| Mock text drifts from the live docs | A docs page changes      | The suite teaches outdated content | Mock bodies are excerpts with their source URL; refresh them with the derived-content release check | Maintainer |
| A pinned model is retired           | Anthropic retires the ID | Runs fail to start                 | The run fails loudly; change the IDs in one place in the workflow                                   | Maintainer |

### Confirmation

| Criterion or claim                          | Verification method                                          | Evidence or result                                                                                        | Responsible party | Review condition                 |
| ------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------------- |
| The pinned models are used                  | The job summary prints the model keys of the result document | pending: first CI run after this ADR                                                                      | Maintainer        | Each CI run                      |
| Mocked tools answer without the real server | The run's `mocked:` progress line and `mock-calls.jsonl`     | Local smoke on 2026-10-08: `svelte(get-documentation=fixed, list-sections=fixed, svelte-autofixer=fixed)` | Claude Code       | When a plugin adds an MCP server |

## Pros and cons of the options

### Pin both models, mock MCP servers, three runs per case

- Good, because results do not depend on the machine, the network or a model rollout.
- Bad, because it does not measure the real MCP server or the default model users get.

### Keep inherited models and real MCP servers

- Good, because it measures what users get by default, with the live server.
- Bad, because the judge was Haiku and scores were advisory outside an isolated runner.

## More information

Docs: [plugin evals](https://code.claude.com/docs/en/plugin-evals) ("Mock MCP servers", "Command options", "How runs are isolated", "Grant tools"), read with curl on 2026-10-07.
