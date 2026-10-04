# Architecture Decision Records

Use [the ADR template](../../templates/adr/ADR_YYYY-MM-DD_decision-slug.md) when an important decision for Claude Essentials needs a record. Save the record in [decisions/](decisions) as `ADR_YYYY-MM-DD_<decision-slug>.md`. The date is the registration date and the slug is lowercase kebab-case, so the file list shows what was decided and when without opening a record.

## Create a record

1. Copy the template into `decisions/` and replace every brace-delimited placeholder.
2. Keep the frontmatter `date` equal to the filename date. Use one `status`: `proposed`, `accepted`, `rejected`, `deprecated`, or `superseded`. Name accountable decision makers.
3. Omit unused `consulted` and `informed` fields. Keep the purpose, scope, context, drivers, options, rationale, consequences, and confirmation concrete. Remove the optional `Pros and cons of the options` or `More information` sections when they add no value.
4. Link supporting issues, pull requests, tests, or other evidence. Run `python3 scripts/validate_adrs.py` (also part of `python3 scripts/check.py`) and review the rendered Markdown.

Recording a discussion does not imply acceptance. Keep accepted ADRs as historical records. To change one, create a new ADR, link both records, and mark the earlier one `superseded` without rewriting its rationale.

This project uses the MADR decision structure without corporate document metadata: the filename and Git history already identify the record, and taxonomy or copyright fields would not improve this repository's decisions.
