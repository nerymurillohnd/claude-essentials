"""Which environment variables a shipped script reads, and the `*_TEST_BASH` convention.

R6 says a plugin's README names every variable its own scripts read. Finding that set means
reading the scripts the way the interpreter does:

* a `$VAR` inside single quotes is not an expansion in shell, and neither is anything after
  an unquoted `#`, so both are removed before the scan;
* a name the script assigns itself is a local, not an input, so every binding form the
  shipped scripts use is subtracted;
* names the operating system, the shell or Claude Code provide are subtracted as a dated
  baseline, because a README that listed `PATH` would say nothing useful.

What remains is the plugin's own configuration surface, which the README has to document.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

SHELL_EXPANSION: Final = re.compile(r"\$\{?(?P<name>[A-Z][A-Z0-9_]*)")
"""A shell expansion of an upper-case name, in the braced or the bare form."""

SHELL_BINDING: Final = re.compile(
    r"(?:\b(?P<assigned>[A-Z][A-Z0-9_]*)\s*\+?=)"
    r"|(?:\b(?:local|readonly|export|declare|typeset)\s+(?:-[A-Za-z]+\s+)*(?P<declared>[A-Z][A-Z0-9_]*))"
    r"|(?:\bfor\s+(?P<loop>[A-Z][A-Z0-9_]*)\s+in\b)"
    r"|(?:\bread\s+(?:-[A-Za-z]+\s+)*(?P<read>[A-Z][A-Z0-9_]*))"
    r"|(?:\bprintf\s+-v\s+(?P<printf>[A-Z][A-Z0-9_]*))"
    r"|(?:\$\{(?P<default>[A-Z][A-Z0-9_]*):=)"
)
"""Every binding form the shipped scripts use; a bound name is a local, not an input."""

SINGLE_QUOTED: Final = re.compile(r"'[^']*'")
"""A single-quoted segment, where the shell performs no expansion at all."""

COMMENT: Final = re.compile(r"(?m)(?:^[ \t]*#.*$)|(?:(?<=[ \t])#[ \t].*$)")
"""A comment: a `#` opening a line, or one surrounded by whitespace.

`${NAME#prefix}` is deliberately not a comment, so a parameter expansion that trims a
prefix does not hide the rest of its line from the scan.
"""

PYTHON_ENV: Final = re.compile(
    r"os\.environ\[\s*[\"'](?P<index>[A-Za-z_][A-Za-z0-9_]*)[\"']\s*\]"
    r"|os\.environ\.get\(\s*[\"'](?P<get>[A-Za-z_][A-Za-z0-9_]*)[\"']"
    r"|os\.getenv\(\s*[\"'](?P<getenv>[A-Za-z_][A-Za-z0-9_]*)[\"']"
)
"""The three ways a shipped Python script reads the environment."""

ENVIRONMENT_BASELINE: Final[frozenset[str]] = frozenset(
    {
        "BASH_REMATCH",
        "BASH_SOURCE",
        "BASH_VERSION",
        "COLUMNS",
        "EDITOR",
        "EUID",
        "FUNCNAME",
        "HOME",
        "HOSTNAME",
        "IFS",
        "LANG",
        "LC_ALL",
        "LINENO",
        "NO_COLOR",
        "OPTARG",
        "OPTIND",
        "OSTYPE",
        "PATH",
        "PIPESTATUS",
        "PPID",
        "PWD",
        "RANDOM",
        "REPLY",
        "SECONDS",
        "SHELL",
        "TERM",
        "TMPDIR",
        "TZ",
        "UID",
        "USER",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
    }
)
"""Names the shell, the operating system or the XDG convention already define."""

HOST_PREFIX: Final = "CLAUDE_"
"""Variables Claude Code sets for a plugin; the README documents behaviour, not the host."""

TEST_BASH_SUFFIX: Final = "_TEST_BASH"
"""The suffix of the variable that selects which `bash` a plugin's own suite runs under."""

SHARED_TEST_BASH: Final = "BNV_TEST_BASH"
"""The fallback every suite in this marketplace honours, exported by `run_plugin_suites`."""


def _without_comments(text: str) -> str:
    """Remove the comments from a shell script.

    Comments go first, before anything else looks at the source: an apostrophe inside a
    comment would otherwise pair with a later quote and swallow the code between them.

    Args:
        text: The script's source.

    Returns:
        The source with comment text removed.
    """
    return COMMENT.sub("", text)


def shell_bindings(text: str) -> set[str]:
    """List the upper-case names a shell script binds itself.

    Args:
        text: The script's source; a binding inside a quoted fixture counts too, a
            binding written only in a comment does not.

    Returns:
        The bound names.
    """
    bound: set[str] = set()
    for match in SHELL_BINDING.finditer(_without_comments(text)):
        bound.update(name for name in match.groupdict().values() if name)
    return bound


def shell_env_vars(text: str) -> set[str]:
    """List the environment variables a shell script reads.

    Args:
        text: The script's source.

    Returns:
        Upper-case names read but never bound, minus the baseline and the host's own.
    """
    code = _without_comments(text)
    bound = shell_bindings(code)
    names = {
        match.group("name") for match in SHELL_EXPANSION.finditer(SINGLE_QUOTED.sub("''", code))
    }
    return _filtered(names - bound)


def python_env_vars(text: str) -> set[str]:
    """List the environment variables a shipped Python script reads.

    Args:
        text: The script's source.

    Returns:
        The names, minus the baseline and the host's own.
    """
    names: set[str] = set()
    for match in PYTHON_ENV.finditer(text):
        names.update(name for name in match.groupdict().values() if name)
    return _filtered(names)


def _filtered(names: set[str]) -> set[str]:
    """Remove the names a README would say nothing useful about.

    Args:
        names: Candidate variable names.

    Returns:
        The plugin's own configuration surface.
    """
    return {
        name
        for name in names
        if name not in ENVIRONMENT_BASELINE and not name.startswith(HOST_PREFIX)
    }


def env_vars_for(path: Path) -> set[str]:
    """Read one shipped script and list the environment variables it reads.

    Args:
        path: The script; its suffix picks the extractor.

    Returns:
        The names, empty for a file that is neither shell nor Python.
    """
    if path.suffix == ".sh":
        return shell_env_vars(path.read_text(encoding="utf-8"))
    if path.suffix == ".py":
        return python_env_vars(path.read_text(encoding="utf-8"))
    return set()


def suite_interpreter_vars(names: set[str]) -> set[str]:
    """Select the `*_TEST_BASH` names out of a variable set.

    The name deliberately avoids a `test_` prefix: pytest collects every module and every
    function whose name starts with `test_`, so a helper called `test_bash_vars` would be
    picked up as a test wherever it is imported.

    Args:
        names: Variable names read by a plugin's scripts.

    Returns:
        The names that select an interpreter for a test suite.
    """
    return {name for name in names if name.endswith(TEST_BASH_SUFFIX)}
