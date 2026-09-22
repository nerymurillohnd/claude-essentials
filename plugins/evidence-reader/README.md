# 🔎 Evidence Reader

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fevidence-reader%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Python](https://img.shields.io/badge/Python-%E2%89%A53.14-3776AB?logo=python&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![poppler](https://img.shields.io/badge/poppler-recommended-555555)
![Hooks](https://img.shields.io/badge/hooks-SubagentStop,_PreToolUse-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **When Claude reads your files, it reads all of them, cites where every fact came from, and tells you plainly what it could not read.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Evidence Reader helps anyone who hands Claude contracts, reports, spreadsheets,
exports or photos get answers they can check. Three read-only agents do the
heavy reading outside your main conversation and return one report per job,
with a page, cell, row or image-region locator on every claim and a checklist of
what was and wasn't covered. It does **not** create or edit documents,
spreadsheets or images.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| A 120-page PDF contract must be reviewed in full | `document-reader` reads the text layer page by page in 20-page chunks and reads scanned pages with vision | Clauses quoted with `p<page> L<line>`, and a coverage line proving pages 1–120 were read |
| A Word contract under negotiation | The Word extractor shows every paragraph under its heading, plus tracked insertions, deletions and comments | "Payment > P4" citations instead of page numbers Word doesn't store, and who changed FOB to CIF |
| A workbook exported by another system | `tabular-auditor` lists every sheet (hidden ones too), formulas beside cached values, error cells and odd formulas | No invented totals: missing values are flagged, recomputations are labelled |
| A 2-million-row CSV export | The profiler streams the whole file | Exact row count and exact decimal column sums, never a sample |
| Twenty iPhone photos of product labels | `image-inspector` converts HEIC, crops small print and views every image | Lot codes and dates per image with region locators and legibility notes |
| A folder with repeated scans | Exact and perceptual duplicate detection | Each image reported once, with its copies listed |

## 🚫 What it does not do

- **Does not** create, edit, convert for delivery or fix documents, spreadsheets or images — use a document-authoring skill for that.
- **Does not** run macros, crack passwords, or open encrypted files; those are reported as not reviewed.
- **Does not** call any network service; every extractor runs locally.
- **Does not** read legacy binary formats (`.doc`, `.xls`, `.ppt`), OpenDocument, Apple iWork, audio or video in this version.
- **Not a fit when** you want a quick gist of one short file — Claude reads that directly; this plugin earns its keep on long, many, or high-stakes files.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install evidence-reader@claude-essentials
```

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Evidence Reader** from the list.
The skills and agents should load there; the extractors need `python3` (and the
recommended tools) inside Cowork's sandbox, which hasn't been verified. See
[Compatibility](#-compatibility).

> [!TIP]
> Installation is complete when `/plugin list` shows `evidence-reader` as enabled,
> `/agents` lists `evidence-reader:document-reader`, `evidence-reader:tabular-auditor`
> and `evidence-reader:image-inspector`, and `/hooks` lists a `SubagentStop` hook from
> **Plugin Hooks**.

Then check which optional tools your machine has. The skills run this check for you
at the start of every job; to run it yourself, replace `${CLAUDE_PLUGIN_ROOT}` with the
plugin's install directory (under `~/.claude/plugins/`), because your shell does not set it:

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/check-requirements.sh
```

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers four skills, three subagents and two hooks (`SubagentStop`, `PreToolUse` on `SubagentHandback`) in Claude Code's plugin state, and adds an `enforcement` row to `/config` (default `block`). |
| **Does not** | Touch your files, repositories, settings files or CLAUDE.md. The skills and agents run only when Claude reads files with them; the `PreToolUse` hook runs on every `SubagentHandback` in a session and exits at once, writing nothing, for any agent that is not one of the three. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable evidence-reader@claude-essentials
/plugin uninstall evidence-reader@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**. Uninstalling removes the hooks at once.
Uninstalling from the last scope also deletes the plugin's data directory, which
holds only the gate's retry counters and report copies. When Claude Code sets no data
directory, the gate keeps them in `$TMPDIR/evidence-reader-gate-<uid>` instead, which
uninstalling does not remove; each file there is deleted when its agent finishes. Converted images and crops
live in private folders in your system temp folder (`$TMPDIR/evidence-reader-*`),
one per conversion, and are removed by the operating system's normal temp cleanup.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`evidence-standard`](skills/evidence-standard/SKILL.md) | — | Any evidence-reader job: defines receipts, coverage, "unknown" instead of guesses, and the report template | Claude only (preloaded by the agents) |
| [`document-reading`](skills/document-reading/SKILL.md) | `/evidence-reader:document-reading` | You ask to read, review, summarize or extract from PDF, Word, PowerPoint, Markdown or text files | Claude + user |
| [`tabular-data`](skills/tabular-data/SKILL.md) | `/evidence-reader:tabular-data` | You ask to audit, reconcile, total or extract from workbooks, CSV/TSV, JSON or XML | Claude + user |
| [`image-analysis`](skills/image-analysis/SKILL.md) | `/evidence-reader:image-analysis` | You ask to read, transcribe, describe or compare images, photos or scans | Claude + user |

## 🤖 Agents

| Agent | Role | Tools | Model |
| --- | --- | --- | --- |
| [`document-reader`](agents/document-reader.md) | Reads documents completely and returns one cited report | `Read, Grep, Glob, Bash, Skill` (no `Write`, `Edit` or `Agent`) | `inherit` |
| [`tabular-auditor`](agents/tabular-auditor.md) | Audits workbooks and data files programmatically and returns one cited report | `Read, Grep, Glob, Bash, Skill` (no `Write`, `Edit` or `Agent`) | `inherit` |
| [`image-inspector`](agents/image-inspector.md) | Views every image, crops fine print and returns one cited report | `Read, Grep, Glob, Bash, Skill` (no `Write`, `Edit` or `Agent`) | `inherit` |

Each agent preloads `evidence-standard` plus its own format skill, runs without
your CLAUDE.md files (`omitClaudeMd`), stops after 150 turns at most, and cannot
spawn further agents. The main conversation receives only the finished report;
page images and extractor output stay inside the agent.

## 🪝 Hooks and side effects

| Event | Matcher | What it does | Blocks? |
| --- | --- | --- | --- |
| `SubagentStop` | `^evidence-reader:(document-reader\|tabular-auditor\|image-inspector)$` | Checks that the returned report has the Status, Tier, Files reviewed, Findings, Not verified and Needs human judgment sections | Yes, in `block` mode: sends the agent back to complete the report, at most twice, then lets it stop and shows you a warning that the report is incomplete (the warning reaches you, not Claude) |
| `PreToolUse` | `SubagentHandback` | When one of the three agents hands its report back through that tool, keeps a copy so the gate checks the real report; ignores every other agent | No |

The gate writes only small retry counters and handed-back reports for its own
agents under the plugin's data directory, deleting each when the agent finishes.
It fails open: malformed input or a missing `jq` never blocks an agent. Set
`enforcement` in `/config` to `warn` or `off` to soften or disable it.

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

- **Least privilege:** the agents have no file-writing tools. They use `Bash` to run the bundled extractors and the optional tools listed under Requirements; each skill pre-approves only its own scripts (`Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)`) and the requirements check for the turn that invokes it.
- **Cowork:** not tested in Cowork; the extractors need `python3` in the sandbox.

## 📋 Requirements

> [!IMPORTANT]
> **Requires Python 3.14 or later as `python3` on your `PATH`.** Every extractor
> stops with exit code 5 and a message naming the version it found when `python3` is
> older, and the report lists those files as not reviewed. The Python that ships with
> the Xcode Command Line Tools on macOS (3.9) and the default `python3` of Ubuntu 24.04
> (3.12) or Debian 13 (3.13) are too old: install 3.14 from python.org, with
> `brew install python@3.14`, or with `uv python install 3.14 --default`.

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.275 | `claude --version` | `SubagentStop` matchers on agent names fire only for the named agents from 2.1.275; `omitClaudeMd` needs 2.1.271. Above npm `stable` at release time |
| Python | 3.14 | `python3 -V` | Runs every bundled extractor (standard library only). It is the only Python the repository's gates lint, type-check and run the extractors with |
| Bash | 3.2 | `bash --version` | Runs the requirements check and the hook |
| jq | 1.6 | `jq --version` | Parses hook payloads for the report gate |
| poppler | 26.09 tested (recommended) | `pdftotext -v` | Exact PDF text with page and line locators, page counts, scanned-page detection, and Read's page-range reading of long PDFs |
| exiftool | 13.55 tested (recommended) | `exiftool -ver` | Image metadata (capture date, software, orientation) |
| ImageMagick | 7.1.2 tested (recommended); 6 accepted | `magick -version` (7) or `convert -version` (6) | HEIC and every TIFF page to PNG, cropping and enlarging fine print, near-duplicate detection. Version 7 installs `magick`; Debian and Ubuntu still ship version 6 as `convert` and `compare`, which the scripts also use |
| sips | macOS built-in | `sips --help` | HEIC conversion and cropping on macOS when ImageMagick is absent (first TIFF page only) |
| heif-convert | any (optional, not tested) | `heif-convert --version` | HEIC conversion on Linux when ImageMagick lacks HEIC support. On Linux, HEIC also needs the HEVC decoder `libde265` |

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/check-requirements.sh
```

It only checks; it never installs anything or asks for credentials. Install the
recommended tools with `brew install poppler exiftool imagemagick` on macOS, or
`apt install poppler-utils libimage-exiftool-perl imagemagick libheif-examples libde265-0`
on Debian and Ubuntu. On Windows, the hook and the requirements check need Git
Bash on `PATH`.

Environment variables the scripts read: the hook reads `CLAUDE_PLUGIN_DATA` (set by
Claude Code) and `CLAUDE_PLUGIN_OPTION_ENFORCEMENT` (the `enforcement` option); the
image tool and the hook's fallback state use `TMPDIR`. `${CLAUDE_PLUGIN_ROOT}` in the
commands above is filled in by Claude Code inside skills and hooks only.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
folder containing any PDF longer than 20 pages:

```text
Revisa completo <file>.pdf y dime qué dice la última página, con cita.
```

Expected result: Claude delegates to `evidence-reader:document-reader`, and the
report ends with a Files reviewed table whose coverage adds up to every page,
and cites the last page as `p<last> L<line>`.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/evidence-reader --strict
scripts/plugin_validation/suites/evidence-reader/test-hooks.sh
scripts/plugin_validation/suites/evidence-reader/test-scripts.sh
claude plugin eval plugins/evidence-reader --ablation with-without --allow-tools Bash Write Edit --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 12
```

`make check` runs both suites under `bash` and under `/bin/bash`, and each suite runs
its handler or extractor with the same interpreter. Both suites live in the repository,
not in the plugin, so neither is installed. `ER_TEST_PYTHON` selects the Python
interpreter `test-scripts.sh` runs the extractors under; otherwise it uses `BNV_TEST_PYTHON`
(the repository's Python, set by `make check`) or `python3`. The suite
also checks that an older interpreter gets each extractor's version message and exit 5.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | 🧪 Not tested | 2026-09-21, Claude Code 2.1.278, local checkout only | Live `claude -p --plugin-dir` runs: the three agents load, `document-reader` preloads both skills, resolves its reference files and scripts, reads a 45-page PDF in 20-page chunks and returns the report template; the report gate blocks an incomplete report and the agent completes it. Extractor suite (101 cases) and hook suite (22 cases) pass on bash 3.2 and 5.x with Python 3.14; Python 3.9 gets the version message and exit 5 (measured 2026-09-22). Not yet installed from the remote marketplace |
| Claude Cowork | 🧪 Not tested | — | Skills and agents should load; extractors need `python3` and the optional tools in the sandbox; hooks need `bash` and `jq` there |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Full read of a long report**

```text
Read all of quality-report.pdf and list every lot whose moisture is above 4%.
```

→ `document-reader` probes the PDF, reads pages 1–20, 21–40 and 41–45 from the
text layer, and returns each lot with its `p<page> L<line>` receipt and a
coverage line for all 45 pages.

**Workbook audit without invented numbers**

```text
Audita sales.xlsx: ¿cuadra el total y hay fórmulas raras?
```

→ `tabular-auditor` reports that `Sales!D12` (`=SUM(D2:D11)`) has no cached
value because the file was never calculated, gives the recomputed 97.5 labelled
as recomputed, notes the hidden sheet `Internal`, and flags `D12` as a formula
outlier that is expected for a total row.

**Label photos from a phone**

```text
Extract the lot and expiry date from every photo in ./labels
```

→ `image-inspector` converts the HEIC photos, crops the small print, and returns
one line per image such as `label.heic — Batana oil 250 ml label; extracted: LOT-042,
EXP 2028-03 (region x=0 y=180 w=1200 h=90); legibility: clear`.

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | The files you point it at, read in memory only |
| Write | Temporary PNG conversions and crops in new private folders `$TMPDIR/evidence-reader-*`; the gate's retry counters and report copies in the plugin data directory (or `$TMPDIR/evidence-reader-gate-<uid>` when Claude Code sets none), each deleted when its agent finishes. Never your files |
| Process | `python3` extractors bundled with the plugin; optional `pdftotext`, `pdfinfo`, `pdftoppm`, `exiftool`, `magick`, `sips`, `heif-convert`; `bash` and `jq` for the hook |
| Network | Not used |
| Credentials | None |

- **Human approval:** the agents' `Bash` calls follow your normal permission mode; plugin agents cannot set their own.
- **Untrusted files:** extractors refuse XML that declares a DTD or entities and parts that expand beyond a size limit (entity-expansion and zip-bomb guards). Text found inside files is treated as data; instructions embedded in a document are reported as suspected prompt injection, never followed.
- **Privacy:** GPS coordinates, device serial numbers and owner fields in image metadata are withheld unless you ask for them.
- **Trust:** review the current hook and script sources before enabling this in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| Without `python3` 3.14+ | No bundled script runs: long PDFs, Office, CSV, JSON and XML files, and images that need conversion or cropping are reported as not reviewed; each script exits 5 with the version it found, and the tier line says `python3=too-old` or `python3=missing` | Install Python 3.14 (python.org, `brew install python@3.14`, or `uv python install 3.14 --default`) |
| Without poppler (`pdftotext`, `pdfinfo`, `pdftoppm`) | Long PDFs only partly verified; the report lists the uncovered pages | `brew install poppler` or `apt install poppler-utils` |
| Without `exiftool` | Image capture dates and camera details reported as not verified | `brew install exiftool` or `apt install libimage-exiftool-perl` |
| Without ImageMagick (`magick`, or `convert` and `compare` from version 6) | No near-duplicate detection; multi-page TIFFs beyond page 1 not reviewed when only `sips` is present | `brew install imagemagick` |
| Without `sips` and ImageMagick | HEIC and TIFF images reported as not reviewed | Install ImageMagick with libheif, or `heif-convert` on Linux |
| Without `heif-convert` on Linux | HEIC not reviewed unless ImageMagick has HEIC support | `apt install libheif-examples` |
| HEIC listed but no HEVC decoder (common on minimal Linux) | `heic=…-unverified` in the tier line; the photo is not reviewed and the report quotes the converter's error | `apt install libde265-0`, or convert the photos to JPEG before the review |
| A file that is neither UTF-8 nor Windows-1252 | The CSV is reported as not verified (unknown encoding) | Re-export as UTF-8, or state the encoding so the review can force it |
| Without `jq`, or if the hook times out | No report gate; one notice per stop | Install `jq` 1.6 or later |
| Windows: the hook runs `bash` from `PATH` | Without Git Bash on `PATH`, the gate never runs | Add Git Bash to `PATH`; only macOS and Linux are tested |
| Formulas without cached values are recomputed only for simple aggregates | `NOT RECOMPUTED` with the reason for other functions | Open and save the workbook in Excel or LibreOffice, then audit again |
| The gate checks the report's form, not the truth of its receipts | A well-formed report with a wrong citation passes the gate | Re-run the cited extractor command on the cited locator |
| Legacy binary and encrypted files | Reported as not reviewed | Convert to `.docx`, `.xlsx`, `.pptx` or an unencrypted PDF first |
| Read-only is enforced by tools, not a permission mode | The agents' `Bash` calls go through your normal permission prompts | Keep your usual permission mode; review what they ask to run |
| In auto mode the classifier may block the bundled scripts as external code | The report is marked PARTIAL and names the blocked command under Not verified; Read stands in only for PDFs, text and directly viewable images | Approve the call, or add an allow rule for `python3` running scripts under the plugin's install directory |
| For a single, simple file Claude may read it directly instead of delegating | No agent report; Claude answers inline, and the report gate (which only checks agent reports) does not run | Ask for a full, cited review, or name the agent (`evidence-reader:document-reader`) |
| Cowork not verified | Extractors may be missing tools in the sandbox | Use Claude Code, or rely on the skills inline |

## ❓ FAQ

<details>
<summary>Does it replace Anthropic's pdf, docx and xlsx skills?</summary>

No. Those skills create and edit files; Evidence Reader only reads, audits and
reports, with receipts and a completeness checklist. They work side by side.

</details>

<details>
<summary>Why does a report say "recomputed" instead of giving the workbook's total?</summary>

Because the workbook has no stored value for that formula — typically a file
written by a program and never opened in a spreadsheet application. The plugin
never presents a value the file does not contain as if it did.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`evidence-reader--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
