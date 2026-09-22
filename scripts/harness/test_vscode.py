"""§A16: the workspace is complete on its own and can never weaken the gate.

The principle is the maintainer's: `.vscode/` is this project's editor configuration, and it
never inherits from, or assumes anything in, a user-level `settings.json`. A fresh clone with
the recommended extensions has to behave identically to the gate — same binaries from
`.venv/`, same policy from `pyproject.toml`, `.shellcheckrc` and `.editorconfig`.

Two failures this catches. A key that is simply absent lets the user's own default decide,
so the editor and `make check` can disagree about the same file. And a key that *is* present
but names policy — a type-checking mode, a rule list, a line length — lets the editor report
less than the gate, which is the drift Q1 exists to prevent one level down.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import load_json

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

SETTINGS: Final = ".vscode/settings.json"
EXTENSIONS: Final = ".vscode/extensions.json"
TASKS: Final = ".vscode/tasks.json"
LAUNCH: Final = ".vscode/launch.json"
"""The four workspace files, all four re-included by `.gitignore`."""

VENV: Final = "${workspaceFolder}/.venv"
"""Every binary the editor runs comes from here, the same one `make` uses."""

REQUIRED: Final[Mapping[str, object]] = {
    # Python runtime and language server: the project's .venv, basedpyright only.
    "python.defaultInterpreterPath": f"{VENV}/bin/python",
    "python.terminal.activateEnvironment": True,
    "python.languageServer": "None",
    "python.analysis.typeCheckingMode": "off",
    "python.testing.pytestEnabled": True,
    "python.testing.unittestEnabled": False,
    "python.testing.pytestArgs": ["scripts"],
    "python.terminal.activateEnvInCurrentTerminal": True,
    # basedpyright: the locked binary, policy only from [tool.basedpyright].
    "basedpyright.importStrategy": "fromEnvironment",
    "basedpyright.disableOrganizeImports": True,
    "basedpyright.analysis.diagnosticMode": "workspace",
    # Ruff: the locked binary, policy only from [tool.ruff].
    "ruff.enable": True,
    "ruff.nativeServer": "on",
    "ruff.path": [f"{VENV}/bin/ruff"],
    "ruff.interpreter": [f"{VENV}/bin/python"],
    "ruff.importStrategy": "fromEnvironment",
    "ruff.configurationPreference": "filesystemFirst",
    "ruff.lint.enable": True,
    "ruff.format.backend": "internal",
    "ruff.showSyntaxErrors": True,
    "ruff.organizeImports": True,
    "ruff.fixAll": True,
    "ruff.codeAction.fixViolation": {"enable": True},
    "ruff.codeAction.disableRuleComment": {"enable": False},
    # Shell: ShellCheck reads .shellcheckrc, shfmt reads .editorconfig.
    # Bash IDE stays out of linting and formatting: ShellCheck and shfmt run from .venv through
    # the two extensions below, and Bash IDE cannot point at .venv (no ${workspaceFolder}).
    "bashIde.shellcheckPath": "",
    "bashIde.shfmt.path": "",
    "shellcheck.enable": True,
    "shellcheck.run": "onSave",
    "shellcheck.useWorkspaceRootAsCwd": True,
    "shellformat.useEditorConfig": True,
    "shellformat.flag": "",
    # Whole-workspace behaviour, mirroring .editorconfig so both agree.
    "editor.formatOnSaveMode": "file",
    "editor.rulers": [100],
    "files.eol": "\n",
    "files.insertFinalNewline": True,
    "files.trimTrailingWhitespace": True,
    "files.trimFinalNewlines": True,
    "yaml.format.enable": False,
    "json.schemaDownload.enable": False,
    "git.branchProtection": ["main"],
    "git.branchProtectionPrompt": "alwaysPrompt",
    "makefile.configureOnOpen": False,
    "task.problemMatchers.neverPrompt": True,
    "search.useIgnoreFiles": True,
    "editor.unicodeHighlight.invisibleCharacters": True,
    "editor.unicodeHighlight.ambiguousCharacters": True,
    "git.pruneOnFetch": True,
}
"""Every key §A16 requires, with the value it requires. Presence is half the contract."""

FORBIDDEN: Final[tuple[str, ...]] = (
    # Ruff policy lives in pyproject.toml; the editor may not restate or weaken it.
    "ruff.configuration",
    "ruff.lineLength",
    "ruff.exclude",
    "ruff.lint.select",
    "ruff.lint.ignore",
    "ruff.lint.extendSelect",
    "ruff.lint.args",
    "ruff.lint.preview",
    "ruff.format.args",
    "ruff.format.preview",
    # basedpyright policy likewise: the language-server doc says to use the config file.
    "basedpyright.analysis.typeCheckingMode",
    "basedpyright.analysis.diagnosticSeverityOverrides",
    "basedpyright.analysis.include",
    "basedpyright.analysis.exclude",
    "basedpyright.analysis.ignore",
    "basedpyright.analysis.extraPaths",
    "basedpyright.analysis.stubPath",
    "basedpyright.analysis.typeshedPaths",
    "basedpyright.analysis.configFilePath",
    "basedpyright.analysis.baselineFile",
    "basedpyright.analysis.baselineMode",
    "basedpyright.analysis.useTypingExtensions",
    # Deprecated or superseded keys that would quietly re-enable another resolver.
    "basedpyright.openFilesOnly",
    "basedpyright.useLibraryCodeForTypes",
    "python.pythonPath",
    "python.venvPath",
)
"""Keys that would let the editor report less than the gate, or resolve a different tool."""

ALLOWED_PYTHON_ANALYSIS: Final[frozenset[str]] = frozenset({"python.analysis.typeCheckingMode"})
"""The one `python.analysis.*` key allowed: the explicit Pylance neutralisation."""

REQUIRED_EXTENSIONS: Final[tuple[str, ...]] = (
    "anthropic.claude-code",
    "ms-python.python",
    "charliermarsh.ruff",
    "detachhead.basedpyright",
    "timonwong.shellcheck",
    "foxundermoon.shell-format",
    "editorconfig.editorconfig",
    "redhat.vscode-yaml",
    "tamasfe.even-better-toml",
    "ms-vscode.makefile-tools",
    "github.vscode-github-actions",
)
"""The toolchain a fresh clone needs to behave like the gate."""

UNWANTED_EXTENSIONS: Final[tuple[str, ...]] = (
    "ms-python.vscode-pylance",
    "biomejs.biome",
    "esbenp.prettier-vscode",
    "mkhl.shfmt",
)
"""A second type checker, the two formatters this repository replaced, and a second shfmt."""

PYTHON_TAB_SIZE: Final = 4
"""What `.editorconfig` gives a `.py` file, so the editor and the formatter agree."""

MAKE_TARGETS: Final = "Makefile"
"""Where a task's target has to exist."""


