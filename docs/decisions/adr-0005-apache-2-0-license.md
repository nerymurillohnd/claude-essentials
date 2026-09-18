---

status: accepted
date: 2026-09-18
decision-makers: Nery Samuel Murillo Tejada
consulted: Claude Code (Opus 5) — license analysis, official marketplace comparison
informed: Contributors to this repository
supersedes: none
superseded-by: none

---

# The marketplace and every plugin it ships are licensed Apache-2.0

## Context and Problem Statement

claude-essentials started under MIT. It is Nery's personal, public marketplace
of Claude Code plugins, built for the developer community and meant to collect
top-tier plugins, skills, and agents in one place. It is not a company
repository. The maintainer's marketplace specification (§16) prefers Apache-2.0
unless there's a concrete reason for MIT.

No plugin has shipped yet, and the maintainer is the only copyright holder.
Relicensing is therefore a same-day change now. After the first third-party
contribution, it would need that contributor's consent.

Which license should the repository and its plugins use?

## Decision Drivers

- Plugins are not only prose: hooks, MCP servers, LSP configs, and scripts are
  executable code that organizations run.
- The repository invites third-party plugin contributions, so the terms for
  inbound contributions matter.
- Organizations adopt plugins through license allowlists; matching the
  ecosystem's official marketplaces lowers that friction.
- One license across the repo and every plugin keeps enforcement mechanical.

## Considered Options

- Apache-2.0
- MIT (status quo)
- MPL-2.0

## Decision Outcome

Chosen option: "Apache-2.0", because it covers every driver where MIT is
silent:

- **Patent grant with retaliation** (Section 3) for the executable parts of
  plugins.
- **Inbound = outbound** (Section 5): contributions intentionally submitted are
  licensed under the same terms without a separate CLA.
- **No trademark grant** (Section 6): forks can't present themselves as
  claude-essentials or use the maintainer's name as an endorsement.
- **Ecosystem alignment**: verified 2026-09-18 via the GitHub API,
  `anthropics/claude-plugins-official` and `anthropics/knowledge-work-plugins`
  are both Apache-2.0, each with a verbatim root `LICENSE`, a verbatim
  per-plugin `LICENSE`, and no `NOTICE` file.

Conventions adopted from that comparison:

- The license file is named `LICENSE`, without an extension. Its contents are
  byte-identical to <https://www.apache.org/licenses/LICENSE-2.0.txt>
  (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`).
- Every plugin ships its own `LICENSE`, since a plugin is copied to the user's
  cache on its own, and declares `"license": "Apache-2.0"` in `plugin.json`.
- There is no `NOTICE` file. Adding one would bind every redistribution to keep
  it (Section 4(d)), so one needs its own decision.
- `templates/LICENSE-Apache-2.0-reusable-template.md` is the source for every
  `LICENSE`. `templates/LICENSE-MIT-reference-template.md` remains as a
  reference document only, not for use in this repository.

MPL-2.0 was rejected: its file-level copyleft adds obligations for adopters
without addressing any driver better than Apache-2.0.

### Consequences

- Good, because adopters get an explicit patent license, and contributions come
  in under the same terms automatically.
- Good, because the license matches Anthropic's own marketplaces, which eases
  organizational approval.
- Bad, because the text is longer, and redistributors of modified files must
  mark their changes (Section 4(b)).
- Neutral: Apache-2.0 is incompatible with GPLv2-only code. Nothing in this
  repository is GPLv2-only.

### Risks and mitigations

| Risk | Likelihood or condition | Impact | Mitigation or response | Owner |
| --- | --- | --- | --- | --- |
| A plugin ships with a non-Apache or edited `LICENSE` | New plugin, or hand-edited file | License ambiguity for that plugin | Planned validator check: every `LICENSE` byte-matches the canonical hash and `plugin.json` says `Apache-2.0` | Maintainer |
| A contributed plugin bundles third-party code under another license | Third-party PR | Mixed licensing | Review requires third-party material to be declared in the plugin README and its license kept alongside | Maintainer |
| A stale MIT reference remains in the docs | Missed file | Contradictory signal | Repo-wide grep during this change; the planned validator check prevents regressions | Maintainer |

### Confirmation

| Criterion or claim | Verification method | Evidence or result | Responsible party | Review condition |
| --- | --- | --- | --- | --- |
| Root and template `LICENSE` files are canonical | `shasum -a 256 LICENSE templates/*/LICENSE` | All match `cfc7749b…3d30`, 2026-09-18 | Maintainer | Any `LICENSE` change |
| No MIT reference outside the reference template and dated plans | `git grep -n -E "MIT\|LICENSE\.md"` | Clean, 2026-09-18 | Maintainer | Any docs/template change |
| Validator enforces license coherence | Planned `npm run validate` check | pending — publication-contract phase | Maintainer | When implemented |
| GitHub detects Apache-2.0 | `gh api repos/nerymurillohnd/claude-essentials --jq .license.spdx_id` | pending — after merge | Maintainer | After merge |

### Amendment — 2026-09-18: license detection confirmed

- After [PR #6](https://github.com/nerymurillohnd/claude-essentials/pull/6) merged, `gh api repos/nerymurillohnd/claude-essentials --jq .license.spdx_id` returns `Apache-2.0`. The Confirmation row "GitHub detects Apache-2.0" is satisfied.
- Still pending: the validator check for license coherence (canonical `LICENSE` hash plus `plugin.json` SPDX). It's phase 1 of the [spec-alignment design](../superpowers/specs/2026-09-18-marketplace-spec-alignment-design.md).

