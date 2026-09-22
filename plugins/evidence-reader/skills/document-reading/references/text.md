# Reading Markdown and plain text

## Procedure

1. Count the lines first (`wc -l FILE`) so you know the total you must cover.
2. Read with the Read tool in chunks of 500–1000 lines using `offset` and
   `limit`, in order, until the last line.
3. Log each chunk as `L<a>-L<b>`. The chunks must add up to `L1-L<total>`.

## Citing

- `L<line>` or `L<a>-L<b>` using the line numbers Read prints.
- For Markdown, add the nearest heading when it helps: `notes.md (Lot notes) L3`.

## Pitfalls

- Very long single lines (minified text, logs) can hide content inside one line
  number. Say so when a finding sits inside a long line.
- Non-UTF-8 text may show replacement characters. Report the encoding problem
  instead of guessing the original characters.
- Front matter, HTML comments and code blocks are content too; include them in a
  full read unless the task excludes them.
