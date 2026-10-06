---
paths:
  - "plugins/**/NOTICE"
  - "plugins/svelte-development/**"
  - "THIRD_PARTY_NOTICES.md"
  - "docs/sourcing-log.md"
---

# Plugins derived from upstream AI content

Policy: ADR derived-third-party-content (2026-10-05). It applies to every plugin that ships a `NOTICE`; today that is `svelte-development`, derived from `sveltejs/ai-tools`.

- Derive only from a project's own official AI content that the maintainer named; everything else stays under the clean-room policy.
- `NOTICE` at the plugin root holds the upstream repository, the base commit (full SHA), the upstream copyright and license text verbatim, and the list of derived files with what changed. The plugin `LICENSE` stays the repository template.
- Derived skills carry `license: MIT` (or the upstream license) and `metadata` with `upstream` and `base` keys.
- Never call derived content "official", never use the upstream logo or colours, and keep component names distinct from upstream's.
- Before every release of a derived plugin:
  1. Compare upstream's current HEAD with the base commit for the upstream source paths in `NOTICE` (`gh api repos/<owner>/<repo>/compare/<base>...HEAD`), read every changed file, and merge what still applies.
  2. Re-check the plugin's `references/known-doc-errata.md` rows against the current docs; drop fixed errata, add new ones. The verification belongs to this release step and to the pull request, never to a stamp inside a skill or a reference: those carry no version snapshot and no date (ADR no-version-stamps-in-skills).
  3. Update the base commit in `NOTICE`, the `THIRD_PARTY_NOTICES.md` row and the plugin changelog.
- Keep the evidence (raw downloads, hashes) for every reference rewrite in the research directory named in the pull request.
