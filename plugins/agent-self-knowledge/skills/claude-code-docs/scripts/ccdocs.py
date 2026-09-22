#!/usr/bin/env python3
"""claude-code-docs - retrieve live, citable Claude Code documentation.

Stdlib only. Every command prints the source URL(s) it read so answers can cite them.

Commands
  find TERM...            Search the docs map (every page's heading tree) and print matching
                          headings with the page they belong to. Start here when unsure where
                          a topic lives.
  grep PATTERN            Regex search the full docs corpus (body text, not just headings) and
                          print each hit with its page and nearest heading. Use it when `find`
                          misses because the term lives in prose, a table or a code block
                          (env vars, setting keys, flags, error strings) - and before asserting
                          that something does not exist.
  index [--grep RE]       Print the llms.txt page index (title + slug + one-line summary).
  outline SLUG            Print the heading tree of one page (from the docs map).
  page SLUG [--section H] [--nth N] [--max N]
                          Print the raw markdown of a page, or only the section whose heading
                          contains H (case-insensitive), including its subsections. When several
                          headings match, it prints the first and lists the others - pick one
                          with --nth or a longer --section string.
  changelog [--last N] [--since VER] [--grep RE]
                          Release notes from the official CHANGELOG.md (GitHub raw).
  version                 Latest/stable/next on npm + locally installed `claude --version`,
                          and how many releases behind local is.
  whatsnew [--last N]     Weekly "What's new" digest entries.
  raw URL [--max N]       Fetch any URL as text (e.g. a GitHub raw file, schemastore).
  selfcheck               Validate every page slug and quoted section name in this skill's SKILL.md
                          and references/topic-routing.md against the live index and map.
                          Run it when the skill seems stale; it prints what moved.

SLUG examples: hooks, hooks-guide, sub-agents, agent-sdk/hooks, whats-new/2026-w37
Env: CCDOCS_LANG (default en), CCDOCS_CACHE_TTL seconds (default 900, 0 disables),
     CCDOCS_CORPUS_TTL seconds for the 9 MB full corpus used by `grep` (default 3600).
"""

# Everything above the version check must parse and run on old Pythons, so that an old
# `python3` prints the requirement instead of a SyntaxError or an ImportError.
from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING
import urllib.error
import urllib.request

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import IO, TypeIs

MIN_PYTHON = (3, 14)


def _require_python() -> None:
    """Exit with status 2 and a one-line explanation when the interpreter is too old."""
    if tuple(sys.version_info[:2]) >= MIN_PYTHON:
        return
    found = ".".join(str(part) for part in sys.version_info[:3])
    _ = sys.stderr.write(
        "".join(
            (
                "ccdocs.py needs Python 3.14 or later; ",
                f"this is python3 {found} at {sys.executable}. ",
                "Install Python 3.14 (python.org, brew install python@3.14, ",
                "or uv python install 3.14 --default) so `python3` is 3.14.\n",
            )
        )
    )
    sys.exit(2)


_require_python()

if hasattr(signal, "SIGPIPE"):
    _ = signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped to head

BASE = "https://code.claude.com/docs"
LANG = os.environ.get("CCDOCS_LANG", "en")
LLMS = f"{BASE}/llms.txt"
FULL = f"{BASE}/llms-full.txt"
MAP = f"{BASE}/{LANG}/claude_code_docs_map.md"
CHANGELOG_RAW = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
CHANGELOG_DOC = f"{BASE}/{LANG}/changelog"
NPM = "https://registry.npmjs.org/@anthropic-ai/claude-code"


def _env_seconds(name: str, raw: str | None, default: int) -> int:
    """Parse a non-negative number of seconds read from `name`, else the default."""
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = -1
    if value < 0:
        _ = sys.stderr.write(f"ccdocs.py: ignoring {name}={raw!r}; using {default} seconds\n")
        return default
    return value


def _positive_int(text: str) -> int:
    """Parse a 1-based index for argparse, refusing 0 and negatives with a clear message."""
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        message = f"expected a whole number of 1 or more, got {text!r}"
        raise argparse.ArgumentTypeError(message)
    return value


