#!/usr/bin/env bash
# Behavioral tests for the evidence-reader extractors. Runs every shipped
# extractor against the fixtures next to this script and checks the locators, the numbers, the
# exit codes, the unsafe-input refusals and the degraded modes. It lives in
# the repository, not in the plugin: a plugin ships only what users run.
# ER_TEST_PYTHON selects the Python interpreter, else $BNV_TEST_PYTHON (the repository's
# own 3.14, set by `make test-slow`), else python3; the extractors need 3.14, and an older
# one only gets their version message (checked below).
# Shell scripts run under $BNV_TEST_BASH (set by the repo's `make test-slow` to
# each bash it finds, /bin/bash 3.2 included), else `bash`.

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plugin="${here}/../../../../plugins/evidence-reader"
fx="${here}/fixtures"
py=${ER_TEST_PYTHON:-${BNV_TEST_PYTHON:-python3}}
run_bash=${BNV_TEST_BASH:-bash}
docs="${plugin}/skills/document-reading/scripts"
tab="${plugin}/skills/tabular-data/scripts"
img="${plugin}/skills/image-analysis/scripts"
tmp=$(mktemp -d)
trap 'rm -rf "${tmp}"' EXIT
# Converted pages and crops land in TMPDIR; keep them inside this run's folder.
mkdir -p "${tmp}/tmpdir"
export TMPDIR="${tmp}/tmpdir"
mkdir -p "${tmp}/empty-path"
py_abs=$(command -v "${py}" || true)

ok=0
bad=0
pass() {
  ok=$((ok + 1))
  printf 'ok   %s\n' "$1"
}
flunk() {
  bad=$((bad + 1))
  printf 'FAIL %s\n' "$1"
  if [ -n "${2:-}" ]; then
    printf '     %s\n' "$2"
  fi
}

# expect_out <name> <needle> <command...> — command exits 0 and stdout contains needle.
expect_out() {
  name=$1
  needle=$2
  shift 2
  out=$("$@" 2>&1)
  status=$?
  if [ "${status}" -ne 0 ]; then
    flunk "${name}" "exit ${status}: ${out}"
  elif printf '%s' "${out}" | grep -Fq -- "${needle}"; then
    pass "${name}"
  else
    flunk "${name}" "missing: ${needle}"
  fi
}