def _document(repo: Path, rel: str) -> dict[str, object]:
    """Read one workspace file.

    Args:
        repo: The repository root.
        rel: The file's repository-relative path.

    Returns:
        The parsed document.
    """
    parsed = load_json(repo / rel)
    assert is_json_object(parsed), rel
    return {str(key): value for key, value in parsed.items()}


@pytest.fixture
def settings(repo: Path) -> dict[str, object]:
    """Read the workspace settings.

    Args:
        repo: The repository root.

    Returns:
        The parsed document.
    """
    return _document(repo, SETTINGS)


@pytest.mark.parametrize("key", sorted(REQUIRED))
def test_every_required_key_is_present_with_its_value(
    settings: dict[str, object], key: str
) -> None:
    """A key left out lets the user's own default decide, so the editor may differ from `make`."""
    assert key in settings, f"{key} is not set"
    assert settings[key] == REQUIRED[key], f"{key} is {settings[key]!r}"


@pytest.mark.parametrize("key", FORBIDDEN)
def test_no_forbidden_key_is_present(settings: dict[str, object], key: str) -> None:
    """These would let the editor report less than the gate; policy lives in `pyproject.toml`."""
    assert key not in settings


def test_no_other_python_analysis_key_is_set(settings: dict[str, object]) -> None:
    """`python.analysis.*` belongs to Pylance, which this workspace turns off rather than tunes."""
    found = {key for key in settings if key.startswith("python.analysis.")}
    assert found <= ALLOWED_PYTHON_ANALYSIS, sorted(found - ALLOWED_PYTHON_ANALYSIS)