# Each variable is read by name here, so the README check (R6) sees every knob.
TTL = _env_seconds("CCDOCS_CACHE_TTL", os.environ.get("CCDOCS_CACHE_TTL"), 900)
CORPUS_TTL = _env_seconds("CCDOCS_CORPUS_TTL", os.environ.get("CCDOCS_CORPUS_TTL"), 3600)
# An empty XDG_CACHE_HOME means unset (XDG Base Directory spec), never the working directory.
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or str(Path("~/.cache").expanduser())) / "ccdocs"
UA = "ccdocs/1.1 (+claude-code-docs skill)"  # code.claude.com returns 403 without a User-Agent
ACCEPT = "text/markdown, text/plain, */*"
FETCH_TIMEOUT = 60
VERSION_TIMEOUT = 20
FRESH_SECONDS = 5  # a cache entry younger than this was written by the current run
MAX_OTHER_MATCHES = 8  # alternative headings listed when a --section is ambiguous
MAP_PAGE = r"^#{2,4} \[([^\]]+)\]\((https://[^)]+)\)"

# json.loads is annotated `-> Any`; this alias is the one place that Any becomes object, so no
# caller ever handles an Any-typed value.
_loads: Callable[[str], object] = json.loads
# OpenerDirector.open is annotated `-> Any` too; what it returns is a readable binary stream.
_open_url: Callable[[urllib.request.OpenerDirector, str, None, float], IO[bytes]] = (
    urllib.request.OpenerDirector.open
)

# Backticked words that live on routing lines but are not doc pages. Extend rather than
# widening the slug regex: a too-loose regex makes selfcheck noisy and people stop reading it.
NON_SLUGS = {
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
    "python3",
    "node",
    "npx",
    "env",
    "json",
    "yaml",
    "find",
    "index",
    "outline",
    "page",
    "changelog",
    "version",
    "whatsnew",
    "raw",
    "selfcheck",
    "latest",
    "stable",
    "next",
    "best",
    "opus",
    "sonnet",
    "haiku",
    "opusplan",
    "ultracode",
    "ultrareview",
    "v1",
    "claude-code-guide",
    "plugin-root",
    "pt-br",
    "zh-hant",
}


def _cache_key(url: str) -> Path:
    """Return the cache file for a URL (the hash only names a file; it protects nothing)."""
    return CACHE / hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()


def _read_cache(key: Path, ttl: int) -> str | None:
    """Return a fresh cache entry, or None when it is absent, stale, disabled or unreadable."""
    if ttl <= 0:
        return None
    try:
        fresh = time.time() - key.stat().st_mtime < ttl
        text = key.read_text(encoding="utf-8") if fresh else None
    except (OSError, UnicodeDecodeError):
        return None
    return text


def _write_cache(key: Path, text: str) -> None:
    """Store a cache entry atomically; a cache that cannot be written only loses caching."""
    tmp = key.with_name(f"{key.name}.{os.getpid()}.tmp")
    try:
        CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp.touch(mode=0o600)  # a cached page is readable by its owner only
        _ = tmp.write_text(text, encoding="utf-8")
        _ = tmp.replace(key)  # atomic: a killed run never leaves a half-written cache entry
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def _download(url: str) -> str:
    """Fetch a URL as text, exiting with a one-line error when it cannot be read."""
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", UA), ("Accept", ACCEPT)]
    try:
        with _open_url(opener, url, None, FETCH_TIMEOUT) as response:
            body = response.read()
    except urllib.error.HTTPError as e:
        sys.exit(
            "".join(
                (
                    f"ERROR {e.code} fetching {url} - page may have moved; ",
                    "run `ccdocs.py find <topic>` to relocate it.",
                )
            )
        )
    except (OSError, ValueError, http.client.HTTPException) as e:  # network / proxy / TLS
        sys.exit(f"ERROR fetching {url}: {e}")
    return body.decode("utf-8", "replace")


def fetch(url: str, ttl: int | None = None) -> str:
    """Return the text at a URL, from the cache when an entry is younger than the TTL."""
    ttl = TTL if ttl is None else ttl
    key = _cache_key(url)
    cached = _read_cache(key, ttl)
    if cached is not None:
        return cached
    text = _download(url)
    if ttl > 0:
        _write_cache(key, text)
    return text


