# Reading JSON and XML data

## Procedure

1. `locate_json_xml.py FILE` prints one line
   per value with a locator and a final `COVERED … values=N` line.
2. Narrow with `--grep REGEX` (matches the locator or the value) and cap output
   with `--limit N`; the COVERED line still reports the total.
3. `.jsonl` / `.ndjson` files are read line by line; locators start with
   `line<n>`.

## Citing

- JSON: the JSON Pointer (RFC 6901), e.g. `/order/lines/1/qty`. Array positions
  are zero-based, as in the standard.
- XML: `line <l>` plus an XPath-like path with 1-based sibling positions, e.g.
  `line 4 /catalog[1]/product[2]/@sku`.

## Pitfalls

- XML that declares a DTD or entities is refused (exit `4`) to prevent
  entity-expansion attacks. Report it as not reviewed: unsafe input.
- XML element and attribute names appear exactly as written, including any
  namespace prefix (`ns:price`). The prefix is not resolved to its namespace URI.
- JSON integers keep their exact value. Decimal numbers are re-printed by Python
  and can lose digits beyond double precision (about 15–17 significant digits);
  when a finding depends on more digits, quote the raw text from the file instead.
- Duplicate keys in a JSON object keep only the last value (standard parser
  behavior). If the raw text shows duplicates, report it.
