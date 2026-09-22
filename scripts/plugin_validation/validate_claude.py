"""`make validate-cli`: the official CLI's verdict on the marketplace and every plugin.

This gate is deliberately separate from `validate_plugins`: the CLI owns manifest and hook
shape, this repository owns the invariants the CLI does not cover (P6), and keeping the two
in separate targets makes it obvious which one refused a change.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from scripts.common.errors import ExitCode, MaintainerError, MissingPathError
from scripts.common.plugins import plugin_ids, repo_root
from scripts.plugin_validation.claude_cli import targets, validate

if TYPE_CHECKING:
    from collections.abc import Sequence


def parse_args(argv: Sequence[str] | None) -> Path | None:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The tree to check instead of this working tree, or None.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.plugin_validation.validate_claude",
        description="Run `claude plugin validate --strict` on the marketplace and every plugin.",
    )
    _ = parser.add_argument("--root", default=None, help="check this tree instead of this one")
    values: dict[str, object] = vars(parser.parse_args(argv))
    raw = values["root"]
    return Path(raw) if isinstance(raw, str) else None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the official CLI over every target.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when the CLI accepts every target, 1 when it refuses one, 2 when it cannot run.
    """
    chosen = parse_args(argv)
    try:
        root = chosen if chosen is not None else repo_root()
        if not root.is_dir():
            raise MissingPathError(root, "the repository root")
        checked = targets(root, plugin_ids(root))
        results = [(target, *validate(root, target)) for target in checked]
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    failed = False
    for target, ok, output in results:
        print(f"{'pass' if ok else 'FAIL'}  claude plugin validate {target} --strict")
        if output:
            print("\n".join(f"      {line}" for line in output.splitlines()))
        failed = failed or not ok
    return int(ExitCode.FINDINGS if failed else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
