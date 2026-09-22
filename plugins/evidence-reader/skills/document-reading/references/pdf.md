# Reading PDFs

## Tools and what each one is good for

| Tool | Gives you | Use it for |
| --- | --- | --- |
| `pdf_probe.py probe` (poppler) | page count, encryption, pages with no text layer, a 20-page chunk plan | always first |
| `pdf_probe.py text --pages A-B` (poppler) | the exact text layer with `p<page> L<line>` locators | quotes, numbers, clauses |
| Read with `pages="A-B"` (needs poppler's `pdftoppm`) | page **images only**, up to 20 pages per call | scanned pages, stamps, signatures, handwriting, charts, layout |
| Read without `pages` | text layer **and** an image of every page | short PDFs only; a long PDF floods the context |

## Procedure

1. `pdf_probe.py probe FILE`.
2. For each range in `chunk_plan`, run `pdf_probe.py text FILE --pages A-B` and
   log the range as covered. `text` refuses a range longer than 20 pages
   (exit 2), so follow the plan instead of asking for the whole file.
3. For every page listed in `pages_without_text_layer`, read it with Read
   `pages=` (vision) and cite it as `p<n> (vision)`.
4. When a page has a text layer but the question depends on what the page
   *looks like* (a signature, a stamp, a table whose columns the text layer
   scrambled), also read that page with vision and say which source you used.
5. The covered ranges must equal `1-<pages>`. Anything missing is partial.

## When poppler is missing (exit code 5)

An exit 5 whose message starts `pdf_probe.py needs Python 3.14` is the interpreter,
not poppler: report the file as **Not verified: python3 older than 3.14**. Otherwise:


- A short PDF (roughly 10 pages or fewer) can still be read whole with Read,
  which returns the text layer and page images. Cite `p<n>` from its page markers.
- For a longer PDF, do not guess. Read what Read allows, list the uncovered pages
  under **Not verified: poppler not installed**, and name the install command
  from the script message.

## Pitfalls

- A page with an empty text layer is usually scanned. Its text exists only in
  the image; never report it as blank.
- Password-protected PDFs exit `3`. Report them as not reviewed; never try to
  crack or bypass the password.
- Multi-column layouts can interleave in `-layout` mode; use `--raw` for reading
  order and say which you used when the order matters.
- Text-layer numbers win over vision for exact values. If a scanned page and its
  (OCR'd) text layer disagree, report both readings.
