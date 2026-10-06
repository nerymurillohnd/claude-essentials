---
status: accepted
date: 2026-10-06
decision-makers:
  - "Maintainer"
consulted:
  - "Claude"
informed:
  - "Plugin authors"
---

# No version or verification stamps inside skills and references

## Purpose

Establishes where a plugin declares the versions it targets, and forbids repeating a version
or a verification date inside the skills, agents and reference files it ships.

## Scope

Every plugin in this marketplace: `skills/**`, `agents/**`, bundled references, fixtures and
hook comments. It does not touch release verification, which keeps happening: the pull
request, the changelog, the sourcing log, `NOTICE` and the pre-release re-check of a derived
plugin (`.claude/rules/plugins/derived-content.md`) are where that evidence belongs.

## Context and problem statement

`svelte-development` 0.2.0 shipped a verification stamp at the top of every reference file
("Verified against svelte 5.57.1 on 2026-10-05") plus a `Checked` date column on 30 errata
rows, patch versions pasted into shell examples, and HTTP-200-on-a-date claims: 23 stamped
headers, about 100 dates and about 245 exact versions across the plugin.

Each stamp is a promise the next release has to re-verify in a place no gate can see. The
cost is paid by the user who installs the plugin, because a stale stamp reads as a fact. The
first verification pass was also the trigger for reading a changelog ("if the installed
version is newer than this line"), which coupled a safety check to a snapshot that goes out
of date on its own.

## Decision drivers

- A fact that goes stale must live in one place, or it will not be updated everywhere.
- The skill is loaded into every session that touches the topic: tokens spent on provenance
  are tokens not spent on the rules.
- The protection the stamps carried (read the changelog before trusting a reference) must
  survive their removal, and must not depend on a date.
- Agent Skills best practice: no time-sensitive statements inside a skill.

## Considered options

- Declare the targets once, keep version numbers only where the number is the fact
- Keep the stamps and add a gate that re-verifies them
- Remove the stamps and the version-dependent guidance together

## Decision outcome

Chosen option: **declare the targets once, keep version numbers only where the number is the
fact**, because it removes the maintenance debt without removing content or protection.

Rules:

1. A plugin declares the versions it targets in its `README.md` and its `plugin.json`
   description, in majors. A skill may name the majors it is written for; it does not repeat
   patch versions, peer ranges or engines.
2. No file under `skills/**` or `agents/**` carries a verification date, a "checked on" line,
   a snapshot count or an HTTP-status-on-a-date claim.
3. A version number stays only when it is the fact being taught: the release that added or
   removed an API, a minimum that carries a security fix, a peer range, a compatibility
   table. Such a number lives in exactly one reference, and other files link to it.
4. An example that needs the installed version reads it
   (`node -p "require('<package>/package.json').version"`), never a pasted literal.
5. The trigger for reading a changelog window is mechanical and stampless: the installed
   version is not the latest on the registry, or a reference disagrees with what the
   installed version does. The cases live in the plugin's `changelogs.md`.

### Consequences

- Good, because a release no longer has to find and refresh stamps scattered across the
  plugin, and a user never reads a date that stopped being true.
- Good, because the changelog check now fires on a comparison the model can always make,
  instead of on a line that silently ages.
- Bad, because the plugin no longer tells a reader which exact versions its references were
  written against; the pull request and the changelog carry that instead.
- Bad, because rule 3 is a judgment call, so a review has to tell a taught version number
  from a decorative one.

### Confirmation

Applied to `svelte-development` on 2026-10-06 on branch `svelte-development/skill-contracts`:
23 stamped headers, the errata date column, 16 pasted versions in examples and every dated
claim removed, with `grep -rnE '20[0-9]{2}-[0-9]{2}-[0-9]{2}'` over the plugin returning
nothing outside `CHANGELOG.md` and the `NOTICE` base commit. Reviewed by the maintainer in
that branch's pull request; `scripts/check.py` must pass. Revisit if a gate is written to
enforce rule 2 mechanically, which would let rule 3 be tightened.

## Pros and cons of the options

### Declare the targets once, keep version numbers only where the number is the fact

- Good, because the debt disappears while the teaching content stays intact.
- Good, because it matches the Agent Skills guidance against time-sensitive text.
- Bad, because nothing mechanical stops a new stamp from being added later.

### Keep the stamps and add a gate that re-verifies them

- Good, because the provenance would stay visible and provably current.
- Bad, because the gate would have to fetch upstream docs and packages on every run, which no
  offline gate in this repository does.
- Bad, because it keeps spending session tokens on provenance in every loaded skill.

### Remove the stamps and the version-dependent guidance together

- Good, because it is the simplest to maintain.
- Bad, because it deletes the plugin's most valuable content: which release added or removed
  an API is exactly what training data gets wrong.

## More information

Related: [ADR derived-third-party-content](ADR_2026-10-05_derived-third-party-content.md),
whose pre-release re-check stays in force and is now the only place that verification is
recorded. Best practices followed:
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
