# Reading PowerPoint decks (.pptx)

## Procedure

1. `extract_pptx.py FILE` lists slides in
   presentation order with every shape's text, table cells, speaker notes, chart
   titles and cached series values, SmartArt text and reviewer comments.
2. The first line gives the slide count, the hidden slides and any orphan slide
   files. Coverage is "all N slides (H hidden)".

## Citing

- `S<n>.<shape name>` for slide text, `S<n>.notes` for speaker notes,
  `S<n>.chart<k>` for chart data, `S<n>.T<t>.R<r>.C<c>` for tables,
  `S<n>.diagram<k>` for SmartArt and `S<n>.comment<k>` for reviewer comments.
- Slide numbers follow the deck's own order (the slide list inside the file),
  not the internal file names.

## Pitfalls

- **Hidden slides** are part of the file but not the slideshow. Report their
  content and say they are hidden; they often hold backup or outdated numbers.
- **Orphan slides** exist in the package but are not in the deck. Mention them
  once; do not treat their text as deck content.
- **Speaker notes** frequently qualify the slide ("the 12% excludes the returned
  shipment"). A summary that drops a qualifying note is misleading; include it.
- Chart numbers come from the chart's cached values. They can be stale relative
  to a linked spreadsheet; say they are the values stored in the deck.
- Images on slides carry no text for the extractor. If a slide's meaning depends
  on an image, say so under **Not verified** or inspect it with vision.