def cache_age(url: str) -> str:
    """Describe how old the cached copy of a URL is."""
    try:
        age = int(time.time() - _cache_key(url).stat().st_mtime)
    except OSError:
        return "just fetched"
    return "just fetched" if age < FRESH_SECONDS else f"cached {age // 60}m{age % 60}s ago"


def page_url(slug: str) -> str:
    """Turn a slug, a docs URL or a `.md` path into the page's markdown URL."""
    slug = slug.strip().strip("/")
    slug = re.sub(r"^https?://code\.claude\.com/docs/[a-z-]+/", "", slug)
    slug = re.sub(r"\.mdx?$", "", slug).split("#")[0]
    return f"{BASE}/{LANG}/{slug}.md"


def anchor(heading: str) -> str:
    """Return the URL fragment the docs site gives a heading."""
    return "#" + re.sub(r"[^a-z0-9 /_-]", "", heading.lower()).strip().replace(" ", "-")


def src(*urls: str) -> None:
    """Print the SOURCE line that closes every command's output."""
    print(
        "\nSOURCE: "
        + " | ".join(u[:-3] if u.endswith(".md") and "/docs/" in u else u for u in urls)
    )


def _find_hits(text: str, pats: list[re.Pattern[str]]) -> list[tuple[tuple[str, str], str]]:
    """Return ((page name, page URL), heading) for every map entry matching all patterns."""
    page: tuple[str, str] | None = None
    hits: list[tuple[tuple[str, str], str]] = []
    for line in text.splitlines():
        m = re.match(MAP_PAGE, line)
        if m:
            page = (m.group(1), m.group(2))
            continue
        low = line.lower()
        if page and line.strip().startswith("*") and all(p.search(low) for p in pats):
            hits.append((page, line.strip("* ").strip()))
    # also match page names themselves
    for m in re.finditer(MAP_PAGE, text, re.MULTILINE):
        if all(p.search(m.group(1).lower()) for p in pats):
            hits.insert(0, ((m.group(1), m.group(2)), "(page)"))
    return hits


def cmd_find(term: list[str], limit: int) -> None:
    """Print the docs-map headings that contain every search term."""
    text = fetch(MAP)
    terms = [t.lower() for t in term]
    pats = [re.compile(r"(?<![a-z0-9])" + re.escape(t)) for t in terms]
    hits = _find_hits(text, pats)
    if not hits:
        print(
            f"No heading matches for {terms}. ",
            "The term may live in body text rather than a heading - ",
            f"try `ccdocs.py grep '{' '.join(terms)}'`, or `index --grep`.",
            sep="",
        )
    last = None
    for (name, url), h in hits[:limit]:
        if name != last:
            print(f"\n{name}  ->  {url[:-3]}")
            last = name
        print(f"   - {h}")
    if len(hits) > limit:
        print(f"\n... {len(hits) - limit} more; narrow the query.")
    src(MAP)


def iter_corpus(text: str) -> Iterator[tuple[str, str, str, str]]:
    """Yield (title, url, heading, line) for every line of llms-full.txt.

    A page starts with `# Title` immediately followed by `Source: <url>`; requiring both keeps
    `# comment` lines inside bash code blocks from being mistaken for a page boundary.
    """
    lines = text.splitlines()
    title, url, heading = "?", "", ""
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("# ") and i + 1 < n and lines[i + 1].startswith("Source: https://"):
            title, url, heading = line[2:].strip(), lines[i + 1][8:].strip(), ""
            i += 2
            continue
        m = re.match(r"^(#{2,6})\s+(.*)", line)
        if m:
            heading = m.group(2).strip()
        yield title, url, heading, line
        i += 1


@dataclass
class _PageHits:
    """The grep hits on one page: its title and each (heading, line) that matched."""

    title: str
    hits: list[tuple[str, str]] = field(default_factory=list)


def _grep_corpus(
    text: str, rx: re.Pattern[str], slug_rx: re.Pattern[str] | None
) -> dict[str, _PageHits]:
    """Group the corpus lines matching rx by page URL, in first-hit order."""
    per_page: dict[str, _PageHits] = {}
    for title, url, heading, line in iter_corpus(text):
        if slug_rx and not slug_rx.search(url):
            continue
        if not rx.search(line):
            continue
        if url not in per_page:
            per_page[url] = _PageHits(title)
        per_page[url].hits.append((heading, line.strip()))
    return per_page


