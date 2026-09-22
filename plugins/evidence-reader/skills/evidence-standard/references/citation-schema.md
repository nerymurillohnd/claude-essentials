# Citation schema

Every finding carries one locator in this form: `<file> <locator>`. The
locators below are exactly what the evidence-reader scripts print, so a reader
can re-run the script and land on the same spot.

| Source | Locator | Example | Produced by |
| --- | --- | --- | --- |
| PDF, text layer | `p<page> L<line>` | `report.pdf p45 L2` | `pdf_probe.py text` |
| PDF, page read with vision | `p<page> (vision)` | `invoices.pdf p2 (vision)` | Read with `pages` |
| Word body paragraph | `<heading path> > P<n>` | `contract.docx Payment > P4` | `extract_docx.py` |
| Word table cell | `T<t>.R<r>.C<c>` | `contract.docx T1.R2.C2` | `extract_docx.py` |
| Word header, footer, notes | `<part> P<n>` | `contract.docx footer1.xml P1` | `extract_docx.py` |
| Word tracked change | `P<n> insertion/deletion by <author> on <date>` | `contract.docx P6 deletion by Buyer on 2026-09-01` | `extract_docx.py` |
| Word comment | `comment <id> on <locator>` | `contract.docx comment 0 on P4` | `extract_docx.py` |
| PowerPoint shape | `S<n>.<shape name>` | `deck.pptx S1.Title 1` | `extract_pptx.py` |
| PowerPoint notes, chart, table | `S<n>.notes`, `S<n>.chart<k>`, `S<n>.T<t>.R<r>.C<c>` | `deck.pptx S1.notes` | `extract_pptx.py` |
| PowerPoint SmartArt, comment | `S<n>.diagram<k>`, `S<n>.comment<k>` | `deck.pptx S3.comment1` | `extract_pptx.py` |
| Spreadsheet cell | `<Sheet>!<A1>` | `sales.xlsx Sales!D12` | `extract_xlsx.py` |
| Spreadsheet range | `<Sheet>!<A1>:<B2>` | `sales.xlsx Sales!D2:D11` | `extract_xlsx.py` |
| CSV/TSV row | `row <r> (line <l>)` | `shipments.csv row 50000 (line 50001)` | `profile_csv.py` |
| JSON value | JSON Pointer | `order.json /order/lines/1/qty` | `locate_json_xml.py` |
| XML value | `line <l> <path>` | `catalog.xml line 4 /catalog[1]/product[2]/@sku` | `locate_json_xml.py` |
| Markdown or plain text | `L<line>` or `L<a>-L<b>` | `notes.md L3` | Read (line numbers) |
| Image, whole | `<file>` | `label.png` | Read |
| Image, region | `region x=<x> y=<y> w=<w> h=<h>` | `label.png region x=0 y=360 w=600 h=90` | `image_tool.py tile` |
| Image page (TIFF, HEIC) | `page <n>` | `packing-list.tiff page 3` | `image_tool.py convert` |
| Image metadata | `meta <Group:Tag>` | `label.jpg meta EXIF:Software` | `image_tool.py info` |

## Rules

- **Word has no page numbers.** Pagination is computed by whatever program
  renders the file, so never cite "page N" for a .docx. Use the heading path and
  paragraph number.
- **Value provenance.** Mark spreadsheet values as `cached` (stored by the
  spreadsheet application), `recomputed` (computed by the script because no cached
  value existed) or `missing`. Never cite a recomputed value as if Excel stored it.
- **Vision vs text.** When the same PDF page has a text layer, quote the text
  layer. Use `(vision)` only for scanned pages, stamps, signatures, handwriting or
  layout that the text layer does not carry. If the two disagree, report both.
- **Metadata is a claim.** Cite metadata as "according to the metadata"; it can
  be edited and proves nothing on its own.
- **Derived images.** A crop or converted page is cited by its original file plus
  page or region, never by its temporary path.
