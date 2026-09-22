#!/usr/bin/env python3
"""Inspect, convert, tile and de-duplicate images for evidence reading (read-only).

Subcommands:
  info FILE...              format (from magic bytes), size, dimensions, page count,
                            SHA-256, whether the Read tool can view it directly, and
                            evidence metadata (EXIF/XMP/IPTC/PNG via exiftool when present;
                            --all-metadata adds container internals). GPS coordinates and
                            device serial numbers are withheld unless --include-sensitive.
  convert FILE              write PNG copies Read can view (HEIC, TIFF incl. every page,
                            BMP...) into a temp folder; prints each output path and the
                            source page it came from. ImageMagick applies EXIF orientation.
  tile FILE --grid CxR | --region X,Y,W,H [--scale N]
                            crop regions into a temp folder so fine print survives Read's
                            downscaling; prints each crop with its pixel region.
  dedupe FILE...            exact duplicates (same SHA-256) and, with ImageMagick,
                            visual near-duplicates by perceptual hash distance.

Tools: stdlib only, plus optional exiftool, ImageMagick (7: magick; 6: convert and
compare, as Linux distributions ship it), heif-convert and macOS sips.
Originals are never modified; every derived file lives in a new private folder,
$TMPDIR/evidence-reader-<first 12 hex of the source SHA-256>-<random>/, and must be
cited back to the original file and region.

Exit codes: 0 ok, 2 unreadable input, 5 no tool available for the requested step (including
python3 older than 3.14).
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import functools
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, BinaryIO, Literal, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeIs


MIN_PYTHON = (3, 14)


def _require_python() -> None:
    """Exit with status 5 and a one-line explanation when the interpreter is too old."""
    if tuple(sys.version_info[:2]) >= MIN_PYTHON:
        return
    found = ".".join(str(part) for part in sys.version_info[:3])
    _ = sys.stderr.write(
        "".join(
            (
                f"{Path(__file__).name} needs Python 3.14 or later; ",
                f"this is python3 {found} at {sys.executable}. ",
                "Install Python 3.14 (python.org, brew install python@3.14, ",
                "or uv python install 3.14 --default) so `python3` is 3.14.\n",
            )
        )
    )
    sys.exit(5)


_require_python()


READ_VIEWABLE = {"png", "jpeg", "gif", "webp"}
# Metadata that identifies a person, a device or a place. Matched on the tag name
# without its group, lower-cased, with "-", "_" and spaces removed. Tool and software
# names (CreatorTool, Software) are evidence, not personal data, and stay visible.
SENSITIVE_TAGS = frozenset(
    {
        "artist",
        "author",
        "xpauthor",
        "creator",
        "byline",
        "bylinetitle",
        "captionwriter",
        "writereditor",
        "contact",
        "ownername",
        "cameraownername",
        "imageuniqueid",
        "location",
        "sublocation",
        "city",
        "state",
        "provincestate",
        "country",
        "countrycode",
        "countryprimarylocationname",
        "countryprimarylocationcode",
    }
)
SENSITIVE_PREFIXES = (
    "gps",
    "creatorcontactinfo",
    "creatorwork",
    "creatoraddress",
    "creatorcity",
    "creatorcountry",
    "creatorpostal",
    "creatorregion",
    "locationcreated",
    "locationshown",
)
EVIDENCE_GROUPS = ("EXIF:", "XMP", "IPTC:", "PNG:", "Composite:")
IDENTICAL_MAX = 0.1
NEAR_MAX = 5.0


# json.loads is annotated `-> Any`; this alias is the one place that Any becomes object.
_loads: Callable[[str], object] = json.loads


def _is_list(value: object) -> TypeIs[list[object]]:
    return isinstance(value, list)


def _is_mapping(value: object) -> TypeIs[Mapping[str, object]]:
    """JSON object keys are always strings, so a parsed mapping is a `Mapping[str, object]`."""
    return isinstance(value, Mapping)


def _strings(value: object) -> list[str]:
    """Return an argparse `nargs` option, which argparse always stores as a list."""
    return [str(item) for item in value] if _is_list(value) else []


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


_HEIC_FAMILY_SUBTYPES = (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis", b"hevc", b"avif")
_SIMPLE_MAGIC: tuple[tuple[int, int, tuple[bytes, ...], str], ...] = (
    (0, 8, (b"\x89PNG\r\n\x1a\n",), "png"),
    (0, 3, (b"\xff\xd8\xff",), "jpeg"),
    (0, 6, (b"GIF87a", b"GIF89a"), "gif"),
    (0, 4, (b"II*\x00", b"MM\x00*"), "tiff"),
    (0, 2, (b"BM",), "bmp"),
    (0, 4, (b"%PDF",), "pdf"),
)


def _sniff_heic_family(head: bytes) -> str | None:
    if head[4:8] != b"ftyp" or head[8:12] not in _HEIC_FAMILY_SUBTYPES:
        return None
    return "avif" if head[8:12] == b"avif" else "heic"


def _sniff(path: str) -> str:
    with Path(path).open("rb") as handle:
        head = handle.read(32)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    heic = _sniff_heic_family(head)
    if heic is not None:
        return heic
    for start, end, options, kind in _SIMPLE_MAGIC:
        if head[start:end] in options:
            return kind
    return "unknown"


JPEG_MARKER_BYTE = 0xFF
JPEG_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    i = 2
    while i < len(data) - 9:
        if data[i] != JPEG_MARKER_BYTE:
            i += 1
            continue
        marker = data[i + 1]
        if marker in JPEG_SOF_MARKERS:
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + length
    return None


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if data[12:16] != b"VP8X":
        return None
    w = int.from_bytes(data[24:27], "little") + 1
    h = int.from_bytes(data[27:30], "little") + 1
    return w, h


def _dimensions(path: str, kind: str) -> tuple[int, int] | None:
    with Path(path).open("rb") as handle:
        data = handle.read(1 << 16)
    try:
        if kind == "png":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        if kind == "gif":
            w, h = struct.unpack("<HH", data[6:10])
            return w, h
        if kind == "webp":
            return _webp_dimensions(data)
        if kind == "jpeg":
            return _jpeg_dimensions(data)
    except struct.error:
        return None
    return None


MAX_TIFF_PAGES = 10_000


def _read_uint(handle: BinaryIO, size: int, order: Literal["little", "big"]) -> int:
    """Read one unsigned integer, raising EOFError on a truncated file."""
    data = handle.read(size)
    if len(data) != size:
        raise EOFError(size)
    return int.from_bytes(data, order)


def _tiff_pages(path: str) -> int | None:
    """Count TIFF pages by walking the IFD chain (stdlib, no decoding)."""
    try:
        with Path(path).open("rb") as handle:
            order: Literal["little", "big"] = "little" if handle.read(2) == b"II" else "big"
            _ = handle.read(2)
            offset = _read_uint(handle, 4, order)
            pages = 0
            seen: set[int] = set()
            while offset and offset not in seen and pages < MAX_TIFF_PAGES:
                seen.add(offset)
                _ = handle.seek(offset)
                count = _read_uint(handle, 2, order)
                _ = handle.seek(offset + 2 + 12 * count)
                offset = _read_uint(handle, 4, order)
                pages += 1
            return pages
    except (OSError, EOFError):
        return None


def _plain_arg(path: str) -> str:
    """A path a tool cannot mistake for an option: `-ver` becomes `./-ver`."""
    return f"./{path}" if path.startswith("-") else path


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )


def _is_sensitive(key: str) -> bool:
    tag = re.sub(r"[-_ ]", "", key.rsplit(":", 1)[-1]).lower()
    return tag in SENSITIVE_TAGS or tag.startswith(SENSITIVE_PREFIXES) or "serialnumber" in tag


@functools.cache
def _imagemagick() -> dict[str, list[str]]:
    """Return the ImageMagick commands: {"convert": [...], "compare": [...]}, or {}.

    ImageMagick 7 installs `magick`; ImageMagick 6 (still the Debian/Ubuntu package)
    installs `convert` and `compare` only. A `convert` that is not ImageMagick (another
    tool with the same name) is ignored.
    """
    if shutil.which("magick"):
        return {"convert": ["magick"], "compare": ["magick", "compare"]}
    convert = shutil.which("convert")
    if not convert or "ImageMagick" not in _run([convert, "-version"]).stdout:
        return {}
    tools = {"convert": [convert]}
    compare = shutil.which("compare")
    if compare:
        tools["compare"] = [compare]
    return tools


def _last_error(proc: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in (proc.stderr or proc.stdout or "").splitlines() if line.strip()]
    return lines[-1].strip() if lines else f"exit {proc.returncode}, no message"


def _work_dir(path: str) -> str:
    # A fresh directory per run, created atomically with mode 0700: on a shared /tmp no other
    # user can pre-create it or plant a symlink, so the pages the agent views are ours.
    return tempfile.mkdtemp(prefix=f"evidence-reader-{_sha256(path)[:12]}-")


def _metadata(
    path: str, *, include_sensitive: bool, everything: bool
) -> tuple[dict[str, object], list[str]]:
    if not shutil.which("exiftool"):
        return {}, []
    proc = _run(["exiftool", "-json", "-G", "-n", "-q", _plain_arg(path)])
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}, []
    records = _loads(proc.stdout)
    record = records[0] if _is_list(records) and records else None
    if not _is_mapping(record):
        return {}, []
    kept: dict[str, object] = {}
    withheld: list[str] = []
    for key, value in record.items():
        if key == "SourceFile" or key.startswith(("ExifTool:", "System:")):
            continue
        if not everything and not key.startswith(EVIDENCE_GROUPS):
            continue
        if not include_sensitive and _is_sensitive(key):
            withheld.append(key)
            continue
        kept[key] = value
    return kept, withheld


# ImageMagick picks a decoder from a file's bytes, so an SVG named photo.png can reach coders
# that read other local files (the ImageTragick class). Every input is named with the decoder
# its magic bytes proved, and anything else never reaches ImageMagick.
_IMAGEMAGICK_CODERS = frozenset({"png", "jpeg", "gif", "webp", "tiff", "bmp", "heic", "avif"})


def _coder_path(path: str, kind: str) -> str | None:
    return f"{kind}:{path}" if kind in _IMAGEMAGICK_CODERS else None


def _read_tool_advice(kind: str) -> str:
    if kind in READ_VIEWABLE:
        return "view directly with Read"
    if kind in _IMAGEMAGICK_CODERS:
        return "DO NOT Read directly: run `convert` first and read the PNG output"
    if kind == "pdf":
        return "not an image: read it with the document-reading skill (pdf_probe.py)"
    return "not a supported image format: report this file as NOT REVIEWED"


def _print_metadata(meta: dict[str, object], withheld: list[str]) -> None:
    for key in sorted(meta):
        print(f"meta {key} = {meta[key]}")
    if withheld:
        print(
            "meta withheld (sensitive, pass --include-sensitive only if the user asked):",
            f"{', '.join(sorted(withheld))}",
        )
    if meta:
        print(
            "note: metadata is self-reported by the file and can be edited; cite it as",
            "'according to the metadata'",
        )
    elif not withheld:
        print("meta unavailable (exiftool missing or no metadata)")


def _cmd_info(paths: list[str], *, include_sensitive: bool, everything: bool) -> None:
    for path in paths:
        if not Path(path).is_file():
            print(f"{path}: NOT REVIEWED (file not found)")
            continue
        kind = _sniff(path)
        dims = _dimensions(path, kind)
        pages = _tiff_pages(path) if kind == "tiff" else None
        print(f"== {path}")
        print(f"format={kind} bytes={Path(path).stat().st_size} sha256={_sha256(path)}")
        dim_text = f"{dims[0]}x{dims[1]}" if dims else "unknown (use metadata or convert)"
        print(f"dimensions={dim_text}" + (f" pages={pages}" if pages else ""))
        print(f"read_tool={_read_tool_advice(kind)}")
        meta, withheld = _metadata(path, include_sensitive=include_sensitive, everything=everything)
        _print_metadata(meta, withheld)


def _try_imagemagick(
    path: str, kind: str, folder: str, reasons: list[str]
) -> list[tuple[str, str]]:
    magick = _imagemagick()
    if not magick:
        return []
    source = _coder_path(path, kind)
    if source is None:
        reasons.append(f"ImageMagick: not given a {kind} file (only known image formats)")
        return []
    pattern = str(Path(folder) / "page-%d.png")
    proc = _run([*magick["convert"], source, "-auto-orient", pattern])
    if proc.returncode != 0:
        reasons.append(f"ImageMagick: {_last_error(proc)}")
        return []

    def _page_number(name: str) -> int:
        return int(name.removeprefix("page-").removesuffix(".png"))

    made = sorted(
        (f.name for f in Path(folder).iterdir() if re.fullmatch(r"page-\d+\.png", f.name)),
        key=_page_number,
    )
    return [(str(Path(folder) / f), f"page {_page_number(f) + 1}") for f in made]


def _try_sips(path: str, folder: str, reasons: list[str]) -> list[tuple[str, str]]:
    if not shutil.which("sips"):
        return []
    out = str(Path(folder) / "page-0.png")
    proc = _run(["sips", "-s", "format", "png", _plain_arg(path), "--out", out])
    if proc.returncode == 0 and Path(out).exists():
        return [(out, "page 1")]
    reasons.append(f"sips: {_last_error(proc)}")
    return []


def _try_heif_convert(
    path: str, kind: str, folder: str, reasons: list[str]
) -> list[tuple[str, str]]:
    if kind != "heic" or not shutil.which("heif-convert"):
        return []
    out = str(Path(folder) / "page-0.png")
    proc = _run(["heif-convert", _plain_arg(path), out])
    if proc.returncode == 0:
        return [(out, "page 1")]
    reasons.append(f"heif-convert: {_last_error(proc)}")
    return []


def _no_converter_error(kind: str, path: str, reasons: list[str]) -> NoReturn:
    if reasons:
        hint = "; ".join(reasons)
        if kind == "heic":
            hint += (
                " (a HEIC photo needs an HEVC decoder: libheif with libde265, "
                "e.g. apt install libheif-examples libde265-0)"
            )
        msg = f"conversion failed for {kind} ({path}): {hint}; report this file as NOT REVIEWED"
        _fail(5, msg)
    msg = f"no converter available for {kind} ({path}): "
    msg += "install ImageMagick (with libheif for HEIC), or use macOS sips; "
    msg += "report this file as NOT REVIEWED"
    _fail(5, msg)


def _cmd_convert(path: str) -> None:
    kind = _sniff(path)
    if kind not in _IMAGEMAGICK_CODERS:
        # No converter is handed bytes this script could not identify as an image.
        _fail(2, f"{path} is not a supported image format ({kind}); report it as NOT REVIEWED")
    folder = _work_dir(path)
    pages = _tiff_pages(path) if kind == "tiff" else 1
    reasons: list[str] = []
    outputs = _try_imagemagick(path, kind, folder, reasons)
    if not outputs:
        outputs = _try_sips(path, folder, reasons)
    if not outputs:
        outputs = _try_heif_convert(path, kind, folder, reasons)
    if not outputs:
        _no_converter_error(kind, path, reasons)
    for out, origin in outputs:
        print(f"{out} <- {path} {origin}")
    if pages and len(outputs) < pages:
        print(
            f"WARNING only {len(outputs)} of {pages} pages converted",
            "(sips converts the first page only):",
            f"pages {len(outputs) + 1}-{pages} NOT REVIEWED unless ImageMagick is installed",
        )


REGION_FIELDS = 4
MAX_TILES = 64
"""More tiles than this is a mistake, not fine print: each one is viewed separately."""


def _is_whole(text: str) -> bool:
    # str.isdigit() also accepts "²" and other digits int() rejects.
    text = text.strip()
    return text.isascii() and text.isdigit()


GRID_FIELDS = 2


def _region_box(region: str, width: int, height: int) -> list[tuple[int, int, int, int]]:
    """One crop box from `X,Y,W,H`, clipped to the image; exit 2 when it is not one."""
    parts = region.split(",")
    if len(parts) != REGION_FIELDS or not all(_is_whole(v) for v in parts):
        _fail(2, f"--region must be X,Y,W,H in whole pixels, got {region!r}")
    x, y, w, h = (int(v) for v in parts)
    if w == 0 or h == 0 or x >= width or y >= height:
        _fail(2, f"--region {region} is empty or outside the {width}x{height} image")
    return [(x, y, min(w, width - x), min(h, height - y))]


def _grid_boxes(grid: str | None, width: int, height: int) -> list[tuple[int, int, int, int]]:
    """Crop boxes for a `CxR` grid over the image; exit 2 when the grid is not one."""
    parts = (grid or "2x2").lower().split("x")
    if len(parts) != GRID_FIELDS or not all(_is_whole(v) and int(v) > 0 for v in parts):
        _fail(2, f"--grid must be COLUMNSxROWS, e.g. 2x3, got {grid!r}")
    cols, rows = (int(v) for v in parts)
    if cols * rows > MAX_TILES:
        _fail(2, f"--grid {grid} makes {cols * rows} tiles; use at most {MAX_TILES}")
    tw, th = -(-width // cols), -(-height // rows)
    return [
        (c * tw, r * th, min(tw, width - c * tw), min(th, height - r * th))
        for r, c in itertools.product(range(rows), range(cols))
        if c * tw < width and r * th < height
    ]


def _cmd_tile(path: str, grid: str | None, region: str | None, scale: int) -> None:
    if scale < 1:
        _fail(2, f"--scale must be a whole number of 1 or more, got {scale}")
    kind = _sniff(path)
    dims = _dimensions(path, kind)
    if dims is None:
        _fail(2, f"cannot read dimensions of {path} ({kind}); run `convert` first and tile the PNG")
    width, height = dims
    boxes = _region_box(region, width, height) if region else _grid_boxes(grid, width, height)
    folder = _work_dir(path)
    for i, (x, y, w, h) in enumerate(boxes, 1):
        out = str(Path(folder) / f"tile-{i}-{x}_{y}_{w}x{h}.png")
        magick = _imagemagick()
        source = _coder_path(path, kind)
        if magick and source is not None:
            args = [*magick["convert"], source, "-crop", f"{w}x{h}+{x}+{y}", "+repage"]
            if scale > 1:
                args += ["-resize", f"{scale * 100}%"]
            ok = _run([*args, out]).returncode == 0
        elif shutil.which("sips"):
            ok = (
                _run(
                    [
                        "sips",
                        "-c",
                        str(h),
                        str(w),
                        "--cropOffset",
                        str(y),
                        str(x),
                        _plain_arg(path),
                        "--out",
                        out,
                    ]
                ).returncode
                == 0
            )
        else:
            msg = "no cropping tool: install ImageMagick (or use macOS sips); "
            msg += "read the whole image and flag fine print as unverified"
            _fail(5, msg)
        print(
            f"{out} <- {path} region x={x} y={y} w={w} h={h}"
            if ok
            else f"FAILED region x={x} y={y} w={w} h={h}"
        )


def _distinct_paths(paths: list[str]) -> list[str]:
    seen_real: dict[str, str] = {}
    distinct: list[str] = []
    for path in paths:
        real = os.path.realpath(path)
        if real in seen_real:
            print(f"SAME FILE listed twice (not a duplicate): {seen_real[real]} and {path}")
            continue
        seen_real[real] = path
        distinct.append(path)
    return distinct


def _hash_groups(distinct: list[str]) -> dict[str, list[str]]:
    by_hash: dict[str, list[str]] = {}
    for path in distinct:
        by_hash.setdefault(_sha256(path), []).append(path)
    return by_hash


MAX_PAIRWISE_COMPARE = 200


def _scan_near_duplicates(unique: list[str], compare: list[str]) -> None:
    sources: dict[str, str] = {}
    for path in unique:
        kind = _sniff(path)
        source = _coder_path(path, kind)
        if source is None:
            print(f"near-duplicate check skipped for {path}: not a known image format ({kind})")
        else:
            sources[path] = source
    for a, b in itertools.combinations(sources, 2):
        proc = _run([*compare, "-metric", "PHASH", sources[a], sources[b], "null:"])
        match = re.match(r"\s*([0-9.eE+-]+)", proc.stderr or proc.stdout)
        if not match:
            continue
        distance = float(match.group(1))
        if distance <= IDENTICAL_MAX:
            print(f"VISUALLY IDENTICAL (phash {distance:.4g}): {a} ~ {b}")
        elif distance <= NEAR_MAX:
            print(
                f"NEAR-DUPLICATE candidate (phash {distance:.4g}), confirm by viewing both:",
                f"{a} ~ {b}",
            )


def _cmd_dedupe(paths: list[str]) -> None:
    distinct = _distinct_paths(paths)
    by_hash = _hash_groups(distinct)
    groups = [g for g in by_hash.values() if len(g) > 1]
    for g in groups:
        print(f"EXACT duplicates (same bytes): {', '.join(g)}")
    unique = [g[0] for g in by_hash.values()]
    compare = _imagemagick().get("compare")
    if not compare:
        print(
            "near-duplicate check skipped: ImageMagick compare not installed",
            "(exact duplicates only)",
        )
    elif len(unique) > MAX_PAIRWISE_COMPARE:
        print(
            f"near-duplicate check skipped: {len(unique)} images exceeds the pairwise limit",
            f"of {MAX_PAIRWISE_COMPARE}; batch them",
        )
    else:
        _scan_near_duplicates(unique, compare)
    print(
        f"COVERED {len(distinct)} distinct files ({len(paths)} arguments):",
        f"{len(groups)} exact-duplicate groups",
    )


def main() -> None:
    """Parse the command line and run the chosen image subcommand."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_info = sub.add_parser("info")
    _ = p_info.add_argument("paths", nargs="+")
    _ = p_info.add_argument(
        "--include-sensitive", action="store_true", help="include GPS, serials and owner fields"
    )
    _ = p_info.add_argument(
        "--all-metadata", action="store_true", help="include codec/container internals too"
    )
    p_conv = sub.add_parser("convert")
    _ = p_conv.add_argument("path")
    p_tile = sub.add_parser("tile")
    _ = p_tile.add_argument("path")
    _ = p_tile.add_argument("--grid", help="columns x rows, e.g. 2x3")
    _ = p_tile.add_argument("--region", help="X,Y,W,H in pixels")
    _ = p_tile.add_argument(
        "--scale", type=int, default=1, help="enlarge crops N times (ImageMagick only)"
    )
    p_dup = sub.add_parser("dedupe")
    _ = p_dup.add_argument("paths", nargs="+")
    values: dict[str, object] = vars(parser.parse_args())
    command = str(values["command"])
    try:
        if command == "info":
            _cmd_info(
                _strings(values["paths"]),
                include_sensitive=bool(values["include_sensitive"]),
                everything=bool(values["all_metadata"]),
            )
        elif command == "convert":
            _cmd_convert(str(values["path"]))
        elif command == "tile":
            grid = values["grid"]
            region = values["region"]
            scale = values["scale"]
            _cmd_tile(
                str(values["path"]),
                str(grid) if grid is not None else None,
                str(region) if region is not None else None,
                scale if isinstance(scale, int) else 1,
            )
        else:
            _cmd_dedupe(_strings(values["paths"]))
    except OSError as exc:
        _fail(2, f"cannot read input ({exc})")


if __name__ == "__main__":
    main()
