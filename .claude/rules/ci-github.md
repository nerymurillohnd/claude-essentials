---
paths:
  - ".github/**"
  - "scripts/check_pr.py"
  - "scripts/check_commit_msg.py"
---

# CI and GitHub

- The workflows are validate, pull-request, release, labels and labeler.
- All of them use `permissions: {}`, actions pinned by SHA and `persist-credentials: false`.
- The labeler runs on `pull_request_target` without checking out the PR's code.
- `check_pr.py` requires a changelog note, exactly one `semver:` label and a Migration section for majors.
- A version change can only go in a release PR.
- Labels are defined as code with crazy-max (which deletes the ones not in the file), and `actions/labeler` applies them by path.
- The label prefixes are `type:`, `semver:`, `status:`, `priority:`, `category:` and `plugin:<name>`, plus `security-review`.
- Pinned action versions: checkout v7.0.1, setup-uv v10.2.0, setup-node v7.0.0 and labeler v7.0.0.
