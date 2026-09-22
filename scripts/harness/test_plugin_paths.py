"""Parity between the exempt rule's two homes: Python and the shell hook that mirrors it.

`version_plan.EXEMPT_FILE` decides whether changing a file inside a plugin owes a version
bump. `.claude/hooks/lib/plugin-paths.sh` answers the same question for `session-start.sh`
and `post-edit.sh`, which cannot import Python. Two copies of a rule drift, and a drifting
copy means the hook tells the maintainer one thing while the gate enforces another. This test
runs both over one table, under `bash` from PATH and, when it resolves to a different binary,
under `/bin/bash` as well, because macOS ships bash 3.2 at that path.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Final

import pytest

from scripts.common.plugins import repo_root
from scripts.versioning.version_plan import is_exempt

LIBRARY: Final = ".claude/hooks/lib/plugin-paths.sh"
"""The shell mirror of the exempt rule."""

TABLE: Final[tuple[tuple[str, bool], ...]] = (
    ("README.md", True),
    ("CHANGELOG.md", True),
    ("LICENSE", True),
    ("LICENSE.md", True),
    ("LICENSE.x/y", False),
    ("docs/a.md", True),
    ("evals/a/b.md", True),
    ("evalsx/b.md", False),
    ("skills/x/evals/y", False),
    ("test-x.sh", False),
    ("scripts/test-hooks.sh", False),
    ("skills/block-no-verify/scripts/test-handler.sh", False),
    ("test-x/y.sh", False),
    ("skills/test-a.sh.bak", False),
    ("tests/a.sh", False),
    ("skills/x/tests/a.sh", False),
    ("tests", False),
    ("testsuite/a", False),
    ("hooks/hooks.json", False),
    (".claude-plugin/plugin.json", False),
)
"""Every edge the two implementations could disagree on, with the answer both must give.

`docs/` and `evals/` count only at the plugin root, `LICENSE.<ext>` only when it sits directly in
the plugin directory, and a test file is runtime at any depth.
"""

SCRIPT: Final = """
set -euo pipefail
source "$1"
shift
for rel in "$@"; do
  if plugin_path_is_exempt "${rel}"; then printf 'exempt\\n'; else printf 'runtime\\n'; fi
done
"""
"""Driver that sources the library and answers one line per path."""


def _bash_binaries() -> list[str]:
    """Resolve the bash binaries the hooks may run under.

    Returns:
        `bash` from PATH, plus `/bin/bash` when it is a different file.
    """
    found = shutil.which("bash")
    assert found is not None, "bash must be on PATH for the maintainer test suite"
    binaries = [found]
    system = "/bin/bash"
    if Path(system).exists() and Path(system).resolve() != Path(found).resolve():
        binaries.append(system)
    return binaries


def _ask_bash(binary: str, library: Path, paths: tuple[str, ...]) -> list[str]:
    """Run the shell mirror over the whole table in one process.

    Args:
        binary: The bash binary to run.
        library: The library to source.
        paths: The paths to classify.

    Returns:
        One verdict per path, in order.
    """
    completed = subprocess.run(
        [binary, "-c", SCRIPT, "driver", str(library), *paths],
        executable=binary,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.split()


EXEMPT_PATHS: Final = tuple(rel for rel, exempt in TABLE if exempt)
"""The table's exempt half, for a parametrised test without a boolean argument."""

RUNTIME_PATHS: Final = tuple(rel for rel, exempt in TABLE if not exempt)
"""The table's runtime half."""


@pytest.mark.parametrize("rel", EXEMPT_PATHS)
def test_python_treats_these_as_exempt(rel: str) -> None:
    """Changing one of these owes no version bump."""
    assert is_exempt(rel)


@pytest.mark.parametrize("rel", RUNTIME_PATHS)
def test_python_treats_these_as_runtime(rel: str) -> None:
    """The exempt list is closed, so everything else is something Claude may load."""
    assert not is_exempt(rel)


@pytest.mark.slow
@pytest.mark.parametrize("binary", _bash_binaries())
def test_bash_mirror_agrees_with_python(binary: str) -> None:
    """The hook and the gate classify every path in the table identically."""
    root = repo_root(Path(__file__).resolve().parent)
    paths = tuple(rel for rel, _ in TABLE)
    verdicts = _ask_bash(binary, root / LIBRARY, paths)
    assert len(verdicts) == len(paths), f"{binary} answered {verdicts}"
    for (rel, expected), verdict in zip(TABLE, verdicts, strict=True):
        assert (verdict == "exempt") is expected, f"{binary} says {rel} is {verdict}"
        assert (verdict == "exempt") is is_exempt(rel), f"{binary} disagrees with Python on {rel}"
