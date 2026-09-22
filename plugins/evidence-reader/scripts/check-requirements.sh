#!/usr/bin/env bash
# check-requirements.sh — report which evidence-reader tiers are available.
# Bash 3.2 compatible. It only checks: it never installs anything, never uses
# the network, and never asks for credentials.
#
# Output: one line per tool, then a final machine-readable line:
#   TIERS python3=<ok|too-old|missing> poppler=<ok|missing> exiftool=<ok|missing> \
#         imagemagick=<ok|missing> heic=<sips|imagemagick-unverified|heif-convert-unverified|none> \
#         jq=<ok|missing>
# Every bundled extractor, the PDF probe and the image tool included, needs python3 3.14;
# python3=too-old means it is installed but older, and each extractor then exits 5.
# ImageMagick counts as present as 7 (`magick`) or 6 (`convert`, the Debian/Ubuntu
# package). HEIC via ImageMagick or heif-convert is "unverified": the format can be
# listed while the HEVC decoder (libde265) is missing; image_tool.py convert then
# reports the real reason.
# Exit status is always 0: a missing optional tool is a degraded mode, not an error.

set -u

first_line() {
  # first_line <command> [args...] — first line of the command's output, or empty.
  "$@" 2>&1 | head -n 1 || true
}

probe() {
  # probe <label> <command> <version-args...> — prints a status line; returns 0 when present.
  label=$1
  cmd=$2
  shift 2
  if command -v "${cmd}" >/dev/null 2>&1; then
    version=$(first_line "${cmd}" "$@")
    printf '%-12s ok       %s\n' "${label}" "${version}"
    return 0
  fi
  printf '%-12s MISSING\n' "${label}"
  return 1
}

python_ok=missing
if command -v python3 >/dev/null 2>&1; then
  python_version=$(first_line python3 -V)
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)' >/dev/null 2>&1; then
    printf '%-12s ok       %s\n' "python3" "${python_version}"
    python_ok=ok
  else
    printf '%-12s TOO OLD  %s (every extractor needs Python >= 3.14)\n' "python3" "${python_version}"
    python_ok=too-old
  fi
else
  printf '%-12s MISSING  (every extractor needs Python >= 3.14)\n' "python3"
fi

poppler=missing
if probe "pdftotext" pdftotext -v &&
  command -v pdftoppm >/dev/null 2>&1 &&
  command -v pdfinfo >/dev/null 2>&1; then
  poppler=ok
else
  printf '%-12s          (install poppler for exact PDF text and page-range reading)\n' ""
fi

exif=missing
if probe "exiftool" exiftool -ver; then
  exif=ok
fi

magick_ok=missing
im_cmd=""
if command -v magick >/dev/null 2>&1; then
  im_cmd=magick
elif command -v convert >/dev/null 2>&1; then
  # Another tool can be named convert; accept it only when it says it is ImageMagick.
  convert_version=$(convert -version 2>/dev/null || true)
  case "${convert_version}" in
  *ImageMagick*) im_cmd=convert ;;
  *) ;;
  esac
fi
if [ -n "${im_cmd}" ]; then
  im_version=$("${im_cmd}" -version 2>/dev/null | grep -m 1 '^Version:' || true)
  printf '%-12s ok       %s (%s)\n' "imagemagick" "${im_version}" "${im_cmd}"
  magick_ok=ok
else
  printf '%-12s MISSING\n' "imagemagick"
fi

heic=none
magick_formats=""
if [ -n "${im_cmd}" ]; then
  magick_formats=$("${im_cmd}" -list format 2>/dev/null || true)
fi
if command -v sips >/dev/null 2>&1; then
  heic=sips
elif printf '%s\n' "${magick_formats}" | grep -q 'HEIC'; then
  heic=imagemagick-unverified
elif command -v heif-convert >/dev/null 2>&1; then
  heic=heif-convert-unverified
fi
printf '%-12s %s\n' "heic-decoder" "${heic}"

jq_ok=missing
if probe "jq" jq --version; then
  jq_ok=ok
fi

printf 'TIERS python3=%s poppler=%s exiftool=%s imagemagick=%s heic=%s jq=%s\n' \
  "${python_ok}" "${poppler}" "${exif}" "${magick_ok}" "${heic}" "${jq_ok}"
exit 0
