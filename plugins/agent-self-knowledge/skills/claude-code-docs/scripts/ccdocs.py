#!/usr/bin/env python3
"""ccdocs - retrieve live, citable Claude Code documentation.

Stdlib only, Python 3.12+ (older versions stop with a one-line message).
Every command ends with a SOURCE line naming what it read.

Commands
  research PHRASE...      THE ENTRY POINT. Routes the phrases through references/areas.md, discovers every
                          correlated page (Claude Code corpus + Help Center + Platform indexes), reads the
                          live pages keeping only the sections about the topic, follows their hyperlinks
                          one hop, and checks the Claude Code, Claude apps and Platform release notes for
                          the last --months. Writes a folder (MAP.md, changelog.md, one file per
                          section) under --out or <cache>/research and prints a short summary.
  show FILE [--out DIR]   Print a file of a research folder.
  url TARGET              Canonical, verified URL of a docs MCP path (/en/x.mdx), a relative link, an old
                          alias or a slug. Every URL taken from the docs MCP goes through it.
  inventory               Every page of every area of references/areas.md (references/area-pages.md).
  find TERM...            Headings in the docs map that contain every TERM, with their page.
  grep PATTERN            Regex over the full docs corpus (body text, tables, code), each hit with its
                          page and section. Use it when `find` misses, and before any negative claim.
  related TOPIC...        Correlation map: every page and section (h2-h6) where TOPIC is documented,
                          ranked by heading match, body mentions, links TO the topic's core pages and
                          links FROM them, grouped by context (subagents, skills, plugins, SDK,
                          settings, CI...). Topic words form one phrase; --any ORs them; --regex RE.
  dossier TOPIC...        Pull the correlated sections in full: one best section per context first
                          (breadth), then more by rank (depth). No character budget unless --budget N
                          is given. Never cuts a section; opens with a manifest of what was read and
                          NOT read and a CONTENTS index giving the output line of every section.
  links SLUG [--section H] [--direction in|out|both]
                          Hyperlink graph of a page or section: who links to it, where it links out.
  quote SLUG PATTERN      Verbatim sentence(s) matching PATTERN on the LIVE page, each with its
                          verified section URL. Exits non-zero when the text is not on the page.
  index [--grep RE]       The llms.txt page index (slug, title, one-line summary).
  outline SLUG [--map]    Heading tree of the live page with verified anchors and section sizes.
  page SLUG [--section H | --intro] [--nth N] [--max N]
                          Raw markdown of a live page, one section with its subsections, or the
                          intro before the first heading.
  changelog [--last N] [--since VER] [--grep RE]
                          Release notes from the official CHANGELOG.md.
  version                 npm latest/stable/next, local `claude --version`, and the release gap.
  whatsnew [--last N]     Weekly "What's new" digest entries.
  raw URL [--max N]       Fetch any https URL as text.
  catalog                 Every page of the index grouped by its official navigation path, with the
                          pages it links to and the pages that link to it (references/docs-catalog.md).
  selfcheck [--live]      Validate every page slug and quoted section name in SKILL.md and
                          references/topic-routing.md against the docs map (--live: live pages).

Anchors
  Section anchors are never guessed. Every `#anchor` printed is taken from the id attribute of the
  heading on the rendered page (https://code.claude.com/docs/en/<slug>). When that page cannot be read
  or the heading is not on it, the page URL is printed without an anchor and marked unverified, and the
  ANCHORS footer says why. --no-anchor-check skips the rendered-page reads and marks all unverified.

Freshness
  llms-full.txt and the docs map are generated separately from the live pages and can differ from
  them. related/dossier/links/grep read that corpus (discovery); page/outline/quote read the live page
  (truth). Re-read with `page` or `quote` before quoting keys, enums or JSON into a config.

SLUG examples: hooks, hooks-guide, sub-agents, agent-sdk/hooks, whats-new/2026-w37
Env: CCDOCS_LANG (en), CCDOCS_CACHE_TTL (900 s, 0 disables), CCDOCS_CORPUS_TTL (3600 s),
     CCDOCS_ANCHOR_TTL (3600 s), XDG_CACHE_HOME (cache root, default ~/.cache).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import typing
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple, cast, final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from typing import TypeAlias

    _AddParser: TypeAlias = Callable[[str], argparse.ArgumentParser]

# The syntax of this file stays readable by Python 3.10 on purpose (ruff target-version py310), so an
# older interpreter reaches this check and prints one line instead of a SyntaxError or ImportError.
MIN_PYTHON: Final = (3, 12)


def python_too_old(version: tuple[int, ...]) -> str | None:
    """The message for an interpreter older than MIN_PYTHON, or None when it is new enough."""
    if tuple(version[:2]) >= MIN_PYTHON:
        return None
    found = ".".join(str(v) for v in version[:3])
    need = ".".join(str(v) for v in MIN_PYTHON)
    return (
        f"ccdocs.py needs Python {need} or later; this python3 is {found} ({sys.executable}). "
        f"Install Python {need}+ and make it the first `python3` on PATH."
    )


_RUNNING: Final = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
if (_too_old := python_too_old(_RUNNING)) is not None:
    _ = sys.stderr.write(_too_old + "\n")
    sys.exit(2)


__all__ = ["CcdocsError", "main"]

VERSION: Final = "2.0.0"
BASE: Final = "https://code.claude.com/docs"
HOST: Final = "https://code.claude.com"
CHANGELOG_RAW: Final = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
NPM: Final = "https://registry.npmjs.org/@anthropic-ai/claude-code"
USER_AGENT: Final = f"ccdocs/{VERSION} (+agent-self-knowledge plugin, claude-code-docs skill)"
HTTP_TIMEOUT: Final = 60.0
FETCH_WORKERS: Final = 8


# --------------------------------------------------------------------------------------------------
# Settings and errors
# --------------------------------------------------------------------------------------------------


class CcdocsError(Exception):
    """A failure the user must see: printed to stderr, exit status 1."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        msg = f"{name}={raw!r} is not an integer (seconds; 0 disables the cache)"
        raise CcdocsError(msg) from exc


@dataclass(frozen=True)
class Settings:
    """Runtime configuration, read from the environment once per process."""

    lang: str
    ttl: int
    corpus_ttl: int
    anchor_ttl: int
    cache_dir: Path
    verify_anchors: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from CCDOCS_* variables and XDG_CACHE_HOME."""
        xdg = os.environ.get("XDG_CACHE_HOME", "")
        # XDG spec: an empty or relative XDG_CACHE_HOME is invalid and must be ignored.
        root = Path(xdg) if xdg and Path(xdg).is_absolute() else Path("~/.cache").expanduser()
        return cls(
            lang=os.environ.get("CCDOCS_LANG", "en") or "en",
            ttl=_env_int("CCDOCS_CACHE_TTL", 900),
            corpus_ttl=_env_int("CCDOCS_CORPUS_TTL", 3600),
            anchor_ttl=_env_int("CCDOCS_ANCHOR_TTL", 3600),
            cache_dir=root / "ccdocs",
        )

    @property
    def llms_url(self) -> str:
        """Page index."""
        return f"{BASE}/llms.txt"

    @property
    def full_url(self) -> str:
        """Full-text corpus."""
        return f"{BASE}/llms-full.txt"

    @property
    def map_url(self) -> str:
        """Heading tree of every page."""
        return f"{BASE}/{self.lang}/claude_code_docs_map.md"

    @property
    def changelog_doc_url(self) -> str:
        """Rendered changelog (carries release dates)."""
        return f"{BASE}/{self.lang}/changelog"


_settings_lock = threading.Lock()
_SETTINGS: list[Settings] = []


def settings() -> Settings:
    """Return the active settings (created on first use)."""
    with _settings_lock:
        if not _SETTINGS:
            _SETTINGS.append(Settings.from_env())
        return _SETTINGS[0]


def reset_settings() -> None:
    """Forget the active settings so the next settings() call re-reads the environment."""
    with _settings_lock:
        _SETTINGS.clear()
    _clear_memo()


def use_settings(new: Settings) -> None:
    """Replace the active settings (CLI flags, tests)."""
    with _settings_lock:
        _SETTINGS.clear()
        _SETTINGS.append(new)
    _clear_memo()


# --------------------------------------------------------------------------------------------------
# HTTP and cache
# --------------------------------------------------------------------------------------------------


def download(url: str, accept: str) -> str:
    """GET an https URL and return its body as text.

    The only function that touches the network; tests replace it with a fixture router.
    """
    if not url.startswith("https://"):
        msg = f"refusing non-https URL {url!r}"
        raise CcdocsError(msg)
    req = urllib.request.Request(  # noqa: S310 - scheme checked above
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "gzip"},
    )
    try:
        with cast("http.client.HTTPResponse", urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)) as resp:  # noqa: S310
            body = resp.read()
            if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                body = gzip.decompress(body)
    except urllib.error.HTTPError as exc:
        msg = f"HTTP {exc.code} fetching {url} - the page may have moved; run `ccdocs.py find <topic>`."
        raise CcdocsError(msg) from exc
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        msg = f"network error fetching {url}: {exc}"
        raise CcdocsError(msg) from exc
    return body.decode("utf-8", "replace")


def parse_json(text: str, what: str) -> object:
    """json.loads that reports bad payloads as CcdocsError instead of a traceback."""
    try:
        return cast("object", json.loads(text))
    except ValueError as exc:
        snippet = " ".join(text[:120].split())
        msg = f"{what} is not valid JSON ({exc.__class__.__name__}: {exc}); starts with: {snippet!r}"
        raise CcdocsError(msg) from exc


def cache_path(key: str) -> Path:
    """On-disk cache file for KEY."""
    return settings().cache_dir / hashlib.sha256(key.encode()).hexdigest()


def cache_age(key: str) -> str:
    """Human description of how old the cached copy of KEY is."""
    path = cache_path(key)
    if not path.exists():
        return "just fetched"
    age = int(time.time() - path.stat().st_mtime)
    return "just fetched" if age < 5 else f"cached {age // 60}m{age % 60}s ago"  # noqa: PLR2004


def _cache_read(key: str, ttl: int) -> str | None:
    path = cache_path(key)
    if ttl <= 0 or not path.exists() or time.time() - path.stat().st_mtime >= ttl:
        return None
    return path.read_text(encoding="utf-8")


def _cache_write(key: str, text: str, ttl: int) -> None:
    if ttl <= 0:
        return
    path = cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    _ = tmp.write_text(text, encoding="utf-8")
    _ = tmp.replace(path)  # atomic: a killed run never leaves a half-written entry


def fetch_raw(url: str, ttl: int | None = None, accept: str = "text/markdown, text/plain, */*") -> str:
    """Fetch URL through the on-disk cache, without any normalization."""
    ttl = settings().ttl if ttl is None else ttl
    cached = _cache_read(url, ttl)
    if cached is not None:
        return cached
    text = download(url, accept)
    _cache_write(url, text, ttl)
    return text


def fetch(url: str, ttl: int | None = None) -> str:
    """Fetch a docs text resource; markdown gets HTML headings normalized (see normalize_md)."""
    text = fetch_raw(url, ttl)
    return normalize_md(text) if url.endswith((".md", ".txt")) else text


# --------------------------------------------------------------------------------------------------
# Markdown utilities
# --------------------------------------------------------------------------------------------------

HTML_HEADING: Final = re.compile(r'<h([2-6])(?:\s+id="([^"]+)")?[^>]*>\s*(.*?)\s*</h\1>', re.DOTALL)
MD_HEADING: Final = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
EXPLICIT_ID: Final = re.compile(r"\s*\{#([^}]+)\}\s*$")
FENCE: Final = ("```", "~~~")


def normalize_md(text: str) -> str:
    """Rewrite `<h2 id="x">Title</h2>` as `## Title {#x}` so markdown parsers don't skip it."""
    if "<h" not in text:
        return text

    def repl(m: re.Match[str]) -> str:
        level, hid, inner = int(m.group(1)), m.group(2), " ".join(m.group(3).split())
        return "#" * level + " " + inner + (f" {{#{hid}}}" if hid else "")

    return HTML_HEADING.sub(repl, text)


def heading_title(raw: str) -> str:
    """Heading text without a trailing `{#id}`."""
    return EXPLICIT_ID.sub("", raw).strip()


def page_url(slug: str) -> str:
    """Raw-markdown URL of a docs page given a slug or a docs URL."""
    s = slug.strip().strip("/")
    s = re.sub(r"^https?://code\.claude\.com/docs/[a-z-]+/", "", s)
    s = re.sub(r"\.mdx?$", "", s).split("#", maxsplit=1)[0]
    return f"{BASE}/{settings().lang}/{s}.md"


def human_url(slug: str, anchor: str | None = None) -> str:
    """Citation URL of a page (and verified anchor, when given)."""
    return f"{BASE}/{settings().lang}/{slug}" + (f"#{anchor}" if anchor else "")


class Heading(NamedTuple):
    """A heading line of a markdown document."""

    line: int
    level: int
    text: str


def headings_in(md: str, min_level: int = 2) -> list[Heading]:
    """All headings of MD at MIN_LEVEL or deeper, skipping fenced code blocks."""
    out: list[Heading] = []
    in_code = False
    for i, line in enumerate(md.splitlines()):
        if line.lstrip().startswith(FENCE):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = MD_HEADING.match(line)
        if m and len(m.group(1)) >= min_level:
            out.append(Heading(i, len(m.group(1)), m.group(2)))
    return out


def section_bounds(md: str, heads: Sequence[Heading], idx: int) -> tuple[int, int]:
    """Line range [start, end) of heading IDX including its subsections."""
    h = heads[idx]
    end = len(md.splitlines())
    for nxt in heads[idx + 1 :]:
        if nxt.level <= h.level:
            end = nxt.line
            break
    return h.line, end


def collapse_tables(text: str) -> str:
    """Docs tables are space-padded to hundreds of columns; squeeze them."""
    return "\n".join(
        re.sub(r"-{4,}", "---", re.sub(r" {2,}", " ", ln)) if ln.lstrip().startswith("|") else ln
        for ln in text.splitlines()
    )


def source_line(*urls: str) -> str:
    """Trailing citation line of every command."""
    shown = [u[:-3] if u.endswith(".md") and "/docs/" in u else u for u in urls]
    return "\nSOURCE: " + " | ".join(shown)


# --------------------------------------------------------------------------------------------------
# Verified anchors (rendered page ids)
# --------------------------------------------------------------------------------------------------


class RenderedHeading(NamedTuple):
    """A heading of the rendered HTML page with its real id."""

    level: int
    hid: str
    text: str


