"""Cross-file pins: the CLI version, the tool versions, the workflow SHAs, the pipeline (G2, G3).

Every check here compares two files that must agree and that nothing else forces to agree.
None of them reads a plugin's behaviour; they read the repository's own wiring:

* **`check_claude_code_versions`** — one `CLAUDE_CODE_VERSION` across every workflow. `latest`
  is allowed only on a workflow that runs on a schedule or on demand, because a required
  check that floats is a check that can go red without a commit.
* **`check_tool_pins` (G3)** — the Ruff `required-version` is satisfied by the version
  `uv.lock` actually resolves, `.python-version` equals the `requires-python` floor, and the
  ShellCheck and shfmt binaries `uv.lock` installs into `.venv/bin` (the ones CI puts on
  `PATH` for the plugin suites) are at least what the plugin READMEs promise a user. A README
  that advertises a minimum CI does not meet is a promise nothing keeps.
* **`check_pipeline_invocation` (G2)** — `ci.yml` drives the gate through `make`, so the gate
  a maintainer runs and the gate CI runs are the same target list.
* **`check_workflow_pins` (G2)** — every `uses:` names a full commit SHA with the release in a
  comment, which is what makes a third-party action reproducible (DEBT-0004).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import re
import tomllib
from typing import TYPE_CHECKING, Final, TypeIs

import yaml

from scripts.common.errors import ExecutableNotFoundError, Finding
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import plugin_ids
from scripts.lint.tools import run, tool_path

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOWS_DIR: Final = ".github/workflows"
"""Where every workflow lives."""

PYPROJECT: Final = "pyproject.toml"
UV_LOCK: Final = "uv.lock"
PYTHON_VERSION_FILE: Final = ".python-version"
"""The three files the Python toolchain is pinned across."""

CLAUDE_CODE_KEY: Final = "CLAUDE_CODE_VERSION"
"""The environment variable every workflow sets to the pinned CLI version."""

FLOATING_VERSION: Final = "latest"
"""The one non-pinned value, and only where a red run blocks nothing."""

ON_DEMAND_TRIGGERS: Final = frozenset({"schedule", "workflow_dispatch"})
"""Triggers that may run against a floating CLI version."""

GATE_WORKFLOW: Final = "ci.yml"
TAG_WORKFLOW: Final = "tag-versions.yml"
"""The two workflows whose CLI version must be identical (G3)."""

PINNED_TOOLS: Final[tuple[tuple[str, str], ...]] = (
    ("shellcheck", "ShellCheck"),
    ("shfmt", "shfmt"),
)
"""Locked binaries in `.venv/bin` paired with the tool name a plugin README advertises."""

REQUIREMENT_ROW: Final = re.compile(r"^\|\s*(?P<tool>[^|]+?)\s*\|\s*(?P<minimum>[^|]*?)\s*\|")
"""One row of a plugin README's Requirements table."""

VERSION_TOKEN: Final = re.compile(r"\d+(?:\.\d+)*")
"""The first dotted number in a cell, which is the minimum the row advertises."""

USES_LINE: Final = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
"""An action reference in a workflow."""

PINNED_USES: Final = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
"""`owner/repo@<40 hex>`; a tag or a branch is not reproducible."""

VERSION_COMMENT: Final = re.compile(r"#\s*(?:v\d+(?:\.\d+)*|\d{4}-\d{2}-\d{2}\b)")
"""The comment that makes a pinned SHA readable.

`# vX.Y.Z` for a released action, which is also Dependabot's anchor. An action that
publishes no release at all (Anthropic's `validate-plugins`, measured 2026-09-21: zero tags)
has no version to name, so its pin carries the commit's date instead; Dependabot cannot bump
it, and the maintainer moves it by hand.
"""

LOCAL_USES_PREFIX: Final = "./"
"""A `uses:` that points inside this repository needs no SHA."""

MAKE_INVOCATION: Final = re.compile(r"(?:^|[\s;&|])make\s")
"""A `run:` step that drives the gate through the Makefile."""

_safe_load: Callable[[str], object] = yaml.safe_load
"""`yaml.safe_load` is annotated `-> Any`; this alias is the one place that becomes `object`."""


def version_tuple(text: str) -> tuple[int, ...]:
    """Parse a dotted version into comparable integers.

    Args:
        text: A version such as `0.11.0` or `3.12`.

    Returns:
        The components; an empty tuple when the text carries no version.
    """
    match = VERSION_TOKEN.search(text)
    if match is None:
        return ()
    return tuple(int(part) for part in match.group().split("."))


