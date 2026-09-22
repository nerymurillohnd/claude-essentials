# Duplicate and near-duplicate images

## Command

`image_tool.py dedupe FILE...`

| Output | Meaning | Report as |
| --- | --- | --- |
| `SAME FILE listed twice` | one file passed under two paths | not a duplicate; review it once |
| `EXACT duplicates (same bytes)` | identical SHA-256 | one image with several copies |
| `VISUALLY IDENTICAL (phash <distance>)`, distance ≤ 0.1 | same picture re-encoded or re-saved | one image with several copies, after a quick view of both |
| `NEAR-DUPLICATE candidate (phash <distance>)`, distance ≤ 5 | resized, brightened or recompressed version | view both before deciding; they may differ in a detail that matters (a date, a lot code) |

Perceptual-hash distances need ImageMagick; without it only exact duplicates
are detected, which the output states. A file whose bytes are not a known image
format is never passed to ImageMagick: the output says its near-duplicate check
was skipped, and it still counts in the exact-duplicate check.

## Rules

- Duplicates are reported once, listing every copy, not as separate findings.
- Near-duplicates are candidates, not conclusions: two photos of different lots
  with identical labels can score as near-duplicates. Compare the details.
- More than 200 distinct images exceeds the pairwise comparison limit; split the
  batch.
