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
- Check records with `python3 scripts/validate_adrs.py`, which also runs in `python3 scripts/check.py`.