def _is_any_mapping(value: object) -> TypeIs[Mapping[object, object]]:
    """Report whether a value is a mapping, whatever its keys are.

    PyYAML resolves the bare key `on` to the boolean `True` under YAML 1.1, so a workflow's
    top level is not a string-keyed mapping and `is_json_object` would be a false claim.

    Args:
        value: The parsed value.

    Returns:
        True when the value is a mapping.
    """
    return isinstance(value, Mapping)


def workflow_paths(root: Path) -> list[Path]:
    """List every workflow file.

    Args:
        root: The repository root.

    Returns:
        The `.yml` files under `.github/workflows`, sorted by name.
    """
    directory = root / WORKFLOWS_DIR
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.yml"))


def workflow_document(path: Path) -> Mapping[str, object]:
    """Parse a workflow, working around YAML 1.1's reading of `on` as a boolean.

    PyYAML resolves the bare key `on` to `True`, so a workflow's trigger block would
    otherwise be unreachable by name.

    Args:
        path: The workflow file.

    Returns:
        The parsed document with top-level keys as text; empty when it is not a mapping.
    """
    parsed = _safe_load(path.read_text(encoding="utf-8"))
    if not _is_any_mapping(parsed):
        return {}
    document: dict[str, object] = {}
    for key, value in parsed.items():
        if key is True:
            document["on"] = value
        elif isinstance(key, str):
            document[key] = value
    return document


def workflow_triggers(document: Mapping[str, object]) -> set[str]:
    """Return the event names a workflow runs on.

    Args:
        document: The parsed workflow.

    Returns:
        The trigger names, whatever form the `on` block takes.
    """
    triggers = document.get("on")
    if isinstance(triggers, str):
        return {triggers}
    if is_json_object(triggers):
        return set(triggers)
    if is_json_array(triggers):
        return {item for item in triggers if isinstance(item, str)}
    return set()


def workflow_env(document: Mapping[str, object]) -> dict[str, str]:
    """Collect the string environment variables a workflow sets, at any level.

    Args:
        document: The parsed workflow.

    Returns:
        Variable names mapped to their values; a later definition wins.
    """
    found: dict[str, str] = {}
    _collect_env(document, found)
    return found


def _env_entries(value: object) -> dict[str, str]:
    """Return the string entries of one `env` block.

    Args:
        value: The value of an `env` key.

    Returns:
        The variables it sets; empty when it is not a mapping of strings.
    """
    if not is_json_object(value):
        return {}
    return {name: item for name, item in value.items() if isinstance(item, str)}


def _collect_env(value: object, found: dict[str, str]) -> None:
    """Walk a parsed workflow and record every `env` mapping it carries.

    Args:
        value: The current node.
        found: The accumulator, mutated in place.
    """
    if is_json_object(value):
        found.update(_env_entries(value.get("env")))
        for key, item in value.items():
            if key != "env":
                _collect_env(item, found)
    elif is_json_array(value):
        for item in value:
            _collect_env(item, found)


def check_claude_code_versions(root: Path) -> list[Finding]:
    """Check that every workflow pins the same Claude Code CLI version (G2).

    Args:
        root: The repository root.

    Returns:
        One finding per workflow that disagrees or floats where it must not.
    """
    findings: list[Finding] = []
    pinned: dict[str, str] = {}
    for path in workflow_paths(root):
        rel = f"{WORKFLOWS_DIR}/{path.name}"
        document = workflow_document(path)
        version = workflow_env(document).get(CLAUDE_CODE_KEY)
        if version is None:
            continue
        if version == FLOATING_VERSION:
            if not workflow_triggers(document) <= ON_DEMAND_TRIGGERS:
                findings.append(
                    Finding(
                        "G2",
                        rel,
                        f"{CLAUDE_CODE_KEY} is {FLOATING_VERSION!r}, which is allowed only on a "
                        f"workflow triggered solely by {sorted(ON_DEMAND_TRIGGERS)}",
                    ),
                )
            continue
        pinned[rel] = version
    distinct = sorted(set(pinned.values()))
    if len(distinct) > 1:
        findings.append(
            Finding(
                "G2",
                WORKFLOWS_DIR,
                f"{CLAUDE_CODE_KEY} differs across workflows: "
                + ", ".join(f"{rel}={version}" for rel, version in sorted(pinned.items())),
            ),
        )
    return findings


