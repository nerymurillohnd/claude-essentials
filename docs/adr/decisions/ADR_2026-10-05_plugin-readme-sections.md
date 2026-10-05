---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Plugin README sections a user needs before installing

## Purpose

Make every plugin README answer, before installation, what the plugin contains, what it is for and what it solves, and how to keep it updated or remove it.

## Scope

`templates/readme/plugin.md`, `scripts/repo.py` (`README_SECTIONS`), `scripts/sync_readmes.py`, `scripts/check_repo.py`, `scripts/new_plugin.py`, every `plugins/*/README.md` and the gate test fixture.

## Context and problem statement

The README is what a user reads before choosing to install a plugin. The structure set by ADR generated-readme-content had no section for the situations a plugin solves, no questions users ask, and the update and removal commands were split between Installation and a one-line Uninstall section. Users who reach a plugin's README directly also need the full marketplace and install steps there.

## Decision drivers

- A user can decide to install from the plugin README alone.
- Structure and commands come from one source and cannot drift between plugins.
- The repo gate enforces the structure.

## Considered options

- Shared section list with new What it does and FAQ sections, Prerequisites, generated install, update and uninstall commands, emoji headings and generated component links
- Leave the structure to each plugin's author

## Decision outcome

Chosen option: **shared section list**. Sections, in order: Overview, What it does, Prerequisites, Installation, Usage, Components, Configuration and Permissions when they apply, FAQ, Update and uninstall, Documentation, License, each heading with one emoji. `repo.README_SECTIONS` is the single list the template, the generated Contents line and the gate share. What it does is a table of situations, what the plugin does and the result. Prerequisites replaces Requirements and generates a table with the Claude Code minimum and its check command. Installation generates the one-command session install with `--marketplace`, the two-step session install and the shell install. Update and uninstall generates the update, `/reload-plugins`, version check, disable and uninstall commands, with the note on data that uninstalling deletes. The Components table links each skill, agent, command and output style to its file. The FAQ holds 3 to 5 questions and opens with "Does installing this plugin modify my project?".

### Consequences

- Good, because every plugin README carries the same pre-install answers and the same commands.
- Good, because the gate rejects a missing section, a FAQ outside 3 to 5 questions and a different first question.
- Bad, because emoji headings change every anchor to a leading-hyphen form, so links into a README must use `repo.readme_anchor`.

### Confirmation

`scripts/check_repo.py` requires the headings from `repo.README_SECTIONS` and checks the FAQ; `scripts/sync_readmes.py --check` keeps the generated blocks current; `tests/test_gates.py` covers a missing section and each FAQ rule.

## Pros and cons of the options

### Shared section list

- Good, because structure and commands are generated or enforced.
- Bad, because a new section touches the template, the generator, the gate and the fixture together.

### Structure left to authors

- Good, because it is flexible.
- Bad, because READMEs drift apart and omit what users need before installing.

## More information

Updates part of [ADR generated-readme-content](ADR_2026-10-03_generated-readme-content.md). Commands verified on 2026-10-05 against the Claude Code 2.1.289 plugin CLI reference and install pages. Authoring rules: [docs/readme-guide.md](../../readme-guide.md).
