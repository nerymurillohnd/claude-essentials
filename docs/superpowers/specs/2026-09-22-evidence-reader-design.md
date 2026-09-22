# evidence-reader 0.1.0 — design

**Status:** derived after the fact. The plugin was built outside this repository and moved into
`plugins/evidence-reader/` on 2026-09-22 already complete, so `/plugin-design` never ran before
it was built. On 2026-09-22 the maintainer chose "Spec derivado + exención": this spec records
the design as the files implement it, and the waiver of the `/plugin-design` checklist is
DEBT-0041 in [`pending-debt.md`](../../maintenance/pending-debt.md).
**Canonical user-facing contract:** [`plugins/evidence-reader/README.md`](../../../plugins/evidence-reader/README.md)
(components, Requirements, Security, Limitations). This spec records the decisions and their
evidence; it does not repeat the README's tables.

## Goal

When Claude reads a user's files (contracts, reports, workbooks, exports, photos), it reads all
of them, ties every claim to a checkable place in the source, and says plainly what it could not
read, instead of skimming, sampling or guessing.

## Requirements

1. **Complete coverage.** A full read covers every page, row, sheet or image in fixed chunks, and
   the report logs the ranges covered (`evidence-standard` §4).
2. **A receipt per claim.** Every finding carries one locator from the citation schema
   (`p12 L4`, `Sales!D12`, `row 50000 (line 50001)`, `region x=… y=… w=… h=…`).
3. **No invented values.** A workbook value is cached, recomputed or missing, never presented as
   stored when it is not; totals come from script output.
4. **Unknown is said.** Whatever was not read goes under **Not verified** with its reason.
5. **Read-only.** The agents have no file-writing tools; derived images go to a private temp
   folder and are cited back to the original.
6. **File contents are data.** Embedded instructions are reported as suspected prompt injection.
7. **Privacy by default.** GPS, device serials and owner fields in metadata are withheld unless
   asked for.
8. **The report's form is enforced.** A `SubagentStop` gate sends an agent back, at most twice,
   when its report lacks the template sections.

## Decisions

- **Shape: `bundle`.** Four skills (one contract, `evidence-standard`, preloaded by three
  per-format skills), three read-only agents that keep page images and extractor output out of
  the main context, one hook pair. One agent per format keeps each agent's instructions short
  and its tool path narrow.
- **Stdlib-only Python extractors.** No third-party packages, so nothing to install. Python 3.14
  is the floor (maintainer decision, 2026-09-22, as DEBT-0029 set for agent-self-knowledge):
  each extractor checks the version first and exits 5 with a message.
- **Optional system tools, reported not installed.** poppler, exiftool, ImageMagick 6/7, sips and
  heif-convert are probed by `check-requirements.sh`, which prints a `TIERS` line and never
  installs anything; a missing tool is a degraded mode named in the report.
- **Gate as a plugin hook** ([ADR-0007](../../decisions/adr-0007-gates-ship-as-plugin-hooks.md)):
  `SubagentStop` scoped by matcher to the three agents, and `PreToolUse` on `SubagentHandback`
  to see the report an agent hands back in auto mode. Modes `block` (default), `warn`, `off`
  through the `enforcement` `userConfig` option.

## Non-goals

- Creating, editing or converting documents for delivery.
- Legacy binary formats (`.doc`, `.xls`, `.ppt`), OpenDocument, iWork, audio and video.
- Opening encrypted files, cracking passwords or running macros.
- Any network access.
- Checking that a receipt is true: the gate checks the report's form only.

## Failure modes

| Failure | Behavior |
| --- | --- |
| `python3` older than 3.14 or missing | Every extractor exits 5 with the version it found; `TIERS python3=too-old` or `missing` |
| poppler missing | `pdf_probe.py` exits 5; long PDFs are partly verified and the uncovered pages listed |
| No converter or cropper for an image | `image_tool.py` exits 5 with an install hint or the converter's own error |
| Encrypted or legacy binary file | Exit 3, reported as not reviewed |
| Part declares a DTD or entity (UTF-8 or UTF-16), or expands past 500 MiB | Exit 4, refused |
| Malformed or hostile input (bad XML, formulas, CSV quoting, regions) | Exit 2 with a message; a formula the evaluator cannot take is `NOT RECOMPUTED` |
| `jq` missing, bad hook payload, no trusted state directory | The gate fails open; a repeat stop with no retry state is released |
| Main session reads a short file inline | No agent report, so the gate does not run (stated in Limitations) |

## Surfaces

- **Claude Code:** tested from a local checkout (`claude -p --plugin-dir`, 2026-09-21, Claude
  Code 2.1.278); not yet installed from the remote marketplace, so 🧪.
- **Claude Cowork:** untested; the extractors and hook need `python3`, `bash` and `jq` in the
  sandbox.
- **Windows:** the hook needs Git Bash on `PATH`; only macOS and Linux are tested.

## References

- Hooks reference: `SubagentStop` matchers on agent type, `SubagentHandback` and
  `last_assistant_message` (code.claude.com/docs/en/hooks).
- Subagents: `tools`, `disallowedTools`, `maxTurns`, `omitClaudeMd`, preloaded `skills`
  (code.claude.com/docs/en/sub-agents).
- Skills: `${CLAUDE_SKILL_DIR}` is substituted only in `SKILL.md` and `allowed-tools`
  (code.claude.com/docs/en/skills).
- Plugins reference: `userConfig`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PLUGIN_OPTION_*`.
- Changelog: the 2.1.275 minimum (agent-name matchers), 2.1.271 (`omitClaudeMd`).

## Verification

- `scripts/plugin_validation/suites/evidence-reader/test-scripts.sh`: extractor behavior,
  locators, exit codes, hostile inputs, the Python floor, private work folders.
- `scripts/plugin_validation/suites/evidence-reader/test-hooks.sh`: gate modes, retries,
  handback, fail-open paths, large payloads, both bash versions.
- `make check` runs both suites under `bash` and `/bin/bash` with the repository's Python
  (`BNV_TEST_PYTHON`).
- `evals/`: five behavioral cases, including one that must not fire. Not run for 0.1.0 (DEBT-0042).
- Independent review on 2026-09-22: `/plugin-release-review` (coherence audit, code review,
  security review, prompt audit) and three completion verifiers; findings and their gates are in
  DEBT-0040.
