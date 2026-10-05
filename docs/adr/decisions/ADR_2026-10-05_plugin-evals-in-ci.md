---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Plugin eval suites run in CI on demand

## Purpose

Run a plugin's `claude plugin eval` suite on a CI runner before its pull request merges, so the with-minus-without delta is measured in an isolated environment, without making evals a blocking gate.

## Scope

`.github/workflows/plugin-evals.yml`, `scripts/check.py ci-eval-tools`, the `run-evals` label, and the optional per-plugin files `evals/ci-packages.txt` and `evals/ci-allow-tools.txt`. The ten gates in `scripts/check.py` and the other workflows are unchanged.

## Context and problem statement

`docs/testing.md` kept evals out of CI because they call models and need authentication. The first real plugin, `svelte-development`, ships a 13-case suite that starts its real MCP server, and the Claude Code docs say scores with real MCP servers are advisory unless the run is in an isolated environment such as a container or CI runner ("Trust the plugin directory"). Local runs on the maintainer's machine are a pilot at best. The maintainer decided on 2026-10-05, in this session, to run the full suite in CI before release.

## Decision drivers

- Isolation: the docs' own standard for trusting scores with real servers.
- Cost control: every run and judge grader is a real model call on the maintainer's account.
- No weakened gate: zizmor flags package installs outside a lockfile in a workflow, and the repository has no Node manifest.
- A new workflow must run on the pull request that adds it.

## Considered options

- An informative workflow triggered by the `run-evals` label, installing its tools through `scripts/check.py ci-eval-tools`
- A blocking gate on every pull request
- Local runs only, results attached to the pull request

## Decision outcome

Chosen option: **an informative, label-triggered workflow**.

- Trigger: `pull_request` of type `labeled` with the label `run-evals`; re-run by removing and re-applying it. `workflow_dispatch` was not used because GitHub offers it only for workflows already on the default branch, while a `pull_request` workflow from a same-repository branch runs from that branch.
- The job has `contents: read` only and authenticates with the existing `CLAUDE_CODE_OAUTH_TOKEN` secret.
- `scripts/check.py ci-eval-tools` installs the latest Claude Code, `bubblewrap` and `socat` (the Linux sandbox for granted shell commands) and the npm packages each plugin lists in `evals/ci-packages.txt`; like `ci-tools`, it refuses to run outside GitHub Actions and follows ADR unpinned-tooling-and-shebang-interpreters. No `package.json` is added.
- For each plugin the pull request changes that has `evals/`, the job runs `claude plugin eval` with `--trust-plugin --scaffold --allow-real-servers --no-publish`, pinned agent and judge models, `--runs 1`, `--max-cost-usd 10` and `--threshold 0`, so scores never fail the job while load and run errors do. Grants are Write, Edit, `Bash(npx|npm|curl *)`, every server in the plugin's `.mcp.json`, and the extra grants in `evals/ci-allow-tools.txt`.
- The result summary goes to the job's step summary; the evidence line goes into the pull request.

### Consequences

- Good, because the delta is measured in an isolated runner before release, on demand.
- Good, because no gate is weakened and no Node manifest is added.
- Bad, because each run costs real usage, up to the ceiling per plugin.
- Bad, because the `run-evals` label must exist on GitHub before it can be applied; the labels workflow only creates labels after a merge.

### Confirmation

`actionlint` and `zizmor --offline` pass on the workflow; tests cover `ci-eval-tools` refusing outside Actions and reading the package lists. The first labeled run on the pull request that adds `svelte-development` is the runtime proof. Revisit when evals should become a blocking gate.

## Pros and cons of the options

### Label-triggered informative workflow

- Good, because it runs only when asked and isolates the run.
- Bad, because it depends on the maintainer applying the label.

### Blocking gate on every pull request

- Good, because no plugin change merges unmeasured.
- Bad, because every push pays for model calls, and scores vary between runs.

### Local runs only

- Good, because nothing new is added.
- Bad, because scores with real servers are advisory outside an isolated environment.

## More information

Partly replaces the CI exclusion in [docs/testing.md](../../testing.md#behavioral-evaluation). Docs: [plugin evals](https://code.claude.com/docs/en/plugin-evals) ("Run evals in CI", "Grant tools", "How runs are isolated").
