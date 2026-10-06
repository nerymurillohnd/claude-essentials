---
status: accepted
date: 2026-10-06
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Eval runs inherit their models and keep their full results

## Purpose

Record that the CI eval workflow no longer pins the agent and judge models, records the models each run used instead, and keeps the full result of every run as a workflow artifact.

## Scope

`.github/workflows/plugin-evals.yml` and the eval rules in `.claude/rules/testing/plugin-evals.md`. It replaces the "pinned agent and judge models" part of [ADR plugin-evals-in-ci](ADR_2026-10-05_plugin-evals-in-ci.md); the label trigger, the grants, the cost ceiling and the informative threshold stay as that ADR decided.

## Context and problem statement

The first CI run of the `svelte-development` suite pinned `claude-sonnet-5-5` as the agent and `claude-haiku-4-5-20251001` as the judge, and its job summary kept only each case's score, delta and errors. The full result document, which holds every grader's verdict per run, stayed in `RUNNER_TEMP` and was lost when the job ended. Without it, nobody could tell which graders always pass or always fail, whether a zero delta came from the plugin or from a broken grader, or whether trace graders see tool calls made inside a subagent.

The maintainer decided on 2026-10-06, in the session that prepared `svelte-development` 0.2.0, that eval models are inherited, not pinned.

## Decision drivers

- The suite should measure the plugin with the models users actually get by default.
- Every grader verdict must be available after the run, for analysis.
- The Claude Code docs recommend pinning `--model` in CI "so a model rollout isn't mistaken for a plugin regression" (plugin evals, command options).

## Considered options

- Inherit the models, record the models each run used, and keep the full result as an artifact
- Keep both models pinned

## Decision outcome

Chosen option: **Inherit the models, record them, keep the full result**, because it measures the plugin under the defaults users run and makes every verdict available for analysis. The delta compares the two arms of the same run, which use the same model, so it stays meaningful; comparisons across runs are valid only when the recorded models match.

### Consequences

- Good, because a run reflects the default models of the Claude Code version CI installs.
- Good, because the uploaded result and HTML report hold every grader verdict, the trace evidence and the configuration.
- Bad, because a change of default model between two runs can move scores without any plugin change; the recorded models make that visible, they do not prevent it.
- Bad, because the uploaded results are readable by anyone who can read the repository's workflow artifacts; they hold eval transcripts of the public fixture, never secrets.

### Confirmation

Each run's job summary lists the model keys found in the result document, and the run's artifacts include `evals-<plugin>.json` and the `evals/results/` directory. Revisit when the eval docs document a stable model field, or when a cross-run comparison is needed: then pin for that comparison only.

## Pros and cons of the options

### Inherit, record and keep the full result

- Good, because it measures what users get.
- Bad, because scores across runs need the same recorded model to compare.

### Keep both models pinned

- Good, because runs are comparable over time, as the docs recommend.
- Bad, because it measures one fixed model, not the defaults users run, and the maintainer chose against it.

## More information

Docs: [plugin evals](https://code.claude.com/docs/en/plugin-evals) ("Command options", "JSON result"). Artifact action: `actions/upload-artifact` v7.0.1, pinned by SHA.
