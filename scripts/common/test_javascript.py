"""V8 helper: a snippet's value, a thrown message, and a matcher's real semantics."""

from __future__ import annotations

import pytest

from scripts.common.javascript import (
    JavaScriptShapeError,
    evaluate_json,
    literal,
    regex_matches,
    run,
    run_async,
)


def test_run_returns_the_value() -> None:
    """A snippet that returns data hands it back as parsed JSON."""
    assert run("return { a: [1, 2] };") == ({"a": [1, 2]}, None)


def test_run_reports_a_thrown_error_as_data() -> None:
    """A throw comes back as a message, not as a Python exception."""
    value, error = run('throw new Error("boom");')
    assert value is None
    assert error is not None
    assert "boom" in error


def test_run_async_awaits_a_resolved_promise() -> None:
    """An `await` on a settled value resolves without an event loop."""
    assert run_async("const x = await Promise.resolve(3); return { x: x };") == ({"x": 3}, None)


def test_a_broken_matcher_is_reported_by_v8() -> None:
    """`Write|Edit[` is the matcher Python's `re` accepts and JavaScript does not."""
    matched, error = regex_matches("Write|Edit[", ["Write", "Edit"])
    assert matched == []
    assert error is not None
    assert "Invalid regular expression" in error


def test_a_matcher_uses_unanchored_test_semantics() -> None:
    """`Edit.*` matches `NotebookEdit` too, the way `RegExp.prototype.test` does."""
    matched, error = regex_matches("Edit.*", ["Edit", "NotebookEdit", "Read"])
    assert error is None
    assert matched == ["Edit", "NotebookEdit"]


def test_a_negative_lookahead_matches_everything_it_does_not_name() -> None:
    """The shape `verify-completion` ships is evaluated, not approximated."""
    matched, error = regex_matches("^(?!(?:Read|Glob)$)", ["Read", "Glob", "Write", "Bash"])
    assert error is None
    assert matched == ["Write", "Bash"]


def test_literal_escapes_data_into_source() -> None:
    """Data crosses into a snippet as JSON, so a quote cannot end the expression."""
    assert run(f"return {literal('a"b')};") == ('a"b', None)


def test_a_snippet_that_returns_no_string_is_refused() -> None:
    """`evaluate_json` requires the JSON string its callers always produce."""
    with pytest.raises(JavaScriptShapeError):
        _ = evaluate_json("42")
