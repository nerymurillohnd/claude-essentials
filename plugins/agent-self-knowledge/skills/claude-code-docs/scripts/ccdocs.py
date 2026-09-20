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
                          and references/topic-routing.md against the live index and map. Run it when
                          the skill seems stale; it prints what moved.

SLUG examples: hooks, hooks-guide, sub-agents, agent-sdk/hooks, whats-new/2026-w37
Env: CCDOCS_LANG (default en), CCDOCS_CACHE_TTL seconds (default 900, 0 disables),
     CCDOCS_CORPUS_TTL seconds for the 9 MB full corpus used by `grep` (default 3600).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped to head

BASE = "https://code.claude.com/docs"
LANG = os.environ.get("CCDOCS_LANG", "en")
LLMS = f"{BASE}/llms.txt"
FULL = f"{BASE}/llms-full.txt"
MAP = f"{BASE}/{LANG}/claude_code_docs_map.md"
CHANGELOG_RAW = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
CHANGELOG_DOC = f"{BASE}/{LANG}/changelog"
NPM = "https://registry.npmjs.org/@anthropic-ai/claude-code"
TTL = int(os.environ.get("CCDOCS_CACHE_TTL", "900"))
CORPUS_TTL = int(os.environ.get("CCDOCS_CORPUS_TTL", "3600"))
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "ccdocs")
UA = "ccdocs/1.1 (+claude-code-docs skill)"  # code.claude.com returns 403 without a User-Agent

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


def fetch(url: str, ttl: int = None) -> str:
    ttl = TTL if ttl is None else ttl
    key = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
    if ttl > 0 and os.path.exists(key) and time.time() - os.path.getmtime(key) < ttl:
        with open(key, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "text/markdown, text/plain, */*"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        sys.exit(
            f"ERROR {e.code} fetching {url} - page may have moved; run `ccdocs.py find <topic>` to relocate it."
        )
    except Exception as e:  # network / proxy / TLS
        sys.exit(f"ERROR fetching {url}: {e}")
    if ttl > 0:
        os.makedirs(CACHE, exist_ok=True)
        tmp = key + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, key)  # atomic: a killed run never leaves a half-written cache entry
    return text


def cache_age(url: str) -> str:
    key = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
    if not os.path.exists(key):
        return "just fetched"
    age = int(time.time() - os.path.getmtime(key))
    return "just fetched" if age < 5 else f"cached {age // 60}m{age % 60}s ago"


def page_url(slug: str) -> str:
    slug = slug.strip().strip("/")
    slug = re.sub(r"^https?://code\.claude\.com/docs/[a-z-]+/", "", slug)
    slug = re.sub(r"\.mdx?$", "", slug).split("#")[0]
    return f"{BASE}/{LANG}/{slug}.md"


def anchor(heading: str) -> str:
    return "#" + re.sub(r"[^a-z0-9 /_-]", "", heading.lower()).strip().replace(" ", "-")


def src(*urls):
    print(
        "\nSOURCE: "
        + " | ".join(u[:-3] if u.endswith(".md") and "/docs/" in u else u for u in urls)
    )


def cmd_find(a):
    text = fetch(MAP)
    terms = [t.lower() for t in a.term]
    pats = [re.compile(r"(?<![a-z0-9])" + re.escape(t)) for t in terms]
    page, hits = None, []
    for line in text.splitlines():
        m = re.match(r"^#{2,4} \[([^\]]+)\]\((https://[^)]+)\)", line)
        if m:
            page = (m.group(1), m.group(2))
            continue
        low = line.lower()
        if page and line.strip().startswith("*") and all(p.search(low) for p in pats):
            hits.append((page, line.strip("* ").strip()))
    # also match page names themselves
    for m in re.finditer(r"^#{2,4} \[([^\]]+)\]\((https://[^)]+)\)", text, re.MULTILINE):
        if all(p.search(m.group(1).lower()) for p in pats):
            hits.insert(0, ((m.group(1), m.group(2)), "(page)"))
    if not hits:
        print(
            f"No heading matches for {terms}. The term may live in body text rather than a heading - "
            f"try `ccdocs.py grep '{' '.join(terms)}'`, or `index --grep`."
        )
    last = None
    for (name, url), h in hits[: a.max]:
        if name != last:
            print(f"\n{name}  ->  {url[:-3]}")
            last = name
        print(f"   - {h}")
    if len(hits) > a.max:
        print(f"\n... {len(hits) - a.max} more; narrow the query.")
    src(MAP)


def iter_corpus(text):
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