@final
@final
class _HeadingParser(HTMLParser):
    """Collect (level, id, visible text) of every h2-h6 content heading.

    The id comes from the heading itself or, when it has none, from an `<a id="...">` placed right
    before it (the docs use that for some deep headings). Headings with neither get an empty id.

    ALIASES maps every other link target id to the index of the heading it belongs to: the empty
    `<span id>`/`<a id>` markers a renamed section keeps for its old anchors (they sit right before
    the heading), and ids placed inside a paragraph (they belong to the section around them).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[RenderedHeading] = []
        self._level: int = 0
        self._hid: str = ""
        self._buf: list[str] = []
        self._skip_depth: int = 0
        self._pending_anchor: str = ""
        self._react_heading: bool = False
        self.aliases: dict[str, int] = {}
        self._pending_ids: list[str] = []

    @typing.override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if not self._level and re.fullmatch(r"h[2-6]", tag):
            own = a.get("id", "")
            self._react_heading = own.startswith("_")  # generated ids of UI chrome, not content
            self._level, self._buf, self._skip_depth = int(tag[1]), [], 0
            self._hid = own if own and not self._react_heading else self._pending_anchor
            self._pending_anchor = ""
            for pid in self._pending_ids:
                _ = self.aliases.setdefault(pid, len(self.found))
            self._pending_ids = []
            return
        if self._level:
            if self._skip_depth or a.get("aria-label") == "Navigate to header":
                self._skip_depth += 1
            return
        if tag == "a" and a.get("id") and not a.get("href"):
            self._pending_anchor = a["id"]
        if tag in {"a", "span"} and a.get("id") and not a.get("href"):
            self._pending_ids.append(a["id"])

    @typing.override
    def handle_endtag(self, tag: str) -> None:
        if not self._level:
            return
        if tag == f"h{self._level}":
            if not self._react_heading:
                text = " ".join("".join(self._buf).replace("\u200b", "").split())
                self.found.append(RenderedHeading(self._level, self._hid, text))
            self._level = 0
        elif self._skip_depth:
            self._skip_depth -= 1

    @typing.override
    def handle_data(self, data: str) -> None:
        if self._level:
            if not self._skip_depth:
                self._buf.append(data)
        elif data.strip():
            self._pending_anchor = ""  # an anchor only binds to the heading that directly follows it
            for pid in self._pending_ids:  # an id inside a paragraph belongs to the section around it
                if self.found:
                    _ = self.aliases.setdefault(pid, len(self.found) - 1)
            self._pending_ids = []


def parse_rendered_headings(page_html: str) -> list[RenderedHeading]:
    """Headings with ids from a rendered docs page."""
    return parse_rendered(page_html)[0]


def parse_rendered(page_html: str) -> tuple[list[RenderedHeading], dict[str, int]]:
    """Headings with ids, and the other anchor ids mapped to the heading index they belong to."""
    parser = _HeadingParser()
    parser.feed(page_html)
    parser.close()
    return parser.found, parser.aliases


_QUOTES: Final = str.maketrans({0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"', 0x200B: None})


def norm_heading(text: str) -> str:
    """Comparable form of a heading: markup, quotes, ids and case removed."""
    t = heading_title(html.unescape(text))
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.translate(_QUOTES)
    t = re.sub("[\ue000-\uf8ff]", "", t)
    t = re.sub(r"[`*_~]", "", t)
    return " ".join(t.split()).casefold()


@dataclass
class AnchorResolver:
    """Maps headings of a page to the ids of the rendered page; remembers every failure."""

    failures: dict[str, str] = field(default_factory=dict)
    no_id: set[tuple[str, str]] = field(default_factory=set)
    _pages: dict[str, list[RenderedHeading] | None] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def rendered(self, slug: str) -> list[RenderedHeading] | None:
        """Rendered headings of SLUG (cached), or None when unavailable."""
        with self._lock:
            if slug in self._pages:
                return self._pages[slug]
        result: list[RenderedHeading] | None
        if not settings().verify_anchors:
            result = None
            reason = "anchor check disabled (--no-anchor-check)"
        else:
            reason = ""
            try:
                result = _load_rendered(slug)
            except CcdocsError as exc:
                result, reason = None, str(exc)
            if result is not None and not result:
                result, reason = None, "rendered page has no heading ids (layout changed?)"
        with self._lock:
            self._pages[slug] = result
            if result is None:
                self.failures[slug] = reason
        return result

    def lookup(self, slug: str, anchor: str) -> RenderedHeading | None:
        """The rendered heading a link anchor points to: its own id first, then an alias id."""
        rendered = self.rendered(slug)
        if rendered is None:
            return None
        wanted = {anchor, urllib.parse.unquote(anchor)}
        hit = next((r for r in rendered if r.hid in wanted), None)
        if hit is not None:
            return hit
        try:
            aliases = _load_aliases(slug)
        except CcdocsError:
            return None
        idx = next((aliases[a] for a in wanted if a in aliases), None)
        return rendered[idx] if idx is not None and 0 <= idx < len(rendered) else None

    def prefetch(self, slugs: Iterable[str]) -> None:
        """Load several pages in parallel."""
        todo = sorted({s for s in slugs if s not in self._pages})
        if len(todo) <= 1:
            for s in todo:
                _ = self.rendered(s)
            return
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            _ = list(pool.map(self.rendered, todo))

    def resolve(self, slug: str, headings: Sequence[str], levels: Sequence[int] | None = None) -> list[str | None]:
        """Id for each heading of SLUG, in document order (None = not verified).

        Headings are matched by text and level, in order: rendered pages add component headings
        (cards, tabs) that can share a section's text at another level. Without LEVELS, or when no
        heading of that level matches, text alone is used.
        """
        rendered = self.rendered(slug)
        if rendered is None:
            return [None] * len(headings)
        by_level: dict[tuple[str, int], list[RenderedHeading]] = {}
        by_text: dict[str, list[RenderedHeading]] = {}
        for r in rendered:
            by_level.setdefault((norm_heading(r.text), r.level), []).append(r)
            by_text.setdefault(norm_heading(r.text), []).append(r)
        taken: set[int] = set()

        def take(queue: list[RenderedHeading] | None, *, prefer_ids: bool) -> RenderedHeading | None:
            free = [r for r in queue or [] if id(r) not in taken]
            if prefer_ids:
                free = [r for r in free if r.hid] or free
            if not free:
                return None
            taken.add(id(free[0]))
            return free[0]

        out: list[str | None] = []
        for i, h in enumerate(headings):
            key = norm_heading(h)
            hit = take(by_level.get((key, levels[i])), prefer_ids=False) if levels is not None else None
            # text-only fallback: component headings (cards, tabs) repeat section titles without ids
            hit = hit or take(by_text.get(key), prefer_ids=True)
            hid = hit.hid if hit else None
            if hid == "":
                with self._lock:
                    self.no_id.add((slug, norm_heading(h)))
            out.append(hid or None)
        return out

    def footer(self, cited: Iterable[tuple[str, str | None, str]]) -> str:
        """ANCHORS line for a command's output. CITED = (slug, anchor or None, heading)."""
        items = list(cited)
        unverified = [(s, h) for s, a, h in items if a is None and h]
        if not items:
            return ""
        if not unverified:
            return f"\nANCHORS: all {len(items)} cited anchors verified against the rendered pages."
        lines = [
            f"\nANCHORS: {len(items) - len(unverified)} verified, {len(unverified)} UNVERIFIED (cited without #anchor):"
        ]
        for slug, heading in unverified[:15]:
            why = self.failures.get(slug) or (
                "the rendered page shows this heading without any anchor; cite the page URL"
                if (slug, norm_heading(heading)) in self.no_id
                else "heading not found on the rendered page"
            )
            lines.append(f"   - {slug} > {heading_title(heading)}: {why}")
        if len(unverified) > 15:  # noqa: PLR2004
            lines.append(f"   ... {len(unverified) - 15} more")
        return "\n".join(lines)


def rendered_url(page: str) -> str:
    """Rendered HTML URL of a page key: a Claude Code slug, or a full https URL of another docs site."""
    return page.removesuffix(".md") if page.startswith("https://") else human_url(page)


def _load_rendered(slug: str) -> list[RenderedHeading]:
    key = f"anchors:{rendered_url(slug)}"
    ttl = settings().anchor_ttl
    cached = _cache_read(key, ttl)
    data: object = None
    if cached is not None:
        try:
            data = parse_json(cached, "anchor cache")
        except CcdocsError:
            data = None  # corrupt cache entry: refetch below
        if isinstance(data, list):
            rows = cast("list[object]", data)
            good: list[RenderedHeading] = []
            for row in rows:
                if isinstance(row, list):
                    cells = cast("list[object]", row)
                    if len(cells) == 3:  # noqa: PLR2004
                        lvl, hid, txt = cells
                        if isinstance(lvl, int) and isinstance(hid, str) and isinstance(txt, str):
                            good.append(RenderedHeading(lvl, hid, txt))
            return good
    page = download(rendered_url(slug), "text/html")
    found, aliases = parse_rendered(page)
    _cache_write(key, json.dumps([list(r) for r in found]), ttl)
    _cache_write(f"anchor-aliases:{rendered_url(slug)}", json.dumps(aliases), ttl)
    return found


def _load_aliases(slug: str) -> dict[str, int]:
    """Alias anchor ids of a page (see _HeadingParser); read with the headings, refetched if missing."""
    key = f"anchor-aliases:{rendered_url(slug)}"
    ttl = settings().anchor_ttl
    cached = _cache_read(key, ttl)
    if cached is None:
        found, aliases = parse_rendered(download(rendered_url(slug), "text/html"))
        _cache_write(f"anchors:{rendered_url(slug)}", json.dumps([list(r) for r in found]), ttl)
        _cache_write(key, json.dumps(aliases), ttl)
        return aliases
    try:
        data = parse_json(cached, "anchor alias cache")
    except CcdocsError:
        return {}
    if not isinstance(data, dict):
        return {}
    items = cast("dict[object, object]", data).items()
    return {k: v for k, v in items if isinstance(k, str) and isinstance(v, int)}


# --------------------------------------------------------------------------------------------------
# Corpus (llms-full.txt) as sections + hyperlink graph
# --------------------------------------------------------------------------------------------------

LINK_RX: Final = re.compile(
    r"\]\((?:https://code\.claude\.com)?/(?:docs/)?[a-z]{2}(?:-[a-z]+)?/([a-z0-9/_-]+?)(?:\.md)?(?:#([^)\s]*))?\)",
)
INTRA_RX: Final = re.compile(r"\]\(#([^)\s]+)\)")


class Link(NamedTuple):
    """A hyperlink found in a section. ANCHOR is the author-written id ('' for the page)."""

    target: str
    anchor: str


@dataclass(eq=False)
class Section:
    """One heading (or a page intro) of the corpus with its line range and outgoing links."""

    idx: int
    slug: str
    title: str
    heading: str
    level: int
    start: int
    end: int = 0
    links: list[Link] = field(default_factory=list)
    anchor: str | None = None

    @property
    def label(self) -> str:
        """Heading text for display."""
        return heading_title(self.heading) if self.heading else "(intro)"

    @property
    def cite(self) -> str:
        """Citation URL; carries an anchor only when it was verified."""
        return human_url(self.slug, self.anchor)


@dataclass
class Corpus:
    """Parsed llms-full.txt."""

    lines: list[str]
    sections: list[Section]
    by_slug: dict[str, list[Section]]

    def body(self, s: Section, *, children: bool) -> tuple[str, int]:
        """Text of S (heading line included) and the exclusive end line."""
        end = s.end
        if children:
            for nxt in self.sections[s.idx + 1 :]:
                if nxt.slug != s.slug or nxt.level <= s.level:
                    break
                end = nxt.end
        return "\n".join(self.lines[s.start : end]).strip(), end


def slug_of(url: str) -> str:
    """Slug of a docs URL."""
    m = re.search(r"/docs/[a-z]{2}(?:-[a-z]+)?/(.+?)(?:\.md)?$", url)
    return m.group(1) if m else url


def build_corpus(text: str) -> Corpus:
    """Split the corpus into sections; pages start with `# Title` + `Source: <url>`."""
    lines = text.splitlines()
    secs: list[Section] = []
    cur: Section | None = None
    in_code = False
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("# ") and i + 1 < n and lines[i + 1].startswith("Source: https://"):
            if cur:
                cur.end = i
            cur = Section(len(secs), slug_of(lines[i + 1][8:].strip()), line[2:].strip(), "", 1, i + 2)
            secs.append(cur)
            in_code = False
            i += 2
            continue
        if line.lstrip().startswith(FENCE):
            in_code = not in_code
        elif not in_code and cur:
            m = re.match(r"^(#{2,6})\s+(.*?)\s*$", line)
            if m:
                cur.end = i
                cur = Section(len(secs), cur.slug, cur.title, m.group(2), len(m.group(1)), i)
                secs.append(cur)
        if cur:
            cur.links.extend(Link(m.group(1).rstrip("/"), m.group(2) or "") for m in LINK_RX.finditer(line))
            cur.links.extend(Link(cur.slug, m.group(1)) for m in INTRA_RX.finditer(line))
        i += 1
    if cur:
        cur.end = n
    by_slug: dict[str, list[Section]] = {}
    for s in secs:
        by_slug.setdefault(s.slug, []).append(s)
    return Corpus(lines, secs, by_slug)


_memo: dict[str, Corpus] = {}


def _clear_memo() -> None:
    _memo.clear()
    _ARTICLES.clear()


def load_corpus() -> Corpus:
    """The corpus, parsed once per process."""
    st = settings()
    text = fetch(st.full_url, st.corpus_ttl)
    key = hashlib.sha256(text.encode()).hexdigest()
    if key not in _memo:
        _memo.clear()
        _memo[key] = build_corpus(text)
    return _memo[key]


def assign_anchors(corpus: Corpus, resolver: AnchorResolver, slugs: Iterable[str]) -> None:
    """Set Section.anchor (verified ids) for every section of SLUGS."""
    wanted = [s for s in dict.fromkeys(slugs) if s in corpus.by_slug]
    resolver.prefetch(wanted)
    for slug in wanted:
        heads = [s for s in corpus.by_slug[slug] if s.heading]
        for sec, hid in zip(
            heads, resolver.resolve(slug, [s.heading for s in heads], [s.level for s in heads]), strict=True
        ):
            sec.anchor = hid


# --------------------------------------------------------------------------------------------------
# Correlation
# --------------------------------------------------------------------------------------------------

FACETS: Final[tuple[tuple[str, str], ...]] = (
    ("agent-sdk", r"^agent-sdk/"),
    ("release-history", r"^(changelog|whats-new)"),
    ("subagents-teams", r"^(sub-agents|agents|agent-teams|agent-view|cross-session-messaging|worktrees)$"),
    ("skills-commands", r"^(skills|commands|slash-commands)$"),
    ("plugins-marketplaces", r"plugin|marketplace"),
    ("mcp-channels", r"^(mcp|mcp-quickstart|managed-mcp|channels|channels-reference)$"),
    ("workflows", r"^workflows$"),
    ("hooks", r"^hooks"),
    ("memory-rules", r"^(memory|claude-directory|large-codebases|best-practices)$"),
    ("settings-permissions", r"settings|permission|env-vars|cli-reference|sandboxing|auto-mode|managed-"),
    ("ci-headless", r"github|gitlab|headless|code-review|routines"),
    ("models-cost", r"^(model-config|fast-mode|advisor|costs|prompt-caching)$"),
    ("tools", r"^(tools-reference|interactive-mode|glossary|checkpointing|output-styles|statusline)$"),
    ("observability", r"monitoring|analytics|otel|telemetry|data-usage"),
    ("surfaces", r"desktop|cloud|web|ide|vs-code|jetbrains|chrome|slack|claude-projects|remote|self-hosted|sessions"),
    ("troubleshooting", r"troubleshoot|errors|debug|feature-availability"),
)


def facet_of(slug: str, seeds: set[str]) -> str:
    """Context a page documents a topic in ('core' for seed pages)."""
    if slug in seeds:
        return "core"
    return next((name for name, rx in FACETS if re.search(rx, slug)), "other")


def _stem(word: str) -> str:
    w = word.lower().strip()
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):  # noqa: PLR2004
        w = w[:-1]
    return re.escape(w) + r"(?:e?s)?"


def topic_regex(terms: Sequence[str], raw: str | None, *, any_term: bool = False) -> re.Pattern[str]:
    """Topic words form ONE phrase by default ("agent teams" != agent OR teams); plurals match."""
    if raw:
        try:
            return re.compile(raw, re.IGNORECASE)
        except re.error as exc:
            msg = f"bad --regex {raw!r}: {exc}"
            raise CcdocsError(msg) from exc
    words = [w for t in terms for w in re.split(r"[\s_-]+", t) if w]
    if not words:
        msg = "give topic words or --regex"
        raise CcdocsError(msg)
    left, right = r"(?<![a-z0-9])", r"(?![a-z0-9])"
    if any_term:
        return re.compile("|".join(left + _stem(w) + right for w in words), re.IGNORECASE)
    return re.compile(left + r"[\s_-]+".join(_stem(w) for w in words) + right, re.IGNORECASE)


class Scored(NamedTuple):
    """A section with its relevance score and the signals behind it."""

    score: float
    section: Section
    signals: tuple[str, ...]


