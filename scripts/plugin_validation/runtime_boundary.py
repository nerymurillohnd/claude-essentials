"""B1: the boundary between the maintainer's environment and a user's machine (§2.1).

A plugin runs from `~/.claude/plugins/cache/…` on a machine that has whatever the user
already had. Everything it may assume is `bash`, `python3` at the floor its README declares,
and the binaries that README lists with a minimum version. Everything the maintainer's
environment provides — `uv`, a virtual environment, Node — is unavailable there, and a
plugin that assumes it never fires and never says why.

The static checks here are deliberately conservative: they read only what git tracks, and
they look at command positions rather than at every occurrence of a word, so a message
that mentions `uv tool install ruff` is not mistaken for an invocation of `uv`.
"""

from __future__ import annotations

import ast
import re
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import PLUGINS_DIRNAME, load_json, tracked_files
from scripts.plugin_validation.frontmatter import TOOL_GRANT, read, tool_grants
from scripts.plugin_validation.hook_contract import (
    ALLOWED_SHEBANGS,
    EXECUTABLE_MODE,
    FRAGMENT_NAME,
    HOOKS_RELATIVE_PATH,
    fragment_groups,
    git_mode,
    groups_from_hooks_json,
)
from scripts.plugin_validation.kind import agent_names, skill_names
from scripts.plugin_validation.script_env import COMMENT, SINGLE_QUOTED
from scripts.versioning.version_plan import is_exempt

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

FORBIDDEN_BINARIES: Final[frozenset[str]] = frozenset({"node", "npm", "npx", "python", "uv", "uvx"})
"""Binaries a plugin may not invoke: they assume the maintainer's environment (§2.1).

`python` without the `3` is on the list because it resolves to a virtual environment's
interpreter, or to nothing at all, on a user's machine; `python3` is the portable spelling.
"""

EXTERNAL_BINARIES: Final[frozenset[str]] = frozenset(
    {
        "bash",
        "bun",
        "curl",
        "deno",
        "docker",
        "gh",
        "git",
        "jq",
        "make",
        "node",
        "npm",
        "npx",
        "pnpm",
        "python3",
        "ruff",
        "shellcheck",
        "shfmt",
        "uv",
        "uvx",
        "wget",
        "yarn",
    }
)
"""Binaries a user may not have, which a README therefore has to list (feeds R5).

Everything POSIX and every coreutil (`sed`, `awk`, `grep`, `find`, `mktemp`, `printf`) is
deliberately absent: a requirement row for them would say nothing a reader can act on.
"""

MESSAGE_STRING: Final = re.compile(r'"(?:\\.|[^"\\])*"')
"""A double-quoted shell string; only those without a substitution are treated as prose."""

SUBSTITUTION: Final = re.compile(r"\$\(|`")
"""A command substitution, which keeps a double-quoted segment in the scan."""

_COMMAND_POSITION_PATTERN: Final = (
    r"(?:^|[\n;&|(){}]|&&|\|\||\b(?:then|else|elif|do|fi|done|exec|command|env)\s)\s*"
    r"(?P<binary>[A-Za-z][\w.-]*)"
)
COMMAND_POSITION: Final = re.compile(_COMMAND_POSITION_PATTERN)
"""A word in command position: at the start of a line or after an operator or keyword."""

PYTHON_SUFFIX: Final = ".py"
"""The suffix of a shipped Python script."""

SHELL_SUFFIX: Final = ".sh"
"""The suffix of a shipped shell script."""

STDLIB_MODULES: Final[frozenset[str]] = frozenset(sys.stdlib_module_names)
"""The allowlist for a shipped `.py`'s imports.

This is the standard library of the interpreter running the gate (3.14), which is also the
floor every plugin that ships Python must declare: `run_plugin_suites` fails a plugin whose
README states another floor, and smoke-runs the script under this interpreter.
"""


def _shell_code(text: str) -> str:
    """Reduce a shell script to the parts where a word can be a command.

    Args:
        text: The script's source.

    Returns:
        The source with comments, single-quoted segments and message strings removed.
    """
    code = SINGLE_QUOTED.sub("''", COMMENT.sub("", text))
    return MESSAGE_STRING.sub(
        lambda match: match.group(0) if SUBSTITUTION.search(match.group(0)) else '""',
        code,
    )


def shell_commands(text: str) -> set[str]:
    """List the words a shell script uses in command position.

    Args:
        text: The script's source.

    Returns:
        The command words, without paths.
    """
    return {
        match.group("binary").rsplit("/", 1)[-1]
        for match in COMMAND_POSITION.finditer(_shell_code(text))
    }