def cmd_grep(a):
    text = fetch(FULL, CORPUS_TTL)
    try:
        rx = re.compile(a.pattern, 0 if a.case else re.IGNORECASE)
    except re.error as e:
        sys.exit(f"ERROR bad regex {a.pattern!r}: {e}")
    slug_rx = re.compile(a.slug, re.IGNORECASE) if a.slug else None
    per_page, order, total = {}, [], 0
    for title, url, heading, line in iter_corpus(text):
        if slug_rx and not slug_rx.search(url):
            continue
        if not rx.search(line):
            continue
        total += 1
        if url not in per_page:
            per_page[url] = (title, [])
            order.append(url)
        per_page[url][1].append((heading, line.strip()))
    if total == 0:
        print(
            f"No match for {a.pattern!r} in the full docs corpus ({cache_age(FULL)}).\n"
            f"That is real evidence of absence in the docs, but not proof the feature is missing: "
            f"check `ccdocs.py changelog --grep <term> --last 40` (the changelog can be ahead of the docs) "
            f"before telling the user it does not exist."
        )
        src(FULL)
        return
    print(f"{total} match(es) across {len(per_page)} page(s) - corpus {cache_age(FULL)}\n")
    shown = 0
    for url in sorted(order, key=lambda u: -len(per_page[u][1])):
        title, hits = per_page[url]
        print(f"{url}  ({len(hits)} hit{'s' if len(hits) > 1 else ''})  - {title}")
        if a.pages:
            continue
        for heading, line in hits[: a.per_page]:
            print(f"   [{heading or 'intro'}] {line[:220]}")
            shown += 1
        if len(hits) > a.per_page:
            print(f"   ... {len(hits) - a.per_page} more on this page")
        print()
        if shown >= a.max:
            print(f"... output capped at {a.max} lines; narrow with --slug or a tighter pattern.")
            break
    src(FULL)


def cmd_index(a):
    text = fetch(LLMS)
    rx = re.compile(a.grep, re.IGNORECASE) if a.grep else None
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
            "No page title/summary matches; try `find` (every heading) or `grep` (full text) instead."
        )
    src(LLMS)


def cmd_outline(a):
    text = fetch(MAP)
    slug = re.sub(r"\.md$", "", a.slug.strip("/"))
    out, on = [], False
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


def headings_matching(md: str, needle: str):
    """Return [(line_index, level, heading_text)] for every heading containing needle, skipping code blocks."""
    n, in_code, out = needle.lower(), False, []
    for i, l in enumerate(md.splitlines()):
        if l.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", l)
        if m and n in m.group(2).lower():
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def section_at(md: str, start: int, level: int) -> str:
    lines, in_code = md.splitlines(), False
    for i in range(start + 1, len(lines)):
        l = lines[i]
        if l.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+", l)
        if m and len(m.group(1)) <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:])


def cmd_page(a):
    url = page_url(a.slug)
    md = fetch(url)
    head = ""
    if a.section:
        matches = headings_matching(md, a.section)
        if not matches:
            heads = [l for l in md.splitlines() if re.match(r"^#{2,4} ", l)]
            sys.exit(
                f"Section '{a.section}' not found in {url}. Headings:\n"
                + "\n".join(heads)
                + f"\nSOURCE: {url}"
            )
        if a.nth > len(matches):
            sys.exit(
                f"--nth {a.nth} but only {len(matches)} heading(s) match '{a.section}' in {url}:\n"
                + "\n".join(f"  {i + 1}. {h}" for i, (_, _, h) in enumerate(matches))
            )
        i, level, head = matches[a.nth - 1]
        if len(matches) > 1:
            # Silently returning the first match is how you end up citing the generic section
            # when the user asked about a specific event/tool. Make the ambiguity visible.
            rest = [f"[{n + 1}] {h}" for n, (_, _, h) in enumerate(matches) if n != a.nth - 1]
            others = ", ".join(rest[:8]) + (f", +{len(rest) - 8} more" if len(rest) > 8 else "")
            print(
                f"NOTE: {len(matches)} headings match '{a.section}'. Showing [{a.nth}] \"{head}\". "
                f"Others: {others}. Re-run with --nth N or a longer --section string.\n"
            )
        md = section_at(md, i, level)
    # collapse table padding: docs tables are space-padded to hundreds of columns
    md = "\n".join(
        re.sub(r"-{4,}", "---", re.sub(r" {2,}", " ", l)) if l.lstrip().startswith("|") else l
        for l in md.splitlines()
    )
    if a.max and len(md) > a.max:
        md = md[: a.max] + f"\n\n[... truncated at {a.max} chars; use --section or --max 0]"
    print(md)
    src(url[:-3] + anchor(head) if head else url)


