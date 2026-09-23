# Review-thread closure

How a program closes historical review conversations on the provider. A closed or merged PR
does not resolve its threads. An unresolved thread is not proof of a current defect.

## Protocol

1. Refresh the population. Enumerate every PR and every review thread page
   (`provider.md`, P3), then reconcile with `02-registers.md`: new threads get rows, and
   threads that disappeared are noted.
2. Adjudicate each thread (`adjudication.md`, section 1). Batches go to `thread-adjudicator`
   agents. The main thread reviews each verdict and runs any verification command the agent
   proposes.
3. Group by root cause to fix efficiently, but verify and reply to each thread separately.
4. Wait for the fix to land. A thread whose verdict is *fixed in this work* is replied to and
   resolved only after the fix is merged. *Still present* and *blocked* threads stay open.
5. Reply. Each reply is specific to its thread. It states:
   - the verdict;
   - the evidence (commit, test, decision);
   - what was not changed;
   - no claim of a fix that did not happen.
6. Resolve the thread.
7. Re-read it and confirm `isResolved: true`. If a mutation fails or its result is
   ambiguous, re-read before retrying, so no reply is posted twice.
8. Record the receipt:

   | PR | Thread | Reply | Re-read resolved |
   | --- | --- | --- | --- |
   | #81 (PR link) | `PRRT_…` | comment link | true |

## Batching and counters

- Work in batches of 20 threads, in the order the register sets: owner-flagged first, then
  the newest PRs, then the densest.
- Each batch record states:
  - threads closed in this batch;
  - the cumulative total out of the starting population;
  - the unresolved count at the last full refresh.

  Label arithmetic between refreshes as arithmetic, not as a census.
- Never mass-resolve. Never delete comments, PRs or history to reach zero.

## Commands (GitHub)

```sh
gh api graphql -f query='mutation($id:ID!,$body:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}){comment{url}}}' -F id=PRRT_xxx -F body=@reply.md
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -F id=PRRT_xxx
gh api graphql -f query='query($id:ID!){node(id:$id){... on PullRequestReviewThread{isResolved}}}' -F id=PRRT_xxx
```

The reply body is written to a file first (`reply.md` in the evidence package). Replies and
resolutions are provider mutations: each one requires S08 (or its equivalent) to be
approved, and each is recorded.