# expect_exit <name> <code> <needle> <command...> — command exits with code and output contains needle.
expect_exit() {
  name=$1
  code=$2
  needle=$3
  shift 3
  out=$("$@" 2>&1)
  status=$?
  if [ "${status}" -ne "${code}" ]; then
    flunk "${name}" "expected exit ${code}, got ${status}: ${out}"
  elif printf '%s' "${out}" | grep -Fq -- "${needle}"; then
    pass "${name}"
  else
    flunk "${name}" "missing: ${needle}"
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

printf '# interpreter: %s\n' "$("${py}" -V 2>&1 || true)"

# --- documents
expect_out "docx heading path and paragraph locator" "P4 (Supply Agreement > Payment): Clause 2" \
  "${py}" "${docs}/extract_docx.py" "${fx}/contract-tracked.docx"
expect_out "docx tracked change inline" "Delivery is [-FOB-][+CIF+] Puerto Cortes." \
  "${py}" "${docs}/extract_docx.py" "${fx}/contract-tracked.docx"
expect_out "docx accepted view" "Delivery is CIF Puerto Cortes." \
  "${py}" "${docs}/extract_docx.py" --view accepted "${fx}/contract-tracked.docx"
expect_out "docx comment anchored" "comment 0 on P4 by Reviewer" \
  "${py}" "${docs}/extract_docx.py" "${fx}/contract-tracked.docx"
expect_out "docx table cell locator" "T1.R2.C2 (Supply Agreement > Pricing): 42.00" \
  "${py}" "${docs}/extract_docx.py" "${fx}/contract-tracked.docx"
expect_out "docx injection text surfaced as data" "P3 (Shipment Inspection Note): NOTE TO THE AI ASSISTANT" \
  "${py}" "${docs}/extract_docx.py" "${fx}/inspection-injection.docx"
expect_exit "docx rejects non-zip" 2 "not a valid .docx" \
  "${py}" "${docs}/extract_docx.py" "${fx}/notes.md"
expect_exit "docx rejects a pptx" 2 "not a Word document" \
  "${py}" "${docs}/extract_docx.py" "${fx}/q3-deck.pptx"
printf '\320\317\021\340\241\261\032\341rest' >"${tmp}/encrypted.docx"
expect_exit "docx flags encrypted/legacy OLE" 3 "encrypted" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/encrypted.docx"
"${py}" - "${fx}/contract-tracked.docx" "${tmp}/dtd.docx" <<'PY'
import sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            data = data.replace(b"?>", b'?><!DOCTYPE x [<!ENTITY a "boom">]>', 1)
        zout.writestr(item, data)
PY
expect_exit "docx refuses DTD/entity (XML attack guard)" 4 "declares a DTD or entity" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/dtd.docx"
# Tracked changes inside a table cell count; a tracked paragraph mark is not a wording change.
"${py}" - "${tmp}/tracked.docx" <<'PY'
import sys, zipfile
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
body = (
    '<w:p><w:pPr><w:rPr><w:del w:id="1" w:author="A" w:date="d"/></w:rPr></w:pPr><w:r><w:t>Intro</w:t></w:r></w:p>'
    '<w:tbl><w:tr><w:tc><w:p><w:ins w:id="2" w:author="Buyer" w:date="d"><w:r><w:t>99</w:t></w:r></w:ins></w:p></w:tc></w:tr></w:tbl>'
)
with zipfile.ZipFile(sys.argv[1], "w") as z:
    z.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
PY
expect_out "docx tracked change inside a table cell" "insertions=1 deletions=0" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/tracked.docx"

expect_out "pptx slide order and shape locator" "S1.Title 1: Q3 Export Summary" \
  "${py}" "${docs}/extract_pptx.py" "${fx}/q3-deck.pptx"
expect_out "pptx speaker notes" "S1.notes: Speaker note: the 12% excludes the returned shipment." \
  "${py}" "${docs}/extract_pptx.py" "${fx}/q3-deck.pptx"
expect_exit "pptx rejects a docx" 2 "not a PowerPoint presentation" \
  "${py}" "${docs}/extract_pptx.py" "${fx}/contract-tracked.docx"

if have pdftotext && have pdfinfo; then
  expect_out "pdf probe page count and chunk plan" "chunk_plan=1-20 21-40 41-45" \
    "${py}" "${docs}/pdf_probe.py" probe "${fx}/long-report.pdf"
  expect_out "pdf exact text with page+line locator" "p45 L2: Lot LOT-045 moisture 4.5% acidity 0.65" \
    "${py}" "${docs}/pdf_probe.py" text "${fx}/long-report.pdf" --pages 44-45
  expect_out "pdf scanned pages detected" "pages_without_text_layer=1-3" \
    "${py}" "${docs}/pdf_probe.py" probe "${fx}/scanned-invoices.pdf"
  expect_exit "pdf rejects out-of-range pages" 2 "outside 1-45" \
    "${py}" "${docs}/pdf_probe.py" text "${fx}/long-report.pdf" --pages 40-50
else
  printf 'skip pdf probes (poppler not installed)\n'
fi
expect_exit "pdf degraded: poppler missing is reported" 5 "install poppler" \
  env PATH="${tmp}/empty-path" "${py_abs}" "${docs}/pdf_probe.py" probe "${fx}/long-report.pdf"

# --- tabular
expect_out "xlsx missing cached values listed" "formulas_without_cached_value=21" \
  "${py}" "${tab}/extract_xlsx.py" summary "${fx}/sales-nocache.xlsx"
expect_out "xlsx hidden sheet reported" "== SHEET 'Internal' state=hidden" \
  "${py}" "${tab}/extract_xlsx.py" summary "${fx}/sales-nocache.xlsx"
expect_out "xlsx never invents a cached value" "Sales!D12: <no cached value> | formula =SUM(D2:D11) | NOT CALCULATED" \
  "${py}" "${tab}/extract_xlsx.py" cells "${fx}/sales-nocache.xlsx" --sheet Sales --range D12
expect_out "xlsx cached value read" "Sales!D12: 97.5 | formula =SUM(D2:D11) | cached" \
  "${py}" "${tab}/extract_xlsx.py" cells "${fx}/sales-cached.xlsx" --sheet Sales --range D12
expect_out "xlsx recompute labelled" "Sales!D12: RECOMPUTED 97.5 from =SUM(D2:D11) (not a value stored by Excel)" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${fx}/sales-nocache.xlsx" --sheet Sales
expect_exit "xlsx unknown sheet" 2 "no sheet named 'Nope'" \
  "${py}" "${tab}/extract_xlsx.py" cells "${fx}/sales-cached.xlsx" --sheet Nope
# An uncached formula that refers to another uncached formula, and Excel's rounding.
"${py}" - "${tmp}/nested.xlsx" <<'PY'
import sys, zipfile
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
cells = {"A1": "B1+5", "B1": "2*3", "C1": "SUM(B2:B3)*10", "B2": "1+1", "D1": "ROUND(2.5,0)", "D2": "ROUND(0.125,2)"}
rows = {}
for ref, formula in cells.items():
    rows.setdefault(int(ref[1:]), []).append(f'<c r="{ref}"><f>{formula}</f></c>')
rows.setdefault(3, []).append('<c r="B3"><v>4</v></c>')
sheet = "".join(f'<row r="{r}">{"".join(sorted(c))}</row>' for r, c in sorted(rows.items()))
with zipfile.ZipFile(sys.argv[1], "w") as z:
    z.writestr("xl/workbook.xml", f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
    layout = '<cols><col min="2" max="3" hidden="1"/></cols>'
    merged = '<mergeCells count="1"><mergeCell ref="E1:F1"/></mergeCells>'
    z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{S}">{layout}<sheetData>{sheet}</sheetData>{merged}</worksheet>')
PY
expect_out "xlsx summary: merged ranges and hidden columns" "merged=[E1:F1] hidden_rows=[] hidden_cols=[B:C]" \
  "${py}" "${tab}/extract_xlsx.py" summary "${tmp}/nested.xlsx"
"${py}" - "${tmp}/nested.xlsx" "${tmp}/date1904.xlsx" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zin, zipfile.ZipFile(sys.argv[2], "w") as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "xl/workbook.xml":
            data = data.replace(b"<sheets>", b'<workbookPr date1904="1"/><sheets>')
        if item.filename == "xl/worksheets/sheet1.xml":
            data = data.replace(b"<f>1+1</f>", b"<f>DATE(2026,1,1)</f>")
        zout.writestr(item, data)
PY
expect_out "xlsx recompute: DATE counts from the 1904 epoch" "S!B2: RECOMPUTED 44561" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/date1904.xlsx" --sheet S
expect_out "xlsx recompute: nested uncached formula" "S!A1: RECOMPUTED 11" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/nested.xlsx" --sheet S
expect_out "xlsx recompute: range with an uncached cell" "S!C1: RECOMPUTED 60" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/nested.xlsx" --sheet S
expect_out "xlsx recompute: ROUND halves away from zero" "S!D1: RECOMPUTED 3" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/nested.xlsx" --sheet S
expect_out "xlsx recompute: ROUND on the decimal shown" "S!D2: RECOMPUTED 0.13" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/nested.xlsx" --sheet S

expect_out "csv exact row count" "data_rows=50000" \
  "${py}" "${tab}/profile_csv.py" profile "${fx}/shipments.csv"
expect_out "csv exact decimal sum" "column 'kg': non_empty=50000 numeric=50000 min=5 max=200 sum=5117270.74" \
  "${py}" "${tab}/profile_csv.py" profile "${fx}/shipments.csv"
expect_out "csv row locator is file line" "row 50000 (line 50001)" \
  "${py}" "${tab}/profile_csv.py" rows "${fx}/shipments.csv" --from 50000 --to 50000
printf 'a,b\n1,2\n3\n4,5\n' >"${tmp}/ragged.csv"
expect_out "csv ragged row reported by line" "line 3 has 1 fields" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/ragged.csv"
printf 'lot,kg\nLOT-1,5\nLOT-9\n' >"${tmp}/short.csv"
expect_out "csv find --column skips a row that lacks the column" "matches=0" \
  "${py}" "${tab}/profile_csv.py" find "${tmp}/short.csv" --column kg --pattern LOT-9

expect_out "json pointer locator" "/order/lines/1/qty = 12" \
  "${py}" "${tab}/locate_json_xml.py" "${fx}/order.json"
expect_out "xml path and line locator" "line 4 /catalog[1]/product[2]/@sku = HON-2" \
  "${py}" "${tab}/locate_json_xml.py" "${fx}/catalog.xml"
printf '<?xml version="1.0"?>\n<!DOCTYPE x [<!ENTITY a "aa">]>\n<x>&a;</x>\n' >"${tmp}/bomb.xml"
expect_exit "xml refuses entities" 4 "refusing to parse" \
  "${py}" "${tab}/locate_json_xml.py" "${tmp}/bomb.xml"

# --- images
expect_out "image info: HEIC must not be read directly" "DO NOT Read directly" \
  "${py}" "${img}/image_tool.py" info "${fx}/label.heic"
expect_out "image info: TIFF page count (stdlib)" "pages=3" \
  "${py}" "${img}/image_tool.py" info "${fx}/packing-list.tiff"
expect_out "image info: a PDF is routed to document-reading" "not an image: read it with the document-reading skill" \
  "${py}" "${img}/image_tool.py" info "${fx}/long-report.pdf"
expect_exit "image tile: malformed region is a clean error" 2 "--region must be X,Y,W,H" \
  "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --region 1,2,3
expect_exit "image tile: region outside the image is refused" 2 "outside the 1200x450 image" \
  "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --region 5000,0,10,10
expect_exit "image tile: a zero-column grid is refused" 2 "--grid must be COLUMNSxROWS" \
  "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --grid 0x2
if have exiftool; then
  expect_out "image info: GPS withheld by default" "meta withheld (sensitive" \
    "${py}" "${img}/image_tool.py" info "${fx}/label-photo.jpg"
else
  printf 'skip image metadata case (exiftool not installed)\n'
fi
if have magick || have sips; then
  expect_out "image convert: HEIC to PNG" "<- ${fx}/label.heic page 1" \
    "${py}" "${img}/image_tool.py" convert "${fx}/label.heic"
  expect_out "image tile: region cited" "region x=0 y=360 w=600 h=90" \
    "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --region 0,360,600,90
else
  printf 'skip image convert/tile cases (neither ImageMagick nor sips installed)\n'
fi
if have magick; then
  expect_out "image convert: every TIFF page" "packing-list.tiff page 3" \
    "${py}" "${img}/image_tool.py" convert "${fx}/packing-list.tiff"
  expect_out "image dedupe: near-duplicate candidate" "NEAR-DUPLICATE candidate" \
    "${py}" "${img}/image_tool.py" dedupe "${fx}/label.png" "${fx}/label-near-duplicate.jpg"
else
  printf 'skip image TIFF/near-duplicate cases (ImageMagick not installed)\n'
fi
# Derived images go to a new private folder per run: on a shared /tmp another user must
# not be able to pre-create it or plant a symlink and swap the pages the agent views.
# A stand-in magick that writes its output file keeps this case independent of the machine.
mkdir -p "${tmp}/touchmagick"
cat >"${tmp}/touchmagick/magick" <<'SH'
#!/bin/sh
for last in "$@"; do :; done
: >"${last}"
SH
chmod +x "${tmp}/touchmagick/magick"
crop_dir() {
  env PATH="${tmp}/touchmagick:/usr/bin:/bin" "${py_abs}" "${img}/image_tool.py" tile "${fx}/label.png" --region 0,360,600,90 2>/dev/null |
    awk '/ <- / { print $1; exit }' | xargs dirname
}
first_dir=$(crop_dir)
second_dir=$(crop_dir)
first_mode=$("${py}" -c 'import os, stat, sys; m = os.lstat(sys.argv[1]).st_mode; print(stat.S_ISDIR(m), oct(stat.S_IMODE(m)))' "${first_dir}" 2>/dev/null)
case "${first_dir##*/}:${first_mode}" in
"evidence-reader-"*":True 0o700")
  if [ "${first_dir}" != "${second_dir}" ]; then
    pass "image work dir: private and new per run"
  else
    flunk "image work dir: private and new per run" "reused ${first_dir}"
  fi
  ;;
*) flunk "image work dir: private and new per run" "got ${first_dir} ${first_mode}" ;;
esac
expect_out "image dedupe: same path twice is not a duplicate" "SAME FILE listed twice" \
  "${py}" "${img}/image_tool.py" dedupe "${fx}/label.png" "${fx}/../fixtures/label.png"