def python_commands(text: str) -> set[str]:
    """List the binaries a shipped Python script hands to `subprocess`.

    Only the first word of a `subprocess` call's command is read, so a module-level list of
    tool names used as data is not mistaken for an invocation.

    Args:
        text: The script's source.

    Returns:
        The binaries, without paths.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            binary = _subprocess_binary(node)
            if binary is not None:
                found.add(binary.rsplit("/", 1)[-1])
    return found


def _subprocess_binary(node: ast.Call) -> str | None:
    """Read the binary a `subprocess.<fn>(...)` call would run.

    Args:
        node: The call node.

    Returns:
        The binary, or None when the call is not a subprocess call or is built at run time.
    """
    func = node.func
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
        return None
    if func.value.id != "subprocess" or not node.args:
        return None
    first = node.args[0]
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        first = first.elts[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value.split()[0] if first.value.split() else None
    return None


def imported_modules(text: str) -> set[str]:
    """List the top-level modules a shipped Python script imports.

    Args:
        text: The script's source.

    Returns:
        The module names, with submodules reduced to their package.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def shipped_scripts(root: Path, plugin_id: str) -> list[str]:
    """List the shell and Python files a plugin ships.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted repository-relative paths.
    """
    return [
        rel
        for rel in tracked_files(root, f"{PLUGINS_DIRNAME}/{plugin_id}/*")
        if rel.endswith((SHELL_SUFFIX, PYTHON_SUFFIX))
    ]


def runtime_scripts(root: Path, plugin_id: str) -> list[str]:
    """List the shipped scripts Claude Code can run for a user.

    An eval scaffold ships inside `evals/` but only `claude plugin eval` runs it, on the
    maintainer's machine, so what it invokes or reads is no requirement of the plugin. The
    exempt rule is the versioning one (`EXEMPT_FILE`), so "runtime" means the same thing here
    as it does for a version bump.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted repository-relative paths.
    """
    prefix = f"{PLUGINS_DIRNAME}/{plugin_id}/"
    return [
        rel for rel in shipped_scripts(root, plugin_id) if not is_exempt(rel.removeprefix(prefix))
    ]


def check_shebangs(root: Path, plugin_id: str) -> list[Finding]:
    """Check every shipped script's shebang and exec bit (B1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        An error per script with no shebang, with an interpreter a user may not have, or
        without the exec bit its shebang needs.
    """
    findings: list[Finding] = []
    for rel in shipped_scripts(root, plugin_id):
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
        first = lines[0] if lines else ""
        if not first.startswith("#!"):
            findings.append(Finding("B1", rel, "a shipped script declares no shebang"))
            continue
        if first not in ALLOWED_SHEBANGS:
            findings.append(
                Finding("B1", rel, f"shebang {first!r} is not one of {list(ALLOWED_SHEBANGS)}")
            )
            continue
        if git_mode(root, rel) != EXECUTABLE_MODE:
            findings.append(
                Finding("B1", rel, f"declares a shebang but is not tracked as {EXECUTABLE_MODE}")
            )
    return findings


def check_forbidden(root: Path, plugin_id: str) -> list[Finding]:
    """Check that no shipped script invokes a binary from the maintainer's side (B1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per script that runs a forbidden binary.
    """
    findings: list[Finding] = []
    for rel in shipped_scripts(root, plugin_id):
        text = (root / rel).read_text(encoding="utf-8")
        used = shell_commands(text) if rel.endswith(SHELL_SUFFIX) else python_commands(text)
        findings.extend(
            Finding("B1", rel, f"invokes {binary!r}, which a user's machine may not have")
            for binary in sorted(used & FORBIDDEN_BINARIES)
        )
    return findings


def check_imports(root: Path, plugin_id: str) -> list[Finding]:
    """Check that every shipped Python script imports only the standard library (B1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per script importing a module a user would have to install.
    """
    findings: list[Finding] = []
    for rel in shipped_scripts(root, plugin_id):
        if not rel.endswith(PYTHON_SUFFIX):
            continue
        outside = sorted(
            imported_modules((root / rel).read_text(encoding="utf-8")) - STDLIB_MODULES
        )
        findings.extend(
            Finding("B1", rel, f"imports {module!r}, which is not in the standard library")
            for module in outside
        )
    return findings


