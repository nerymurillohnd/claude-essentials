# Security Policy

## Reporting a vulnerability

Report a security issue in this marketplace's own tooling (schemas, the
generator/validator scripts, CI) or in a specific plugin's manifest/skill/agent
content via [GitHub Security Advisories](https://github.com/nerymurillohnd/claude-essentials/security/advisories/new)
for this repository. Don't open a public issue for an unpatched vulnerability.

## Scope

- **In scope:** this repository's own catalog/tooling, and the content of
  plugins hosted under `plugins/`.
- **Out of scope:** Claude Code itself — report those to Anthropic via their
  [HackerOne program](https://hackerone.com/4f1f16ba-10d3-4d09-9ecc-c721aad90f24/embedded_submissions/new),
  per [Claude Code's security docs](https://code.claude.com/docs/en/security).

## Before installing a plugin from this marketplace

Plugins are highly trusted components — see each plugin's own README
(**Installation effects** / **Runtime effects on a target project** sections)
for what it reads, writes, or reaches over the network before installing it.