@dataclass(frozen=True)
class TopicQuery:
    """Arguments shared by related and dossier."""

    topic: tuple[str, ...]
    regex: str | None
    any_term: bool
    seeds: tuple[str, ...]
    min_score: float
    include_history: bool
    follow_links: bool

    @property
    def label(self) -> str:
        """Display form of the query."""
        return " ".join(self.topic) if self.topic else f"/{self.regex}/"


@dataclass
class Correlation:
    """Result of correlate()."""

    corpus: Corpus
    scored: list[Scored]
    seeds: set[str]
    resolver: AnchorResolver


def _auto_seeds(corpus: Corpus, rx: re.Pattern[str]) -> set[str]:
    """Pages whose slug or title names the topic."""
    return {
        slug
        for slug, secs in corpus.by_slug.items()
        if rx.search(slug.rsplit("/", maxsplit=1)[-1].replace("-", " ")) or rx.search(secs[0].title)
    }


def _score_section(s: Section, corpus: Corpus, rx: re.Pattern[str], seeds: set[str]) -> Scored:
    """Heading, body and inbound-link signals of one section."""
    sig: list[str] = []
    score = 0.0
    if s.heading and rx.search(heading_title(s.heading)):
        score += 6
        sig.append("H")
    hits = sum(1 for ln in corpus.lines[s.start : s.end] if rx.search(ln))
    if hits:
        score += min(hits, 12) * 0.5
        sig.append(f"T{hits}")
    inbound = sorted(
        {
            f"{ln.target}#{ln.anchor}" if ln.anchor else ln.target
            for ln in s.links
            if ln.target in seeds and ln.target != s.slug
        },
    )
    if inbound:
        score += 3 + min(len(inbound), 5)
        sig.append("L->" + ",".join(inbound[:3]))
    if s.slug in seeds:
        score *= 1.5
    return Scored(score, s, tuple(sig))


def _outbound_counts(corpus: Corpus, scan: Sequence[Section], seeds: set[str], pages: set[str]) -> dict[int, int]:
    """How often seed pages link to each (verified) section of PAGES."""
    by_id: dict[tuple[str, str], Section] = {}
    for slug in pages:
        for s in corpus.by_slug.get(slug, []):
            if s.anchor:
                by_id[(slug, s.anchor)] = s
            elif not s.heading:
                by_id[(slug, "")] = s
    counts: dict[int, int] = {}
    for s in scan:
        if s.slug not in seeds:
            continue
        for ln in s.links:
            tgt = by_id.get((ln.target, ln.anchor))
            if tgt is not None and tgt.slug != s.slug:
                counts[tgt.idx] = counts.get(tgt.idx, 0) + 1
    return counts


def correlate(q: TopicQuery, resolver: AnchorResolver) -> Correlation:
    """Score every section of the corpus against the topic."""
    corpus = load_corpus()
    rx = topic_regex(q.topic, q.regex, any_term=q.any_term)
    seeds = set(q.seeds)
    unknown = sorted(s for s in seeds if s not in corpus.by_slug)
    if unknown:
        msg = f"--seed {unknown} not in the corpus; find slugs with `ccdocs.py index --grep <term>`"
        raise CcdocsError(msg)
    seeds = seeds or _auto_seeds(corpus, rx)
    scan = [s for s in corpus.sections if q.include_history or facet_of(s.slug, set()) != "release-history"]
    # Link anchors are real ids, so seed pages and every page they link to need verified anchors
    # before links can be matched to sections.
    targets = {ln.target for s in scan if s.slug in seeds for ln in s.links if ln.target in corpus.by_slug}
    assign_anchors(corpus, resolver, [*sorted(seeds), *sorted(targets)])
    scored = [sc for sc in (_score_section(s, corpus, rx, seeds) for s in scan) if sc.score >= q.min_score]
    pos = {sc.section.idx: i for i, sc in enumerate(scored)}
    for idx, cnt in _outbound_counts(corpus, scan, seeds, seeds | targets).items():
        bonus = 2 + min(cnt, 4)
        if idx in pos:
            old = scored[pos[idx]]
            scored[pos[idx]] = Scored(old.score + bonus, old.section, (*old.signals, f"<-seed x{cnt}"))
        elif q.follow_links:
            pos[idx] = len(scored)
            scored.append(Scored(float(bonus), corpus.sections[idx], (f"<-seed x{cnt}",)))
    scored.sort(key=lambda x: -x.score)
    return Correlation(corpus, scored, seeds, resolver)


def _page_order(c: Correlation) -> tuple[list[str], dict[str, float]]:
    rank: dict[str, float] = {}
    for sc in c.scored:
        rank[sc.section.slug] = rank.get(sc.section.slug, 0.0) + sc.score
    order = sorted(rank, key=lambda k: (k not in c.seeds, -rank[k]))
    return order, rank


# --------------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------------

MAP_PAGE: Final = re.compile(r"^#{2,4} \[([^\]]+)\]\((https://[^)]+)\)")


def cmd_find(terms: Sequence[str], max_hits: int) -> str:
    """Headings of the docs map containing every term."""
    st = settings()
    text = fetch(st.map_url)
    pats = [re.compile(r"(?<![a-z0-9])" + re.escape(t.lower())) for t in terms]
    hits: list[tuple[str, str, str]] = []
    page: tuple[str, str] | None = None
    for line in text.splitlines():
        m = MAP_PAGE.match(line)
        if m:
            page = (m.group(1), m.group(2))
            if all(p.search(page[0].lower()) for p in pats):
                hits.append((page[0], page[1], "(page)"))
            continue
        low = line.lower()
        if page and line.strip().startswith("*") and all(p.search(low) for p in pats):
            hits.append((page[0], page[1], line.strip("* ").strip()))
    hits.sort(key=lambda h: h[2] != "(page)")
    out: list[str] = []
    if not hits:
        out.append(
            f"No heading matches {list(terms)}. The term may live in body text - try "
            f"`ccdocs.py grep '{' '.join(terms)}'` or `index --grep`."
        )
    last = ""
    for name, url, h in hits[:max_hits]:
        if name != last:
            out.append(f"\n{name}  ->  {url.removesuffix('.md')}")
            last = name
        out.append(f"   - {h}")
    if len(hits) > max_hits:
        out.append(f"\n... {len(hits) - max_hits} more; narrow the query.")
    return "\n".join(out) + source_line(st.map_url)


@dataclass(frozen=True)
class GrepOptions:
    """Options of the grep command."""

    slug_rx: str | None = None
    pages_only: bool = False
    case: bool = False
    per_page: int = 6
    max_lines: int = 60


def _grep_hits(
    corpus: Corpus, rx: re.Pattern[str], srx: re.Pattern[str] | None
) -> dict[str, list[tuple[Section, str]]]:
    per: dict[str, list[tuple[Section, str]]] = {}
    for s in corpus.sections:
        if srx and not srx.search(s.slug):
            continue
        per_sec = [(s, ln.strip()) for ln in corpus.lines[s.start : s.end] if rx.search(ln)]
        if per_sec:
            per.setdefault(s.slug, []).extend(per_sec)
    return per


def cmd_grep(pattern: str, opts: GrepOptions) -> str:
    """Regex search of the full corpus, hits attributed to page and section."""
    st = settings()
    corpus = load_corpus()
    try:
        rx = re.compile(pattern, 0 if opts.case else re.IGNORECASE)
        srx = re.compile(opts.slug_rx, re.IGNORECASE) if opts.slug_rx else None
    except re.error as exc:
        msg = f"bad regex: {exc}"
        raise CcdocsError(msg) from exc
    per = _grep_hits(corpus, rx, srx)
    total = sum(len(v) for v in per.values())
    if not total:
        return (
            f"No match for {pattern!r} in the full docs corpus ({cache_age(st.full_url)}).\n"
            "Evidence of absence in the docs, not proof the feature is missing: check "
            "`ccdocs.py changelog --grep <term> --last 40` before saying it does not exist." + source_line(st.full_url)
        )
    out = [f"{total} match(es) across {len(per)} page(s) - corpus {cache_age(st.full_url)}\n"]
    shown = 0
    for slug in sorted(per, key=lambda k: -len(per[k])):
        hits = per[slug]
        out.append(f"{human_url(slug)}  ({len(hits)} hit{'s' if len(hits) > 1 else ''})  - {hits[0][0].title}")
        if opts.pages_only:
            continue
        out.extend(f"   [{sec.label}] {ln[:220]}" for sec, ln in hits[: opts.per_page])
        shown += min(len(hits), opts.per_page)
        if len(hits) > opts.per_page:
            out.append(f"   ... {len(hits) - opts.per_page} more on this page")
        out.append("")
        if shown >= opts.max_lines:
            out.append(f"... output capped at {opts.max_lines} lines; narrow with --slug or a tighter pattern.")
            break
    return "\n".join(out) + source_line(st.full_url)


def cmd_index(grep: str | None) -> str:
    """The llms.txt index, optionally filtered."""
    st = settings()
    text = fetch(st.llms_url)
    rx = re.compile(grep, re.IGNORECASE) if grep else None
    out: list[str] = []
    n = 0
    for line in text.splitlines():
        if line.startswith("#") and not rx:
            out.append(line)
            continue
        m = re.match(r"^- \[([^\]]+)\]\(https://code\.claude\.com/docs/[a-z-]+/([^)]+)\.md\):?\s*(.*)", line)
        if m and (not rx or rx.search(line)):
            out.append(f"  {m.group(2):<42} {m.group(1)} - {m.group(3)[:140]}")
            n += 1
    if rx and not n:
        out.append("No page title/summary matches; try `find` (headings) or `grep` (full text).")
    return "\n".join(out) + source_line(st.llms_url)


def cmd_outline(slug: str, *, use_map: bool) -> str:
    """Heading tree of a page: live with verified anchors and sizes, or from the docs map."""
    slug = re.sub(r"\.md$", "", slug.strip("/"))
    if use_map:
        st = settings()
        out: list[str] = []
        on = False
        for line in fetch(st.map_url).splitlines():
            m = MAP_PAGE.match(line)
            if m:
                on = m.group(2).endswith(f"/{slug}.md")
                if on:
                    out.append(line)
                continue
            if line.startswith("## "):
                on = False
            if on and line.strip():
                out.append(line)
        body = "\n".join(out) if out else f"No page '{slug}' in the docs map."
        return body + source_line(st.map_url)
    url = page_url(slug)
    md = fetch(url)
    heads = headings_in(md)
    resolver = AnchorResolver()
    ids = resolver.resolve(slug, [h.text for h in heads], [h.level for h in heads])
    lines = md.splitlines()
    out = [f"{slug}  ({len(md):,} chars, {len(heads)} headings, live)"]
    for n, (h, hid) in enumerate(zip(heads, ids, strict=True)):
        end = heads[n + 1].line if n + 1 < len(heads) else len(lines)
        size = sum(len(x) + 1 for x in lines[h.line : end])
        out.append(
            f"{'  ' * (h.level - 2)}* {heading_title(h.text)}  {'#' + hid if hid else '(anchor unverified)'}"
            f"  [{size:,}]"
        )
    footer = resolver.footer((slug, hid, h.text) for h, hid in zip(heads, ids, strict=True))
    return "\n".join(out) + footer + source_line(url)


def cmd_page(slug: str, *, section: str | None, nth: int, max_chars: int, intro: bool = False) -> str:
    """A live page, its intro, or one of its sections, with a verified citation."""
    url = page_url(slug)
    pslug = slug_of(url)
    md = fetch(url)
    out: list[str] = []
    cite = human_url(pslug)
    footer = ""
    if section is not None and not section.strip():
        msg = (
            "--section must not be empty (it matches every heading); use --intro for the text before the first heading"
        )
        raise CcdocsError(msg)
    if intro:
        heads = headings_in(md)
        md = "\n".join(md.splitlines()[: heads[0].line]) if heads else md
    elif section:
        heads = headings_in(md)
        matches = [i for i, h in enumerate(heads) if section.lower() in heading_title(h.text).lower()]
        if not matches:
            listing = "\n".join(f"{'#' * h.level} {heading_title(h.text)}" for h in heads)
            msg = f"section {section!r} not found in {url}. Headings:\n{listing}"
            raise CcdocsError(msg)
        if nth < 1 or nth > len(matches):
            listing = "\n".join(f"  {i + 1}. {heading_title(heads[m].text)}" for i, m in enumerate(matches))
            msg = f"--nth {nth} but {len(matches)} heading(s) match {section!r} in {url}:\n{listing}"
            raise CcdocsError(msg)
        idx = matches[nth - 1]
        if len(matches) > 1:
            rest = [f"[{i + 1}] {heading_title(heads[m].text)}" for i, m in enumerate(matches) if i != nth - 1]
            more = f", +{len(rest) - 8} more" if len(rest) > 8 else ""  # noqa: PLR2004
            out.append(
                f"NOTE: {len(matches)} headings match {section!r}. Showing [{nth}] "
                f'"{heading_title(heads[idx].text)}". Others: {", ".join(rest[:8])}{more}. '
                "Re-run with --nth N or a longer --section string.\n"
            )
        start, end = section_bounds(md, heads, idx)
        md = "\n".join(md.splitlines()[start:end])
        resolver = AnchorResolver()
        hid = resolver.resolve(pslug, [h.text for h in heads], [h.level for h in heads])[idx]
        cite = human_url(pslug, hid)
        footer = resolver.footer([(pslug, hid, heads[idx].text)])
    md = collapse_tables(md)
    if max_chars and len(md) > max_chars:
        md = md[:max_chars] + f"\n\n[... truncated at {max_chars} chars; use --section or --max 0]"
    out.append(md)
    return "\n".join(out) + footer + source_line(cite)


def vkey(v: str) -> tuple[int, ...] | None:
    """Comparable version tuple from the first three numbers in V."""
    parts = cast("list[str]", re.findall(r"\d+", v))[:3]
    return tuple(int(x) for x in parts) if parts else None


def cmd_changelog(*, last: int, since: str | None, grep: str | None) -> str:
    """Release notes, newest first."""
    st = settings()
    text = fetch(CHANGELOG_RAW)
    rx = re.compile(grep, re.IGNORECASE) if grep else None
    floor = vkey(since) if since else None
    if since and floor is None:
        msg = f"--since {since!r} is not a version number (expected e.g. 2.1.270)"
        raise CcdocsError(msg)
    out: list[str] = []
    shown = 0
    for block in re.split(r"(?m)^## ", text)[1:]:
        ver, _, body = block.partition("\n")
        ver = ver.strip()
        key = vkey(ver)
        if floor and (key is None or key <= floor):
            continue  # skip, don't break: never assume the file is perfectly ordered
        items = [ln for ln in body.splitlines() if ln.strip()]
        if rx:
            items = [ln for ln in items if rx.search(ln)]
            if not items:
                continue
        out.append(f"## {ver}\n" + "\n".join(items) + "\n")
        shown += 1
        if not floor and shown >= last:
            break
    if not shown:
        out.append("No matching entries." + (" Try a broader --grep, more --last, or `grep`." if rx else ""))
    return "\n".join(out) + source_line(CHANGELOG_RAW, st.changelog_doc_url)


def local_claude_version() -> str | None:
    """`claude --version` of this machine, or None when claude is not on PATH or fails."""
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        res = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20, check=False)  # noqa: S603
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() or None


def _npm_tags() -> tuple[dict[str, str], dict[str, str]]:
    data = parse_json(fetch_raw(NPM), f"npm registry response from {NPM}")
    if not isinstance(data, dict):
        msg = f"unexpected npm registry payload from {NPM}"
        raise CcdocsError(msg)
    obj = cast("dict[str, object]", data)

    def str_map(value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(k): v for k, v in cast("dict[object, object]", value).items() if isinstance(v, str)}

    return str_map(obj.get("dist-tags")), str_map(obj.get("time"))