def hook_commands(root: Path, plugin_id: str) -> list[tuple[str, str]]:
    """List every hook command a plugin declares, with the file it came from.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Pairs of repository-relative path and command line.
    """
    base = f"{PLUGINS_DIRNAME}/{plugin_id}"
    sources: list[tuple[str, list[object]]] = []
    hooks_rel = f"{base}/{HOOKS_RELATIVE_PATH}"
    if (root / hooks_rel).is_file():
        groups, _ = groups_from_hooks_json(load_json(root / hooks_rel))
        sources.append((hooks_rel, [handler for group in groups for handler in group.handlers]))
    for rel in tracked_files(root, f"{base}/*"):
        if rel.rsplit("/", 1)[-1] != FRAGMENT_NAME:
            continue
        groups = fragment_groups(load_json(root / rel))
        sources.append((rel, [handler for group in groups for handler in group.handlers]))
    return [
        (rel, command)
        for rel, handlers in sources
        for handler in handlers
        if is_json_object(handler)
        for command in [handler.get("command")]
        if isinstance(command, str)
    ]


def _grant_patterns(root: Path, plugin_id: str) -> list[tuple[str, str]]:
    """List every `Bash(...)` pattern a plugin's skills and agents grant.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Pairs of repository-relative path and the granted command pattern.
    """
    base = f"{PLUGINS_DIRNAME}/{plugin_id}"
    files = [f"{base}/skills/{name}/SKILL.md" for name in skill_names(root, plugin_id)]
    files.extend(f"{base}/agents/{name}.md" for name in agent_names(root, plugin_id))
    patterns: list[tuple[str, str]] = []
    for rel in files:
        block = read(root / rel)
        for grant in tool_grants(block.data.get("allowed-tools")):
            match = TOOL_GRANT.match(grant)
            if match is not None and match.group("tool") == "Bash" and match.group("pattern"):
                patterns.append((rel, match.group("pattern")))
    return patterns


def _first_word(command: str) -> str:
    """Return the binary a command line starts with, without its path.

    Args:
        command: The command line.

    Returns:
        The binary, or an empty string for an empty command.
    """
    words = command.split()
    return words[0].rsplit("/", 1)[-1] if words else ""


def check_declared_commands(root: Path, plugin_id: str) -> list[Finding]:
    """Check hook commands and tool grants for forbidden binaries (B1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per command or grant that names a forbidden binary.
    """
    findings: list[Finding] = []
    for rel, command in hook_commands(root, plugin_id):
        binary = _first_word(command)
        if binary in FORBIDDEN_BINARIES:
            findings.append(
                Finding("B1", rel, f"a hook command runs {binary!r}, which a user may not have")
            )
    for rel, pattern in _grant_patterns(root, plugin_id):
        binary = _first_word(pattern)
        if binary in FORBIDDEN_BINARIES:
            findings.append(
                Finding(
                    "B1",
                    rel,
                    f"an `allowed-tools` grant runs {binary!r}, which a user may not have",
                )
            )
    return findings


def invoked_binaries(root: Path, plugin_id: str) -> set[str]:
    """List the external binaries a plugin's shipped files invoke (feeds R5).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The binaries from `EXTERNAL_BINARIES` that the scripts, hook commands and `Bash`
        grants actually run.
    """
    used: set[str] = set()
    for rel in runtime_scripts(root, plugin_id):
        text = (root / rel).read_text(encoding="utf-8")
        used |= shell_commands(text) if rel.endswith(SHELL_SUFFIX) else python_commands(text)
    used |= {_first_word(command) for _, command in hook_commands(root, plugin_id)}
    used |= {_first_word(pattern) for _, pattern in _grant_patterns(root, plugin_id)}
    return used & EXTERNAL_BINARIES


def ships_python(root: Path, plugin_id: str) -> bool:
    """Report whether a plugin ships a Python script.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        True when at least one tracked `.py` file ships.
    """
    return any(rel.endswith(PYTHON_SUFFIX) for rel in shipped_scripts(root, plugin_id))


def env_var_sources(root: Path, plugin_id: str) -> Iterable[str]:
    """List the shipped scripts whose environment reads feed R6.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Yields:
        Repository-relative paths of shipped shell and Python scripts.
    """
    yield from runtime_scripts(root, plugin_id)


def collect(root: Path, plugin_id: str) -> list[Finding]:
    """Run every B1 check over one plugin.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding, in check order.
    """
    return [
        *check_shebangs(root, plugin_id),
        *check_forbidden(root, plugin_id),
        *check_imports(root, plugin_id),
        *check_declared_commands(root, plugin_id),
    ]


def binaries_for_readme(root: Path, plugin_ids_: Sequence[str]) -> dict[str, set[str]]:
    """Map each plugin to the external binaries its shipped files invoke.

    Args:
        root: The repository root.
        plugin_ids_: The plugin directory names.

    Returns:
        One entry per plugin.
    """
    return {plugin_id: invoked_binaries(root, plugin_id) for plugin_id in plugin_ids_}
