"""Plugin workflows: W1, the one invariant over `plugins/*/workflows/*.js`.

A workflow is JavaScript that Claude Code compiles and runs, so it is checked by V8 and not
by a Python approximation (P12). Four things are proved here, in order, because each one
only makes sense if the previous one held:

1. `meta` is a pure literal, so reading it never runs code.
2. Every phase title the body uses is declared in `meta.phases`.
3. The body compiles as `new AsyncFunction(...globals, body)`, the shape the runtime uses.
4. The orchestration runs to completion against a stub runtime that records every call.

The stub returns a value synthesised from each `agent` call's own JSON schema, so a body
that reads the fields it asked for keeps working without any fixture per workflow.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.javascript import JavaScriptError, literal, run, run_async
from scripts.common.jsontext import is_json_array, is_json_object

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

WORKFLOW_GLOBALS: Final[tuple[str, ...]] = (
    "agent",
    "parallel",
    "pipeline",
    "phase",
    "log",
    "console",
    "args",
)
"""The names the dynamic-workflow runtime binds, in the order the stub runner passes them."""

META_EXPORT: Final = re.compile(r"export\s+const\s+meta\s*=\s*")
"""The statement that opens a workflow's metadata literal."""

PHASE_CALL: Final = re.compile(r"""\bphase\s*\(\s*(?P<quote>["'`])(?P<title>[^"'`]*)(?P=quote)""")
"""A `phase("Title")` call in the body."""

PHASE_OPTION: Final = re.compile(r"""\bphase\s*:\s*(?P<quote>["'`])(?P<title>[^"'`]*)(?P=quote)""")
"""A `phase: "Title"` option passed to `agent`."""

DYNAMIC_IMPORT: Final = re.compile(r"\bimport\s*\(")
"""A dynamic import, which a workflow may not use."""

IMPURE_TOKEN: Final = re.compile(r"[`(]|=>|\.\.\.")
"""Syntax a pure object literal never needs: a call, a template literal or a spread."""

IDENTIFIER: Final = re.compile(r"(?<![\w$.])[A-Za-z_$][\w$]*")
"""A bare word in the metadata literal, once string contents have been removed."""

LITERAL_WORDS: Final[frozenset[str]] = frozenset({"true", "false", "null"})
"""The only bare words a pure JSON-shaped literal may contain outside a key position."""

QUOTES: Final[frozenset[str]] = frozenset({'"', "'", "`"})
"""The three characters that open a JavaScript string literal."""

STRING_LITERAL: Final = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
"""A quoted string, removed before the identifier scan so its words are not read as code."""

STUB_RUNTIME: Final = """
const calls = [];
function record(kind, payload) { calls.push({ kind: kind, payload: payload }); }
function synth(schema) {
  if (!schema || typeof schema !== "object") { return null; }
  if (Array.isArray(schema.enum) && schema.enum.length > 0) { return schema.enum[0]; }
  if (schema.type === "object") {
    const out = {};
    const props = schema.properties || {};
    Object.keys(props).forEach(function (key) { out[key] = synth(props[key]); });
    (schema.required || []).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(out, key)) { out[key] = null; }
    });
    return out;
  }
  if (schema.type === "array") { return [synth(schema.items)]; }
  if (schema.type === "string") { return "stub"; }
  if (schema.type === "integer" || schema.type === "number") {
    return typeof schema.minimum === "number" ? schema.minimum : 1;
  }
  if (schema.type === "boolean") { return false; }
  return null;
}
function agent(prompt, options) {
  const opts = options || {};
  record("agent", {
    label: opts.label || null,
    phase: opts.phase || null,
    agentType: opts.agentType || null
  });
  return Promise.resolve(opts.schema ? synth(opts.schema) : { text: "stub" });
}
function parallel(items) {
  const list = Array.isArray(items) ? items : [];
  return Promise.all(list.map(function (item) {
    return typeof item === "function" ? item() : item;
  }));
}
async function pipeline(items, first, second) {
  const list = Array.isArray(items) ? items : [];
  const stage = await Promise.all(list.map(function (item, index) { return first(item, index); }));
  if (typeof second !== "function") { return stage; }
  return await Promise.all(stage.map(function (value, index) {
    return second(value, list[index], index);
  }));
}
function phase(title) { record("phase", { title: title }); }
function log(message) { record("log", { message: String(message) }); }
const console = { log: log, warn: log, error: log, info: log };
const args = { requirement: "stub requirement", scope: "stub scope", commands: ["stub check"] };
"""
"""The runtime the orchestration runs against: every call is recorded, nothing is spawned."""


def meta_source(text: str) -> str | None:
    """Extract the text of a workflow's `meta` object literal.

    Args:
        text: The module source.

    Returns:
        The literal, braces included, or None when the export is absent or unbalanced.
    """
    match = META_EXPORT.search(text)
    if match is None:
        return None
    start = text.find("{", match.end())
    if start == -1:
        return None
    end = _matching_brace(text, start)
    return None if end is None else text[start : end + 1]


def _matching_brace(text: str, start: int) -> int | None:
    """Find the index of the brace that closes the one at `start`.

    String contents are skipped, so a brace inside a description does not unbalance it.

    Args:
        text: The module source.
        start: Index of the opening brace.

    Returns:
        The closing brace's index, or None when there is none.
    """
    depth = 0
    index = start
    while index < len(text):
        character = text[index]
        if character in QUOTES:
            index = _skip_string(text, index)
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _skip_string(text: str, start: int) -> int:
    """Return the index just past the string literal that opens at `start`.

    Args:
        text: The module source.
        start: Index of the opening quote.

    Returns:
        The index after the closing quote, or the end of the text when it is unterminated.
    """
    quote = text[start]
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == quote:
            return index + 1
        index += 1
    return index


