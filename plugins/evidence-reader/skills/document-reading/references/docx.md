# Reading Word documents (.docx)

## Procedure

1. `extract_docx.py FILE` prints every body
   paragraph (`P<n>`), table cell (`T<t>.R<r>.C<c>`), header, footer, footnote and
   endnote, plus sections for tracked changes and comments.
2. The first line gives the counts. Your coverage statement is "all N body
   paragraphs, M tables, K extra parts".
3. Use `--json` when you need to post-process many paragraphs, `--view accepted`
   for the text as it would read after accepting every change, `--view original`
   for the text before the changes.

## Citing

- Cite as `<heading path> > P<n>`, e.g. `Payment > P4`. Word stores no page
  numbers; never cite a page for a .docx.
- Tracked changes: report who inserted or deleted what and when, from the
  **TRACKED CHANGES** section. In the default markup view, `[+text+]` is an
  insertion, `[-text-]` a deletion, and `[+-text-+]` text one reviewer inserted and
  another deleted, which appears in neither the accepted nor the original view.
  A moved passage is a deletion where it came from and an insertion where it went.
- Comments: report the comment text, author, date and the paragraph it is
  anchored to. An unanchored comment is still a finding.

## Pitfalls

- A contract under negotiation often has tracked changes that alter the meaning
  (FOB becoming CIF). Always say whether a quoted clause includes pending changes.
- Text in text boxes, shapes or embedded objects may not be in the body XML;
  if the document plainly refers to content you did not see, list it under
  **Not verified**.
- Exit `3` means a password-protected or legacy `.doc` file. Report it; do not
  try to open it another way.
