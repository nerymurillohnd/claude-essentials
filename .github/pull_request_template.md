## Summary

<!-- What changes and why. Link the issue: "Closes #123". -->

## Plugin checklist

<!-- Delete this section if the PR doesn't touch plugins/. CI enforces the first three items. -->

- [ ] If runtime files changed ([what counts](../docs/contributing/versioning.md#the-rule-bump-when-claude-would-load-something-different)): bumped `version` per [the bump rules](../docs/contributing/versioning.md#which-number-to-bump), or a maintainer applied `bump: deferred`. Docs/README/metadata-only changes need no bump.
- [ ] Added `## [X.Y.Z] - YYYY-MM-DD` to each bumped plugin's `CHANGELOG.md` (breaking changes marked **Breaking:**); notable non-runtime changes noted under `## [Unreleased]`.
- [ ] `npm run check:versions` and `npm run validate:claude` (`claude plugin validate --strict`) pass locally.
- [ ] The plugin README follows the [README contract](../templates/plugin-README-reusable-template.md): all 15 sections present, and **What it does not do**, **Security**, and **Limitations** match this version (`npm run validate` checks the structure).
- [ ] The root [README catalog](../README.md#-plugin-catalog) has this plugin's row, matching its README (`npm run validate` enforces it).
- [ ] **Compatibility** marks a surface ✅ only after a dated install from the remote marketplace on that surface.
- [ ] `evals/` has a case that triggers the plugin and one that must not (once the eval skeleton lands, DEBT-0007); any Δ from `claude plugin eval` is recorded.

## Public-repository safety

<!-- Always required: everything in this repository is public. -->

- [ ] No secrets, tokens, or credentials — plugin secrets go through `userConfig` with `"sensitive": true`.
- [ ] No private paths, customer data, internal endpoints, or confidential procedures.
- [ ] No top-level `bin/` in a plugin; any third-party material is declared with its license.
- [ ] My contribution is licensed under [Apache-2.0](../LICENSE), like the rest of this repository.

## Verification

<!-- Commands you ran and what you observed. `npm run check` is the CI gate for every PR. -->