def locked_version(root: Path, package: str) -> str | None:
    """Read the version `uv.lock` resolves for one package.

    Args:
        root: The repository root.
        package: The distribution name.

    Returns:
        The locked version, or None when the package is not in the lock.
    """
    path = root / UV_LOCK
    if not path.is_file():
        return None
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = document.get("package")
    if not is_json_array(packages):
        return None
    for entry in packages:
        if is_json_object(entry) and entry.get("name") == package:
            version = entry.get("version")
            if isinstance(version, str):
                return version
    return None


def _pyproject(root: Path) -> Mapping[str, object]:
    """Parse `pyproject.toml`.

    Args:
        root: The repository root.

    Returns:
        The parsed document; empty when the file is absent.
    """
    path = root / PYPROJECT
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _nested(document: Mapping[str, object], *keys: str) -> object:
    """Read a nested value out of a parsed TOML document.

    Args:
        document: The parsed document.
        *keys: The path to follow.

    Returns:
        The value, or None when any step is missing or not a table.
    """
    current: object = document
    for key in keys:
        if not is_json_object(current):
            return None
        current = current.get(key)
    return current


def _check_ruff_pin(root: Path) -> list[Finding]:
    """Check that the locked Ruff satisfies the `required-version` floor (G3).

    Args:
        root: The repository root.

    Returns:
        One finding when the two disagree or the floor is not a `>=` specifier.
    """
    required = _nested(_pyproject(root), "tool", "ruff", "required-version")
    locked = locked_version(root, "ruff")
    if not isinstance(required, str) or locked is None:
        return []
    if not required.startswith(">="):
        return [
            Finding(
                "G3",
                PYPROJECT,
                f"`required-version` is {required!r}; this repository pins a `>=` floor so a "
                f"Dependabot bump of the lock cannot silently drop below it",
            ),
        ]
    floor = required[2:].strip()
    if version_tuple(locked) < version_tuple(floor):
        return [
            Finding(
                "G3",
                UV_LOCK,
                f"the lock resolves ruff {locked}, below the `required-version` floor {floor}",
            ),
        ]
    return []


def _check_python_floor(root: Path) -> list[Finding]:
    """Check that `.python-version` equals the `requires-python` floor (G3).

    Args:
        root: The repository root.

    Returns:
        One finding when the interpreter uv installs is not the one the project declares.
    """
    path = root / PYTHON_VERSION_FILE
    requires = _nested(_pyproject(root), "project", "requires-python")
    if not path.is_file() or not isinstance(requires, str):
        return []
    declared = path.read_text(encoding="utf-8").strip()
    floor = requires.removeprefix(">=").strip()
    if declared != floor:
        return [
            Finding(
                "G3",
                PYTHON_VERSION_FILE,
                f"{declared!r} is not the `requires-python` floor {floor!r}",
            ),
        ]
    return []


def advertised_minimum(root: Path, tool: str) -> tuple[int, ...]:
    """Return the highest minimum version any plugin README advertises for a tool.

    Args:
        root: The repository root.
        tool: The name as the Requirements table's first column writes it.

    Returns:
        The version components, or an empty tuple when no README names the tool.
    """
    highest: tuple[int, ...] = ()
    for plugin_id in plugin_ids(root):
        readme = root / "plugins" / plugin_id / "README.md"
        if not readme.is_file():
            continue
        for line in readme.read_text(encoding="utf-8").splitlines():
            match = REQUIREMENT_ROW.match(line)
            if match is None or match["tool"].strip("` ").lower() != tool.lower():
                continue
            minimum = version_tuple(match["minimum"])
            highest = max(highest, minimum)
    return highest


def locked_tool_version(root: Path, binary: str) -> tuple[int, ...] | None:
    """Ask a locked binary in `.venv/bin` for its version.

    The wheel's own version is not the tool's (`shfmt-py 4.2.0` ships shfmt 3.14.1), so the
    binary is asked directly.

    Args:
        root: The repository root.
        binary: The executable's file name, for example `shfmt`.

    Returns:
        The version components, or None when the binary is not installed or says no version.
    """
    try:
        executable = tool_path(root, binary)
        completed = run(executable, ["--version"], cwd=root)
    except ExecutableNotFoundError:
        return None
    version = version_tuple(completed.stdout)
    return version or None