def test_the_locked_binaries_are_named_from_inside_the_environment(
    settings: dict[str, object],
) -> None:
    """`ruff.path` beats `importStrategy`, so it is what actually binds the editor to the lock."""
    for key in ("ruff.path", "ruff.interpreter"):
        value = settings[key]
        assert is_json_array(value)
        assert all(isinstance(item, str) and item.startswith(VENV) for item in value), key


def test_the_shell_tools_come_from_the_project_environment(settings: dict[str, object]) -> None:
    """ShellCheck and shfmt are pinned in `uv.lock`; a Homebrew copy would be a second version."""
    for key in ("shellcheck.executablePath", "shellformat.path"):
        value = settings[key]
        assert isinstance(value, str)
        assert value.startswith(VENV), f"{key} is {value!r}"


def test_nothing_points_outside_the_workspace(settings: dict[str, object]) -> None:
    """A path under `~` would make the workspace depend on one machine's layout."""
    flattened = repr(settings)
    assert "~/" not in flattened
    assert "${env:HOME}" not in flattened
    assert "${userHome}" not in flattened


def test_every_schema_path_exists_on_disk(repo: Path, settings: dict[str, object]) -> None:
    """A schema mapped to a path that is not there validates nothing and says nothing."""
    schemas = settings["yaml.schemas"]
    assert is_json_object(schemas)
    for path in schemas:
        assert (repo / str(path)).is_file(), path


def test_the_read_only_paths_cover_the_generated_artifacts(settings: dict[str, object]) -> None:
    """Editing a generated file by hand is exactly what M7 and X2 exist to catch."""
    readonly = settings["files.readonlyInclude"]
    assert is_json_object(readonly)
    assert ".claude-plugin/marketplace.json" in readonly
    assert "uv.lock" in readonly


def test_python_editing_agrees_with_the_lint_policy(settings: dict[str, object]) -> None:
    """A tab size or a ruler that disagreed with Ruff would fight the formatter on every save."""
    python = settings["[python]"]
    assert is_json_object(python)
    assert python["editor.defaultFormatter"] == "charliermarsh.ruff"
    assert python["editor.formatOnSave"] is True
    assert python["editor.tabSize"] == PYTHON_TAB_SIZE


def test_markdown_keeps_its_trailing_whitespace(settings: dict[str, object]) -> None:
    """Two trailing spaces are a hard line break; `.editorconfig` says the same thing."""
    markdown = settings["[markdown]"]
    assert is_json_object(markdown)
    assert markdown["files.trimTrailingWhitespace"] is False


@pytest.mark.parametrize("extension", REQUIRED_EXTENSIONS)
def test_every_toolchain_extension_is_recommended(repo: Path, extension: str) -> None:
    """A fresh clone gets the gate's behaviour only with these installed."""
    recommendations = _document(repo, EXTENSIONS)["recommendations"]
    assert is_json_array(recommendations)
    assert extension in recommendations


@pytest.mark.parametrize("extension", UNWANTED_EXTENSIONS)
def test_every_replaced_extension_is_marked_unwanted(repo: Path, extension: str) -> None:
    """A second type checker or formatter would disagree with the gate on save."""
    unwanted = _document(repo, EXTENSIONS)["unwantedRecommendations"]
    assert is_json_array(unwanted)
    assert extension in unwanted


def test_every_task_calls_make_with_a_target_that_exists(repo: Path) -> None:
    """A task is a shortcut for the pipeline, never a command line of its own."""
    makefile = (repo / MAKE_TARGETS).read_text(encoding="utf-8")
    tasks = _document(repo, TASKS)["tasks"]
    assert is_json_array(tasks)
    for task in tasks:
        assert is_json_object(task)
        if task.get("command") != "make":
            continue
        arguments = task["args"]
        assert is_json_array(arguments)
        target = arguments[0]
        assert isinstance(target, str)
        assert f"\n{target}:" in makefile, target


def test_every_launch_configuration_uses_the_project_interpreter(repo: Path) -> None:
    """Debugging under another interpreter would not see the locked dependencies."""
    configurations = _document(repo, LAUNCH)["configurations"]
    assert is_json_array(configurations)
    for configuration in configurations:
        assert is_json_object(configuration)
        assert configuration["python"] == f"{VENV}/bin/python"
        assert configuration["cwd"] == "${workspaceFolder}"