def cmd_version() -> str:
    """Npm dist-tags, the local build and the gap between them."""
    tags, times = _npm_tags()
    out = [
        f"npm {t:<7} {tags[t]:<12} published {times.get(tags[t], '?')}"
        for t in ("latest", "stable", "next")
        if t in tags
    ]
    local = local_claude_version()
    latest = tags.get("latest", "")
    if local is None:
        out.append("local   claude not on PATH or not runnable - ask the user for `claude --version`.")
        return "\n".join(out) + source_line(NPM, CHANGELOG_RAW)
    out.append(f"local   {local}")
    lkey, lat = vkey(local), vkey(latest)
    if lkey and lat and lkey < lat:
        versions = [v.strip() for v in cast("list[str]", re.findall(r"(?m)^## (.+)$", fetch(CHANGELOG_RAW)))]
        behind = [v for v in versions if (k := vkey(v)) and k > lkey]
        lv = ".".join(map(str, lkey))
        out.append(
            f"gap     local is {len(behind)} release(s) behind latest ({latest}); features newer than "
            f"{lv} may not exist here.\n        `ccdocs.py changelog --since {lv}` lists what is missing."
        )
    elif lkey and lat and lkey > lat:
        out.append(f"gap     local is AHEAD of npm latest ({latest}) - a next/nightly build; docs may lag it.")
    return "\n".join(out) + source_line(NPM, CHANGELOG_RAW)


def cmd_whatsnew(last: int) -> str:
    """Weekly digest entries."""
    url = f"{BASE}/{settings().lang}/whats-new/index.md"
    text = fetch(url)
    entries = re.findall(r'<Update label="([^"]+)" description="([^"]+)"([^>]*)>(.*?)</Update>', text, re.DOTALL)
    if not entries:
        return (
            "No <Update> entries parsed - the digest format may have changed; read it with "
            f"`ccdocs.py raw {url} --max 4000`." + source_line(url)
        )
    out: list[str] = []
    for label, desc, attrs, body in cast("list[tuple[str, str, str, str]]", entries)[:last]:
        tm = re.search(r"tags=\{\[([^\]]*)\]\}", attrs)
        tags = ("[" + tm.group(1) + "]").replace('"', "") if tm else ""
        out.append(f"### {label} ({desc}) {tags}\n" + re.sub(r"\n\s+", "\n", body.strip()) + "\n")
    return "\n".join(out) + source_line(url)


def cmd_raw(url: str, max_chars: int) -> str:
    """Any https URL as text."""
    t = fetch_raw(url)
    if max_chars and len(t) > max_chars:
        t = t[:max_chars] + f"\n[... truncated at {max_chars} chars]"
    return t + source_line(url)


PREVIEW: Final = 8


def _preview(items: Sequence[str], n: int = PREVIEW) -> str:
    return ", ".join(items[:n]) + (" ..." if len(items) > n else "")


def _by_page(scored: Iterable[Scored]) -> dict[str, list[Scored]]:
    per: dict[str, list[Scored]] = {}
    for sc in scored:
        per.setdefault(sc.section.slug, []).append(sc)
    return per


def _coverage_lines(order: Sequence[str], seeds: set[str]) -> list[str]:
    facets: dict[str, list[str]] = {}
    for slug in order:
        facets.setdefault(facet_of(slug, seeds), []).append(slug)
    out = ["\nCOVERAGE BY FACET (every context this topic is documented in):"]
    out.extend(
        f"   {name:<22} {len(facets[name]):>3} page(s): {_preview(facets[name])}"
        for name in ["core", *(f for f, _ in FACETS), "other"]
        if name in facets
    )
    empty = [
        f
        for f, frx in FACETS
        if f not in facets and f != "release-history" and not any(re.search(frx, sd) for sd in seeds)
    ]
    if empty:
        out.append(f"   (no hits) {', '.join(empty)}")
    return out


def _section_line(sc: Scored) -> str:
    s = sc.section
    where = f"#{s.anchor}" if s.anchor else ("(anchor unverified)" if s.heading else "")
    return f"   {'#' * s.level} {s.label}  {where}  [{' '.join(sc.signals)}]"


def cmd_related(q: TopicQuery, *, max_pages: int, per_page: int) -> str:
    """Correlation map of a topic."""
    st = settings()
    c = correlate(q, AnchorResolver())
    if not c.scored:
        return (
            f"No section matches {q.label!r}. Try synonyms, --any, --regex, or `changelog --grep` before "
            "claiming it does not exist." + source_line(st.full_url)
        )
    order, rank = _page_order(c)
    shown_pages = order[:max_pages]
    assign_anchors(c.corpus, c.resolver, shown_pages)
    per = _by_page(c.scored)
    out = [
        f"RELATED  topic={q.label!r}  seeds={sorted(c.seeds) or 'none'}  corpus {cache_age(st.full_url)}",
        (
            f"{len(c.scored)} sections across {len(order)} pages. Signals: H=heading names topic, Tn=n lines "
            "mention it, L->=links to a seed page, <-seed=seed page links here. Anchors verified against "
            "rendered pages.\n"
        ),
    ]
    cited: list[tuple[str, str | None, str]] = []
    for slug in shown_pages:
        items = sorted(per[slug], key=lambda x: -x.score)
        plural = "s" if len(items) > 1 else ""
        out.append(
            f"[{facet_of(slug, c.seeds)}] {slug}  - {items[0].section.title}  "
            f"(score {rank[slug]:.0f}, {len(items)} section{plural})",
        )
        out.extend(_section_line(sc) for sc in items[:per_page])
        cited.extend((sc.section.slug, sc.section.anchor, sc.section.heading) for sc in items[:per_page])
        if len(items) > per_page:
            out.append(f"   ... {len(items) - per_page} more sections (--per-page N)")
    if len(order) > max_pages:
        out.append(f"\n... {len(order) - max_pages} more pages with weaker signals (--max N).")
    out.extend(_coverage_lines(order, c.seeds))
    out.append(
        "\nNext: `ccdocs.py dossier <same topic>` pulls these sections in full; "
        '`ccdocs.py page <slug> --section "<heading>"` for one.',
    )
    return "\n".join(out) + c.resolver.footer(cited) + source_line(st.full_url)


@dataclass(frozen=True)
class DossierLimits:
    """Budget knobs of the dossier command (budget 0 = no character limit)."""

    budget: int
    sections: int
    breadth_cap: int
    breadth_min: float
    child_limit: int
    children: bool


def _breadth_pages(c: Correlation, lim: DossierLimits) -> list[str]:
    """Round-robin across facets: every context gets its best page before any gets a second."""
    order, rank = _page_order(c)
    by_facet: dict[str, list[str]] = {}
    for slug in order:
        if slug in c.seeds or rank[slug] >= lim.breadth_min:
            by_facet.setdefault(facet_of(slug, c.seeds), []).append(slug)
    rr: list[str] = []
    depth = 0
    while any(depth < len(v) for v in by_facet.values()):
        rr.extend(v[depth] for v in by_facet.values() if depth < len(v))
        depth += 1
    return rr


def _section_text(c: Correlation, s: Section, lim: DossierLimits) -> tuple[str, int]:
    """Body of S for the dossier; subsections dropped (and named) when the block is too large."""
    body, end = c.corpus.body(s, children=lim.children)
    if lim.children and len(body) > lim.child_limit:
        own, own_end = c.corpus.body(s, children=False)
        if own != body:
            kids = [x.label for x in c.corpus.sections[s.idx + 1 :] if x.slug == s.slug and x.start < end]
            body = own + f"\n[subsections not included: {_preview(kids, 10).replace(', ', '; ')}]"
            end = own_end
    return collapse_tables(body), end


@dataclass
class _Plan:
    picked: list[tuple[Scored, str]] = field(default_factory=list)
    omitted: list[tuple[Scored, int]] = field(default_factory=list)
    covered: list[tuple[str, int, int]] = field(default_factory=list)
    used: int = 0

    def contains(self, s: Section) -> bool:
        return any(sl == s.slug and a <= s.start < b for sl, a, b in self.covered)


def _dossier_plan(c: Correlation, lim: DossierLimits) -> tuple[list[tuple[Scored, str]], list[tuple[Scored, int]]]:
    """Choose sections: breadth pass (one per page, capped size) then depth pass by rank."""
    per = _by_page(c.scored)
    passes = [(sc, True) for slug in _breadth_pages(c, lim) for sc in per[slug]]
    passes += [(sc, False) for sc in c.scored]
    plan = _Plan()
    done: set[str] = set()
    for sc, breadth in passes:
        s = sc.section
        if (breadth and s.slug in done) or plan.contains(s):
            continue
        body, end = _section_text(c, s, lim)
        if breadth and len(body) > lim.breadth_cap * (2 if s.slug in c.seeds else 1):
            continue
        if len(plan.picked) >= lim.sections or (lim.budget and plan.used + len(body) > lim.budget):
            plan.omitted.append((sc, len(body)))
            continue
        if breadth:
            done.add(s.slug)
        plan.covered.append((s.slug, s.start, end))
        plan.picked.append((sc, body))
        plan.used += len(body)
    seen: set[int] = set()
    omitted: list[tuple[Scored, int]] = []
    for sc, size in sorted(plan.omitted, key=lambda x: -x[0].score):
        if sc.section.idx not in seen and not plan.contains(sc.section):
            seen.add(sc.section.idx)
            omitted.append((sc, size))
    order, _ = _page_order(c)
    plan.picked.sort(key=lambda x: (order.index(x[0].section.slug), x[0].section.start))
    return plan.picked, omitted


def cmd_dossier(q: TopicQuery, lim: DossierLimits) -> str:
    """Correlated sections in full plus a manifest of what was not read."""
    st = settings()
    c = correlate(q, AnchorResolver())
    if not c.scored:
        return f"No section matches {q.label!r}." + source_line(st.full_url)
    picked, omitted = _dossier_plan(c, lim)
    assign_anchors(
        c.corpus, c.resolver, [sc.section.slug for sc, _ in picked] + [sc.section.slug for sc, _ in omitted[:12]]
    )
    order, _ = _page_order(c)
    bar = "=" * 100
    used = sum(len(b) for _, b in picked)
    got = {sc.section.slug for sc, _ in picked}
    budget = f"budget {lim.budget:,}" if lim.budget else "no budget limit"
    # The manifest comes first: past ~30,000 chars Claude Code hands the model a saved file plus a short
    # preview, so what was (not) read and where each section starts must sit at the top of the output.
    head = [
        (
            f"DOSSIER MANIFEST  topic={q.label!r}  {len(picked)} sections from {len(got)}/{len(order)} "
            f"correlated pages, {used:,} chars ({budget}), corpus {cache_age(st.full_url)}"
        )
    ]
    facets: dict[str, list[str]] = {}
    for slug in order:
        facets.setdefault(facet_of(slug, c.seeds), []).append(slug)
    for name, pages in facets.items():
        have = [p for p in pages if p in got]
        miss = [p for p in pages if p not in got]
        extra = f" | not read: {', '.join(miss[:6])}{' ...' if len(miss) > 6 else ''}" if miss else ""  # noqa: PLR2004
        head.append(f"   {name:<22} read: {', '.join(have) or '-'}{extra}")
    if omitted:
        head.append(f"   NOT included: {len(omitted)} section(s). Highest-ranked omissions:")
        for sc, size in omitted[:12]:
            s = sc.section
            how = f'--section "{s.label}"' if s.heading else "--intro"
            head.append(f"     - {s.slug} > {s.label}  ({size:,} chars)  -> ccdocs.py page {s.slug} {how}")
        head.append(
            "   Raise --sections (or --budget), or fetch the omissions that matter, before claiming full coverage."
        )
    else:
        head.append("   Nothing omitted: every scored section is included.")
    blocks: list[tuple[str, list[str]]] = []
    for sc, body in picked:
        s = sc.section
        mark = "" if s.anchor or not s.heading else "   (anchor unverified - cited without #anchor)"
        title = f"[{facet_of(s.slug, c.seeds)}] {s.title} > {s.label}"
        blocks.append((title, ["", bar, title, f"SOURCE: {s.cite}{mark}   signals: {' '.join(sc.signals)}", bar, body]))
    head.append("CONTENTS  (output line of each section; read only the ranges you need)")
    line = len(head) + len(blocks)  # the last line of the CONTENTS index
    for title, block in blocks:
        head.append(f"   L{line + 3:<7} {title}")
        line += sum(part.count("\n") + 1 for part in block)
    out = [*head, *(part for _, block in blocks for part in block)]
    cited = [(sc.section.slug, sc.section.anchor, sc.section.heading) for sc, _ in picked]
    return "\n".join(out) + c.resolver.footer(cited) + source_line(st.full_url)


class LinkScope(NamedTuple):
    """The page or section whose links are listed."""

    root: Section | None
    scope: list[Section]
    label: str


def _links_scope(corpus: Corpus, slug: str, section: str | None) -> tuple[Section | None, list[Section]]:
    secs = corpus.by_slug[slug]
    if not section:
        return None, secs
    pick = [s for s in secs if section.lower() in s.label.lower()]
    if not pick:
        msg = f"section {section!r} not found on {slug}; run `ccdocs.py outline {slug}`"
        raise CcdocsError(msg)
    root = pick[0]
    scope = [root]
    for s in corpus.sections[root.idx + 1 :]:
        if s.slug != slug or s.level <= root.level:
            break
        scope.append(s)
    return root, scope


def _outbound_lines(slug: str, scope: Sequence[Section], label: str, *, intra: bool) -> list[str]:
    targets: dict[str, dict[str, set[str]]] = {}
    for s in scope:
        for ln in s.links:
            if ln.target != slug or intra:
                targets.setdefault(ln.target, {}).setdefault(ln.anchor, set()).add(s.label)
    total = sum(len(v) for v in targets.values())
    out = [
        (
            f"OUTBOUND from {label}: {total} distinct targets on {len(targets)} page(s) "
            "(anchors as written by the docs authors)"
        ),
    ]
    for t in sorted(targets, key=lambda k: -len(targets[k])):
        out.append(f"  {t}")
        out.extend(
            f"     {'#' + anc if anc else '(page)':<50} from: {'; '.join(sorted(froms))[:120]}"
            for anc, froms in sorted(targets[t].items())
        )
    return [*out, ""]


def _inbound_lines(corpus: Corpus, slug: str, sc: LinkScope, per_page: int) -> list[str]:
    root, scope, label = sc.root, sc.scope, sc.label
    ids = {s.anchor for s in scope if s.anchor}
    inbound: dict[str, dict[tuple[str, str], int]] = {}
    for s in corpus.sections:
        if s.slug == slug:
            continue
        for ln in s.links:
            wanted = ln.anchor in ids if root else True
            if ln.target == slug and wanted:
                per = inbound.setdefault(s.slug, {})
                per[(s.label, ln.anchor)] = per.get((s.label, ln.anchor), 0) + 1
    occurrences = sum(sum(v.values()) for v in inbound.values())
    distinct = sum(len(v) for v in inbound.values())
    out = [
        (
            f"INBOUND to {label}: {occurrences} link(s) in {distinct} section(s) of {len(inbound)} other "
            "page(s) (same-page links excluded)"
        ),
    ]
    for src_slug in sorted(inbound, key=lambda k: -sum(inbound[k].values())):
        items = sorted(inbound[src_slug].items())
        out.append(f"  {src_slug}")
        out.extend(
            f"     [{h}] -> {'#' + a if a else '(page)'}" + (f"  x{n}" if n > 1 else "")
            for (h, a), n in items[:per_page]
        )
        if len(items) > per_page:
            out.append(f"     ... {len(items) - per_page} more")
    unresolved = [s.label for s in scope if s.heading and not s.anchor]
    if root and unresolved:
        out.append(
            f"WARNING: {len(unresolved)} section(s) in scope have no verified id, so links to them cannot be "
            f"matched and the count above may be low: {_preview(unresolved, 5)}",
        )
    return out


