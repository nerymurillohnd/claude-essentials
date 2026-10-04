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
- The numbered-records ADR is `superseded` by `ADR_2026-10-03_adr-dated-records`.
- Check records with `uv run scripts/validate_adrs.py`, which also runs in `uv run scripts/check.py`.
