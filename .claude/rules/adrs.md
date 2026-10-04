---
paths:
  - "docs/adr/**"
  - "templates/adr/**"
  - "scripts/validate_adrs.py"
---

# Architecture decision records

- ADRs live in `docs/adr/decisions/` as `ADR_YYYY-MM-DD_<slug>.md`; the date is the registration date.
- The frontmatter `date` equals the filename date, and `status` is proposed, accepted, rejected, deprecated or superseded.
- Accepted ADRs are never rewritten: a new ADR links the old one, which is marked `superseded` with a link to its successor.
- One exception: when a newer ADR replaces only part of an accepted ADR, append a dated pointer note under its `## More information` and keep its `status` `accepted`.
- Never edit the decision, options or consequences of an accepted ADR, and never use a pointer note to change them.
- Cite the approval a note records only when it has a traceable source: the session and the date.
- Check records with `python3 scripts/validate_adrs.py`, which also runs in `python3 scripts/check.py`.
