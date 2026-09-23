# Hosting provider

How both skills read and change hosting-provider state: pull requests, reviews, branches,
settings, rulesets, CI, releases, access and alerts (areas P1–P9). GitHub gets full recipes.
GitLab gets P1–P4 through `glab`. Other providers are `blocked (unsupported provider)`.

## Contents

1. Source order
2. Identify the repository
3. Pagination and totals
4. Recipes by area (GitHub)
5. GitLab equivalents
6. Changing provider state
7. Live documentation

## 1. Source order

Use the first source that works, per surface, and record the source used for each surface
in the report:

1. A connected provider MCP server's read tools (for GitHub, tools such as
   `list_pull_requests`, `pull_request_read`, `list_branches`).
2. `gh` (GitHub) or `glab` (GitLab), when installed and authenticated. Use it for every read
   the MCP server does not expose. Check with `gh auth status`; report the token's scopes by
   name, never the token.
3. Otherwise: `unknown (no provider access)`, with the reason.

Never ask for a token and never handle one. An authentication or scope failure only means
that path failed. Try the other source before concluding. A 403 or 404 is reported with the
scope or plan the provider asked for, and it "does not prove absence".

## 2. Identify the repository

```sh
git --no-pager remote -v | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
gh repo view --json nameWithOwner,defaultBranchRef,visibility,isArchived,isFork,parent
```

A fork has two provider repositories. Audit the one the user named, and name the parent in
the report.

## 3. Pagination and totals

- Every list is read to its last page:
  - REST: `gh api --paginate '<endpoint>?per_page=100'`.
  - GraphQL: `gh api graphql --paginate`. The query must declare `$endCursor` (that exact
    name) and select `pageInfo { hasNextPage endCursor }`.
  - MCP: keep requesting pages until an empty page.
- The report states the totals read, for example "124 PRs: 119 merged, 5 closed unmerged,
  0 open".
- A capped or sampled list is `blocked`, never complete.
- Save full enumerations to `provider-evidence.md` in the evidence package.

## 4. Recipes by area (GitHub)

`OWNER/REPO` is the repository from section 2. Every recipe below is a read.

### P1 — Repository settings

```sh
gh api repos/OWNER/REPO --jq '{default_branch, delete_branch_on_merge, allow_merge_commit,
  allow_squash_merge, allow_rebase_merge, allow_auto_merge, archived, visibility}'
```

- `delete_branch_on_merge: false` is the root cause of merged branches left behind. Name it
  in the finding.
- `[doc]` Admins can enable it. Branch protection and rulesets can prevent automatic
  deletion (docs.github.com, "Managing the automatic deletion of branches").

### P2 — Branches, protection and rulesets

```sh
gh api --paginate 'repos/OWNER/REPO/branches?per_page=100' --jq '.[] | [.name, .commit.sha, .protected] | @tsv'
gh api 'repos/OWNER/REPO/rulesets' --jq 'map({id, name, enforcement, target})'
gh api 'repos/OWNER/REPO/rulesets/ID'                       # rules, conditions, bypass_actors
gh api 'repos/OWNER/REPO/branches/BRANCH/protection'         # classic protection; 404 = none
gh api --paginate 'repos/OWNER/REPO/rulesets/rule-suites?per_page=100'   # deep: passes, failures, bypasses
```

Findings to look for:

- Remote branches with no PR.
- Branches whose PR merged or closed.
- Protection that names branches that no longer exist.
- Required status checks that no workflow produces.
- Rulesets `disabled` or in `evaluate`.
- **No "require conversation resolution before merging"**
  (`required_conversation_resolution` in classic protection, or the ruleset rule
  `required_review_thread_resolution`). This is the root cause of unresolved-review
  backlogs.
- Overlapping classic rules. `[doc]` "Only a single branch protection rule can apply at a
  time."

A 403 on rulesets or protection for a private repository on a free plan is a plan limit.
Report it; do not weaken anything to avoid it.

### P3 — Pull requests and review threads

```sh
gh api --paginate 'repos/OWNER/REPO/pulls?state=all&per_page=100' \
  --jq '.[] | [.number, .state, (.merged_at // "-"), .head.ref, .head.sha, .base.ref, .updated_at, .draft] | @tsv'
```

