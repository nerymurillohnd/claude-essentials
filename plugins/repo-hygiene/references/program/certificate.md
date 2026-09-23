# Certificate

`/repo-hygiene:deep certify` checks the plan's acceptance contract at one moment and records
the result. It is read-only, apart from writing the certificate file to the evidence package.

## Procedure

1. Confirm the exclusive window still holds: no active Git operation and no new refs since the
   last operation.
2. For each acceptance criterion, run its proof command. Record the command, its exit code,
   its output (trimmed, redacted) and PASS or FAIL.
3. Refresh the provider with full pagination: branches, PRs, review threads, issues and
   alerts. Record the totals.
4. Cross-check the ledger:
   - every accepted row maps to the final tree;
   - every discarded row has the owner's recorded words;
   - no row is open.
5. Dispatch `certificate-verifier` with the contract and the evidence package path. It
   re-runs each proof independently. A disagreement between it and step 2 is a FAIL until
   explained.
6. Write `certificate.md` to the evidence package. It holds:
   - the final SHA and tree;
   - the criterion table;
   - the provider totals;
   - the backup location, hash, restore proof and retention;
   - the scope exclusions;
   - any criterion that failed, with its blocker.

## Rules

- The program is complete only if every criterion passed. Otherwise the certificate says
  `partial` and names each failing criterion with the retained item and its blocker.
- The certificate holds for its moment only. Any later commit, fetch, build or tool snapshot
  changes the state. Say so in the certificate.
- Write the certificate outside the working tree, so issuing it does not dirty the tree. If
  the owner wants it committed, that is a separate documentation change, and certification is
  repeated afterwards.
- Backup disposal (S14) is never part of certification. It is a separately approved operation
  at the chosen retention boundary. Before it runs, state that nothing it holds can be
  recovered afterwards.