# ImageMagick gets the decoder the magic bytes proved, and never a file it cannot name.
mkdir -p "${tmp}/fakemagick"
cat >"${tmp}/fakemagick/magick" <<'SH'
#!/bin/sh
printf '%s\n' "$@" >>"${MAGICK_LOG}"
exit 1
SH
chmod +x "${tmp}/fakemagick/magick"
printf '<svg xmlns="http://www.w3.org/2000/svg"/>\n' >"${tmp}/disguised.png"
env PATH="${tmp}/fakemagick" MAGICK_LOG="${tmp}/magick-png.log" "${py_abs}" "${img}/image_tool.py" convert "${fx}/label.png" >/dev/null 2>&1
if grep -Fqx "png:${fx}/label.png" "${tmp}/magick-png.log" 2>/dev/null; then
  pass "image convert: ImageMagick is told the decoder"
else
  flunk "image convert: ImageMagick is told the decoder" "args: $(cat "${tmp}/magick-png.log" 2>/dev/null || true)"
fi
expect_exit "image convert: an SVG named .png never reaches ImageMagick" 2 "not a supported image format (unknown)" \
  env PATH="${tmp}/fakemagick" MAGICK_LOG="${tmp}/magick-svg.log" "${py_abs}" "${img}/image_tool.py" convert "${tmp}/disguised.png"
