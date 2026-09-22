# HEIC, TIFF and other formats Read cannot show

## Which formats need conversion

Read shows PNG, JPEG, GIF and WebP. It refuses TIFF as a binary file and, worse,
**returns HEIC as raw bytes with no error**, which looks like content but is not.
`image_tool.py info` says `DO NOT Read directly` for every format that needs
conversion (HEIC, AVIF, TIFF, BMP). For a PDF it points to the document-reading
skill, and for a format it does not recognize it says to report the file as not
reviewed; `convert` refuses both.

## Convert

`image_tool.py convert FILE` writes PNG
pages to a temporary folder and prints `<png> <- <original> page <n>` for each.
View every PNG and cite `<original> page <n>`.

| Converter | HEIC | TIFF pages |
| --- | --- | --- |
| ImageMagick 7 (`magick`) or 6 (`convert`, the Debian/Ubuntu package), with libheif | yes | every page |
| macOS `sips` | yes | **first page only** |
| `heif-convert` (libheif) | yes | — |

When only `sips` is available, `convert` warns that TIFF pages after the first
were not converted. Those pages are **not reviewed**; say so.

## When nothing can convert

`convert` exits `5`. An exit 5 whose message starts `image_tool.py needs Python 3.14`
means the interpreter is too old, not a missing converter: report every image that
needed the tool as not reviewed for that reason. With no converter installed it gives an install hint;
when a converter ran and failed it gives that converter's own error, for example
`no decode delegate` when libheif lacks its HEVC decoder (libde265). A corrupt file
fails the same way, so the quoted error is the only way to tell the two apart. Report the
file as not reviewed with that reason. Never describe it from metadata instead.

`check-requirements.sh` reports `heic=imagemagick-unverified` or
`heic=heif-convert-unverified` because a listed HEIC format does not prove the
decoder is installed; only a real `convert` run does.
