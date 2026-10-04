---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Hand-written JSON Schemas for Claude Code files are not adopted yet

## Purpose

Record why candidate JSON Schemas for `.lsp.json`, `.mcp.json`, `plugin.json` and `marketplace.json` are not part of the repository, and what would change that.

## Scope

Any JSON Schema describing Claude Code file formats, for validation or editor autocomplete.

## Context and problem statement

Claude Code publishes no JSON Schema: the `$schema` URL that `claude plugin init` writes returns HTTP 404. Candidate schemas were offered, written against Claude Code 2.1.281 with `additionalProperties: false`. Checked against 2.1.289 docs and changelog, they reject valid configuration: the LSP schema lacks `requestTimeout` (documented since 2.1.288), and the MCP schema excludes `bareElicitationCapability`, which the 2.1.287 release notes tell users to add.

## Decision drivers

- Gates must never reject configuration Claude Code accepts.
- The official validator is the authority.
- Strict schemas drift with every Claude Code release.

## Considered options

- Do not adopt; rely on `claude plugin validate --strict`
- Adopt the schemas as validation gates
- Adopt them as editor aids only, kept outside the gates

## Decision outcome

Chosen option: **do not adopt yet**. `claude plugin validate --strict` validates manifests, MCP and LSP configuration, and rejects unknown keys in strict objects.

### Consequences

- Good, because no gate can contradict Claude Code.
- Bad, because contributors get no editor autocomplete for these files.

### Confirmation

Revisit when either Claude Code publishes an official schema, or a schema set is maintained with a test that compares its verdicts with `claude plugin validate --strict` on positive and negative fixtures for every release in the review window.

## Pros and cons of the options

### Rely on the official validator

- Good, because it always matches the installed Claude Code.
- Bad, because errors appear only when the validator runs.

### Schemas as gates

- Good, because editors can validate while typing.
- Bad, because a stale schema blocks valid plugins, as shown above.

## More information

The runtime observation recorded with the LSP candidate (one invalid server drops every server in the same file) is noted in CLAUDE.md as a claim to re-verify before relying on it.