if [ -e "${tmp}/magick-svg.log" ]; then
  flunk "image convert: disguised SVG not passed to ImageMagick" "magick ran: $(cat "${tmp}/magick-svg.log" || true)"
else
  pass "image convert: disguised SVG not passed to ImageMagick"
fi
expect_exit "image degraded: no converter reported" 5 "NOT REVIEWED" \
  env PATH="${tmp}/empty-path" "${py_abs}" "${img}/image_tool.py" convert "${fx}/label.heic"

# --- regressions from the Cowork review (2026-09-21)
# corrupt_member <src> <dst> <member>: flip bytes inside one member's compressed data,
# the way a half-downloaded or damaged Office file looks.
corrupt_member() {
  "${py}" - "$1" "$2" "$3" <<'PY'
import struct, sys, zipfile
src, dst, member = sys.argv[1:4]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        zout.writestr(item.filename, zin.read(item.filename))
with zipfile.ZipFile(dst) as z:
    info = z.getinfo(member)
data = bytearray(open(dst, "rb").read())
name_len, extra_len = struct.unpack("<HH", data[info.header_offset + 26:info.header_offset + 30])
start = info.header_offset + 30 + name_len + extra_len
for k in range(start + 2, start + min(info.compress_size - 2, 200)):
    data[k] ^= 0x55
open(dst, "wb").write(bytes(data))
PY
}
corrupt_member "${fx}/contract-tracked.docx" "${tmp}/corrupt.docx" word/document.xml
expect_exit "docx corrupt package is a clean error" 2 "corrupt or incomplete" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/corrupt.docx"
corrupt_member "${fx}/q3-deck.pptx" "${tmp}/corrupt.pptx" ppt/presentation.xml
expect_exit "pptx corrupt package is a clean error" 2 "corrupt or incomplete" \
  "${py}" "${docs}/extract_pptx.py" "${tmp}/corrupt.pptx"
