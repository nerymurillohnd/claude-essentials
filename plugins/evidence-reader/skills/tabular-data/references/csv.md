# Profiling CSV and TSV files

## Procedure

1. `profile_csv.py profile FILE` — one
   streaming pass: encoding, delimiter, exact data-row count, ragged rows with
   their line numbers, and per column the non-empty count, numeric count, min,
   max and exact decimal sum.
2. `profile_csv.py rows FILE --from N --to M` to quote specific rows.
3. `profile_csv.py find FILE --pattern REGEX [--column NAME]` to locate every
   row that matches, with its line number.
4. Force a delimiter with `profile_csv.py --delimiter ';' profile FILE` (before the
   subcommand, like `--encoding`) when sniffing picks the wrong one
   (European exports often use `;` with `,` as the decimal mark).

## Citing

- `row <r> (line <l>)`: `r` counts data rows after the header, `l` is the
  physical line in the file. A quoted field containing a newline makes them
  diverge; both are printed so either can be checked.
- Column totals: cite the `profile` command and the column name.

## Pitfalls

- **Encoding:** `encoding=cp1252` means the file was not valid UTF-8; accented
  names may be mis-decoded. Say so. A file that is neither UTF-8 nor
  Windows-1252 stops with exit 2: report it as not verified. Use
  `--encoding NAME` (before the subcommand) only when the file's source states
  the encoding, and say that you forced it.
- **Codes that look like numbers** (`2024_001`, `00123`, `nan`, `inf`) are
  counted as text, never summed: lot, invoice and SKU codes are identifiers.
  Only plain decimal notation (`12`, `-3.5`, `1e3`) is numeric.
- **Ragged rows** (wrong field count) are data-quality findings in their own
  right; list them with line numbers.
- **Numbers stored with thousands separators or currency symbols** (`1,234.50`,
  `$12`) are counted as text, not numeric. If a column you expected to be numeric
  shows `numeric=0`, report that instead of summing it by hand.
- **Decimal commas** (`12,5`) are text to the profiler; report the column as
  text and the reason.
- The profile covers every row; never state a total from a sample.
