<!--
  Reusable security policy template.

  Copy this file to SECURITY.md at the repository root. Replace every
  {{PLACEHOLDER}}, remove sections that don't apply (e.g. Supported Versions
  for a project with no meaningful version support window), and verify the
  reporting channel actually reaches someone who will act on it before
  publishing.

  Don't invent a reporting mechanism the project doesn't have — GitHub Private
  Vulnerability Reporting (Security Advisories) requires the repo to actually
  exist on GitHub with the feature enabled; confirm that before linking it.
-->

# Security Policy

<!-- Optional: keep only when the project supports specific released versions
differently (e.g. only the latest major gets security fixes). Remove this
whole section for a project with no meaningful version-support distinction. -->

## Supported Versions

| Version | Supported |
| --- | --- |
| {{LATEST_VERSION_OR_RANGE}} | ✅ |
| {{OLDER_VERSION_OR_RANGE}} | ❌ |

## Reporting a vulnerability

Report a security issue via {{REPORTING_CHANNEL — e.g. "GitHub Security Advisories at https://github.com/{{owner}}/{{repo}}/security/advisories/new", or a monitored security-report email address}}.

Don't open a public issue, discussion, or pull request for an unpatched
vulnerability. Include reproduction steps, affected version/commit, and
impact. Expect {{RESPONSE_TIME_COMMITMENT_OR_"an initial response within a stated window, only if that's an actual commitment"}}.

## Scope

- **In scope:** {{what this repo's own security policy covers — its tooling, its distributed artifacts, etc.}}
- **Out of scope:** {{dependencies, platforms, or upstream projects this repo doesn't control — say where to report those instead, don't leave the reporter with nowhere to go.}}

<!-- Optional: keep only when the project distributes something with
material permissions/side-effects a consumer should review before use. -->

## Before using {{THE_DISTRIBUTED_ARTIFACT}}

{{Point the reader at wherever permissions/side-effects are documented per
artifact — don't duplicate that content here.}}