@dataclass(frozen=True)
class GrepQuery:
    """The options of one `grep` run."""

    pattern: str
    slug: str | None
    pages: bool
    case: bool
    per_page: int
    limit: int


def _print_grep_hits(per_page: dict[str, _PageHits], q: GrepQuery) -> None:
    """Print the grep hits, pages with the most hits first."""
    shown = 0
    for url in sorted(per_page, key=lambda u: -len(per_page[u].hits)):
        title, hits = per_page[url].title, per_page[url].hits
        print(f"{url}  ({len(hits)} hit{'s' if len(hits) > 1 else ''})  - {title}")
        if q.pages:
            continue
        for heading, line in hits[: q.per_page]:
            print(f"   [{heading or 'intro'}] {line[:220]}")
            shown += 1
        if len(hits) > q.per_page:
            print(f"   ... {len(hits) - q.per_page} more on this page")
        print()
        if shown >= q.limit:
            print(f"... output capped at {q.limit} lines; narrow with --slug or a tighter pattern.")
            break


def cmd_grep(q: GrepQuery) -> None:
    """Regex-search the full docs corpus and print each hit with its page and heading."""
    text = fetch(FULL, CORPUS_TTL)
    pattern = q.pattern
    try:
        rx = re.compile(pattern, 0 if q.case else re.IGNORECASE)
    except re.error as e:
        sys.exit(f"ERROR bad regex {pattern!r}: {e}")
    slug_rx = re.compile(q.slug, re.IGNORECASE) if q.slug else None
    per_page = _grep_corpus(text, rx, slug_rx)
    total = sum(len(entry.hits) for entry in per_page.values())
    if total == 0:
        print(
            f"No match for {pattern!r} in the full docs corpus ({cache_age(FULL)}).\n",
            "That is real evidence of absence in the docs, ",
            "but not proof the feature is missing: ",
            "check `ccdocs.py changelog --grep <term> --last 40` ",
            "(the changelog can be ahead of the docs) ",
            "before telling the user it does not exist.",
            sep="",
        )
        src(FULL)
        return
    print(f"{total} match(es) across {len(per_page)} page(s) - corpus {cache_age(FULL)}\n")
    _print_grep_hits(per_page, q)
    src(FULL)


def cmd_index(grep: str | None) -> None:
    """Print the llms.txt page index, optionally filtered by a regex."""
    text = fetch(LLMS)
    rx = re.compile(grep, re.IGNORECASE) if grep else None
    n = 0
    for line in text.splitlines():
        if line.startswith("#") and not rx:
            print(line)
            continue
        m = re.match(
            r"^- \[([^\]]+)\]\(https://code\.claude\.com/docs/[a-z-]+/([^)]+)\.md\):?\s*(.*)", line
        )
        if m and (not rx or rx.search(line)):
            print(f"  {m.group(2):<42} {m.group(1)} - {m.group(3)[:140]}")
            n += 1
    if rx and n == 0:
        print(
            "No page title/summary matches; ",
            "try `find` (every heading) or `grep` (full text) instead.",
            sep="",
        )
    src(LLMS)


def cmd_outline(slug: str) -> None:
    """Print the heading tree of one page from the docs map."""
    text = fetch(MAP)
    slug = re.sub(r"\.md$", "", slug.strip("/"))
    out: list[str] = []
    on = False
    for line in text.splitlines():
        m = re.match(r"^#{2,4} \[[^\]]+\]\((https://[^)]+)\)", line)
        if m:
            on = m.group(1).endswith(f"/{slug}.md")
            if on:
                out.append(line)
            continue
        if line.startswith("## "):
            on = False
        if on and line.strip():
            out.append(line)
    print(
        "\n".join(out)
        if out
        else f"No page '{slug}' in the docs map. Use `find`, `grep` or `index --grep`."
    )
    src(MAP)


def headings_matching(md: str, needle: str) -> list[tuple[int, int, str]]:
    """Return [(line_index, level, heading_text)] for every heading containing needle.

    Headings inside fenced code blocks are skipped.
    """
    n, in_code = needle.lower(), False
    out: list[tuple[int, int, str]] = []
    for i, line in enumerate(md.splitlines()):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m and n in m.group(2).lower():
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def section_at(md: str, start: int, level: int) -> str:
    """Return the section starting at a heading line, up to the next heading of its level."""
    lines, in_code = md.splitlines(), False
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+", line)
        if m and len(m.group(1)) <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:])