corrupt_member "${fx}/sales-cached.xlsx" "${tmp}/corrupt.xlsx" xl/workbook.xml
expect_exit "xlsx corrupt package is a clean error" 2 "corrupt or incomplete" \
  "${py}" "${tab}/extract_xlsx.py" summary "${tmp}/corrupt.xlsx"

if have pdftotext && have pdfinfo; then
  expect_exit "pdf malformed page range is a clean error" 2 "invalid page range" \
    "${py}" "${docs}/pdf_probe.py" text "${fx}/long-report.pdf" --pages abc
  expect_exit "pdf page cap enforced in code" 2 "at most 20 pages per call" \
    "${py}" "${docs}/pdf_probe.py" text "${fx}/long-report.pdf" --pages 1-45
else
  printf 'skip pdf range cases (poppler not installed)\n'
fi

printf 'code,amount\n2024_001,5\n2024_002,6\n' >"${tmp}/codes.csv"
expect_out "csv underscore code is not a number" "column 'code': non_empty=2 numeric=0" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/codes.csv"
printf 'sku,kg\n00123,1.5\n00456,2\n' >"${tmp}/zeros.csv"
expect_out "csv leading-zero code is not a number" "column 'sku': non_empty=2 numeric=0" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/zeros.csv"
expect_out "csv real numbers still summed" "column 'kg': non_empty=2 numeric=2 min=1.5 max=2 sum=3.5" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/zeros.csv"
printf 'a,b\n\201\215,1\n' >"${tmp}/badenc.csv"
expect_exit "csv unknown encoding is a clean error" 2 "encoding" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/badenc.csv"
expect_out "csv --encoding override" "encoding=latin-1" \
  "${py}" "${tab}/profile_csv.py" --encoding latin-1 profile "${tmp}/badenc.csv"

