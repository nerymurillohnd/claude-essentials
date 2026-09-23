---
name: deep
description: Run a forensic Git and hosting-provider audit, and multi-session cleanup programs built on it. Phase audit covers every area at full depth (every reflog, the unreachable census with and without reflog roots, integrity, every ref namespace, every config scope, full history, every pull request and review thread) and adjudicates what it finds instead of only counting it. Phase plan writes a plan package with an acceptance contract and operation IDs. Phase execute runs approved operations with a restore-tested backup, review-thread closure and defect fixes through the project's own workflow. Phase resume reconciles and continues. Phase certify checks the contract independently.
when_to_use: Only when the user invokes it as /repo-hygiene:deep, optionally followed by a phase and a focus.
disable-model-invocation: true
argument-hint: "[audit | plan | execute S01,S02 | resume | certify] [focus: all | G5 | P3 | area name]"
---

# Repository hygiene — deep

The user invoked this skill: `$ARGUMENTS`. Read the first word as the phase:

| Phase | Default when | What it does |
| --- | --- | --- |
| `audit` | no phase given | Full-depth audit and adjudication, one report, recommendations |
| `plan` | | Plan package from the latest audit (`references/program/plan-package.md`) |
| `execute <IDs>` | | Runs the approved operation IDs (`references/program/execution.md`) |
| `resume` | | Reconciles the plan with a fresh inventory and continues |
| `certify` | | Checks the acceptance contract (`references/program/certificate.md`) |

Treat the rest of `$ARGUMENTS` as a focus (`G5`, `P3`, an area name). Without a focus, cover
everything. All reference paths below are under `${CLAUDE_PLUGIN_ROOT}/references/`.

## Rules

1. **Read freely; mutate only by approval.** Reads need no permission; asking before one is
   a defect. Every mutation needs an approved ID: an audit `R` ID or a plan `S` ID.
2. **Follow `audit-contract.md`** before the first command. In this skill every inspection
   also runs with `-c core.fsmonitor=false -c gc.auto=0 -c maintenance.auto=false`.
3. **Trust preflight first.** Compare the `.git` owner with the current user and list the
   command-executing config keys. For a repository that is not the user's own, stop and
   recommend `git clone --no-local` into a new path.
4. **Order matters, because later steps write objects:**
   1. ref snapshot to the evidence package;
   2. reflogs;
   3. the unreachable census, with and without reflog roots;
   4. integrity;
   5. only then `merge-tree --write-tree` or `commit-tree`.
5. **`--no-replace-objects`** on every count and walk. Redact in the same command that
   prints. Never read secret-shaped files or `cat` unknown payloads.
6. **Mutations are sequential in this conversation.** Agents only read.

## Phase `audit`

1. Run everything `routine` covers (`${CLAUDE_PLUGIN_ROOT}/skills/routine/SKILL.md`, step 3),
   then the **Deep checks** of every area file in `areas/` and the deep recipes in
   `provider.md`:
   - every PR and every review thread, paginated to the end, with totals;
   - rulesets and rule-suite bypasses;
   - Actions retention and storage;
   - access and integrations;
   - alerts in every state;
   - Codespaces.
2. **Adjudicate; do not only count** (`adjudication.md`):
   - Review threads go in batches to the `thread-adjudicator` agent. Pass it the repository
     path, `OWNER/REPO`, the `HEAD` SHA, the thread IDs, and the absolute path
     `${CLAUDE_PLUGIN_ROOT}/references/adjudication.md`.
   - Unreachable commits, stash paths, branches and lost-found entries go to the
     `candidate-classifier` agent, with the same path. Say whether the unreachable census is
     saved.
   - Review every verdict before it enters the report. Run the verification commands the
     agents propose.
3. Apply the false-positive catalogue (`audit-contract.md`, section 9) to every finding.
4. Report with `report-template.md`. Write the full appendices (`local-evidence.md`,
   `provider-evidence.md`) to the evidence package. Give every retained item an exit
   condition. Put preservation recommendations before removals.
5. When the recommendations need more than one session, or the user's goal is an end state
   such as "only main", recommend `/repo-hygiene:deep plan`.

## Phase `plan`

Follow `program/plan-package.md`:

- choose a goal profile (`single-main`, `tidy`, custom) and write its acceptance contract;
- write the four files in the project's documented location, or ask once;
- write operation IDs with dependencies and consequences;
- verify the plan (counts match the audit, shell blocks parse, no placeholders);
- present the approval format.

## Phase `execute`

Follow `program/execution.md`:

- quote the approval verbatim;
- write dated execution records;
- take a backup and prove it restores before any destruction;
- keep a disposition ledger;
- integrate preserved histories with normal merges;
- fix defects that reproduce, red then green then negative control, through the project's own
  workflow and PR lifecycle.

Close review threads per `program/review-closure.md`, one by one, with a receipt for each.
Stop on every condition in `program/plan-package.md`, section 5.

## Phase `resume`

Find the plan package and the latest execution record. Re-run the inventory, report drift,
refresh the provider counts, and continue from the first open row (`program/execution.md`,
section 8).

## Phase `certify`

Follow `program/certificate.md`. Dispatch the `certificate-verifier` agent with the plan path
and the evidence package path, and give it none of your own conclusions. The result is
`complete` only when every criterion passed.

## Size and pacing

- Report progress per area on long runs. Findings still wait for the report.
- Write large enumerations to the evidence package, and put the report's summary sections in
  the reply with the report's path.
- Never sample. When a budget runs out, list the remaining items and carry them to `resume`.