def _pick_section(md: str, url: str, section: str, nth: int) -> tuple[str, str]:
    """Return (section markdown, heading) for the nth heading containing `section`."""
    matches = headings_matching(md, section)
    if not matches:
        heads = [line for line in md.splitlines() if re.match(r"^#{2,4} ", line)]
        sys.exit(
            f"Section '{section}' not found in {url}. Headings:\n"
            + "\n".join(heads)
            + f"\nSOURCE: {url}"
        )
    if nth > len(matches):
        sys.exit(
            f"--nth {nth} but only {len(matches)} heading(s) match '{section}' in {url}:\n"
            + "\n".join(f"  {i + 1}. {h}" for i, (_, _, h) in enumerate(matches))
        )
    i, level, head = matches[nth - 1]
    if len(matches) > 1:
        # Silently returning the first match is how you end up citing the generic section
        # when the user asked about a specific event/tool. Make the ambiguity visible.
        rest = [f"[{n + 1}] {h}" for n, (_, _, h) in enumerate(matches) if n != nth - 1]
        extra = len(rest) - MAX_OTHER_MATCHES
        others = ", ".join(rest[:MAX_OTHER_MATCHES]) + (f", +{extra} more" if extra > 0 else "")
        print(
            f"NOTE: {len(matches)} headings match '{section}'. ",
            f'Showing [{nth}] "{head}". ',
            f"Others: {others}. Re-run with --nth N or a longer --section string.\n",
            sep="",
        )
    return section_at(md, i, level), head


def cmd_page(slug: str, section: str | None, nth: int, limit: int) -> None:
    """Print a page's markdown, or one section of it."""
    url = page_url(slug)
    md = fetch(url)
    head = ""
    if section:
        md, head = _pick_section(md, url, section, nth)
    # collapse table padding: docs tables are space-padded to hundreds of columns
    md = "\n".join(
        re.sub(r"-{4,}", "---", re.sub(r" {2,}", " ", line))
        if line.lstrip().startswith("|")
        else line
        for line in md.splitlines()
    )
    if limit and len(md) > limit:
        md = md[:limit] + f"\n\n[... truncated at {limit} chars; use --section or --max 0]"
    print(md)
    src(url[:-3] + anchor(head) if head else url)


def vkey(v: str) -> tuple[int, ...] | None:
    """Return the first three numbers of a version string, or None when it has none."""
    parts: list[str] = re.findall(r"\d+", v)[:3]
    return tuple(int(x) for x in parts) if parts else None


def cmd_changelog(last: int, since_text: str | None, grep: str | None) -> None:
    """Print release notes from the upstream CHANGELOG.md."""
    text = fetch(CHANGELOG_RAW)
    blocks = re.split(r"(?m)^## ", text)[1:]
    rx = re.compile(grep, re.IGNORECASE) if grep else None
    since = vkey(since_text) if since_text else None
    if since_text and not since:
        sys.exit(f"ERROR --since {since_text!r} is not a version number (expected e.g. 2.1.270).")
    shown = 0
    for b in blocks:
        heading, _, body = b.partition("\n")
        ver = heading.strip()
        key = vkey(ver)
        if since and (key is None or key <= since):
            continue  # skip, don't break: never assume the file is perfectly ordered
        items = [line for line in body.splitlines() if line.strip()]
        if rx:
            items = [line for line in items if rx.search(line)]
            if not items:
                continue
        print(f"## {ver}\n" + "\n".join(items) + "\n")
        shown += 1
        if not since and shown >= last:
            break
    if shown == 0:
        print(
            "No matching entries."
            + (
                " Try a broader --grep, more --last, or `ccdocs.py grep` over the docs corpus."
                if rx
                else ""
            )
        )
    src(CHANGELOG_RAW, CHANGELOG_DOC)


def _is_mapping(value: object) -> TypeIs[dict[object, object]]:
    """Report whether a parsed JSON value is an object."""
    return isinstance(value, dict)