def vkey(v):
    parts = re.findall(r"\d+", v)[:3]
    return tuple(int(x) for x in parts) if parts else None


def cmd_changelog(a):
    text = fetch(CHANGELOG_RAW)
    blocks = re.split(r"(?m)^## ", text)[1:]
    rx = re.compile(a.grep, re.IGNORECASE) if a.grep else None
    since = vkey(a.since) if a.since else None
    if a.since and not since:
        sys.exit(f"ERROR --since {a.since!r} is not a version number (expected e.g. 2.1.270).")
    shown = 0
    for b in blocks:
        ver, _, body = b.partition("\n")
        ver = ver.strip()
        key = vkey(ver)
        if since and (key is None or key <= since):
            continue  # skip, don't break: never assume the file is perfectly ordered
        items = [l for l in body.splitlines() if l.strip()]
        if rx:
            items = [l for l in items if rx.search(l)]
            if not items:
                continue
        print(f"## {ver}\n" + "\n".join(items) + "\n")
        shown += 1
        if not since and shown >= a.last:
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


def cmd_version(a):
    d = json.loads(fetch(NPM))
    tags = d.get("dist-tags", {})
    for t in ("latest", "stable", "next"):
        if t in tags:
            print(f"npm {t:<7} {tags[t]:<12} published {d.get('time', {}).get(tags[t], '?')}")
    local = shutil.which("claude")
    if not local:
        print(
            "local   claude not on PATH (asking the user for `claude --version` is the only way to know their build)"
        )
        src(NPM, CHANGELOG_RAW)
        return
    try:
        out = subprocess.run(
            [local, "--version"], capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception as e:
        print(f"local   (could not run claude --version: {e})")
        src(NPM, CHANGELOG_RAW)
        return
    print(f"local   {out}")
    lkey, latest = vkey(out), tags.get("latest", "")
    if lkey and vkey(latest) and lkey < vkey(latest):
        versions = [v.strip() for v in re.findall(r"(?m)^## (.+)$", fetch(CHANGELOG_RAW))]
        behind = [v for v in versions if vkey(v) and vkey(v) > lkey]
        print(
            f"gap     local is {len(behind)} release(s) behind latest ({latest}); "
            f"features newer than {'.'.join(map(str, lkey))} may not exist on this machine.\n"
            f"        `ccdocs.py changelog --since {'.'.join(map(str, lkey))}` lists exactly what is missing."
        )
    elif lkey and vkey(latest) and lkey > vkey(latest):
        print(
            f"gap     local is AHEAD of npm latest ({latest}) - a `next`/nightly build; docs may not describe it yet."
        )
    src(NPM, CHANGELOG_RAW)


def cmd_whatsnew(a):
    url = f"{BASE}/{LANG}/whats-new/index.md"
    text = fetch(url)
    entries = re.findall(
        r"<Update label=\"([^\"]+)\" description=\"([^\"]+)\"([^>]*)>(.*?)</Update>",
        text,
        re.DOTALL,
    )
    if not entries:
        print(
            "No <Update> entries parsed - the digest format may have changed; read the page directly:"
        )
        print(f"  ccdocs.py raw {url} --max 4000")
    for label, desc, attrs, body in entries[: a.last]:
        tm = re.search(r"tags=\{\[([^\]]*)\]\}", attrs)
        tags = "[" + tm.group(1) + "]" if tm else ""
        body = re.sub(r"\n\s+", "\n", body.strip())
        tags = tags.replace('"', "")
        print(f"### {label} ({desc}) {tags}\n{body}\n")
    src(url)


def cmd_raw(a):
    t = fetch(a.url)
    print(t if not a.max or len(t) <= a.max else t[: a.max] + f"\n[... truncated at {a.max} chars]")
    src(a.url)


def bullets(text):
    """Yield routing bullets and table rows as single joined strings (continuation lines folded in),
    so a section list that wraps over three lines is still checked as one unit.
    """
    buf = []
    for line in text.splitlines():
        s = line.strip()
        starts = s.startswith(("- ", "* ", "|")) or re.match(r"^\d+\. ", s)
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


def cmd_selfcheck(a):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [os.path.join(root, "SKILL.md"), os.path.join(root, "references", "topic-routing.md")]
    missing = [f for f in files if not os.path.exists(f)]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        sys.exit(
            f"ERROR nothing to check under {root}. This script must sit at <skill>/scripts/ccdocs.py "
            f"with SKILL.md and references/ beside it; a flattened copy breaks selfcheck and the\n"
            f"`Bash(python3 ${{CLAUDE_SKILL_DIR}}/scripts/ccdocs.py *)` pre-approval rule."
        )
    for f in missing:
        print(f"[layout] missing {os.path.relpath(f, root)} - expected at {f}")
    llms, mp = fetch(LLMS), fetch(MAP)
    slugs = set(re.findall(r"code\.claude\.com/docs/en/([^)\s]+?)\.md", llms))
    heads, page = {}, None
    for line in mp.splitlines():
        m = re.match(r"^#{2,4} \[[^\]]+\]\(https://code\.claude\.com/docs/en/([^)]+)\.md\)", line)
        if m:
            page = m.group(1)
            heads.setdefault(page, [])
            continue
        if page and line.strip().startswith("*"):
            heads[page].append(line.strip("* ").strip().lower())
    issues, slug_checked, sec_checked = {}, 0, 0
    for f in files:
        name = os.path.basename(f)
        text = open(f, encoding="utf-8").read()
        for unit in bullets(text):
            current = None
            # walk backticked slugs and quoted section names in document order, so each quote is
            # checked against the page named closest before it
            for m in re.finditer(r"`([a-z0-9][a-z0-9-]*(?:/[a-z0-9-]+)*)`|\"([^\"]{3,80})\"", unit):
                if m.group(1):
                    t = m.group(1)
                    if t in NON_SLUGS:
                        continue
                    slug_checked += 1
                    if t in slugs:
                        current = t
                    else:
                        current = None
                        issues[(name, "slug", t, "")] = issues.get((name, "slug", t, ""), 0) + 1
                elif current and current in heads:
                    sec = " ".join(m.group(2).split()).lower().replace("`", "")
                    if sec.endswith(("…", "...")):
                        continue
                    sec_checked += 1
                    if not any(sec in h.replace("`", "") for h in heads[current]):
                        k = (name, "section", m.group(2), current)
                        issues[k] = issues.get(k, 0) + 1
    for (name, kind, what, pg), n in sorted(issues.items()):
        times = f" ({n}x)" if n > 1 else ""
        if kind == "slug":
            print(
                f"[slug] {name}: `{what}` is not a page in llms.txt{times} - run `ccdocs.py find {what.split('/')[-1]}`"
            )
        else:
            print(
                f'[section] {name}: "{what}" not found under `{pg}`{times} - run `ccdocs.py outline {pg}`'
            )
    stamp = (re.search(r"Last updated: ([^\n]+)", mp) or [None, "?"])[1]
    print(
        f"\nselfcheck: {len(slugs)} live pages | {slug_checked} slug refs and {sec_checked} section refs checked "
        f"in {len(files)} file(s) | {len(issues)} issue(s). Map stamp: {stamp}"
    )
    if issues:
        print(
            "Fix the routing tables (or tell the user which lines to fix) before relying on them."
        )
    src(LLMS, MAP)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    s = p.add_subparsers(dest="cmd", required=True)
    f = s.add_parser("find")
    f.add_argument("term", nargs="+")
    f.add_argument("--max", type=int, default=40)
    f.set_defaults(fn=cmd_find)
    gr = s.add_parser("grep")
    gr.add_argument("pattern")
    gr.add_argument("--slug", help="only pages whose URL matches this regex")
    gr.add_argument("--pages", action="store_true", help="list matching pages and hit counts only")
    gr.add_argument("--case", action="store_true", help="case-sensitive")
    gr.add_argument("--per-page", type=int, default=6)
    gr.add_argument("--max", type=int, default=60)
    gr.set_defaults(fn=cmd_grep)
    i = s.add_parser("index")
    i.add_argument("--grep")
    i.set_defaults(fn=cmd_index)
    o = s.add_parser("outline")
    o.add_argument("slug")
    o.set_defaults(fn=cmd_outline)
    g = s.add_parser("page")
    g.add_argument("slug")
    g.add_argument("--section")
    g.add_argument("--nth", type=int, default=1)
    g.add_argument("--max", type=int, default=60000)
    g.set_defaults(fn=cmd_page)
    c = s.add_parser("changelog")
    c.add_argument("--last", type=int, default=5)
    c.add_argument("--since")
    c.add_argument("--grep")
    c.set_defaults(fn=cmd_changelog)
    v = s.add_parser("version")
    v.set_defaults(fn=cmd_version)
    w = s.add_parser("whatsnew")
    w.add_argument("--last", type=int, default=4)
    w.set_defaults(fn=cmd_whatsnew)
    sc = s.add_parser("selfcheck")
    sc.set_defaults(fn=cmd_selfcheck)
    r = s.add_parser("raw")
    r.add_argument("url")
    r.add_argument("--max", type=int, default=60000)
    r.set_defaults(fn=cmd_raw)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
