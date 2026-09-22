"""agent-self-knowledge's `ccdocs.py`, run the way its skill runs it: as a process.

The script requires Python 3.14 but stays parseable by 3.9 (the Xcode Command Line Tools'
`python3`), so an older interpreter reaches its version message instead of a SyntaxError.
Its cache is an optimisation: when it cannot be written, commands still answer. None of
these cases touches the network: `raw` reads a `file://` URL.
"""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import repo_root

if TYPE_CHECKING:
    from collections.abc import Mapping

CCDOCS: Final = "plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py"
"""The script, relative to the repository root."""

OLDEST_PARSER: Final = (3, 9)
"""The oldest `python3` a user is likely to have: the Xcode Command Line Tools' 3.9.6."""

USAGE_EXIT: Final = 2
"""The status of a refused interpreter and of an argparse error."""


def _run(args: list[str], env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run ccdocs.py with this interpreter.

    Args:
        args: The command line after the script path.
        env: Extra environment variables.

    Returns:
        The completed process.
    """
    command = [sys.executable, str(repo_root() / CCDOCS), *args]
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), **(env or {})}
    return subprocess.run(
        command, capture_output=True, text=True, check=False, env=environment, timeout=60
    )


def test_the_source_parses_on_the_oldest_python3_a_user_has() -> None:
    """3.10+ grammar would stop an old interpreter before it can print the version message."""
    source = (repo_root() / CCDOCS).read_text(encoding="utf-8")
    _ = ast.parse(source, feature_version=OLDEST_PARSER)


@pytest.mark.slow
def test_an_older_python_gets_the_version_message_and_exit_2() -> None:
    """The requirement is enforced by the script itself, before any network call."""
    probe = (
        "import runpy, sys; sys.version_info = (3, 9, 6, 'final', 0); "
        f"runpy.run_path({str(repo_root() / CCDOCS)!r}, run_name='__main__')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False, timeout=60
    )
    assert completed.returncode == USAGE_EXIT
    assert "ccdocs.py needs Python 3.14 or later; this is python3 3.9.6" in completed.stderr


@pytest.mark.slow
def test_an_unwritable_cache_only_loses_caching(tmp_path: Path) -> None:
    """A read-only cache directory still returns the fetched text and exit 0.

    Args:
        tmp_path: pytest's per-test directory.
    """
    page = tmp_path / "page.txt"
    _ = page.write_text("canary text\n", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    cache.chmod(0o500)
    try:
        completed = _run(["raw", page.as_uri()], {"XDG_CACHE_HOME": str(cache)})
    finally:
        cache.chmod(0o700)
    assert completed.returncode == 0, completed.stderr
    assert "canary text" in completed.stdout
    assert not any(cache.iterdir())


@pytest.mark.slow
@pytest.mark.parametrize("nth", ["0", "-2", "x"])
def test_nth_below_one_is_refused_before_any_fetch(nth: str) -> None:
    """`--nth` is 1-based; 0 or a negative used to pick a heading from the end.

    Args:
        nth: The rejected value.
    """
    completed = _run(["page", "hooks", "--nth", nth])
    assert completed.returncode == USAGE_EXIT
    assert "expected a whole number of 1 or more" in completed.stderr


@pytest.mark.slow
def test_an_invalid_cache_ttl_falls_back_with_a_warning() -> None:
    """A bad CCDOCS_CACHE_TTL is named and ignored instead of raising a traceback."""
    completed = _run(["--help"], {"CCDOCS_CACHE_TTL": "abc"})
    assert completed.returncode == 0
    assert "ignoring CCDOCS_CACHE_TTL='abc'; using 900 seconds" in completed.stderr