def _is_list(value: object) -> TypeIs[list[object]]:
    """Report whether a parsed value is a list."""
    return isinstance(value, list)


def _str_keyed(value: object) -> dict[str, object]:
    """Return the string-keyed entries of a parsed JSON object; empty for anything else."""
    if not _is_mapping(value):
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str)}


def _local_version(local: str) -> str | None:
    """Print and return `claude --version`, or print why it could not run and return None."""
    try:
        out = subprocess.run(
            [local, "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        print(f"local   (could not run claude --version: {e})")
        return None
    print(f"local   {out}")
    return out


def _print_gap(lkey: tuple[int, ...], latest: str) -> None:
    """Print how far the local build is from npm latest."""
    latest_key = vkey(latest)
    if latest_key is None:
        return
    if lkey < latest_key:
        headings: list[str] = re.findall(r"(?m)^## (.+)$", fetch(CHANGELOG_RAW))
        versions = [v.strip() for v in headings]
        behind = [v for v in versions if (vkey(v) or ()) > lkey]
        local = ".".join(map(str, lkey))
        print(
            f"gap     local is {len(behind)} release(s) behind latest ({latest}); ",
            f"features newer than {local} may not exist on this machine.\n",
            f"        `ccdocs.py changelog --since {local}` lists exactly what is missing.",
            sep="",
        )
    elif lkey > latest_key:
        print(
            f"gap     local is AHEAD of npm latest ({latest}) - ",
            "a `next`/nightly build; docs may not describe it yet.",
            sep="",
        )


def cmd_version() -> None:
    """Print the npm dist-tags, the local `claude --version` and the gap between them."""
    try:
        registry = _loads(fetch(NPM))
    except ValueError:
        sys.exit(f"ERROR: {NPM} did not return JSON; try again later.")
    d = _str_keyed(registry)
    tags = _str_keyed(d.get("dist-tags", {}))
    times = _str_keyed(d.get("time", {}))
    for t in ("latest", "stable", "next"):
        if t in tags:
            tag = tags[t]
            print(f"npm {t:<7} {tag:<12} published {times.get(str(tag), '?')}")
    local = shutil.which("claude")
    if not local:
        print(
            "local   claude not on PATH ",
            "(asking the user for `claude --version` is the only way to know their build)",
            sep="",
        )
        src(NPM, CHANGELOG_RAW)
        return
    out = _local_version(local)
    if out is None:
        src(NPM, CHANGELOG_RAW)
        return
    lkey, latest = vkey(out), tags.get("latest", "")
    if lkey:
        _print_gap(lkey, str(latest))
    src(NPM, CHANGELOG_RAW)


def cmd_whatsnew(last: int) -> None:
    """Print the newest entries of the weekly What's new digest."""
    url = f"{BASE}/{LANG}/whats-new/index.md"
    text = fetch(url)
    entries: list[tuple[str, str, str, str]] = re.findall(
        r"<Update label=\"([^\"]+)\" description=\"([^\"]+)\"([^>]*)>(.*?)</Update>",
        text,
        re.DOTALL,
    )
    if not entries:
        print(
            "No <Update> entries parsed - ",
            "the digest format may have changed; read the page directly:",
            sep="",
        )
        print(f"  ccdocs.py raw {url} --max 4000")
    for label, desc, attrs, body in entries[:last]:
        tm = re.search(r"tags=\{\[([^\]]*)\]\}", attrs)
        tags = "[" + tm.group(1) + "]" if tm else ""
        text_body = re.sub(r"\n\s+", "\n", body.strip())
        tags = tags.replace('"', "")
        print(f"### {label} ({desc}) {tags}\n{text_body}\n")
    src(url)


def cmd_raw(url: str, limit: int) -> None:
    """Print any URL as text."""
    t = fetch(url)
    print(t if not limit or len(t) <= limit else t[:limit] + f"\n[... truncated at {limit} chars]")
    src(url)


def bullets(text: str) -> Iterator[str]:
    """Yield routing bullets and table rows as single joined strings.

    Continuation lines are folded in, so a section list that wraps over three lines is still
    checked as one unit.
    """
    buf: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        starts = s.startswith(("- ", "* ", "|")) or re.match(r"^\d+\. ", s) is not None
        if starts:
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
    """Return every docs-map page slug with its lower-cased headings."""
    heads: dict[str, list[str]] = {}
    page = None
    for line in mp.splitlines():
        m = re.match(r"^#{2,4} \[[^\]]+\]\(https://code\.claude\.com/docs/en/([^)]+)\.md\)", line)
        if m:
            page = m.group(1)
            _ = heads.setdefault(page, [])
            continue
        if page and line.strip().startswith("*"):
            heads[page].append(line.strip("* ").strip().lower())
    return heads


@dataclass
class _Selfcheck:
    """What selfcheck knows about the live docs and what it has found so far."""

    slugs: set[str]
    heads: dict[str, list[str]]
    issues: dict[tuple[str, str, str, str], int] = field(default_factory=dict)
    slug_checked: int = 0
    sec_checked: int = 0

    def flag(self, key: tuple[str, str, str, str]) -> None:
        """Count one more occurrence of an issue."""
        self.issues[key] = self.issues.get(key, 0) + 1

    def check_section(self, name: str, quoted: str, current: str) -> None:
        """Check one quoted section name against the headings of the page named before it."""
        sec = " ".join(quoted.split()).lower().replace("`", "")
        if sec.endswith(("…", "...")):
            return
        self.sec_checked += 1
        if not any(sec in h.replace("`", "") for h in self.heads[current]):
            self.flag((name, "section", quoted, current))

    def check_unit(self, name: str, unit: str) -> None:
        """Check the slugs and quoted section names of one bullet, in document order."""
        current = None
        # walk backticked slugs and quoted section names in document order, so each quote is
        # checked against the page named closest before it
        for m in re.finditer(r"`([a-z0-9][a-z0-9-]*(?:/[a-z0-9-]+)*)`|\"([^\"]{3,80})\"", unit):
            t = m.group(1)
            if t:
                if t in NON_SLUGS:
                    continue
                self.slug_checked += 1
                if t in self.slugs:
                    current = t
                else:
                    current = None
                    self.flag((name, "slug", t, ""))
            elif current and current in self.heads:
                self.check_section(name, m.group(2), current)


def _print_issues(issues: dict[tuple[str, str, str, str], int]) -> None:
    """Print one line per selfcheck issue, sorted."""
    for (name, kind, what, pg), n in sorted(issues.items()):
        times = f" ({n}x)" if n > 1 else ""
        if kind == "slug":
            print(
                f"[slug] {name}: `{what}` is not a page in llms.txt{times} - ",
                f"run `ccdocs.py find {what.split('/')[-1]}`",
                sep="",
            )
        else:
            print(
                f'[section] {name}: "{what}" not found under `{pg}`{times} - ',
                f"run `ccdocs.py outline {pg}`",
                sep="",
            )


def cmd_selfcheck() -> None:
    """Check the skill's page slugs and quoted section names against the live docs."""
    root = Path(os.path.normpath(Path(__file__).absolute())).parent.parent
    candidates = [root / "SKILL.md", root / "references" / "topic-routing.md"]
    missing = [f for f in candidates if not f.exists()]
    files = [f for f in candidates if f.exists()]
    if not files:
        sys.exit(
            "".join(
                (
                    f"ERROR nothing to check under {root}. ",
                    "This script must sit at <skill>/scripts/ccdocs.py ",
                    "with SKILL.md and references/ beside it; ",
                    "a flattened copy breaks selfcheck and the\n",
                    "`Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *)` pre-approval rule.",
                )
            )
        )
    for f in missing:
        print(f"[layout] missing {os.path.relpath(f, root)} - expected at {f}")
    llms, mp = fetch(LLMS), fetch(MAP)
    check = _Selfcheck(
        slugs=set(re.findall(r"code\.claude\.com/docs/en/([^)\s]+?)\.md", llms)),
        heads=_map_headings(mp),
    )
    for f in files:
        for unit in bullets(f.read_text(encoding="utf-8")):
            check.check_unit(f.name, unit)
    _print_issues(check.issues)
    stamp_match = re.search(r"Last updated: ([^\n]+)", mp)
    stamp = stamp_match.group(1) if stamp_match else "?"
    print(
        f"\nselfcheck: {len(check.slugs)} live pages | {check.slug_checked} slug refs and ",
        f"{check.sec_checked} section refs checked in {len(files)} file(s) | ",
        f"{len(check.issues)} issue(s). Map stamp: {stamp}",
        sep="",
    )
    if check.issues:
        print(
            "Fix the routing tables (or tell the user which lines to fix) before relying on them."
        )
    src(LLMS, MAP)


class Args:
    """Typed access to the parsed command line; argparse itself types every value as Any."""

    def __init__(self, namespace: argparse.Namespace) -> None:
        """Keep the parsed values as `object`, to be narrowed on access."""
        self._values: dict[str, object] = vars(namespace)

    def text(self, name: str) -> str:
        """Return a required string argument."""
        value = self._values[name]
        if not isinstance(value, str):
            raise TypeError(name)
        return value

    def optional_text(self, name: str) -> str | None:
        """Return an optional string argument."""
        value = self._values[name]
        if value is not None and not isinstance(value, str):
            raise TypeError(name)
        return value

    def number(self, name: str) -> int:
        """Return an integer argument."""
        value = self._values[name]
        if not isinstance(value, int):
            raise TypeError(name)
        return value

    def flag(self, name: str) -> bool:
        """Return a store_true argument."""
        return self._values[name] is True

    def texts(self, name: str) -> list[str]:
        """Return a list-of-strings argument."""
        value = self._values[name]
        if not _is_list(value):
            raise TypeError(name)
        return [item for item in value if isinstance(item, str)]


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    s = p.add_subparsers(dest="cmd", required=True)
    f = s.add_parser("find")
    _ = f.add_argument("term", nargs="+")
    _ = f.add_argument("--max", type=int, default=40)
    gr = s.add_parser("grep")
    _ = gr.add_argument("pattern")
    _ = gr.add_argument("--slug", help="only pages whose URL matches this regex")
    _ = gr.add_argument(
        "--pages", action="store_true", help="list matching pages and hit counts only"
    )
    _ = gr.add_argument("--case", action="store_true", help="case-sensitive")
    _ = gr.add_argument("--per-page", type=int, default=6)
    _ = gr.add_argument("--max", type=int, default=60)
    i = s.add_parser("index")
    _ = i.add_argument("--grep")
    o = s.add_parser("outline")
    _ = o.add_argument("slug")
    g = s.add_parser("page")
    _ = g.add_argument("slug")
    _ = g.add_argument("--section")
    _ = g.add_argument("--nth", type=_positive_int, default=1)
    _ = g.add_argument("--max", type=int, default=60000)
    c = s.add_parser("changelog")
    _ = c.add_argument("--last", type=int, default=5)
    _ = c.add_argument("--since")
    _ = c.add_argument("--grep")
    _ = s.add_parser("version")
    w = s.add_parser("whatsnew")
    _ = w.add_argument("--last", type=int, default=4)
    _ = s.add_parser("selfcheck")
    r = s.add_parser("raw")
    _ = r.add_argument("url")
    _ = r.add_argument("--max", type=int, default=60000)
    return p


def main() -> None:
    """Parse the command line and run the chosen command."""
    a = Args(_parser().parse_args())
    commands: dict[str, Callable[[], None]] = {
        "find": lambda: cmd_find(a.texts("term"), a.number("max")),
        "grep": lambda: cmd_grep(
            GrepQuery(
                pattern=a.text("pattern"),
                slug=a.optional_text("slug"),
                pages=a.flag("pages"),
                case=a.flag("case"),
                per_page=a.number("per_page"),
                limit=a.number("max"),
            )
        ),
        "index": lambda: cmd_index(a.optional_text("grep")),
        "outline": lambda: cmd_outline(a.text("slug")),
        "page": lambda: cmd_page(
            a.text("slug"), a.optional_text("section"), a.number("nth"), a.number("max")
        ),
        "changelog": lambda: cmd_changelog(
            a.number("last"), a.optional_text("since"), a.optional_text("grep")
        ),
        "version": cmd_version,
        "whatsnew": lambda: cmd_whatsnew(a.number("last")),
        "selfcheck": cmd_selfcheck,
        "raw": lambda: cmd_raw(a.text("url"), a.number("max")),
    }
    commands[a.text("cmd")]()


if __name__ == "__main__":
    main()
