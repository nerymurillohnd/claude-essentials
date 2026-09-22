# evidence-reader 0.1.0 — release review record (2026-09-22)

A snapshot of the reviews run while bringing evidence-reader into the marketplace, on branch
`feat/evidence-reader` (base `13578e3`). Each finding's fix and the gate that now catches it are
in [DEBT-0040](../maintenance/resolved-debt.md); deferred items are DEBT-0041 and DEBT-0042 in
[`pending-debt.md`](../maintenance/pending-debt.md).

| Review | Scope | Findings | Outcome |
| --- | --- | --- | --- |
| `plugin-coherence-auditor` | 60 files end to end, live hooks/sub-agents/skills/plugins-reference/tools-reference docs and changelog (2.1.280) | 23: 0 high, 10 medium, 13 low | All fixed. Medium: unsubstituted `${CLAUDE_SKILL_DIR}` in references, exit 5 read as "poppler missing" when the interpreter was too old, `--delimiter` placement, the gate's `systemMessage` audience, handback delivery wording, no rule for a denied tool call, no command for checking a cached total, undefined PARTIAL/INCOMPLETE, document-reading's trigger scope, no delegation contract |
| `/code-review high` | the plugin diff and the shared tooling it changed | 10 | All fixed. Formula evaluator re-entrancy (`A1 = B1+5` recomputed as 6), ROUND half-even, DATE ignoring `date1904`, tracked changes dropped in Word tables and phantom paragraph-mark changes, `find --column` on ragged rows, a stale handback copy, an uncapped block without retry state, a 1 MB `jq --arg` test that fails on Linux, no `.gitattributes`, non-streaming sheet layout |
| `/security-review` | the same | 0 at confidence ≥ 8 | One 6/10 candidate (ImageMagick picking a decoder from file content) hardened: every input carries the `<format>:` prefix its magic bytes proved, and unknown formats are refused |
| `/claude-api prompt-audit` | 4 `SKILL.md`, 3 agents | 0 to change, 3 low flags | Clean; no edits |
| completion verifier: coherence | the working tree against `13578e3` | 6 | All fixed: fixes without a failing-first case, a stale index, CHANGELOG missing the handback hook, dates, image-analysis exit codes, DEBT-0039's title |
| completion verifier: depth | tests and mocks, with each fix reverted in a scratch copy | 9 | All fixed: five fixes no case caught, suites run with CI's older `python3` (now `BNV_TEST_PYTHON`), silent skips, a temp-folder leak, an untested fail-open branch |
| completion verifier: edges | hostile and odd inputs in both directions | about 30 rows failing | Fixed: tracebacks with an undocumented exit 1, a DTD accepted in UTF-16, text inserted then deleted shown as original, moves shown twice, an unterminated CSV quote swallowing rows, `²` accepted as a digit, `-`-prefixed file names read as options, control characters in the gate's JSON. Accepted as minor: `--scale ≤ 0` ignored, a corrupt image with tools installed exits 5, gate time above ~12 MB reports |
| `repo-auditor` on `1c347b6` | the branch against `main` | `VERDICT: FAIL`, 11 items | Fixed: a stray stderr file in `skills/`, the handback hook's scope, a badge outside the catalog (and the missing catalog check), the catalog row wording, eval case 05, the `script_env` docstring. Waived by the maintainer: `/plugin-design` (DEBT-0041) and the eval run (DEBT-0042) |

Final suites on the branch: `test-scripts.sh` 101/101 and `test-hooks.sh` 22/22 under `bash`
and `/bin/bash`; `make check` exit 0.
