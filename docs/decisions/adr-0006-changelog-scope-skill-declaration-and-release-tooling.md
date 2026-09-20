---

status: accepted
date: 2026-09-20
decision-makers: Nery Samuel Murillo Tejada
consulted: Claude Code (Opus 5) — live docs, changelog, and a read of two comparable public collections
informed: Contributors to this repository

supersedes: none
superseded-by: none

---

# ADR-0006: Per-plugin changelogs, the default skill scan, and CI-enforced versioning

## Context and Problem Statement

Two public Claude Code skill collections are the obvious comparables for this
repository, and both are further along than it is:

- [`obra/superpowers`](https://github.com/obra/superpowers) — 14 skills, version
  6.4.1, distributed through the official marketplace.
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — 25 skills,
  version 1.2.3, distributed through the official marketplace and its own
  single-entry catalog.

Reading them raised three questions about practices this repository does not
follow:

1. Both keep one changelog at the repository root. Should this repository add
   one, replace its per-plugin changelogs with one, or keep what it has?
2. `mattpocock/skills` declares every skill explicitly in `plugin.json`'s
   `skills` array. Should this repository do the same, as a way to control what
   ships?
3. `mattpocock/skills` versions and releases with [Changesets](https://github.com/changesets/changesets);
   `obra/superpowers` synchronises one version across eleven manifests with a
   `.version-bump.json` and a bump script. Should this repository adopt either?

The relevant asymmetry is structural: **both comparables are one plugin per
repository**, so their repository-level artifacts and their plugin-level
artifacts are the same file. This repository is a *catalog* of independently
versioned, independently installable plugins, and has no version of its own
(`package.json` is `0.0.0` and `private`; neither `marketplace.json` nor any of
its entries carries a `version`, per [ADR-0003](adr-0003-plugin-versioning-and-tagging.md)).

## Decision Drivers

- The changelog must stay the artifact a deterministic gate already verifies.
- A second copy of anything must be generated or gated, never hand-maintained.
- Adopt a practice only when it solves a problem this repository actually has.
- Prefer a mechanism that makes drift impossible over one that detects it.
- Keep the cost of a decision proportional to a single-operator repository.

## Considered Options

- Changelog: per plugin only · repository only · both.
- Skills: rely on the default `skills/` scan · declare `skills` in `plugin.json`.
- Release tooling: keep `check-versions.mjs` + CI tagging · adopt Changesets ·
  adopt a multi-manifest version-sync script.

## Decision Outcome

### 1. The changelog stays per plugin, and only per plugin

`plugins/<id>/CHANGELOG.md` is the only changelog. The repository gets none.

The install unit, the version unit and the tag unit are all the plugin, so the
changelog belongs there too. Two facts settle it:

- **Nothing in Claude Code reads a plugin's changelog.** Searched the full live
  documentation: `/plugin` Discover and Browse show "a plugin's commands,
  agents, skills, hooks, and MCP/LSP servers", and `claude plugin details` shows
  "a plugin's component inventory and projected per-session token cost". No
  surface displays a changelog. It is read on GitHub, by someone who goes
  looking — which makes its machine-checked role the more important one.
- **`scripts/lib/version-plan.mjs` already gates it.** `hasChangelogEntry` fails
  a pull request when a released version has no entry in *that plugin's*
  changelog. A repository-level changelog has no version to be organised by and
  no way to bind an entry to `ruff-quality@0.1.0` rather than
  `shell-quality@0.1.0` released the same day.

Keeping both was rejected for the reason this repository rejects every
duplicate: a second changelog written by hand has nothing keeping it current,
which is the definition of debt under `.claude/rules/plugin-authoring.md`
("a finding is closed only when it is fixed **and** a gate exists").

If discovery across plugins becomes a real problem, it is solved by a
**generated** index in the root README, derived from the per-plugin changelogs
through the existing `npm run generate` / `npm run validate` pair — not by a
second changelog. That is recorded as debt, not left as an open question.

### 2. Skills load from the default scan; `plugin.json` declares no `skills`

No plugin manifest here carries a `skills` key.

The field does not do what it appears to do. Live `plugins-reference` states it
plainly: `skills` are "Custom skill directories containing `<name>/SKILL.md`.
**Adds to the default `skills/` scan**", and under the path behavior rules,
"The default `skills/` directory is **always scanned**, and directories listed
in `skills` are loaded alongside it." It is the only additive component field —
`commands`, `agents`, `workflows`, `outputStyles`, `experimental.themes` and
`experimental.monitors` all replace their default directory. The shadowing
behavior that would have made it an allowlist was a bug, fixed upstream:
"Fixed a `skills` entry in `plugin.json` hiding the plugin's default `skills/`
directory".

The documented exception — "for a marketplace entry whose `source` resolves to
the marketplace root, declaring specific subdirectories replaces the default
`skills/` scan" — is why `mattpocock/skills` needs the array: its catalog entry
uses `"source": "./"`, and its skills sit two levels deep under
`skills/engineering/` and `skills/productivity/`, which the default one-level
scan does not reach. Neither condition holds here: catalog entries are
`./plugins/<id>`, and skills are flat at `plugins/<id>/skills/<name>/SKILL.md`.
`obra/superpowers` has the same flat layout and declares no `skills`.

Declaring it would therefore add a second source of truth with no effect, which
a future session would have to remember to update and a new gate would have to
protect. **Excluding a skill from what ships is done by keeping it out of
`skills/`, not through the manifest.**

### 3. Versioning stays with `check-versions.mjs` and CI tagging

Changesets is not adopted, and neither is a multi-manifest sync script.

- Changesets is built for monorepos of published npm packages. These plugins are
  not npm packages; `mattpocock/skills` marks its own `package.json` `private`
  and uses Changesets only for the changelog and the release.
- It would replace a stricter mechanism with a looser one. `check-versions.mjs`
  **requires** a bump for any runtime change, against a closed exempt list, and
  fails the pull request otherwise. A changeset is *declared* by the
  contributor; a forgotten one is silent. A gate beats a convention.
- Its changelog format is not Keep a Changelog, which
  `templates/CHANGELOG-reusable-template.md` mandates for every plugin.

`obra/superpowers`'s `.version-bump.json` solves a problem this repository does
not have: one product whose version lives in eleven manifests across eight agent
ecosystems. Here each plugin owns its version, and the README version badge is
**derived** — `scripts/lib/readme-contract.mjs` requires it to point at
`plugins/<id>/.claude-plugin/plugin.json`, so shields.io reads the live value and
the badge cannot disagree with the manifest. That is stronger than synchronising
two numbers and checking they match.

The one practice worth taking from Changesets needs none of the tooling: **the
changelog entry is written in the pull request that makes the change**, while
the context is fresh, rather than reconstructed at release time. That belongs in
`.claude/rules/plugin-authoring.md`, not in a dependency.

### Consequences

- The per-plugin changelog keeps both of its jobs: the human record and the
  artifact `version-plan.mjs` verifies.
- Adding a skill to a plugin requires no manifest edit, so there is no array to
  forget and no gate to write for it.
- Release mechanics stay in `check-versions.mjs`, the `version-check` job and
  the `Tag plugin versions` workflow, with no new dependency.
- A reader wanting "what changed across the catalog" must open each plugin's
  changelog until the generated index exists.

### Risks and mitigations

- **Per-plugin changelogs scale poorly for discovery.** At four plugins this is
  theoretical; at ten it is real. Mitigated by the generated root index, tracked
  as debt with its closing condition rather than built speculatively.
- **The `skills` field could become replacing rather than additive upstream.**
  It would be a breaking change to documented behavior, and the session-start
  snapshot already surfaces new Claude Code releases; a repository maintenance
  pass re-checks this class of assumption.
- **Rejecting Changesets forgoes contributor attribution in the changelog.**
  Accepted: this is a single-operator repository today, and attribution can be
  added by hand in the entry when an outside contribution lands.

### Confirmation

- `npm run check:versions` reports `bump: none` or the required bump, and the
  `version-check` job fails a runtime change without one.
- `node --test scripts/lib/version-plan.test.mjs` covers "a runtime change
  without a bump fails" and "a new plugin needs a changelog entry for its first
  version".
- `jq -e 'has("skills")' plugins/*/.claude-plugin/plugin.json` returns false for
  every plugin, and `npm run validate` plus `claude plugin validate --strict`
  pass with all six skills loaded from the default scan.

## More Information

- Verified on 2026-09-20 against Claude Code 2.1.278 (CI pins 2.1.276), the live
  [plugins-reference](https://code.claude.com/docs/en/plugins-reference) and
  [skills](https://code.claude.com/docs/en/skills) pages, and the upstream
  changelog.
- Comparables read at `obra/superpowers` 6.4.1 and `mattpocock/skills` 1.2.3.
  [mattpocock/skills#138](https://github.com/mattpocock/skills/issues/138), open
  since 2026-05-06, is a request to make individual skills installable — the
  cost of one plugin per repository, and the problem this catalog's shape
  already avoids.
- Related: [ADR-0001](adr-0001-marketplace-distribution-model.md) (why a
  standalone skill ships as a plugin) and
  [ADR-0003](adr-0003-plugin-versioning-and-tagging.md) (semver, the exempt
  list, and tagging).