def cmd_links(slug: str, *, section: str | None, direction: str, intra: bool, per_page: int) -> str:
    """Inbound and outbound hyperlinks of a page or section."""
    st = settings()
    corpus = load_corpus()
    slug = re.sub(r"\.md$", "", slug.strip("/"))
    if slug not in corpus.by_slug:
        msg = f"no page {slug!r} in the corpus; find slugs with `ccdocs.py index --grep <term>`"
        raise CcdocsError(msg)
    resolver = AnchorResolver()
    assign_anchors(corpus, resolver, [slug])
    root, scope = _links_scope(corpus, slug, section)
    label = root.cite if root else human_url(slug)
    out: list[str] = []
    if direction in {"out", "both"}:
        out.extend(_outbound_lines(slug, scope, label, intra=intra))
    if direction in {"in", "both"}:
        out.extend(_inbound_lines(corpus, slug, LinkScope(root, scope, label), per_page))
    cited = [(root.slug, root.anchor, root.heading)] if root else []
    return "\n".join(out) + resolver.footer(cited) + source_line(st.full_url)


def cmd_quote(slug: str, pattern: str, *, context: int, max_hits: int) -> str:
    """Verbatim sentences from the live page with verified section URLs."""
    url = page_url(slug)
    pslug = slug_of(url)
    md = fetch(url)
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        msg = f"bad regex {pattern!r}: {exc}"
        raise CcdocsError(msg) from exc
    heads = headings_in(md)
    resolver = AnchorResolver()
    ids = resolver.resolve(pslug, [h.text for h in heads], [h.level for h in heads])
    out: list[str] = []
    cited: list[tuple[str, str | None, str]] = []
    for n, raw in enumerate(md.splitlines()):
        if not rx.search(raw):
            continue
        pos = max((i for i, h in enumerate(heads) if h.line <= n), default=-1)
        hid = ids[pos] if pos >= 0 else None
        text = " ".join(raw.split())
        if not text.startswith(("|", "*", "-")):
            parts = re.split(r"(?<=[.!?])\s+(?=[A-Z`\[*])", text)
            hit = [i for i, p in enumerate(parts) if rx.search(p)]
            if hit:
                text = " ".join(parts[max(hit[0] - context, 0) : min(hit[-1] + context + 1, len(parts))])
        where = heading_title(heads[pos].text) if pos >= 0 else "intro"
        flag = "" if hid or pos < 0 else "  (anchor unverified - cited without #anchor)"
        out.append(f'"{text}"\n   -> {human_url(pslug, hid)}  (line {n + 1}, section: {where}){flag}\n')
        cited.append((pslug, hid, heads[pos].text if pos >= 0 else ""))
        if len(out) >= max_hits:
            break
    if not out:
        msg = (
            f"NOT FOUND on the live page {human_url(pslug)}: {pattern!r}. "
            "Do not quote it; locate it with `related` or `grep`."
        )
        raise CcdocsError(msg)
    return "\n".join(out) + resolver.footer(cited) + source_line(url)


# --------------------------------------------------------------------------------------------------
# Research: the one entry point. Route -> discover -> read live -> follow links -> changelogs.
# --------------------------------------------------------------------------------------------------

SUPPORT: Final = "https://support.claude.com"
PLATFORM: Final = "https://platform.claude.com"
SUPPORT_LLMS: Final = f"{SUPPORT}/llms.txt"
PLATFORM_LLMS: Final = f"{PLATFORM}/llms.txt"
SUPPORT_RELEASES: Final = f"{SUPPORT}/en/articles/12138966-release-notes.md"
PLATFORM_RELEASES: Final = f"{PLATFORM}/docs/en/release-notes/overview.md"
SOURCES: Final = ("code", "apps", "platform")
CHILD_LIMIT: Final = 12000  # a section keeps its subsections while the whole block stays under this
DOC_LINK: Final = re.compile(
    r"\]\(((?:https://(?:code|platform|support)\.claude\.com)?/(?:docs|en)/[^)\s]+|#[^)\s]+)\)"
)
FILE_LINK: Final = re.compile(r"\.(?:png|jpe?g|gif|svg|webp|mp4|pdf|zip|json|ya?ml)$", re.IGNORECASE)
MONTH_DAY: Final = re.compile(r"^###\s+([A-Z][a-z]+ \d{1,2}, \d{4})\s*$")


class PageRef(NamedTuple):
    """A docs page: SOURCE is code/apps/platform; KEY is a Claude Code slug or the page's https URL."""

    source: str
    key: str


def page_ref(target: str, base: str = BASE) -> PageRef | None:
    """PageRef of a slug, an absolute docs URL, or a site-relative link found on a page under BASE."""
    url = target.split("#", maxsplit=1)[0].removesuffix(".mdx").removesuffix(".md").rstrip("/")
    if url.startswith("/en/") and not url.startswith("/en/articles/") and not base.startswith(PLATFORM):
        url = "/docs" + url  # docs MCP paths and links omit /docs; https://code.claude.com/en/x is a marketing page
    if url.startswith(HOST + "/en/") and not url.startswith(HOST + "/docs/"):
        url = HOST + "/docs" + url[len(HOST) :]
    if url.startswith("/"):
        host = SUPPORT if url.startswith("/en/articles/") else re.sub(r"^(https://[^/]+).*$", r"\1", base)
        url = host + url
    if url.startswith(HOST + "/docs/"):
        m = re.match(r"^https://code\.claude\.com/docs/[a-z]{2}(?:-[a-z]+)?/(.+)$", url)
        return PageRef("code", m.group(1)) if m else None  # e.g. the docs MCP endpoint, not a page
    if url.startswith(PLATFORM + "/docs/"):
        return PageRef("platform", url)
    if url.startswith(SUPPORT + "/en/articles/"):
        return PageRef("apps", url)
    if not url.startswith("https://") and re.fullmatch(r"[a-z0-9][a-z0-9/_-]*", url):
        return PageRef("code", url)
    return None


_ARTICLES: dict[str, dict[str, PageRef]] = {}


def _article_ids() -> dict[str, PageRef]:
    """Help Center article number -> indexed page, parsed once per process."""
    if "apps" not in _ARTICLES:
        table: dict[str, PageRef] = {}
        for e in other_index("apps"):
            m = re.search(r"/articles/(\d+)", e.ref.key)
            if m:
                table[m.group(1)] = e.ref
        _ARTICLES["apps"] = table
    return _ARTICLES["apps"]


def canonical(ref: PageRef) -> PageRef:
    """Help Center articles keep their number when renamed: map any slug to the indexed URL."""
    m = re.search(r"/articles/(\d+)", ref.key) if ref.source == "apps" else None
    if m is None:
        return ref
    try:
        return _article_ids().get(m.group(1), ref)
    except CcdocsError:
        return ref


def ref_md_url(ref: PageRef) -> str:
    """Raw markdown URL of a page."""
    return page_url(ref.key) if ref.source == "code" else ref.key + ".md"


def ref_cite(ref: PageRef, anchor: str | None = None) -> str:
    """Citation URL of a page, with a verified anchor when given."""
    base = human_url(ref.key) if ref.source == "code" else ref.key
    return base + (f"#{anchor}" if anchor else "")


def ref_label(ref: PageRef) -> str:
    """Short display name."""
    return ref.key if ref.source == "code" else ref.key.rsplit("/", maxsplit=1)[-1]


@dataclass(frozen=True)
class Area:
    """One row of references/areas.md."""

    name: str
    triggers: tuple[str, ...]
    terms: tuple[str, ...]
    nav_groups: tuple[str, ...]
    pages: tuple[PageRef, ...]


AREA_COLUMNS: Final = 5


def _area_refs(cell: str) -> tuple[PageRef, ...]:
    tokens = re.findall(r"`([^`]+)`|(https://[^\s,|)]+)", cell)
    refs = [page_ref(slug or url) for slug, url in cast("list[tuple[str, str]]", tokens)]
    return tuple(r for r in refs if r is not None)


def _cell_list(cell: str, sep: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in cell.split(sep) if x.strip())


def parse_areas(text: str) -> list[Area]:
    """Rows of the areas table: | Area | Triggers | Terms | Nav groups | Pages |."""
    areas: list[Area] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_table = line.strip() == "## Areas"
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not in_table or not line.lstrip().startswith("|") or len(cells) != AREA_COLUMNS:
            continue
        if cells[0] in {"Area", ""} or cells[0].startswith("-"):
            continue
        areas.append(
            Area(
                cells[0],
                _cell_list(cells[1], ","),
                _cell_list(cells[2], ","),
                _cell_list(cells[3], ";"),
                _area_refs(cells[4]),
            )
        )
    return areas


def areas_file() -> Path:
    """references/areas.md beside this script's skill."""
    return Path(__file__).resolve().parent.parent / "references" / "areas.md"


def load_areas() -> list[Area]:
    """The areas table, or none when the skill ships without it."""
    table = areas_file()
    return parse_areas(table.read_text(encoding="utf-8")) if table.is_file() else []


def active_areas(areas: Sequence[Area], phrases: Sequence[str]) -> list[Area]:
    """Areas whose triggers occur in a phrase, or that contain a phrase."""
    out: list[Area] = []
    for area in areas:
        for trig in area.triggers:
            trig_rx = topic_regex([trig], None)
            if any(trig_rx.search(p) or topic_regex([p], None).search(trig) for p in phrases):
                out.append(area)
                break
    return out


STOPWORDS: Final = frozenset(
    {
        *("a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how", "i", "in"),
        *("is", "it", "its", "my", "of", "on", "or", "so", "the", "that", "this", "to", "use", "using", "what"),
        *("when", "where", "which", "why", "with", "without", "your"),
    }
)


def vocabulary(phrases: Sequence[str], areas: Sequence[Area]) -> list[str]:
    """Words of the query plus the terms of every active area, deduplicated."""
    words = [w for p in phrases for w in re.split(r"[\s,]+", p) if len(w) > 2 and w.lower() not in STOPWORDS]  # noqa: PLR2004
    return list(dict.fromkeys([*words, *(t for a in areas for t in a.terms)]))


def any_regex(items: Sequence[str]) -> re.Pattern[str] | None:
    """One regex matching any item (each a word or short phrase; plurals match); None when empty."""
    parts = [topic_regex([i], None).pattern for i in items if re.search(r"\w", i)]
    return re.compile("|".join(f"(?:{p})" for p in parts), re.IGNORECASE) if parts else None


class InventoryEntry(NamedTuple):
    """A page of an area and every reason it belongs there."""

    ref: PageRef
    reasons: tuple[str, ...]


def area_inventory(areas: Sequence[Area], pages: Sequence[IndexPage]) -> dict[str, list[InventoryEntry]]:
    """Every page of every area: its navigation groups, its pinned pages, and index titles naming a trigger."""
    out: dict[str, list[InventoryEntry]] = {}
    for area in areas:
        reasons: dict[PageRef, list[str]] = {}
        groups = set(area.nav_groups)
        trig = any_regex(area.triggers)
        for p in pages:
            ref = PageRef("code", p.slug)
            if " > ".join(p.path) in groups:
                reasons.setdefault(ref, []).append("nav group")
            if trig is not None and trig.search(p.title):  # summaries use generic words; titles don't
                reasons.setdefault(ref, []).append("trigger in title")
        for ref in area.pages:
            reasons.setdefault(ref, []).append("pinned")
        out[area.name] = [InventoryEntry(r, tuple(v)) for r, v in reasons.items()]
    return out


def inventory_gaps(areas: Sequence[Area], pages: Sequence[IndexPage]) -> tuple[list[str], list[str]]:
    """(navigation groups in no area, index pages in no area)."""
    assigned = {g for a in areas for g in a.nav_groups}
    groups = list(dict.fromkeys(" > ".join(p.path) for p in pages))
    covered = {e.ref.key for entries in area_inventory(areas, pages).values() for e in entries}
    return [g for g in groups if g not in assigned], [p.slug for p in pages if p.slug not in covered]


def cmd_inventory() -> str:
    """The resolved page list of every area (references/area-pages.md)."""
    st = settings()
    pages = index_pages(fetch(st.llms_url))
    areas = load_areas()
    inv = area_inventory(areas, pages)
    titles = {p.slug: p.title for p in pages}
    free_groups, free_pages = inventory_gaps(areas, pages)
    today = time.strftime("%Y-%m-%d", time.gmtime())
    out = [
        "# Area pages",
        "",
        f"Generated {today} by `ccdocs.py inventory` from `references/areas.md` and {st.llms_url}.",
        "Regenerate instead of editing:",
        "`python3 scripts/ccdocs.py inventory > references/area-pages.md`.",
        "",
        (
            f"Coverage: {len(pages) - len(free_pages)}/{len(pages)} Claude Code index pages belong to an area; "
            f"{len(free_groups)} navigation group(s) and {len(free_pages)} page(s) belong to none."
        ),
    ]
    out += [f"- unassigned group: {g}" for g in free_groups] + [f"- unassigned page: `{s}`" for s in free_pages]
    for area in areas:
        entries = inv[area.name]
        out += ["", f"## {area.name} ({len(entries)} pages)", "", "| Page | Why |", "|---|---|"]
        for e in entries:
            title = titles.get(e.ref.key, "") if e.ref.source == "code" else e.ref.source
            label = f"`{e.ref.key}`" if e.ref.source == "code" else ref_label(e.ref)
            out.append(f"| [{label}]({ref_cite(e.ref)}) {title.replace('|', '/')} | {', '.join(e.reasons)} |")
    return "\n".join(out) + source_line(st.llms_url)


def phrases_regex(phrases: Sequence[str], raw: str | None) -> re.Pattern[str]:
    """A line matches when it holds every word of any one phrase, in any order (plurals match)."""
    if raw:
        return topic_regex([], raw)
    alts: list[str] = []
    for phrase in phrases:
        words = [w for w in re.split(r"[\s,]+", phrase) if w and w.lower() not in STOPWORDS] or [phrase]
        alts.append("".join(f"(?=.*?{topic_regex([w], None).pattern})" for w in words))
    return re.compile("^(?:" + "|".join(alts) + ")", re.IGNORECASE)


# ---- discovery --------------------------------------------------------------------------------


class Candidate(NamedTuple):
    """A page to read, why it was chosen, and its rank."""

    ref: PageRef
    reason: str
    score: float


class IndexEntry(NamedTuple):
    """A page of a non-Claude-Code llms.txt."""

    ref: PageRef
    title: str
    summary: str
    group: str


def other_index(source: str) -> list[IndexEntry]:
    """English pages of the Help Center or Platform index."""
    url = SUPPORT_LLMS if source == "apps" else PLATFORM_LLMS
    text = fetch_raw(url)
    out: list[IndexEntry] = []
    section, group = "", ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("### "):
            group = line[4:].strip()
            continue
        if source == "apps" and section != "English":
            continue
        m = re.match(r"^- \[([^\]]+)\]\((https://[^)]+?)\.md\)(?:\s*[:-]\s*(.*))?$", line.strip())
        if not m or (source == "platform" and "/docs/en/" not in m.group(2)):
            continue
        ref = page_ref(m.group(2))
        if ref is not None and ref.source == source:
            out.append(IndexEntry(ref, m.group(1).replace("\\", ""), (m.group(3) or "").strip(), group))
    return out


def discover_other(source: str, rx: re.Pattern[str]) -> list[Candidate]:
    """Index pages of SOURCE ranked by title, URL, group and summary matches."""
    found: list[Candidate] = []
    for e in other_index(source):
        score = 0.0
        score += 6 if rx.search(e.title) else 0
        score += 3 if rx.search(e.ref.key.rsplit("/", maxsplit=1)[-1].replace("-", " ")) else 0
        score += 3 if rx.search(e.group) else 0
        score += 2 if rx.search(e.summary) else 0
        if score:
            found.append(Candidate(e.ref, f"index: {e.title}", score))
    return sorted(found, key=lambda c: -c.score)


def discover_code(rx: re.Pattern[str], seeds: Sequence[str], resolver: AnchorResolver) -> list[Candidate]:
    """Claude Code pages ranked by the corpus correlation (headings, mentions, hyperlink graph)."""
    corpus = load_corpus()
    q = TopicQuery(
        topic=(),
        regex=rx.pattern,
        any_term=False,
        seeds=tuple(s for s in seeds if s in corpus.by_slug),
        min_score=3.0,
        include_history=False,
        follow_links=True,
    )
    c = correlate(q, resolver)
    order, rank = _page_order(c)
    return [Candidate(PageRef("code", slug), f"corpus rank {rank[slug]:.0f}", rank[slug]) for slug in order]


