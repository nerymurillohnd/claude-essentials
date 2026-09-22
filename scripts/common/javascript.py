"""V8 evaluation for the JavaScript this repository validates (P12).

A hook matcher is a JavaScript regular expression and a plugin workflow is a JavaScript
module, so both are judged by the engine that actually runs them instead of by a Python
approximation that would accept or reject different inputs.

Every snippet runs in a fresh, short-lived context with no host bindings, and every value
crosses back as JSON text, so no caller ever handles a live V8 object and no value typed
`Any` enters the maintainer code.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

from py_mini_racer import JSEvalException, JSPromise, JSPromiseError, JSValueError, MiniRacer

from scripts.common.errors import MaintainerError
from scripts.common.jsontext import is_json_array, is_json_object

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

EVAL_TIMEOUT_MS: Final = 10_000
"""Wall clock a snippet gets before V8 is told to abandon it."""

# json.loads is annotated `-> Any`; this alias is the one place that Any becomes object.
_loads: Callable[[str], object] = json.loads


class JavaScriptError(MaintainerError):
    """V8 refused a snippet the tooling asked it to run.

    The detail is V8's own message, so a maintainer reading gate output sees the engine's
    complaint rather than a paraphrase of it.
    """

    def __init__(self, detail: str) -> None:
        """Record what V8 reported.

        Args:
            detail: The engine's message.
        """
        super().__init__(f"JavaScript evaluation failed: {detail}")


class JavaScriptShapeError(MaintainerError):
    """A snippet ran but handed back something other than the agreed shape.

    The tooling writes every snippet itself, so this is a defect in the maintainer code
    rather than in a plugin; it is raised instead of narrowing silently.
    """

    def __init__(self, found: object, expected: str) -> None:
        """Record what came back and what was required.

        Args:
            found: The value V8 produced; only its type is reported.
            expected: The required shape, phrased for a reader.
        """
        super().__init__(f"JavaScript evaluation returned {type(found).__name__}, not {expected}")


def evaluate_json(source: str) -> object:
    """Run a snippet that returns a JSON string and parse what it returned.

    Args:
        source: A JavaScript expression whose value is a JSON document as text.

    Returns:
        The parsed document as `object`; never `Any`.

    Raises:
        JavaScriptError: If V8 refuses the snippet.
        JavaScriptShapeError: If the snippet's value is not a string.
    """
    context = MiniRacer()
    try:
        value = context.eval(source, timeout=EVAL_TIMEOUT_MS)
    except (JSEvalException, JSPromiseError, JSValueError) as error:
        raise JavaScriptError(str(error)) from error
    if not isinstance(value, str):
        raise JavaScriptShapeError(value, "a JSON string")
    return _loads(value)


def _guarded(body: str) -> str:
    """Wrap a snippet so a thrown value comes back as data instead of an exception.

    Args:
        body: Statements that `return` the successful result, already JSON-encodable.

    Returns:
        An expression whose value is a JSON object with `ok`, and `value` or `error`.
    """
    return (
        "(function () {\n"
        "  try {\n"
        f"    return JSON.stringify({{ ok: true, value: (function () {{ {body} }})() }});\n"
        "  } catch (error) {\n"
        "    return JSON.stringify({ ok: false, error: String(error) });\n"
        "  }\n"
        "})()"
    )


def _outcome(result: object) -> tuple[bool, object, str]:
    """Split the guarded wrapper's document into success, value and error message.

    Args:
        result: The parsed document `_guarded` produced.

    Returns:
        Whether the snippet succeeded, the value it returned, and V8's error text.

    Raises:
        JavaScriptShapeError: If the document is not the shape `_guarded` always writes.
    """
    if not is_json_object(result):
        raise JavaScriptShapeError(result, "the guarded wrapper's object")
    ok = result.get("ok")
    error = result.get("error")
    if not isinstance(ok, bool):
        raise JavaScriptShapeError(ok, "a boolean `ok` flag")
    return ok, result.get("value"), error if isinstance(error, str) else ""


def run(body: str) -> tuple[object, str | None]:
    """Run JavaScript statements and report the value or the thrown message.

    Args:
        body: Statements that `return` a JSON-encodable value.

    Returns:
        The returned value and None, or None and the message V8 threw.

    Raises:
        JavaScriptError: If V8 itself could not be started.
        JavaScriptShapeError: If the wrapper answered off-contract.
    """
    ok, value, error = _outcome(evaluate_json(_guarded(body)))
    if ok:
        return value, None
    return None, error or "unknown JavaScript error"


def literal(value: object) -> str:
    """Render a Python value as a JavaScript literal.

    JSON is a subset of JavaScript expression syntax for the values this repository
    passes (strings, numbers, booleans, null, arrays and objects), so `json.dumps` is
    the injection-safe way to hand data to a snippet.

    Args:
        value: The value to embed.

    Returns:
        JavaScript source for that value.
    """
    return json.dumps(value, ensure_ascii=True)


def regex_matches(pattern: str, candidates: Sequence[str]) -> tuple[list[str], str | None]:
    """Compile a pattern as `new RegExp` and report which candidates it matches.

    Matching uses `RegExp.prototype.test`, which is what Claude Code applies to a hook
    matcher, so an unanchored pattern matches anywhere in the candidate.

    Args:
        pattern: The matcher source, exactly as the manifest carries it.
        candidates: Values to test, normally the known tool names.

    Returns:
        The matching candidates and None, or an empty list and V8's compile error.

    Raises:
        JavaScriptError: If V8 could not be started.
        JavaScriptShapeError: If the snippet answered off-contract.
    """
    snippet = (
        f"var re = new RegExp({literal(pattern)});\n"
        f"return {literal(list(candidates))}.filter(function (name) {{ return re.test(name); }});"
    )
    value, error = run(snippet)
    if error is not None:
        return [], error
    if not is_json_array(value):
        raise JavaScriptShapeError(value, "an array of matches")
    return [item for item in value if isinstance(item, str)], None


def run_async(body: str) -> tuple[object, str | None]:
    """Run asynchronous JavaScript statements and report the value or the thrown message.

    Every `await` in the snippets this repository runs resolves against an already-settled
    value, so the promise the wrapper returns is read back with `JSPromise.get` rather than
    through an event loop.

    Args:
        body: Statements that `return` a JSON-encodable value; `await` is allowed.

    Returns:
        The returned value and None, or None and the message V8 threw.

    Raises:
        JavaScriptError: If V8 could not be started or refused the snippet.
        JavaScriptShapeError: If the wrapper answered off-contract.
    """
    source = (
        "(async function () {\n"
        "  try {\n"
        "    return JSON.stringify({ ok: true, value: await (async function () {\n"
        f"{body}\n"
        "    })() });\n"
        "  } catch (error) {\n"
        "    return JSON.stringify({ ok: false, error: String(error) });\n"
        "  }\n"
        "})()"
    )
    ok, value, error = _outcome(_resolve(source))
    if ok:
        return value, None
    return None, error or "unknown JavaScript error"


def _resolve(source: str) -> object:
    """Evaluate an expression that yields a promise of a JSON string, and parse the string.

    Args:
        source: The JavaScript expression.

    Returns:
        The parsed document as `object`.

    Raises:
        JavaScriptError: If V8 refuses the snippet.
        JavaScriptShapeError: If the promise did not settle to a string.
    """
    context = MiniRacer()
    try:
        pending = context.eval(source, timeout=EVAL_TIMEOUT_MS)
        value = pending.get(timeout=EVAL_TIMEOUT_MS) if isinstance(pending, JSPromise) else pending
    except (JSEvalException, JSPromiseError, JSValueError) as error:
        raise JavaScriptError(str(error)) from error
    if not isinstance(value, str):
        raise JavaScriptShapeError(value, "a JSON string")
    return _loads(value)