def _check_advertised_tools(root: Path) -> list[Finding]:
    """Check that the locked tools are at least the versions the READMEs promise (G3).

    Args:
        root: The repository root.

    Returns:
        One finding per advertised tool that is missing from `.venv` or older than promised.
    """
    findings: list[Finding] = []
    for binary, tool in PINNED_TOOLS:
        advertised = advertised_minimum(root, tool)
        if not advertised:
            continue
        promised = ".".join(str(part) for part in advertised)
        locked = locked_tool_version(root, binary)
        if locked is None:
            findings.append(
                Finding(
                    "G3",
                    UV_LOCK,
                    f"a plugin README advertises {tool} {promised}, but `.venv/bin/{binary}` "
                    f"reports no version; run `make setup`",
                ),
            )
        elif locked < advertised:
            found = ".".join(str(part) for part in locked)
            findings.append(
                Finding(
                    "G3",
                    UV_LOCK,
                    f"the locked {tool} is {found}, below the {promised} a plugin README "
                    f"advertises",
                ),
            )
    return findings


def _check_cli_pin_equality(root: Path) -> list[Finding]:
    """Check that the gate and the tag workflow pin the same CLI version (G3).

    Args:
        root: The repository root.

    Returns:
        One finding when they differ.
    """
    versions: dict[str, str | None] = {}
    for name in (GATE_WORKFLOW, TAG_WORKFLOW):
        path = root / WORKFLOWS_DIR / name
        versions[name] = (
            workflow_env(workflow_document(path)).get(CLAUDE_CODE_KEY) if path.is_file() else None
        )
    gate, tag = versions[GATE_WORKFLOW], versions[TAG_WORKFLOW]
    if gate is not None and tag is not None and gate != tag:
        return [
            Finding(
                "G3",
                f"{WORKFLOWS_DIR}/{TAG_WORKFLOW}",
                f"{CLAUDE_CODE_KEY} is {tag}, but {GATE_WORKFLOW} pins {gate}",
            ),
        ]
    return []


def check_tool_pins(root: Path) -> list[Finding]:
    """Check every pin that two files must agree on (G3).

    Args:
        root: The repository root.

    Returns:
        One finding per disagreement.
    """
    return [
        *_check_ruff_pin(root),
        *_check_python_floor(root),
        *_check_advertised_tools(root),
        *_check_cli_pin_equality(root),
    ]


def check_pipeline_invocation(root: Path) -> list[Finding]:
    """Check that the gate workflow drives the pipeline through `make` (G2).

    Args:
        root: The repository root.

    Returns:
        One finding when the gate workflow runs no `make` target.
    """
    path = root / WORKFLOWS_DIR / GATE_WORKFLOW
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if MAKE_INVOCATION.search(text) is not None:
        return []
    return [
        Finding(
            "G2",
            f"{WORKFLOWS_DIR}/{GATE_WORKFLOW}",
            "the gate workflow runs no `make` target, so CI and `make check` can drift",
        ),
    ]


def check_workflow_pins(root: Path) -> list[Finding]:
    """Check that every action reference is a full SHA with its tag in a comment (G2).

    Args:
        root: The repository root.

    Returns:
        One finding per reference that is not reproducible.
    """
    findings: list[Finding] = []
    for path in workflow_paths(root):
        rel = f"{WORKFLOWS_DIR}/{path.name}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES_LINE.match(line)
            if match is None:
                continue
            ref = match["ref"]
            if ref.startswith(LOCAL_USES_PREFIX):
                continue
            if PINNED_USES.match(ref) is None:
                findings.append(
                    Finding("G2", rel, f"line {number}: `uses: {ref}` is not a 40-hex commit SHA"),
                )
            elif VERSION_COMMENT.search(match["rest"]) is None:
                findings.append(
                    Finding("G2", rel, f"line {number}: `uses: {ref}` carries no `# vX.Y.Z`"),
                )
    return findings


def collect(root: Path) -> list[Finding]:
    """Run every repository-metadata check.

    Args:
        root: The repository root.

    Returns:
        Every finding, in check order.
    """
    return [
        *check_claude_code_versions(root),
        *check_tool_pins(root),
        *check_workflow_pins(root),
        *check_pipeline_invocation(root),
    ]