def body_source(text: str, meta: str) -> str:
    """Return the module source with the `meta` export removed.

    `export` is a module-level statement and cannot appear inside a function body, so the
    metadata is taken out before the body is compiled the way the runtime compiles it.

    Args:
        text: The module source.
        meta: The metadata literal, as `meta_source` returned it.

    Returns:
        The remaining source.
    """
    match = META_EXPORT.search(text)
    if match is None:
        return text
    end = text.find(meta, match.end()) + len(meta)
    tail = text[end:].lstrip(";")
    return text[: match.start()] + tail


def _impurity(meta: str) -> str | None:
    """Report the first reason a metadata literal is not pure data.

    Args:
        meta: The literal's text.

    Returns:
        A description of the impurity, or None when the literal is pure.
    """
    without_strings = STRING_LITERAL.sub('""', meta)
    token = IMPURE_TOKEN.search(without_strings)
    if token is not None:
        return f"it uses {token.group(0)!r}, which a pure literal never needs"
    for match in IDENTIFIER.finditer(without_strings):
        after = without_strings[match.end() :].lstrip()
        if after.startswith(":") or match.group(0) in LITERAL_WORDS:
            continue
        return f"it reads the identifier {match.group(0)!r}"
    return None


def check_meta(rel: str, text: str) -> tuple[list[Finding], list[str]]:
    """Check that `meta` is a pure literal and read the phase titles it declares (W1).

    Args:
        rel: The file's repository-relative path.
        text: The module source.

    Returns:
        Every finding, and the declared phase titles.
    """
    meta = meta_source(text)
    if meta is None:
        return [Finding("W1", rel, "no `export const meta = { … }` with a balanced literal")], []
    impurity = _impurity(meta)
    if impurity is not None:
        return [Finding("W1", rel, f"`meta` is not a pure literal: {impurity}")], []
    value, error = run(f"return ({meta});")
    if error is not None:
        return [Finding("W1", rel, f"`meta` does not evaluate: {error}")], []
    if not is_json_object(value):
        return [Finding("W1", rel, "`meta` does not evaluate to an object")], []
    return [], _phase_titles(value.get("phases"))


def _phase_titles(phases: object) -> list[str]:
    """Read the `title` of every declared phase.

    Args:
        phases: The value of `meta.phases`.

    Returns:
        The titles, in declaration order.
    """
    if not is_json_array(phases):
        return []
    titles: list[str] = []
    for entry in phases:
        if not is_json_object(entry):
            continue
        title = entry.get("title")
        if isinstance(title, str):
            titles.append(title)
    return titles


def used_phases(body: str) -> list[str]:
    """List the phase titles a body names, in either of the two forms the runtime accepts.

    Args:
        body: The module source without the metadata export.

    Returns:
        The titles, sorted and deduplicated.
    """
    titles = {match.group("title") for match in PHASE_CALL.finditer(body)}
    titles |= {match.group("title") for match in PHASE_OPTION.finditer(body)}
    return sorted(titles)


def check_phases(rel: str, body: str, declared: Sequence[str]) -> list[Finding]:
    """Check that every phase the body names is declared in `meta.phases` (W1).

    Args:
        rel: The file's repository-relative path.
        body: The module source without the metadata export.
        declared: The declared titles.

    Returns:
        One finding per undeclared title.
    """
    return [
        Finding("W1", rel, f"phase {title!r} is used but not declared in `meta.phases`")
        for title in used_phases(body)
        if title not in declared
    ]


def check_imports(rel: str, body: str) -> list[Finding]:
    """Check that the body uses no dynamic import (W1).

    Args:
        rel: The file's repository-relative path.
        body: The module source without the metadata export.

    Returns:
        One finding when `import(` appears.
    """
    if DYNAMIC_IMPORT.search(body) is None:
        return []
    return [
        Finding("W1", rel, "the body uses `import(`, which the workflow runtime does not provide")
    ]


def check_runs(rel: str, body: str) -> list[Finding]:
    """Compile the body and run it against the stub runtime (W1).

    Args:
        rel: The file's repository-relative path.
        body: The module source without the metadata export.

    Returns:
        One finding when V8 refuses the body or the orchestration throws.
    """
    names = ", ".join(WORKFLOW_GLOBALS)
    parameters = literal(",".join(WORKFLOW_GLOBALS))
    source = (
        f"{STUB_RUNTIME}\n"
        "const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;\n"
        f"const workflow = new AsyncFunction({parameters}, {literal(body)});\n"
        f"const value = await workflow({names});\n"
        "return { calls: calls, result: value === undefined ? null : value };"
    )
    try:
        outcome, error = run_async(source)
    except JavaScriptError as failure:
        return [Finding("W1", rel, f"the body does not compile under V8: {failure}")]
    if error is not None:
        return [Finding("W1", rel, f"the orchestration failed against the stub runtime: {error}")]
    if not is_json_object(outcome):
        return [Finding("W1", rel, "the stub run returned no record of its calls")]
    return []


def check_workflow(root: Path, rel: str) -> list[Finding]:
    """Run W1 over one workflow file.

    Args:
        root: The repository root.
        rel: The file's repository-relative path.

    Returns:
        Every finding, stopping after the metadata when it cannot be read.
    """
    text = (root / rel).read_text(encoding="utf-8")
    findings, declared = check_meta(rel, text)
    if findings:
        return findings
    meta = meta_source(text)
    body = text if meta is None else body_source(text, meta)
    return [
        *check_phases(rel, body, declared),
        *check_imports(rel, body),
        *check_runs(rel, body),
    ]