# ---- live reading ---------------------------------------------------------------------------


@dataclass
class ReadSection:
    """A section read from a live page."""

    ref: PageRef
    heading: str
    level: int
    anchor: str | None
    body: str
    signals: str
    via: str


@dataclass
class PageReport:
    """What research did with one page."""

    ref: PageRef
    reason: str
    title: str = ""
    read: list[ReadSection] = field(default_factory=list)
    listed: list[str] = field(default_factory=list)
    error: str = ""
    outline: list[tuple[int, str, str | None]] = field(default_factory=list)


def _own_end(heads: Sequence[Heading], idx: int, n_lines: int) -> int:
    return heads[idx + 1].line if idx + 1 < len(heads) else n_lines


def _block(lines: Sequence[str], heads: Sequence[Heading], idx: int) -> tuple[str, list[str]]:
    """Section IDX with its subsections, or only its own text (subsections named) when too large."""
    start, end = section_bounds("\n".join(lines), heads, idx)
    whole = "\n".join(lines[start:end]).strip()
    if len(whole) <= CHILD_LIMIT:
        return whole, []
    own = "\n".join(lines[start : _own_end(heads, idx, len(lines))]).strip()
    kids = [heading_title(h.text) for h in heads[idx + 1 :] if h.line < end]
    return own + f"\n[subsections not included: {'; '.join(kids)}]", kids


def _page_title(md: str, ref: PageRef) -> str:
    m = re.search(r"^title:\s*(.+)$", md, re.MULTILINE) or re.search(r"^#\s+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else ref_label(ref)


def read_live(ref: PageRef, reason: str, rx: re.Pattern[str], resolver: AnchorResolver) -> PageReport:
    """Read one live page and keep only the sections about the topic."""
    rep = PageReport(ref, reason)
    try:
        md = fetch(ref_md_url(ref))
    except CcdocsError as exc:
        rep.error = str(exc)
        return rep
    rep.title = _page_title(md, ref)
    lines = md.splitlines()
    heads = headings_in(md)
    ids = resolver.resolve(ref.key, [h.text for h in heads], [h.level for h in heads]) if heads else []
    rep.outline = [(h.level, heading_title(h.text), hid) for h, hid in zip(heads, ids, strict=True)]
    stats: list[tuple[int, bool, int]] = []
    for i, h in enumerate(heads):
        own = lines[h.line + 1 : _own_end(heads, i, len(lines))]
        stats.append((i, bool(rx.search(heading_title(h.text))), sum(1 for ln in own if rx.search(ln))))
    chosen = [i for i, is_h, _ in stats if is_h]
    if not chosen:
        chosen = [i for i, _, t in sorted(stats, key=lambda x: -x[2]) if t][:3]
    covered_until = -1
    for i in sorted(chosen):
        if heads[i].line < covered_until:
            continue
        body, _ = _block(lines, heads, i)
        covered_until = (
            section_bounds(md, heads, i)[1] if "[subsections not included" not in body else heads[i].line + 1
        )
        t = stats[i][2]
        sig = ("H " if stats[i][1] else "") + f"T{t}"
        rep.read.append(ReadSection(ref, heads[i].text, heads[i].level, ids[i], collapse_tables(body), sig, "topic"))
    read_heads = {r.heading for r in rep.read}
    rep.listed = [
        f"{heading_title(heads[i].text)} (T{t})"
        for i, is_h, t in stats
        if t and heads[i].text not in read_heads and not is_h
    ]
    if not heads or not rep.read:
        intro = "\n".join(lines[: heads[0].line] if heads else lines).strip()
        if intro:
            rep.read.append(ReadSection(ref, "", 1, None, collapse_tables(intro), "intro", "topic"))
    return rep


def _link_targets(sec: ReadSection) -> list[tuple[PageRef, str]]:
    base = ref_cite(sec.ref)
    out: list[tuple[PageRef, str]] = []
    for m in DOC_LINK.finditer(sec.body):
        raw = m.group(1)
        anchor = raw.split("#", maxsplit=1)[1] if "#" in raw else ""
        if FILE_LINK.search(raw.split("#", maxsplit=1)[0]):
            continue
        ref = sec.ref if raw.startswith("#") else page_ref(raw, base)
        if ref is not None:
            ref = canonical(ref)
            if (ref, anchor) not in out:
                out.append((ref, anchor))
    return out


def read_link(ref: PageRef, anchor: str, via: str, resolver: AnchorResolver) -> ReadSection | str:
    """The section a hyperlink points to (the intro for a page link), or why it could not be read."""
    try:
        md = fetch(ref_md_url(ref))
    except CcdocsError as exc:
        return str(exc)
    lines = md.splitlines()
    heads = headings_in(md)
    if not anchor:
        intro = "\n".join(lines[: heads[0].line] if heads else lines).strip()
        return ReadSection(ref, "", 1, None, collapse_tables(intro), "link", via)
    ids = resolver.resolve(ref.key, [h.text for h in heads], [h.level for h in heads])
    target = resolver.lookup(ref.key, anchor)
    idx: int | None = None
    if target is not None:
        same = [i for i, h in enumerate(heads) if norm_heading(h.text) == norm_heading(target.text)]
        idx = next((i for i in same if heads[i].level == target.level), same[0] if same else None)
    if idx is None:
        idx = next((i for i, h in enumerate(heads) if f"{{#{anchor}}}" in h.text), None)
    if idx is None:
        why = "the rendered page has no such id" if resolver.rendered(ref.key) is not None else "page not rendered"
        return f"anchor #{anchor} not found ({why})"
    body, _ = _block(lines, heads, idx)
    return ReadSection(ref, heads[idx].text, heads[idx].level, ids[idx], collapse_tables(body), "link", via)


# ---- changelogs -------------------------------------------------------------------------------


class ChangeEntry(NamedTuple):
    """A changelog line or release-note paragraph that mentions the topic."""

    source: str
    when: str
    version: str
    text: str


def _code_changes(rx: re.Pattern[str], cutoff: str) -> tuple[list[ChangeEntry], int]:
    _, times = _npm_tags()
    out: list[ChangeEntry] = []
    scanned = 0
    for block in re.split(r"(?m)^## ", fetch(CHANGELOG_RAW))[1:]:
        ver, _, body = block.partition("\n")
        ver = ver.strip()
        when = times.get(ver, "")[:10]
        if not when or when < cutoff:
            continue
        scanned += 1
        out.extend(ChangeEntry("code", when, ver, ln.strip()) for ln in body.splitlines() if rx.search(ln))
    return out, scanned


def _dated_changes(source: str, url: str, rx: re.Pattern[str], cutoff: str) -> tuple[list[ChangeEntry], int]:
    out: list[ChangeEntry] = []
    scanned = 0
    when = ""
    unit: list[str] = []

    def flush() -> None:
        text = " ".join(" ".join(unit).split())
        if when and when >= cutoff and text and rx.search(text):
            out.append(ChangeEntry(source, when, "", text))
        unit.clear()

    for line in fetch_raw(url).splitlines():
        m = MONTH_DAY.match(line)
        if m:
            flush()
            try:
                when = time.strftime("%Y-%m-%d", time.strptime(m.group(1), "%B %d, %Y"))
            except ValueError:
                when = ""
            scanned += 1 if when and when >= cutoff else 0
            continue
        if line.startswith("## "):
            flush()
            continue
        if not line.strip() or line.lstrip().startswith(("* ", "- ")):
            flush()
        if line.strip():
            unit.append(line.strip())
    flush()
    return out, scanned


def changes(sources: Sequence[str], rx: re.Pattern[str], months: int) -> tuple[list[ChangeEntry], list[str]]:
    """Every release-note entry of the last MONTHS months that mentions the topic, per source."""
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - months * 30.44 * 86400))
    out: list[ChangeEntry] = []
    notes: list[str] = []
    readers: dict[str, Callable[[], tuple[list[ChangeEntry], int]]] = {
        "code": lambda: _code_changes(rx, cutoff),
        "apps": lambda: _dated_changes("apps", SUPPORT_RELEASES, rx, cutoff),
        "platform": lambda: _dated_changes("platform", PLATFORM_RELEASES, rx, cutoff),
    }
    names = {"code": CHANGELOG_RAW, "apps": SUPPORT_RELEASES, "platform": PLATFORM_RELEASES}
    for src in sources:
        try:
            found, scanned = readers[src]()
        except CcdocsError as exc:
            notes.append(f"[{src}] changelog NOT checked: {exc}")
            continue
        out.extend(found)
        notes.append(f"[{src}] {scanned} release(s) since {cutoff} scanned, {len(found)} match(es) - {names[src]}")
    return out, notes


# ---- the command ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchQuery:
    """Arguments of `research`."""

    phrases: tuple[str, ...]
    regex: str | None
    sources: tuple[str, ...]
    months: int
    pages: int
    follow: bool
    out: str | None = None


def _plan_pages(
    q: ResearchQuery, rx: re.Pattern[str], areas: Sequence[Area], resolver: AnchorResolver
) -> tuple[list[Candidate], list[Candidate]]:
    """(pages to read, pages found but not read). Every page of every active area is read."""
    routed: list[Candidate] = []
    if areas:
        index = index_pages(fetch(settings().llms_url))
        for name, entries in area_inventory(areas, index).items():
            routed += [Candidate(canonical(e.ref), f"area {name}: {', '.join(e.reasons)}", 100.0) for e in entries]
    routed = [c for c in routed if c.ref.source in q.sources]
    ranked: list[list[Candidate]] = []
    if "code" in q.sources:
        ranked.append(discover_code(rx, [c.ref.key for c in routed if c.ref.source == "code"], resolver))
    ranked += [discover_other(src, rx) for src in ("apps", "platform") if src in q.sources]
    plan: dict[PageRef, Candidate] = {}
    for c in [*routed, *(c for found in ranked for c in found[: q.pages])]:
        if c.ref not in plan:
            plan[c.ref] = c
    rest = [c for found in ranked for c in found[q.pages :] if c.ref not in plan]
    return list(plan.values()), rest


def _versions_line() -> str:
    try:
        tags, times = _npm_tags()
    except CcdocsError as exc:
        return f"VERSIONS  npm NOT checked: {exc}"
    latest = tags.get("latest", "?")
    local = local_claude_version()
    gap = ""
    lk, lt = (vkey(local) if local else None), vkey(latest)
    if lk and lt:
        gap = (
            " · up to date" if lk == lt else (" · local is BEHIND latest" if lk < lt else " · local is AHEAD of latest")
        )
    published = times.get(latest, "?")[:10]
    return f"VERSIONS  Claude Code npm latest {latest} ({published}) · local {local or 'unknown (not on PATH)'}{gap}"


@dataclass
class ResearchResult:
    """Everything research gathered, ready to render."""

    q: ResearchQuery
    areas: list[Area]
    reports: list[PageReport]
    rest: list[Candidate]
    followed: list[ReadSection] = field(default_factory=list)
    link_failures: list[str] = field(default_factory=list)
    entries: list[ChangeEntry] = field(default_factory=list)
    change_notes: list[str] = field(default_factory=list)


def follow_links(res: ResearchResult, resolver: AnchorResolver) -> None:
    """Read, one hop away, the sections that the topic sections link to."""
    seen = {(s.ref, norm_heading(s.heading)) for r in res.reports for s in r.read}
    todo: list[tuple[PageRef, str, str]] = []
    for r in res.reports:
        for s in r.read:
            via = f"{ref_label(s.ref)} > {heading_title(s.heading) if s.heading else '(intro)'}"
            for ref, anchor in _link_targets(s):
                if ref.source in res.q.sources and not any(t[0] == ref and t[1] == anchor for t in todo):
                    todo.append((ref, anchor, via))
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:

        def one(item: tuple[PageRef, str, str]) -> ReadSection | str:
            return read_link(item[0], item[1], item[2], resolver)

        got = list(pool.map(one, todo))
    for (ref, anchor, via), sec in zip(todo, got, strict=True):
        if isinstance(sec, str):
            res.link_failures.append(f"{ref_cite(ref)}{'#' + anchor if anchor else ''} (from {via}): {sec}")
            continue
        key = (sec.ref, norm_heading(sec.heading))
        if sec.body and key not in seen:  # alias anchors and repeated links land on sections already read
            seen.add(key)
            res.followed.append(sec)


def cmd_research(q: ResearchQuery) -> str:
    """Route, discover, read the live pages, follow their links, and check every changelog."""
    if not q.phrases and not q.regex:
        msg = "give one or more topic phrases (quote multi-word phrases) or --regex"
        raise CcdocsError(msg)
    rx = phrases_regex(q.phrases, q.regex)
    resolver = AnchorResolver()
    areas = active_areas(load_areas(), q.phrases)
    vocab = any_regex(vocabulary(q.phrases, areas)) if not q.regex else None
    section_rx = vocab or rx
    plan, rest = _plan_pages(q, rx, areas, resolver)
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:

        def read(c: Candidate) -> PageReport:
            return read_live(c.ref, c.reason, section_rx, resolver)

        reports = list(pool.map(read, plan))
    res = ResearchResult(q, areas, reports, rest)
    if q.follow:
        follow_links(res, resolver)
    res.entries, res.change_notes = changes(q.sources, rx, q.months)
    return _render_research(res, resolver, research_root(q.out))


MAP_INLINE: Final = 25000  # a MAP this size or smaller is printed whole instead of only its path
RUNS_KEPT: Final = 10  # research folders kept per output directory; older ones are deleted
LISTED_SHOWN: Final = 6
NOT_READ_SHOWN: Final = 25
CHANGES_IN_MAP: Final = 10


def _slug(text: str, limit: int = 48) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm_heading(text) if text else "intro").strip("-")[:limit] or "x"


def _section_label(s: ReadSection) -> str:
    return heading_title(s.heading) if s.heading else "(intro)"


def _section_file(i: int, s: ReadSection) -> str:
    return f"sections/{i + 1:03d}-{s.ref.source}-{_slug(ref_label(s.ref), 40)}-{_slug(s.heading)}.md"


def _section_doc(s: ReadSection) -> str:
    via = f"via link from {s.via}" if s.signals == "link" else f"signals: {s.signals}"
    mark = "  (anchor unverified - cite the page URL)" if s.heading and not s.anchor else ""
    return (
        f"# [{s.ref.source}] {ref_label(s.ref)} > {_section_label(s)}\n"
        f"SOURCE: {ref_cite(s.ref, s.anchor)}{mark}\n{via}\n\n{s.body}\n"
    )


def _change_line(e: ChangeEntry) -> str:
    return f"[{e.source}] {e.when}{' ' + e.version if e.version else ''}: {e.text}"


def _summary(res: ResearchResult, sections: Sequence[ReadSection]) -> list[str]:
    failures = [f"{ref_cite(r.ref)}: {r.error}" for r in res.reports if r.error] + res.link_failures
    today = time.strftime("%Y-%m-%d", time.gmtime())
    areas = ", ".join(a.name for a in res.areas) or "none matched (corpus and index discovery only)"
    total = sum(len(s.body) for s in sections)
    return [
        f"RESEARCH  query={list(res.q.phrases) or res.q.regex!r}  sources={','.join(res.q.sources)}  date {today}",
        f"AREAS     {areas}  (references/areas.md)",
        _versions_line(),
        f"READ      {len(sections)} sections, {len(res.reports)} pages, {len(res.followed)} via links, {total:,} chars",
        "FAILURES  " + ("none" if not failures else f"{len(failures)} - say what each one left unverified"),
        *(f"   ! {' '.join(f.split())}" for f in failures),
        f"CHANGELOG last {res.q.months} months (all matches in changelog.md)",
        *(f"   {n}" for n in res.change_notes),
    ]


def _page_file(i: int, ref: PageRef) -> str:
    return f"pages/{i + 1:03d}-{ref.source}-{_slug(ref_label(ref), 60)}.md"