**Review threads.** Save this query as `threads.graphql` in the evidence package, then run it
per PR:

```graphql
query($owner: String!, $repo: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: 1) { totalCount nodes { url originalCommit { oid } } }
        }
      }
    }
  }
}
```

```sh
gh api graphql --paginate -F owner=OWNER -F repo=REPO -F number=N -F query=@threads.graphql \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | [.id, .isResolved, .isOutdated, .path, (.line // .originalLine)] | @tsv'
```

`[observed]` 2026-09-22: on a PR with 27 threads, this returned all 27, 4 of them
unresolved.

- `routine` counts unresolved threads on open PRs.
- `deep` runs the query for **every** PR and reports totals split by resolved or unresolved,
  outdated or not, and merged or closed-unmerged. Unresolved or not-outdated never proves a
  current defect; `deep` adjudicates each thread (`adjudication.md`).

**PR against Git**, for each PR:

- head SHA vs the current branch tip: the branch moved after the PR;
- `git merge-base --is-ancestor <head.sha> <base>`: the head landed;
- a merged PR whose branch still exists;
- a branch that received commits after the merge;
- a closed-unmerged PR whose commits are absent from the base: lost work.

### P4 — Issues, labels, milestones

```sh
gh api --paginate 'repos/OWNER/REPO/issues?state=all&per_page=100' \
  --jq '.[] | select(.pull_request | not) | [.number, .state, .title, .updated_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/labels?per_page=100' --jq '.[].name'
gh api --paginate 'repos/OWNER/REPO/milestones?state=all&per_page=100' --jq '.[] | [.title, .state, .due_on, .open_issues] | @tsv'
```

Look for:

- issues that a merged PR says it fixes ("fixes #N", "closes #N") but that are still open;
- labels no issue or PR uses;
- milestones past their due date that still have open issues.

### P5 — CI and automation

```sh
gh api --paginate 'repos/OWNER/REPO/actions/workflows?per_page=100' --jq '.workflows[] | [.name, .state, .path] | @tsv'
gh run list --branch DEFAULT --limit 20 --json workflowName,conclusion,headSha,createdAt
gh api 'repos/OWNER/REPO/actions/caches' --jq '{total_count}'
gh api 'repos/OWNER/REPO/actions/cache/usage'
gh api --paginate 'repos/OWNER/REPO/actions/artifacts?per_page=100' --jq '.artifacts[] | [.name, .size_in_bytes, .expires_at, .expired] | @tsv'
gh api 'repos/OWNER/REPO/actions/permissions/artifact-and-log-retention'
gh api --paginate 'repos/OWNER/REPO/actions/runners?per_page=100' --jq '.runners[] | [.name, .status, .busy] | @tsv'
```

- `[doc]` Caches are kept 7 days by default, with a 10 GB eviction limit.
- `[doc]` Artifacts and logs are kept 90 days by default.
- `[doc]` From 2026-10-01, the retention setting also applies to checks, workflow runs and
  commit statuses, which until then are kept 400+ days regardless. While that date is ahead
  or recent, report the configured retention as a dated finding.

Also look for:

- workflows that are disabled or failing on the default branch;
- workflow files that reference secrets not defined for the repository (names only);
- actions pinned to a branch or tag instead of a commit SHA.

### P6 — Releases, packages, Pages, environments, deployments

```sh
gh api --paginate 'repos/OWNER/REPO/releases?per_page=100' --jq '.[] | [.tag_name, .draft, .prerelease, .published_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/environments' --jq '.environments[] | [.name, .updated_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/deployments?per_page=100' --jq '.[] | [.environment, .ref, .created_at] | @tsv'
gh api 'repos/OWNER/REPO/pages'            # 404 = Pages not enabled
```

Compare releases with tags. Report releases without a tag, tags without a release when the
project releases, draft releases, and environments with no recent deployment.

### P7 — Access and integrations

```sh
gh api --paginate 'repos/OWNER/REPO/collaborators?per_page=100' --jq '.[] | [.login, .role_name] | @tsv'
gh api --paginate 'repos/OWNER/REPO/invitations?per_page=100' --jq '.[] | [.invitee.login, .created_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/keys?per_page=100' --jq '.[] | [.title, .read_only, .created_at, .last_used] | @tsv'
gh api --paginate 'repos/OWNER/REPO/hooks?per_page=100' --jq '.[] | [.id, .active, .config.url, .last_response.code] | @tsv'
gh api --paginate 'repos/OWNER/REPO/actions/secrets?per_page=100' --jq '.secrets[] | [.name, .updated_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/actions/variables?per_page=100' --jq '.variables[] | [.name, .updated_at] | @tsv'
```