expect_out "image metadata privacy rules" "privacy-rules-ok" \
  "${py}" -B -c '
import importlib.util, sys
spec = importlib.util.spec_from_file_location("image_tool", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
hidden = ["IPTC:By-line", "XMP:Creator", "XMP:CreatorWorkEmail", "EXIF:Artist", "EXIF:OwnerName",
          "EXIF:SerialNumber", "EXIF:LensSerialNumber", "EXIF:GPSLatitude", "Composite:GPSPosition",
          "IPTC:City", "XMP:Country", "EXIF:XPAuthor", "IPTC:Writer-Editor"]
shown = ["XMP:CreatorTool", "EXIF:Software", "EXIF:Make", "EXIF:Model", "EXIF:DateTimeOriginal",
         "XMP:Rights"]
bad = [k for k in hidden if not m._is_sensitive(k)] + [k for k in shown if m._is_sensitive(k)]
print("privacy-rules-ok" if not bad else "wrong: %s" % bad)
' "${img}/image_tool.py"

# ImageMagick 6 layout (Linux distributions): convert/compare, no magick.
im6="${tmp}/im6"
mkdir -p "${im6}"
if have magick && have convert && have compare; then
  convert_path=$(command -v convert || true)
  compare_path=$(command -v compare || true)
  ln -s "${convert_path}" "${im6}/convert"
  ln -s "${compare_path}" "${im6}/compare"
  expect_out "image IM6 layout: every TIFF page" "packing-list.tiff page 3" \
    env PATH="${im6}" "${py_abs}" "${img}/image_tool.py" convert "${fx}/packing-list.tiff"
  expect_out "image IM6 layout: near-duplicate candidate" "NEAR-DUPLICATE candidate" \
    env PATH="${im6}" "${py_abs}" "${img}/image_tool.py" dedupe "${fx}/label.png" "${fx}/label-near-duplicate.jpg"
  expect_out "image IM6 layout: crop" "region x=0 y=360 w=600 h=90" \
    env PATH="${im6}" "${py_abs}" "${img}/image_tool.py" tile "${fx}/label.png" --region 0,360,600,90
  expect_out "requirements probe: IM6 layout detected" "imagemagick=ok" \
    env PATH="${im6}:/usr/bin:/bin" "${run_bash}" "${plugin}/scripts/check-requirements.sh"
else
  printf 'skip ImageMagick 6 layout cases (magick, convert and compare not all installed)\n'
fi
# A convert command that is not ImageMagick (e.g. another tool with that name) is ignored.
mkdir -p "${tmp}/fakeconv"
printf '#!/bin/sh\necho "not imagemagick"\n' >"${tmp}/fakeconv/convert"
chmod +x "${tmp}/fakeconv/convert"
expect_exit "image: non-ImageMagick convert ignored" 5 "NOT REVIEWED" \
  env PATH="${tmp}/fakeconv" "${py_abs}" "${img}/image_tool.py" convert "${fx}/label.heic"
# HEIC decoder missing: the converter's own reason reaches the report.
mkdir -p "${tmp}/nodecoder"
cat >"${tmp}/nodecoder/magick" <<'SH'
#!/bin/sh
case "$1" in
  -version) echo "Version: ImageMagick 7.1.2" ;;
  *)
    echo "no decode delegate for this image format HEIC" >&2
    exit 1
    ;;
