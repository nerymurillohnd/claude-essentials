# Evals — `claude-code-docs`

Behavioural eval suite for the plugin's single skill. One flow: **cited retrieval** —
an answer about Claude Code must come from the live documentation with the deciding
sentence quoted verbatim, its URL, and the version verified against, never from memory.

Run results are not recorded here. They live in `results/` (git-ignored) and, when a
dated result is worth keeping, in `docs/audits/`.

## Cases

| Case | What it can fail at | Baseline it is measured against |
| --- | --- | --- |
| `01-cites-verbatim-with-url` | Quoting the documentation's own sentence, with its URL, for a `PreToolUse` blocking decision | The built-in `claude-code-guide` subagent — `Agent` is granted in both arms, so the delta measures the plugin against the best native resource, not against nothing |
| `02-routes-to-the-right-page` | Landing on `plugin-marketplaces` (authoring) rather than a neighbouring page, without inventing runtime requirements | Memory |
| `03-crosses-corpus-on-models` | Fetching both corpora and attributing each fact to the source that owns it, instead of stating a model id from memory | Memory |
| `04-checks-changelog-and-binary` | Reading the changelog **and** the installed build, not just the docs | Memory |
| `05-ignores-unrelated-code-task` | Not firing on unrelated work — while still doing the work | — |

Prompts are in Spanish (real traffic); quoted sentences are expected in English,
because `references/sources.md` requires citing `/en/` for technical claims even when
answering in Spanish.

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/agent-self-knowledge --ablation with-without \
  --allow-tools Bash WebFetch \
  --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 12
```

The judge is deliberately a different model from the agent: a model grading its own
output prefers it.

A gated tool (`Bash`, `Write`, `Edit`, `WebFetch`, `mcp__*`) needs **two** grants, and the runner
refuses it unless it has both: the case must list it in `allowed_tools`, and the operator must pass
it in `--allow-tools` on the command line. A skill's own `allowed-tools` frontmatter counts for
neither — it only pre-approves permission prompts for tools already granted.

That is why the four retrieval cases list `Bash` and `WebFetch`, and why the command above passes
them too. Without both, `ccdocs.py` cannot run: the first full suite scored a delta that measured
the skill answering from its bundled `references/` rather than from live retrieval.

Both arms receive the grant, so the delta measures the skill, not the tool grant. That makes it a
conservative number: the baseline can fetch the docs too.

## Maintenance

The graders in `01` match sentences quoted verbatim from the live documentation as of
2026-09-20 (Claude Code 2.1.278). If upstream rewrites that section the case fails on an
upstream change, not on a regression — `ccdocs.py selfcheck` tells them apart.

## CI policy

- **Always, required:** `claude plugin validate --strict` (`make validate-cli`).
- **Conditional, never blocking:** `evals.yml` runs `claude plugin eval` for this plugin
  only when the pull request changes one of its runtime files (`.claude-plugin/**`,
  `skills/**`, `agents/**`, `commands/**`, `hooks/**`, `scripts/**`, `.mcp.json`,
  `.lsp.json`, …), the same classification that decides a version bump. A change under
  `evals/**`, `README.md`, `CHANGELOG.md`, `LICENSE` or `docs/**` never selects it.
- **Never in CI:** `claude plugin eval init`.
- The job uploads the aggregate JSON and `report.html` as workflow artifacts, skips when
  `ANTHROPIC_API_KEY` is absent, and is never a required check; `results/` stays git-ignored.