- Webhook URLs can carry tokens: pass them through the redaction `sed` in
  `audit-contract.md`.
- Secret and variable **names** only.
- Look for:
  - deploy keys with write access;
  - webhooks whose last response failed;
  - invitations older than 7 days;
  - secrets or variables no workflow references (compare their names with
    `git grep -n -e 'secrets\.' -e 'vars\.' -- .github/workflows`).

### P8 — Security signals

```sh
gh api --paginate 'repos/OWNER/REPO/dependabot/alerts?per_page=100' --jq '.[] | [.number, .state, .security_advisory.severity, .dependency.package.name, (.fixed_at // .dismissed_at // "-")] | @tsv'
gh api --paginate 'repos/OWNER/REPO/code-scanning/alerts?per_page=100' --jq '.[] | [.number, .state, .rule.severity] | @tsv'
gh api --paginate 'repos/OWNER/REPO/secret-scanning/alerts?per_page=100' --jq '.[] | [.number, .state, .secret_type, .created_at] | @tsv'
gh api --paginate 'repos/OWNER/REPO/forks?per_page=100' --jq '.[] | [.full_name, .pushed_at] | @tsv'
```

- Never request a secret-scanning alert's `secret` field.
- A provider "fixed" state is the provider's conclusion, not an independent audit.

### P9 — Compute and workspaces

```sh
gh api --paginate 'repos/OWNER/REPO/codespaces?per_page=100' --jq '.codespaces[] | [.name, .state, .last_used_at] | @tsv'
```

A 403 or 404 here often means the token lacks the `codespace` scope. Report the scope asked
for; never change authentication.

## 5. GitLab equivalents

```sh
glab repo view
glab mr list --all --per-page 100
glab api --paginate 'projects/:id/merge_requests/<iid>/discussions'   # resolvable, resolved
glab api 'projects/:id/protected_branches'
glab api 'projects/:id' | jq '{default_branch, remove_source_branch_after_merge, only_allow_merge_if_all_discussions_are_resolved}'
```

P5–P9 on GitLab are `blocked (not covered for GitLab in this version)`.

## 6. Changing provider state

Every change below is an approved item. Each shows its exact command and its undo:

| Change | Command | Undo |
| --- | --- | --- |
| Delete a remote branch | `git push origin --delete BRANCH` | `[doc]` "Restore branch" on its closed PR, or `git push origin SHA:refs/heads/BRANCH` |
| Close a PR | `gh pr close N --comment "…"` | `gh pr reopen N` |
| Reply to a review thread | `gh api graphql -f query='mutation($id:ID!,$body:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}){comment{url}}}' -F id=THREAD -F body=@reply.md` | A reply cannot be unsent; it can be edited or deleted |
| Resolve a review thread | `gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -F id=THREAD` | `unresolveReviewThread` |
| Enable auto-delete of head branches | `gh api -X PATCH repos/OWNER/REPO -F delete_branch_on_merge=true` | Same with `false` |
| Delete an artifact | `gh api -X DELETE repos/OWNER/REPO/actions/artifacts/ID` | **Irreversible** (`[doc]`) |
| Remove a deploy key | `gh api -X DELETE repos/OWNER/REPO/keys/ID` | Re-add the public key |

Deleting a branch from GitHub's branches page closes its open PRs (`[doc]`). Check for open
PRs on that head before any branch deletion. After any provider mutation, re-read the state
and record the receipt: ID, URL and re-read value. When a mutation fails or is ambiguous,
re-read before retrying, so no reply is posted twice.

## 7. Live documentation

When a GitHub MCP server is connected and exposes `github_support_docs_search`, use it to
confirm the current behavior, UI or API steps and side effects of any provider
recommendation before writing it. Its topics include Repository Maintenance, Pull Request
Practices, Actions and Authentication. If the live answer differs from this file, the live
answer wins, and the report says so.