esac
SH
chmod +x "${tmp}/nodecoder/magick"
expect_exit "image HEIC decoder failure reason reported" 5 "no decode delegate" \
  env PATH="${tmp}/nodecoder" "${py_abs}" "${img}/image_tool.py" convert "${fx}/label.heic"

# --- Python floor: an older interpreter gets the version message and exit 5, not a traceback.
# The version is faked with runpy (as scripts/plugin_validation/test_ccdocs.py does), so
# the check runs on every machine, not only on one that still has an old python3.
for script in "${docs}"/*.py "${tab}"/*.py "${img}"/*.py; do
  name=${script##*/}
  expect_exit "python floor: ${name} refuses 3.9 with a message" 5 \
    "${name} needs Python 3.14 or later; this is python3 3.9.6" \
    "${py}" -c "import runpy, sys; sys.version_info = (3, 9, 6, 'final', 0); runpy.run_path('${script}', run_name='__main__')"
done

# --- hostile and odd inputs: every one ends in a documented exit code, never a traceback
"${py}" - "${tmp}" <<'PY'
import sys, zipfile
d = sys.argv[1]
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def workbook(path, sheet):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="x/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet)
def document(path, body):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", body)
formulas = ["ROUND()", "DATE(99,1,1)", "10^300*10^300", "1+1"]
cells = "".join(f'<c r="A{i}"><f>{f}</f></c>' for i, f in enumerate(formulas, 1))
workbook(f"{d}/hostile.xlsx", f'<worksheet xmlns="{S}"><sheetData><row r="1">{cells}</row></sheetData></worksheet>'.encode())
dtd = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY a "INJECTED">]>'
workbook(f"{d}/utf16.xlsx", (dtd + f'<worksheet xmlns="{S}"><sheetData/></worksheet>').encode("utf-16"))
document(f"{d}/utf16.docx", (dtd + f'<w:document xmlns:w="{W}"><w:body/></w:document>').encode("utf-16"))
body = (
    '<w:p><w:r><w:t>Keep </w:t></w:r><w:ins w:author="A"><w:del w:author="B"><w:r><w:delText>TEMP</w:delText></w:r></w:del></w:ins><w:r><w:t>end</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>A </w:t></w:r><w:moveFrom w:author="M"><w:r><w:delText>MOVED</w:delText></w:r></w:moveFrom><w:r><w:t> B</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>C </w:t></w:r><w:moveTo w:author="M"><w:r><w:t>MOVED</w:t></w:r></w:moveTo></w:p>'
)
document(f"{d}/changes.docx", f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'.encode())
deep = '<w:ins w:author="A">' * 5000 + '<w:r><w:t>x</w:t></w:r>' + '</w:ins>' * 5000
document(f"{d}/deep.docx", f'<w:document xmlns:w="{W}"><w:body><w:p>{deep}</w:p></w:body></w:document>'.encode())
PY
expect_out "xlsx recompute: a bad formula is reported and the next cells still run" "S!A4: RECOMPUTED 2" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/hostile.xlsx" --sheet S
expect_out "xlsx recompute: missing arguments are NOT RECOMPUTED" "S!A1: NOT RECOMPUTED (cannot evaluate" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/hostile.xlsx" --sheet S
expect_out "xlsx recompute: DATE reads a two-digit year as 19xx" "S!A2: RECOMPUTED 36161" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/hostile.xlsx" --sheet S
expect_out "xlsx recompute: overflow is #NUM!" "S!A3: RECOMPUTED '#NUM!'" \
  "${py}" "${tab}/extract_xlsx.py" recompute "${tmp}/hostile.xlsx" --sheet S
expect_exit "xlsx refuses a UTF-16 DTD" 4 "declares a DTD or entity" \
  "${py}" "${tab}/extract_xlsx.py" cells "${tmp}/utf16.xlsx" --sheet S
expect_exit "xlsx malformed --range is a clean error" 2 "malformed value or --range" \
  "${py}" "${tab}/extract_xlsx.py" cells "${fx}/sales-cached.xlsx" --sheet Sales --range ZZZZ1
expect_exit "docx refuses a UTF-16 DTD" 4 "declares a DTD or entity" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/utf16.docx"
expect_out "docx text inserted then deleted is not in the original" "P1: Keep end" \
  "${py}" "${docs}/extract_docx.py" --view original "${tmp}/changes.docx"
expect_out "docx a moved passage appears once in the accepted view" "P2: A  B" \
  "${py}" "${docs}/extract_docx.py" --view accepted "${tmp}/changes.docx"
expect_exit "docx deep nesting is a clean error" 2 "nests its markup too deeply" \
  "${py}" "${docs}/extract_docx.py" "${tmp}/deep.docx"
printf 'a,b\n"unterminated,1\n2,3\n' >"${tmp}/quote.csv"
expect_exit "csv unterminated quote is an error, not a swallowed row" 2 "malformed delimited text" \
  "${py}" "${tab}/profile_csv.py" profile "${tmp}/quote.csv"
printf 'id,id\n1,2\n' >"${tmp}/dup.csv"
expect_exit "csv find: an ambiguous column is refused" 2 "appears 2 times" \
  "${py}" "${tab}/profile_csv.py" find "${tmp}/dup.csv" --column id --pattern 2
expect_exit "csv find: an invalid regex is a clean error" 2 "not a valid regular expression" \
  "${py}" "${tab}/profile_csv.py" find "${tmp}/dup.csv" --pattern '('
expect_exit "image tile: non-ASCII digits are refused" 2 "--region must be X,Y,W,H" \
  "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --region '²,0,10,10'
expect_exit "image tile: too many tiles is refused" 2 "use at most 64" \
  "${py}" "${img}/image_tool.py" tile "${fx}/label.png" --grid 100x100

# --- eval resources are copies of these fixtures, so both describe the same files
for resource in "${plugin}"/evals/*/resources/*; do
  name=${resource##*/}
  if cmp -s "${resource}" "${fx}/${name}"; then
    pass "eval resource matches fixture: ${name}"
  else
    flunk "eval resource matches fixture: ${name}" "${resource} differs from ${fx}/${name}"
  fi
done

# --- requirements probe
expect_out "requirements probe prints TIERS line" "TIERS python3=" \
  "${run_bash}" "${plugin}/scripts/check-requirements.sh"
mkdir -p "${tmp}/oldpy"
cat >"${tmp}/oldpy/python3" <<'SH'
#!/bin/sh
# An installed but older python3: prints its version, fails the >= 3.14 check.
case "$1" in
-V) echo "Python 3.9.6" ;;
*) exit 1 ;;
esac
SH
chmod +x "${tmp}/oldpy/python3"
expect_out "requirements probe: old python3 is too-old, not missing" "TIERS python3=too-old" \
  env PATH="${tmp}/oldpy:/usr/bin:/bin" "${run_bash}" "${plugin}/scripts/check-requirements.sh"

printf '\n%d passed, %d failed\n' "${ok}" "${bad}"
[ "${bad}" -eq 0 ]
