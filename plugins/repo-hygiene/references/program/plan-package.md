# Plan package

`/repo-hygiene:deep plan` turns an audit into a cleanup program that can run across sessions.
The plan authorizes nothing by itself: execution starts only when the user approves
operation IDs by name.

## Contents

1. Inputs and location
2. The four files
3. Goal profiles and acceptance contracts
4. Operation IDs
5. Stop conditions
6. Approval format
7. Plan verification

## 1. Inputs and location

- Inputs: the latest `deep` audit report and its evidence appendices. If the audit is older
  than the current `HEAD` or the provider state, re-run the affected areas first.
- Location: the project's documented plan or audit folder (CLAUDE.md, AGENTS.md, a nested
  AGENTS.md). If none exists, ask once and record the answer in the plan.
- Record the hashes of the input files: `shasum -a 256 <file>` or `sha256sum <file>`.
- New execution facts go into dated execution records. The plan is never rewritten in place;
  corrections are dated amendments at its top.

## 2. The four files

| File | Holds |
| --- | --- |
| `00-plan.md` | Goal, profile, acceptance contract, global constraints, scope and recovery choices awaiting the owner, operation IDs with dependencies and consequences, tasks with pass/reject checks, stop conditions, approval format, plan-verification record |
| `01-targets.md` | Every observed ref with full SHA, every stash and its paths, object-class counts, worktrees, candidate paths, input hashes, and the disposition schema |
| `02-registers.md` | One row per item that needs a decision: every review thread ID, every candidate (branch, stash path, object class, lost-found entry, generated path). Each row has a status: open, adjudicated, approved, done or blocked. |
| `03-runbook.md` | For each operation: preconditions, the literal commands, the verification read, the recovery command, and what makes it stop |

`00-plan.md` opens with this header:

```markdown
**Goal:** <one sentence, the end state>
**Profile:** single-main | tidy | custom
**Status:** proposed
**Current authority:** this plan's operation IDs once approved, plus fresh execution evidence
**Verification:** <what was re-checked while planning>
**Open risks:** <one line each>
```

## 3. Goal profiles and acceptance contracts

Every plan states its acceptance contract as a table: ID, required result, proof. The
contract is what `certify` checks.

### Profile `single-main`

The end state: only `main`, locally and on the provider, synchronized; every accepted change
incorporated; nothing hidden. Use this contract, adapted to the repository's real branch name
and provider:

| ID | Required result | Proof |
| --- | --- | --- |
| A01 | Current branch is the default branch | `git symbolic-ref HEAD` |
| A02 | Exactly one local branch | `git for-each-ref refs/heads` |
| A03 | Exactly one provider branch | `git ls-remote --branches origin` and the provider's paginated branch list |
| A04 | Exactly one remote-tracking branch, plus the `origin/HEAD` alias | `git for-each-ref refs/remotes` |
| A05 | HEAD = local = tracking = live provider tip | four full SHAs equal; ahead/behind `0 0` |
| A06 | No staged, unstaged, conflicted or untracked non-ignored files | `git status --porcelain=v2` empty |
| A07 | Every candidate has a final disposition; every accepted change is in the final tree | register has zero open rows |
| A08 | One registered worktree; no matching secondary clone in the approved scope | worktree registry and G22 traversal |
| A09 | No stash | `git stash list` empty and `refs/stash` absent |
| A10 | No tool, archive or preservation refs or tags left by the program | full `for-each-ref` |
| A11 | No operation leftovers, lost-found entries or unreachable objects | operation-state checks; `fsck --unreachable` with and without reflogs |
| A12 | Object integrity valid | `fsck --full --strict`, `verify-pack`, `multi-pack-index verify` where present |
| A13 | Zero open PRs and zero unresolved review threads in the refreshed population | full provider pagination |
| A14 | No actionable security alert left unclassified | provider alert pagination |
| A15 | The project's required checks pass on the final tree | exact SHA, commands, exit codes, CI runs |
| A16 | Approved generated paths removed; operational assets kept | exact path manifest |
| A17 | The one external backup is recorded with location, hash, restore proof and retention | backup manifest |

A11 is met only after an approved, exclusive reclamation (`03-runbook.md`). A certificate
holds only for the moment it is issued; later writes create new reflogs and objects.

### Profile `tidy`

Remove proven residue and keep everything else:

- A06 and A12, as in `single-main`.
- Every finding in the audit has a disposition.
- Every removal is covered by a restore-tested backup or is regenerable.
- No unique content was discarded without the owner's recorded choice.

### Custom

Write the contract first, with the owner, then plan operations against it.

## 4. Operation IDs

Operations use `S` IDs (`S01`, `S02`, …), distinct from the audit's `R` IDs. Each row
states:

| Operation | Work authorized when approved | Depends on | Destructive or external consequence |
| --- | --- | --- | --- |

A typical `single-main` chain, adapted to what the audit found:

| Operation | Work |
| --- | --- |
| S01 | Refresh the inventory and write the execution manifests |
| S02 | Create the external backup and restore-test it (`program/execution.md`) |
| S03 | Classify every candidate (`adjudication.md`) |
| S04 | Create one temporary integration branch and integrate the accepted work |
| S05 | Adjudicate and address every review-register row; fix the defects that reproduce |
| S06 | Run the project's verification on the integrated tree |
| S07 | Commit, push, open the PR, repair it, merge it, and sync the default branch, through the project's normal lifecycle |
| S08 | Reply to and resolve each review thread after its fix has landed (`program/review-closure.md`) |
| S09 | Remove the approved extra worktrees and clones |
| S10 | Delete the integrated branches and drop the adjudicated stash |
| S11 | Remove the approved tool refs and lost-found, expire reflogs and reclaim objects, in an exclusive window |
| S12 | Remove the approved generated paths |
| S13 | Certify (`program/certificate.md`) |
| S14 | Dispose of the backup at the chosen retention boundary; approved separately |

A partial approval executes only the operations it names and their prerequisites. The report
then states which acceptance criteria cannot be met.

## 5. Stop conditions

Stop, report and ask before continuing when:

- a target SHA, path or provider state drifted since approval;
- an unknown writer is active: another agent, an editor, a CI job pushing, or new refs
  appearing;
- the project's instructions conflict with an operation (for example a protected path, a hook
  that reads it, or a required check that cannot run);
- a backup restore test fails;
- a hook, test or check fails. Repair the cause; never bypass;
- an item has no disposition and the next operation would remove it.

Never redefine success as a partial cleanup without saying so.

## 6. Approval format

End `00-plan.md` with the exact form the owner can answer with, for example:

> Approve S01–S13 of `<plan path>`, including S07 publication and merge, S08 replies and
> resolutions, S09/S10 removals, and S11 ref deletion, lost-found removal, reflog expiry and
> immediate gc. Scope: <hosts, volumes>. Backup retention: <30 days | until I say | dispose
> after certificate>.

S14 is always a separate approval, because it destroys the last recovery copy.

## 7. Plan verification

Before presenting the plan, check it and record the results at the end of `00-plan.md`:

- The counts in `02-registers.md` equal the audit's counts: every thread ID and every
  candidate.
- Every operation has preconditions, commands, verification and recovery in `03-runbook.md`.
- Shell blocks parse: `bash -n` on each extracted block.
- There are no placeholders left.
- Every destructive operation depends on S02 (backup) and on an adjudication.
