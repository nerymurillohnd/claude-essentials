# Plugin eval protocol

Applies while authoring or running an eval suite. Evals measure behaviour a static validator cannot
see. They cost money and return different numbers for the same input, so they never gate a merge.
Static checks are governed separately; see the validation rules.

## Principles

- An eval proves behaviour, never the correctness of a file.
- A static check is free and deterministic; if a check can be static, it is not an eval.
- An eval is never a required status check, never a Stop hook, and never blocks a PR.
- A green eval is evidence for a claim, not permission to ship.
- Measure **uplift**, not correctness: the headline number is Δ (with-plugin minus without-plugin).
- Non-determinism is the default: `--runs` falls back to `case.runs ?? 3`.
- Never add a case to raise a score. A suite that cannot fail is a vanity metric.

## When to run

- Run the full suite only when a plugin's runtime files change: skills, agents, hooks, scripts, `plugin.json`.
- Never run it for a README, a CHANGELOG, a doc, or a manifest metadata edit.
- Run a single case with `--case <glob>` while authoring that case.
- Pilot the suite with `--runs 1` before paying for the full thing.
- Re-run the full suite once before the PR, on the final head.
- If a run is skipped, say so in the PR and why.

## Before writing a case

- Read the plugin's `SKILL.md`, its references, its `hooks.json` and its scripts. Build nothing from memory.
- Write down what a good answer looks like, and what a bad one looks like, before designing graders.
- Run the plugin's real tool on the real input. Anchor every rubric to what it actually reports.
- Verify every premise the case rests on. A case built on a false premise measures nothing.
- Prefer real user prompts. Never lift an example out of `SKILL.md` as a case input.

## Writing a case

- One case per directory under `evals/`: `prompt.md` plus `graders/*.md`; add `case.yaml` only when the
  case needs scaffold, tags, or run counts.
- A case directory with no `graders/` fails to load (`invalid case.yaml: graders: Required`) at $0.00,
  and the other cases still run — check the load errors, not just the table.
- Name cases with a numeric prefix and the behaviour they test.
- One flow per suite. 4–6 cases that must fire, 1–2 that must not.
- Each case must be able to fail for a different reason. Variants of one prompt add cost, not signal.
- Make the prompt self-contained. The sandbox is an empty directory with no repo, no fixtures, no history.
- Each run executes in a throwaway sandbox: an empty `cwd` and a synthetic `HOME`, not yours.
- `PATH` is inherited verbatim, but entries under your real `HOME` do not resolve: a binary in
  `~/.local/bin`, `~/.cargo/bin` or `~/.nvm` is absent, while `/opt/homebrew/bin` and `/usr/bin` work.
- Never assume a tool is present. Probe it with `--keep-temp` and read `out/trace.jsonl`.
- Name in the prompt any file a grader will read, so the path is deterministic.
- Write prompts in the language real traffic uses.
- Size `max_turns` and `timeout_seconds` to the work: one-shot answer ≈ 5 turns / 120 s; retrieval or
  tool use ≈ 25 turns / 600 s. An under-set budget scores 0 and reads as "the plugin did nothing".
- Version prompts, graders, fixtures and mocks. Never version `results/`.

## Granting tools

- List every tool the skill must call before running anything.
- A gated tool (`Bash`, `Write`, `Edit`, `WebFetch`, `mcp__*`) needs **two** grants: the case's
  `allowed_tools` **and** the operator's `--allow-tools`. Missing either one yields `not granted`.
- The case list is the universe; a skill's own `allowed-tools` frontmatter grants nothing here.
- An ungranted tool makes the suite measure text, not behaviour.
- A grader asserting something was **not** done is meaningless unless the run could have done it.
  Grant `Write` and `Edit` before grading "wrote nothing"; grant `Bash` before grading "never ran it".
- Both arms receive the grant. That makes every Δ conservative, which is correct.

## Writing graders

- One grader per file, one claim per grader.
- Prefer a free grader (`regex`, `file_exists`, `tool_used`) over an `llm` grader whenever the claim
  is mechanical.