class PageDoc(NamedTuple):
    """An index file of one page and the counts the MAP shows for it."""

    name: str
    header: str
    topic: int
    linked: int
    text: str


def _page_docs(res: ResearchResult, sections: Sequence[ReadSection], files: Sequence[str]) -> list[PageDoc]:
    """One index file per page: its topic sections, the sections links reached, what else it mentions."""
    reports = {r.ref: r for r in res.reports}
    order = list(dict.fromkeys([r.ref for r in res.reports] + [s.ref for s in res.followed]))
    docs: list[PageDoc] = []
    for n, ref in enumerate(order):
        r = reports.get(ref)
        header = f"[{ref.source}] {ref_label(ref)} - {r.title if r and r.title else ref_label(ref)}"
        lines = [f"# {header}", f"URL: {ref_cite(ref)}", f"Why read: {r.reason if r else 'reached by a link'}"]
        topic = [i for i, s in enumerate(sections) if s.ref == ref and s.signals != "link"]
        linked = [i for i, s in enumerate(sections) if s.ref == ref and s.signals == "link"]
        if topic:
            lines += ["", "## Sections about the topic"]
            lines += [
                f"- {files[i]}  {'#' * sections[i].level} {_section_label(sections[i])}  [{sections[i].signals}]"
                for i in topic
            ]
        if linked:
            lines += ["", "## Sections reached by a link from another topic section"]
            lines += [f"- {files[i]}  {_section_label(sections[i])}  <- {sections[i].via}" for i in linked]
        if r and r.listed:
            lines += ["", "## Also mentions the topic (not read; `ccdocs.py page` fetches one)"]
            lines += [f"- {x}" for x in r.listed]
        if r and r.outline:
            read_titles = {heading_title(sections[i].heading) for i in [*topic, *linked]}
            lines += ["", "## Every heading of the page (* = in a section file above)"]
            lines += [
                f"{'  ' * (lvl - 2)}- {'* ' if title in read_titles else ''}{title}"
                f"  {ref_cite(ref, hid) if hid else '(no anchor)'}"
                for lvl, title, hid in r.outline
            ]
        docs.append(PageDoc(_page_file(n, ref), header, len(topic), len(linked), "\n".join(lines) + "\n"))
    return docs


def _map_doc(res: ResearchResult, pages: Sequence[PageDoc]) -> list[str]:
    out = ["", f"Newest changelog matches (up to {CHANGES_IN_MAP} per source; all of them in changelog.md):"]
    for src in res.q.sources:
        out += [f"   {_change_line(e)}" for e in [e for e in res.entries if e.source == src][:CHANGES_IN_MAP]]
    out += ["", "## Pages read (open a page file to see its sections, then open only the section files you need)"]
    out += [f"- {d.name}  {d.header}  (topic sections: {d.topic}, via links: {d.linked})" for d in pages if d.topic]
    reached = [d for d in pages if not d.topic]
    if reached:
        out += ["", f"## Pages reached only through links ({len(reached)})"]
        out += [f"- {d.name} ({d.linked})" for d in reached]
    if res.rest:
        out += ["", f"## Not read ({len(res.rest)} lower-ranked pages; `ccdocs.py page <slug>` or `raw <url>`)"]
        out += [f"- [{c.ref.source}] {ref_cite(c.ref)}  ({c.reason})" for c in res.rest[:NOT_READ_SHOWN]]
        if len(res.rest) > NOT_READ_SHOWN:
            out.append(f"- ... {len(res.rest) - NOT_READ_SHOWN} more")
    return out


def research_root(out: str | None) -> Path:
    """Where research folders go: --out, else <cache>/research."""
    return Path(out).expanduser() if out else settings().cache_dir / "research"


def _prune(root: Path) -> None:
    runs = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name)
    for old in runs[:-RUNS_KEPT]:
        shutil.rmtree(old, ignore_errors=True)


def _render_research(res: ResearchResult, resolver: AnchorResolver, root: Path) -> str:
    sections = [s for r in res.reports for s in r.read] + res.followed
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    name = f"{stamp}-{_slug(' '.join(res.q.phrases) or 'regex', 40)}"
    note = ""
    try:
        run = root / name
        for sub in ("sections", "pages"):
            (run / sub).mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # e.g. an unsubstituted ${CLAUDE_PLUGIN_DATA} expanded to /research
        root = settings().cache_dir / "research"
        run = root / name
        for sub in ("sections", "pages"):
            (run / sub).mkdir(parents=True, exist_ok=True)
        note = f"NOTE      --out not writable ({exc}); wrote to the cache instead; run `show` without --out."
    files = [_section_file(i, s) for i, s in enumerate(sections)]
    for name, s in zip(files, sections, strict=True):
        _ = (run / name).write_text(_section_doc(s), encoding="utf-8")
    pages = _page_docs(res, sections, files)
    for doc in pages:
        _ = (run / doc.name).write_text(doc.text, encoding="utf-8")
    summary = _summary(res, sections)
    cited = [(s.ref.key, s.anchor, s.heading) for s in sections if s.heading]
    footer = resolver.footer(cited)
    indexes = {"code": f"{BASE}/llms-full.txt", "apps": SUPPORT_LLMS, "platform": PLATFORM_LLMS}
    sources = source_line(*(indexes[s] for s in res.q.sources))
    map_text = "\n".join(["# Research map", "", *summary, *_map_doc(res, pages)]) + footer + sources
    _ = (run / "MAP.md").write_text(map_text + "\n", encoding="utf-8")
    changelog = [*res.change_notes, "", *(_change_line(e) for e in res.entries)]
    _ = (run / "changelog.md").write_text("\n".join(["# Changelog matches", "", *changelog]) + "\n", encoding="utf-8")
    _prune(root)
    anchors = footer.strip().splitlines()[0] if footer.strip() else "ANCHORS: none cited"
    if len(map_text) <= MAP_INLINE:
        return "\n".join([f"FOLDER    {run}", *([note] if note else []), "", map_text])
    return (
        "\n".join(
            [
                *summary,
                anchors + ("  (details in MAP.md)" if len(footer.strip().splitlines()) > 1 else ""),
                *([note] if note else []),
                f"FOLDER    {run}",
                f"NEXT      read MAP.md ({len(map_text):,} chars), then the page files it lists, then only the section",
                "          files the question needs. Every section file starts with its SOURCE URL.",
            ]
        )
        + sources
    )


def cmd_show(path: str, root: Path) -> str:
    """Print a file of a research folder (keeps reads inside the pre-approved script)."""
    target = Path(path).expanduser().resolve()
    base = root.resolve()
    if base not in target.parents or not target.is_file():
        msg = f"{path} is not a file inside {base}; `show` only reads research output"
        raise CcdocsError(msg)
    return target.read_text(encoding="utf-8")


def load_aliases() -> dict[str, str]:
    """Old Claude Code slugs -> the page they serve, from references/url-aliases.md."""
    table = areas_file().parent / "url-aliases.md"
    if not table.is_file():
        return {}
    rows = re.findall(
        r"^\| https://code\.claude\.com/docs/en/(\S+?) \| \[`([^`]+)`\]",
        table.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return dict(cast("list[tuple[str, str]]", rows))


def _canonical_page(ref: PageRef) -> tuple[PageRef, list[str]]:
    """The indexed page REF stands for, and notes on how it got there."""
    if ref.source == "code":
        if ref.key in {p.slug for p in index_pages(fetch(settings().llms_url))}:
            return ref, []
        alias = load_aliases().get(ref.key)
        if alias is None:
            msg = f"`{ref.key}` is not a page of {settings().llms_url}; locate it with `ccdocs.py find <term>`"
            raise CcdocsError(msg)
        return PageRef("code", alias), [f"`{ref.key}` is an old alias of `{alias}`; cite the canonical page"]
    ref = canonical(ref)
    if ref.key in {e.ref.key for e in other_index(ref.source)}:
        return ref, []
    where = "Help Center" if ref.source == "apps" else "Platform"
    return ref, [f"not in the {where} index (moved or removed?)"]


def cmd_url(target: str) -> str:
    """The canonical, verified URL of a docs path, link, alias or slug (for anything from the docs MCP)."""
    ref = page_ref(target.strip())
    if ref is None:
        msg = f"{target!r} is not a Claude Code, Help Center or Platform docs page"
        raise CcdocsError(msg)
    ref, notes = _canonical_page(ref)
    anchor = target.split("#", maxsplit=1)[1] if "#" in target else ""
    hid: str | None = None
    if anchor:
        found = AnchorResolver().lookup(ref.key, anchor)
        hid = found.hid if found is not None and found.hid else None
        if hid is None:
            notes.append(f"#{anchor} is not an anchor on the rendered page; cite the page URL")
        elif hid != urllib.parse.unquote(anchor):
            notes.append(f"#{anchor} is an old anchor of #{hid}")
    return ref_cite(ref, hid) + "".join(f"\nNOTE: {n}" for n in notes)


# --------------------------------------------------------------------------------------------------
# Catalog: every page, classified by the official navigation, with its hyperlink neighbours
# --------------------------------------------------------------------------------------------------

INDEX_ENTRY: Final = re.compile(r"^- \[([^\]]+)\]\((https://code\.claude\.com/docs/en/[^)]+?)\.md\)(?::\s*(.*))?$")
CATALOG_NEIGHBOURS: Final = 6


class IndexPage(NamedTuple):
    """One page of llms.txt with the navigation path it is listed under."""

    slug: str
    title: str
    summary: str
    path: tuple[str, ...]


def index_pages(llms: str) -> list[IndexPage]:
    """Pages of llms.txt in navigation order; each keeps its section path (## > ### > ####)."""
    path: list[str] = ["", "", ""]
    out: list[IndexPage] = []
    for line in llms.splitlines():
        m = re.match(r"^(#{2,4})\s+(.*?)\s*$", line)
        if m:
            depth = len(m.group(1)) - 2
            path[depth] = m.group(2)
            for d in range(depth + 1, 3):
                path[d] = ""
            continue
        e = INDEX_ENTRY.match(line.strip())
        if e and path[0] != "Indexes":
            crumbs = [path[0], *(p for p in path[1:] if p and p != path[0])]
            out.append(IndexPage(slug_of(e.group(2)), e.group(1), (e.group(3) or "").strip(), tuple(crumbs)))
    return out


def link_graph(corpus: Corpus) -> dict[str, dict[str, int]]:
    """Cross-page hyperlink counts: graph[source slug][target slug] = number of links."""
    graph: dict[str, dict[str, int]] = {}
    for s in corpus.sections:
        for ln in s.links:
            if ln.target != s.slug:
                row = graph.setdefault(s.slug, {})
                row[ln.target] = row.get(ln.target, 0) + 1
    return graph


def _neighbours(counts: dict[str, int], known: set[str]) -> str:
    ranked = sorted(((n, t) for t, n in counts.items() if t in known), key=lambda x: (-x[0], x[1]))
    return ", ".join(f"[`{t}`]({human_url(t)}) x{n}" for n, t in ranked[:CATALOG_NEIGHBOURS]) or "-"


def cmd_catalog() -> str:
    """Every page of the index, grouped by its official navigation path, with its link neighbours."""
    st = settings()
    pages = index_pages(fetch(st.llms_url))
    graph = link_graph(load_corpus())
    known = {p.slug for p in pages}
    inbound: dict[str, dict[str, int]] = {}
    for src, row in graph.items():
        for tgt, n in row.items():
            inbound.setdefault(tgt, {})[src] = n
    today = time.strftime("%Y-%m-%d", time.gmtime())
    out = [
        "# Claude Code docs catalog",
        "",
        f"Generated {today} by `ccdocs.py catalog` from {st.llms_url} (classification: the official",
        f"navigation, `##` section > `###` group > `####` subgroup) and {st.full_url} (hyperlinks).",
        f"{len(pages)} pages. Regenerate instead of editing:",
        "`python3 scripts/ccdocs.py catalog > references/docs-catalog.md`.",
        "",
        "How to read a row:",
        "- **Page**: slug and live URL. Raw markdown is the same URL plus `.md`.",
        "- **Covers**: the page's own one-line summary from the index.",
        "- **Links to**: the pages this page links to most (x = number of links). Read them when the page",
        "  defers a detail to them.",
        "- **Linked from**: the pages that link here most. They document the same feature from another",
        "  context (subagents, plugins, settings, SDK...), so a complete answer checks them too.",
    ]
    group: tuple[str, ...] | None = None
    for p in pages:
        if p.path != group:
            group = p.path
            out += [
                "",
                f"## {' > '.join(p.path)}",
                "",
                "| Page | Covers | Links to | Linked from |",
                "|---|---|---|---|",
            ]
        summary = p.summary.replace("|", "\\|") or "-"
        out.append(
            f"| [`{p.slug}`]({human_url(p.slug)}) - {p.title.replace('|', '/')} | {summary} | "
            f"{_neighbours(graph.get(p.slug, {}), known)} | {_neighbours(inbound.get(p.slug, {}), known)} |"
        )
    return "\n".join(out) + source_line(st.llms_url, st.full_url)


# --------------------------------------------------------------------------------------------------
# Self-check of the routing tables
# --------------------------------------------------------------------------------------------------

BASE_NON_SLUGS: Final = frozenset(
    {
        "awk",
        "sed",
        "grep",
        "rg",
        "cat",
        "head",
        "tree",
        "ls",
        "gh",
        "git",
        "curl",
        "npm",
        "jq",
        "claude",
        "bash",
        "zsh",
        "cd",
        "echo",
        "python3",
        "node",
        "npx",
        "env",
        "json",
        "yaml",
        "latest",
        "stable",
        "next",
        "best",
        "opus",
        "sonnet",
        "haiku",
        "fable",
        "opusplan",
        "ultracode",
        "ultrareview",
        "v1",
        "claude-code-guide",
        "plugin-root",
        "pt-br",
        "zh-hant",
    }
)


def plugin_component_names(skill_dir: Path) -> set[str]:
    """Names of the plugin, its skills and its agents (backticked in the docs, but not doc pages)."""
    names: set[str] = {skill_dir.name}
    plugin_root = skill_dir.parent.parent
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        data = parse_json(manifest.read_text(encoding="utf-8"), str(manifest))
        if isinstance(data, dict):
            name = cast("dict[str, object]", data).get("name")
            if isinstance(name, str):
                names.add(name)
    names.update(p.name for p in (plugin_root / "skills").glob("*") if p.is_dir())
    names.update(p.stem for p in (plugin_root / "agents").glob("*.md"))
    return names


def routing_units(text: str) -> Iterator[str]:
    """Bullets and table rows as single strings (wrapped continuation lines folded in)."""
    buf: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("- ", "* ", "|")) or re.match(r"^\d+\. ", s):
            if buf:
                yield " ".join(buf)
            buf = [s]
        elif s and buf and line[:1] in " \t":
            buf.append(s)
        else:
            if buf:
                yield " ".join(buf)
            buf = []
            if s:
                yield s
    if buf:
        yield " ".join(buf)


def _map_headings(mp: str) -> dict[str, list[str]]:
    heads: dict[str, list[str]] = {}
    page: str | None = None
    for line in mp.splitlines():
        m = re.match(r"^#{2,4} \[[^\]]+\]\(https://code\.claude\.com/docs/en/([^)]+)\.md\)", line)
        if m:
            name: str = m.group(1) or ""
            page = name
            _ = heads.setdefault(name, [])
        elif page and line.strip().startswith("*"):
            heads[page].append(line.strip("* ").strip().lower())
    return heads


