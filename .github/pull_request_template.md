## Summary

<!-- What changes and why. Link the issue: "Closes #123". -->

## Plugin version checklist

<!-- Delete this section if the PR doesn't touch plugins/. CI enforces the first four items. -->

- [ ] If runtime files changed ([what counts](../docs/contributing/versioning.md#the-rule-bump-when-claude-would-load-something-different)): bumped `version` per [the bump rules](../docs/contributing/versioning.md#which-number-to-bump), or a maintainer applied `bump: deferred`. Docs/README/metadata-only changes need no bump.
- [ ] Added `## [X.Y.Z] - YYYY-MM-DD` to each bumped plugin's `CHANGELOG.md` (breaking changes marked **Breaking:**); notable non-runtime changes noted under `## [Unreleased]`.
- [ ] `npm run check` and `npm run check:versions` pass locally.
- [ ] `npm run validate:claude` passes (`claude plugin validate --strict` on the marketplace and every plugin).
- [ ] The plugin README's installation/runtime effects are still accurate.

## Verification

<!-- Commands you ran and what you observed. -->