- Every case needs at least one outcome grader. `tool_used: Skill` never scores and cannot be the only one.
- Grade the outcome, not the trajectory. Measure the act, not the mention: `tool_used` on `Bash` with
  the forbidden flag beats `not_contains` over the text.
- Anchor literal quotes by copying them from the live source at authoring time, and record the date.
- A rubric must never require more than the contract requires. State that changes beyond the named
  findings neither help nor hurt.
- Where a contract has two correct paths — proceed, or stop because a prerequisite is missing — the
  rubric must accept both.
- Give every skill at least one negative case that must not fire it.
- A must-not-fire grader needs `min: 0`, `max: 0` **and** `arm: both`. Without `arm`, it is display-only.
- Mark plugin-fired indicators `with-only`; under `with-without` they signal activation and are not
  part of the score.
- A grader lifted from `SKILL.md` wording is secondary: `weight: 0.5`, paired with an outcome grader.
- Choose the baseline arm deliberately: a native subagent is a harder and more honest baseline than nothing.
- Use a judge model different from the agent model. A model grading its own output prefers it.

## Suite invariants — non-negotiable

- At least one case that must **not** fire, with an outcome grader of its own.
- At least one outcome grader per case.
- `runs: 3` minimum.
- `--ablation with-without` always.

## Running

- Canonical invocation:

  ```bash
  claude plugin eval plugins/<id> \
    --ablation with-without \
    --allow-tools <tools...> \
    --model <model> --judge-model <model> \
    --max-cost-usd <n> --no-publish
  ```

- Always pass `--no-publish`; publishing the HTML report to claude.ai is the default when the account
  supports it.
- Pin `--model` and `--judge-model`; an unpinned run is not comparable to the previous one.
- Set `--max-cost-usd` on every invocation; the ceiling is checked before each run launches and exits 2 when hit.
- Pass `--scaffold` only for cases you wrote yourself: it runs author-supplied bash as you.
- Pass `--trust-plugin` only in CI, and only for a plugin in this repo.
- Leave `--mocks` at `record`; never pass `--allow-real-servers` or `--mocks off` for a plugin you did not write.
- Raise `-j` above 1 only when the wall-clock cost is real; every run is a full child on one rate limit,
  and errors under parallel runs are throttling, not plugin failures.
- Confirm `suite.plugins` lists the plugin with no `problem`. An empty list means the with-arm ran
  without the plugin and the run is meaningless.
- Fix any `⚠ case … cannot pass with the granted tools` before reading any score.

## Reading results

- Read `report.html` for the answers and grader verdicts; `aggregate-result.json` carries neither.
  Traces need `--keep-temp`.
- Record the absolute score of both arms before naming any delta.
- A moved delta is usually the baseline arm falling, not the plugin improving; state which one moved.
- A negative Δ is a grader defect until proven otherwise. Read both arms' answers before blaming the plugin.
- Confirm a rubric's demand against the real tool before accepting that the plugin failed it.
- A case scoring 1.00 in both arms measures something the base model already does. Keep it as a guard,
  do not count it as uplift.
- State every case that scored 0.00 and why, before reporting any average.
- Never report an improvement from a single run.
- Report the run's cost with the numbers.
- `--threshold` defaults to 1.0, so an ablation run exits 1 even when every result is good; read the
  scores, never the exit code, and never lower it to hide a failure.

## Recording

- Eval numbers never go in a README, a skill, or a plugin manifest.
- Keep numbers in the runner output, in the PR body, or in a dated file under `docs/audits/`.
- `evals/results/` is git-ignored; nothing from a local run is committed.
- Record a withdrawn or invalidated case in `docs/maintenance/` with its reason.

## Prohibitions

- Never weaken a grader, lower a threshold, or delete a case to make a suite pass.
- Never soften a grader to make it pass; correct it only when it demands more than the contract.
- Never weaken a plugin to satisfy a grader that is wrong.
- Never present an unverified number, an estimated cost, or a remembered score as measured.
- Never report a Δ from a run you have not confirmed loaded the plugin.
- Never make an eval a required check, a Stop hook, or a merge condition.
- Never run an eval to prove something a static check already proves.