@dataclass
class _Checker:
    """Validates backticked slugs and the quoted section names that follow them."""

    slugs: set[str]
    map_heads: dict[str, list[str]]
    live: bool
    skip: frozenset[str]
    live_heads: dict[str, list[str]] = field(default_factory=dict)
    issues: dict[tuple[str, str, str, str], int] = field(default_factory=dict)
    n_slug: int = 0
    n_sec: int = 0

    def heads_for(self, slug: str) -> list[str] | None:
        if not self.live:
            return self.map_heads.get(slug)
        if slug not in self.live_heads:
            self.live_heads[slug] = [heading_title(h.text).lower() for h in headings_in(fetch(page_url(slug)))]
        return self.live_heads[slug]

    def _flag(self, key: tuple[str, str, str, str]) -> None:
        self.issues[key] = self.issues.get(key, 0) + 1

    def check_unit(self, fname: str, unit: str) -> None:
        current: str | None = None
        for m in re.finditer(r"`([a-z0-9][a-z0-9-]*(?:/[a-z0-9-]+)*)`|\"([^\"]{3,80})\"", unit):
            token, quoted = m.group(1), m.group(2)
            if token:
                if token in self.skip:
                    continue
                self.n_slug += 1
                current = token if token in self.slugs else None
                if current is None:
                    self._flag((fname, "slug", token, ""))
                continue
            heads = self.heads_for(current) if current and quoted else None
            sec = " ".join((quoted or "").split()).lower().replace("`", "")
            if heads is None or sec.endswith(("\u2026", "...")):
                continue
            self.n_sec += 1
            if not any(sec in h.replace("`", "") for h in heads):
                self._flag((fname, "section", quoted or "", current or ""))

    def report(self) -> list[str]:
        out: list[str] = []
        for (name, kind, what, pg), n in sorted(self.issues.items()):
            times = f" ({n}x)" if n > 1 else ""
            if kind == "slug":
                hint = what.rsplit("/", maxsplit=1)[-1]
                out.append(f"[slug] {name}: `{what}` is not a page in llms.txt{times} - run `ccdocs.py find {hint}`")
            else:
                out.append(f'[section] {name}: "{what}" not found under `{pg}`{times} - run `ccdocs.py outline {pg}`')
        return out


def run_selfcheck(skill_dir: Path, *, live: bool, non_slugs: set[str]) -> str:
    """Validate slugs and quoted section names of SKILL.md and references/topic-routing.md."""
    st = settings()
    files = [
        skill_dir / "SKILL.md",
        skill_dir / "references" / "topic-routing.md",
        skill_dir / "references" / "areas.md",
    ]
    present = [f for f in files if f.is_file()]
    if not present:
        msg = (
            f"nothing to check under {skill_dir}: ccdocs.py must sit at <skill>/scripts/ccdocs.py with "
            "SKILL.md and references/ beside it."
        )
        raise CcdocsError(msg)
    llms, mp = fetch(st.llms_url), fetch(st.map_url)
    checker = _Checker(
        slugs=set(re.findall(r"code\.claude\.com/docs/en/([^)\s]+?)\.md", llms)),
        map_heads=_map_headings(mp),
        live=live,
        skip=BASE_NON_SLUGS | frozenset(non_slugs),
    )
    for f in present:
        for unit in routing_units(f.read_text(encoding="utf-8")):
            checker.check_unit(f.name, unit)
    out = [f"[layout] missing {f.relative_to(skill_dir)}" for f in files if not f.is_file()]
    out.extend(checker.report())
    table = skill_dir / "references" / "areas.md"
    if table.is_file():
        areas = parse_areas(table.read_text(encoding="utf-8"))
        index = index_pages(llms)
        groups = {" > ".join(p.path) for p in index}
        coverage = [
            f"[coverage] areas.md: nav group {g!r} is not in llms.txt"
            for a in areas
            for g in a.nav_groups
            if g not in groups
        ]
        free_groups, free_pages = inventory_gaps(areas, index)
        coverage += [f"[coverage] areas.md: nav group {g!r} belongs to no area" for g in free_groups]
        coverage += [f"[coverage] areas.md: page `{s}` belongs to no area" for s in free_pages]
        out.extend(coverage)
        checker.issues.update({("areas.md", "coverage", c, ""): 1 for c in coverage})
    stamp = re.search(r"Last updated: ([^\n]+)", mp)
    basis = (
        f"checked against {len(checker.live_heads)} live pages"
        if live
        else f"map stamp {stamp.group(1) if stamp else '?'} (use --live for page-level truth)"
    )
    out.append(
        f"\nselfcheck: {len(checker.slugs)} live pages | {checker.n_slug} slug refs and {checker.n_sec} section refs "
        f"in {len(present)} file(s) | {len(checker.issues)} issue(s) | {basis}",
    )
    if checker.issues:
        out.append("Fix the routing tables (or tell the user which lines to fix) before relying on them.")
    return "\n".join(out) + source_line(st.llms_url, st.map_url)


# --------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------


class _Args:
    """Typed view over argparse's untyped namespace."""

    def __init__(self, ns: argparse.Namespace) -> None:
        self._raw: dict[str, object] = dict(vars(ns))

    def str_(self, key: str) -> str:
        v = self._raw.get(key)
        if not isinstance(v, str):
            msg = f"internal: argument {key!r} missing"
            raise CcdocsError(msg)
        return v

    def opt_str(self, key: str) -> str | None:
        v = self._raw.get(key)
        return v if isinstance(v, str) else None

    def int_(self, key: str) -> int:
        v = self._raw.get(key)
        if not isinstance(v, int) or isinstance(v, bool):
            msg = f"internal: argument {key!r} is not an int"
            raise CcdocsError(msg)
        return v

    def float_(self, key: str) -> float:
        v = self._raw.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            msg = f"internal: argument {key!r} is not a number"
            raise CcdocsError(msg)
        return float(v)

    def bool_(self, key: str) -> bool:
        return self._raw.get(key) is True

    def strs(self, key: str) -> list[str]:
        v = self._raw.get(key)
        if v is None:
            return []
        if not isinstance(v, list):
            msg = f"internal: argument {key!r} is not a list"
            raise CcdocsError(msg)
        return [x for x in cast("list[object]", v) if isinstance(x, str)]


def _topic_query(a: _Args) -> TopicQuery:
    return TopicQuery(
        topic=tuple(a.strs("topic")),
        regex=a.opt_str("regex"),
        any_term=a.bool_("any"),
        seeds=tuple(a.strs("seed")),
        min_score=a.float_("min_score"),
        include_history=a.bool_("include_history"),
        follow_links=not a.bool_("no_follow_links"),
    )


def _research_query(a: _Args) -> ResearchQuery:
    sources = tuple(s.strip() for s in a.str_("source").split(",") if s.strip())
    bad = [s for s in sources if s not in SOURCES]
    if bad or not sources:
        msg = f"--source must be a comma list of {', '.join(SOURCES)}; got {a.str_('source')!r}"
        raise CcdocsError(msg)
    return ResearchQuery(
        phrases=tuple(a.strs("phrases")),
        regex=a.opt_str("regex"),
        sources=sources,
        months=a.int_("months"),
        pages=a.int_("pages"),
        follow=not a.bool_("no_follow"),
        out=a.opt_str("out"),
    )


COMMANDS: Final = (
    "research",
    "show",
    "url",
    "inventory",
    "find",
    "grep",
    "related",
    "dossier",
    "links",
    "quote",
    "index",
    "outline",
    "page",
    "changelog",
    "version",
    "whatsnew",
    "raw",
    "selfcheck",
    "catalog",
)


def _add_topic_parsers(add: _AddParser) -> None:
    for name in ("related", "dossier"):
        x = add(name)
        _ = x.add_argument("topic", nargs="*", help="topic phrase; plurals match (hooks ~ hook)")
        _ = x.add_argument("--regex", help="custom case-insensitive regex instead of topic words")
        _ = x.add_argument("--any", action="store_true", help="match ANY topic word instead of the phrase")
        _ = x.add_argument("--seed", action="append", help="core page slug (repeatable); default: auto")
        _ = x.add_argument("--min-score", type=float, default=3.0)
        _ = x.add_argument("--include-history", action="store_true", help="also score changelog/whats-new")
        _ = x.add_argument("--no-follow-links", action="store_true", help="don't add sections seed pages link to")
        if name == "related":
            _ = x.add_argument("--max", type=int, default=25, help="pages to list")
            _ = x.add_argument("--per-page", type=int, default=6)
            continue
        _ = x.add_argument("--budget", type=int, default=0, help="max chars of section text (0 = no limit)")
        _ = x.add_argument("--sections", type=int, default=60)
        _ = x.add_argument("--breadth-cap", type=int, default=4000, help="max chars per breadth-pass section")
        _ = x.add_argument("--breadth-min", type=float, default=8.0, help="min page score for a breadth section")
        _ = x.add_argument("--child-limit", type=int, default=8000, help="include subsections while under N chars")
        _ = x.add_argument("--no-children", action="store_true", help="exclude subsections")


def _add_research_parser(add: _AddParser) -> None:
    r = add("research")
    _ = r.add_argument("phrases", nargs="*", help='topic phrases; quote multi-word ones ("agent teams")')
    _ = r.add_argument("--regex", help="custom case-insensitive regex instead of phrases")
    _ = r.add_argument("--source", default="code,apps,platform", help="comma list of code, apps, platform")
    _ = r.add_argument("--months", type=int, default=6, help="changelog window")
    _ = r.add_argument("--pages", type=int, default=25, help="discovered pages read per source (routed always read)")
    _ = r.add_argument("--no-follow", action="store_true", help="don't follow hyperlinks out of the sections read")
    _ = r.add_argument("--out", help="folder for research runs (skill passes ${CLAUDE_PLUGIN_DATA}/research)")
    u = add("url")
    _ = u.add_argument("target", help="a docs MCP path (/en/hooks.mdx), a link, an old alias or a slug")
    _ = add("inventory")
    s = add("show")
    _ = s.add_argument("path")
    _ = s.add_argument("--out", help="the research folder root the file must be inside")


def _add_search_parsers(add: _AddParser) -> None:
    f = add("find")
    _ = f.add_argument("term", nargs="+")
    _ = f.add_argument("--max", type=int, default=40)
    g = add("grep")
    _ = g.add_argument("pattern")
    _ = g.add_argument("--slug", help="only pages whose slug matches this regex")
    _ = g.add_argument("--pages", action="store_true", help="list matching pages and hit counts only")
    _ = g.add_argument("--case", action="store_true", help="case-sensitive")
    _ = g.add_argument("--per-page", type=int, default=6)
    _ = g.add_argument("--max", type=int, default=60)
    lk = add("links")
    _ = lk.add_argument("slug")
    _ = lk.add_argument("--section")
    _ = lk.add_argument("--direction", choices=["in", "out", "both"], default="both")
    _ = lk.add_argument("--intra", action="store_true", help="include same-page anchor links")
    _ = lk.add_argument("--per-page", type=int, default=8)
    i = add("index")
    _ = i.add_argument("--grep")


def _add_page_parsers(add: _AddParser) -> None:
    qt = add("quote")
    _ = qt.add_argument("slug")
    _ = qt.add_argument("pattern")
    _ = qt.add_argument("--context", type=int, default=0, help="extra sentences around the match")
    _ = qt.add_argument("--max", type=int, default=5)
    o = add("outline")
    _ = o.add_argument("slug")
    _ = o.add_argument("--map", action="store_true", help="read the docs map instead of the live page")
    pg = add("page")
    _ = pg.add_argument("slug")
    grp = pg.add_mutually_exclusive_group()
    _ = grp.add_argument("--section")
    _ = grp.add_argument("--intro", action="store_true", help="only the text before the first heading")
    _ = pg.add_argument("--nth", type=int, default=1)
    _ = pg.add_argument("--max", type=int, default=60000)
    r = add("raw")
    _ = r.add_argument("url")
    _ = r.add_argument("--max", type=int, default=60000)


def _add_release_parsers(add: _AddParser) -> None:
    c = add("changelog")
    _ = c.add_argument("--last", type=int, default=5)
    _ = c.add_argument("--since")
    _ = c.add_argument("--grep")
    _ = add("version")
    w = add("whatsnew")
    _ = w.add_argument("--last", type=int, default=4)
    _ = add("catalog")
    sc = add("selfcheck")
    _ = sc.add_argument("--live", action="store_true", help="validate sections against live pages, not the docs map")


def build_parser() -> argparse.ArgumentParser:
    """The ccdocs argument parser."""
    p = argparse.ArgumentParser(
        prog="ccdocs.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _ = p.add_argument(
        "--no-anchor-check",
        action="store_true",
        help="don't read rendered pages; every anchor is reported unverified",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    added: list[str] = []

    def add(name: str) -> argparse.ArgumentParser:
        added.append(name)
        return sub.add_parser(name)

    for register in (
        _add_research_parser,
        _add_search_parsers,
        _add_topic_parsers,
        _add_page_parsers,
        _add_release_parsers,
    ):
        register(add)
    if sorted(added) != sorted(COMMANDS):
        msg = f"internal: parser commands {sorted(added)} != COMMANDS {sorted(COMMANDS)}"
        raise CcdocsError(msg)
    return p


def subcommand_names() -> set[str]:
    """Names of all subcommands (they appear backticked in the skill docs)."""
    return set(COMMANDS)


def dispatch(a: _Args) -> str:
    """Run the selected command and return its output."""
    cmd = a.str_("cmd")
    handlers: dict[str, Callable[[], str]] = {
        "research": lambda: cmd_research(_research_query(a)),
        "url": lambda: cmd_url(a.str_("target")),
        "inventory": cmd_inventory,
        "show": lambda: cmd_show(a.str_("path"), research_root(a.opt_str("out"))),
        "find": lambda: cmd_find(a.strs("term"), a.int_("max")),
        "grep": lambda: cmd_grep(
            a.str_("pattern"),
            GrepOptions(a.opt_str("slug"), a.bool_("pages"), a.bool_("case"), a.int_("per_page"), a.int_("max")),
        ),
        "related": lambda: cmd_related(_topic_query(a), max_pages=a.int_("max"), per_page=a.int_("per_page")),
        "dossier": lambda: cmd_dossier(
            _topic_query(a),
            DossierLimits(
                budget=a.int_("budget"),
                sections=a.int_("sections"),
                breadth_cap=a.int_("breadth_cap"),
                breadth_min=a.float_("breadth_min"),
                child_limit=a.int_("child_limit"),
                children=not a.bool_("no_children"),
            ),
        ),
        "links": lambda: cmd_links(
            a.str_("slug"),
            section=a.opt_str("section"),
            direction=a.str_("direction"),
            intra=a.bool_("intra"),
            per_page=a.int_("per_page"),
        ),
        "quote": lambda: cmd_quote(
            a.str_("slug"), a.str_("pattern"), context=a.int_("context"), max_hits=a.int_("max")
        ),
        "index": lambda: cmd_index(a.opt_str("grep")),
        "outline": lambda: cmd_outline(a.str_("slug"), use_map=a.bool_("map")),
        "page": lambda: cmd_page(
            a.str_("slug"),
            section=a.opt_str("section"),
            nth=a.int_("nth"),
            max_chars=a.int_("max"),
            intro=a.bool_("intro"),
        ),
        "changelog": lambda: cmd_changelog(last=a.int_("last"), since=a.opt_str("since"), grep=a.opt_str("grep")),
        "version": cmd_version,
        "catalog": cmd_catalog,
        "whatsnew": lambda: cmd_whatsnew(a.int_("last")),
        "raw": lambda: cmd_raw(a.str_("url"), a.int_("max")),
        "selfcheck": lambda: run_selfcheck(
            Path(__file__).resolve().parent.parent,
            live=a.bool_("live"),
            non_slugs=subcommand_names() | plugin_component_names(Path(__file__).resolve().parent.parent),
        ),
    }
    handler = handlers.get(cmd)
    if handler is None:
        msg = f"unknown command {cmd!r}"
        raise CcdocsError(msg)
    return handler()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit status."""
    parser = build_parser()
    a = _Args(parser.parse_args(argv))
    try:
        if a.bool_("no_anchor_check"):
            base = settings()
            use_settings(
                Settings(base.lang, base.ttl, base.corpus_ttl, base.anchor_ttl, base.cache_dir, verify_anchors=False)
            )
        text = dispatch(a)
    except CcdocsError as exc:
        _ = sys.stderr.write(f"ERROR {exc}\n")
        return 1
    _ = sys.stdout.write(text.rstrip("\n") + "\n")
    return 0


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        _ = signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped to head
    sys.exit(main())
