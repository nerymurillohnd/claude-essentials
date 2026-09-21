"""The catalog gate: ten invariants over the manifests on disk and the generated catalog.

Every message starts with its invariant ID (P14), and `--list` prints the registry, so a
maintainer reading gate output can look a rule up without reading this file. The registry is
the specification; `test_validate_marketplace` pins it against §A6 of the migration plan.

Nothing here touches the network or the official CLI: the manifests, the catalog and the root
README are the only inputs, so the same command gives the same answer on a laptop and on a
runner.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import (
    ExitCode,
    Finding,
    MaintainerError,
    MissingPathError,
    format_finding,
)
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import as_mapping, as_str, load_json, plugin_ids, repo_root
from scripts.marketplace.catalog import (
    CATALOG_ENTRY_KEYS,
    build_plugins_array,
    check_category,
    check_links,
    check_name,
    check_renames,
    check_tags,
    manifest_path,
    manifest_rel,
    marketplace_metadata,
)
from scripts.marketplace.generate_marketplace import render
from scripts.versioning.semver import InvalidVersionError, parse
from scripts.versioning.version_plan import CATALOG_GENERATED_KEY, MARKETPLACE_PATH

if TYPE_CHECKING:
    from collections.abc import Sequence

MARKETPLACE_INVARIANTS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "M1",
        "`plugin.json` `name` equals its directory name",
        "a catalog/directory mismatch breaks install",
    ),
    (
        "M2",
        "`metadata.marketplace.category` is one of `MARKETPLACE_CATEGORIES`",
        "free-text categories",
    ),
    (
        "M3",
        "`tags`: one to eight, unique, `^[a-z0-9]+(-[a-z0-9]+)*$`",
        "unbounded or duplicated tags",
    ),
    (
        "M4",
        (
            "required fields `name`, `description`, `version`, "
            '`metadata.marketplace.category`, `author.name`, `license == "Apache-2.0"`'
        ),
        "ADR-0005 drift",
    ),
    (
        "M5",
        "`version` is canonical SemVer: no `v`, no build metadata, prerelease `-(beta|rc).N`",
        "the official CLI accepts `1.0`, which Claude Code then orders differently",
    ),
    (
        "M6",
        "`name` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and is at most 42 characters",
        "DEBT-0021: `plugin: <name>` would exceed GitHub's 50-character label limit",
    ),
    (
        "M7",
        "`marketplace.json` is byte-equal to the generated document",
        "hand edits to a generated array",
    ),
    (
        "M8",
        "disk and catalog agree both ways, and no entry carries a `version` key",
        "a stale catalog",
    ),
    (
        "M9",
        "`renames` values are a string or null; no key still ships; a null has no README row",
        "DEBT-0006: a catalog that offers a plugin that no longer exists",
    ),
    (
        "M10",
        "`homepage` ends with `/plugins/<id>`; no `$schema` points at a missing path",
        "dead links",
    ),
)
"""The registry `--list` prints: ID, what it checks, and the defect it catches (P14)."""

REQUIRED_MANIFEST_FIELDS: Final = ("name", "description", "version")
"""Top-level `plugin.json` keys every plugin declares (M4)."""

REQUIRED_LICENSE: Final = "Apache-2.0"
"""The one license this repository ships under (ADR-0005)."""


def check_manifest(root: Path, plugin_id: str) -> list[Finding]:
    """Check one plugin's manifest against M1 to M6.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per rule broken.
    """
    path = manifest_path(root, plugin_id)
    rel = manifest_rel(plugin_id)
    findings: list[Finding] = [*check_name(plugin_id)]
    document = as_mapping(load_json(path), path=path)
    name = document.get("name")
    if name != plugin_id:
        findings.append(
            Finding("M1", rel, f"manifest `name` is {name!r} but the directory is {plugin_id!r}"),
        )
    findings.extend(_check_required_fields(rel, document))
    findings.extend(_check_version(rel, document))
    marketplace = marketplace_metadata(document, path=path)
    findings.extend(check_category(plugin_id, marketplace.get("category")))
    findings.extend(check_tags(plugin_id, marketplace.get("tags")))
    return findings


def _check_required_fields(rel: str, document: dict[str, object]) -> list[Finding]:
    """Check the fields M4 requires, other than the catalog category.

    Args:
        rel: The manifest's repository-relative path.
        document: The parsed manifest.

    Returns:
        One finding per missing or wrong field.
    """
    findings: list[Finding] = [
        Finding("M4", rel, f"`{field}` is missing")
        for field in REQUIRED_MANIFEST_FIELDS
        if not isinstance(document.get(field), str)
    ]
    author = document.get("author")
    if not is_json_object(author) or not isinstance(author.get("name"), str):
        findings.append(Finding("M4", rel, "`author.name` is missing"))
    license_field = document.get("license")
    if license_field != REQUIRED_LICENSE:
        findings.append(
            Finding("M4", rel, f"`license` is {license_field!r}, not {REQUIRED_LICENSE!r}"),
        )
    return findings


def _check_version(rel: str, document: dict[str, object]) -> list[Finding]:
    """Check that the manifest version is canonical SemVer (M5).

    Args:
        rel: The manifest's repository-relative path.
        document: The parsed manifest.

    Returns:
        One finding when the version cannot be parsed; none when it is absent (M4 covers it).
    """
    raw = document.get("version")
    if not isinstance(raw, str):
        return []
    try:
        _ = parse(raw)
    except InvalidVersionError as error:
        return [Finding("M5", rel, str(error))]
    return []


def check_generated(root: Path) -> list[Finding]:
    """Check that the catalog on disk is what the generator would write (M7).

    Args:
        root: The repository root.

    Returns:
        One finding when the file differs, saying whether the array or only the formatting
        moved.
    """
    path = root / MARKETPLACE_PATH
    try:
        rendered = render(root)
    except MaintainerError as error:
        return [Finding("M7", MARKETPLACE_PATH, f"the catalog cannot be generated: {error}")]
    text = path.read_text(encoding="utf-8")
    if text == rendered:
        return []
    catalog = as_mapping(load_json(path), path=path)
    same_array = catalog.get(CATALOG_GENERATED_KEY) == build_plugins_array(root)
    detail = (
        "its formatting is not canonical JSON"
        if same_array
        else f"its `{CATALOG_GENERATED_KEY}` array does not match the manifests on disk"
    )
    return [Finding("M7", MARKETPLACE_PATH, f"{detail}; run `make generate`")]


def check_coverage(root: Path) -> list[Finding]:
    """Check that disk and catalog list the same plugins, and that no entry pins a version.

    Args:
        root: The repository root.

    Returns:
        One finding per plugin missing on either side and per entry carrying a `version`.
    """
    path = root / MARKETPLACE_PATH
    catalog = as_mapping(load_json(path), path=path)
    raw = catalog.get(CATALOG_GENERATED_KEY)
    if not is_json_array(raw):
        return [Finding("M8", MARKETPLACE_PATH, f"`{CATALOG_GENERATED_KEY}` is not an array")]
    findings: list[Finding] = []
    listed: set[str] = set()
    for entry in raw:
        item = as_mapping(entry, path=path)
        name = as_str(item.get("name"), path=path)
        listed.add(name)
        if "version" in item:
            findings.append(
                Finding(
                    "M8",
                    MARKETPLACE_PATH,
                    f"entry {name!r} carries a `version` key; the catalog never pins one",
                ),
            )
        unknown = sorted(set(item) - set(CATALOG_ENTRY_KEYS) - {"version"})
        if unknown:
            findings.append(
                Finding("M8", MARKETPLACE_PATH, f"entry {name!r} has unknown keys: {unknown}"),
            )
    on_disk = set(plugin_ids(root))
    findings.extend(
        Finding("M8", MARKETPLACE_PATH, f"{name!r} ships but has no catalog entry")
        for name in sorted(on_disk - listed)
    )
    findings.extend(
        Finding("M8", MARKETPLACE_PATH, f"entry {name!r} names a plugin that is not on disk")
        for name in sorted(listed - on_disk)
    )
    return findings


def collect(root: Path) -> list[Finding]:
    """Run every catalog invariant over one working tree.

    Args:
        root: The repository root.

    Returns:
        Every finding, manifests first, then the catalog itself.

    Raises:
        MissingPathError: If the root or the catalog is not there; a caller that points at
            the wrong tree gets one line rather than a `FileNotFoundError` traceback.
    """
    if not root.is_dir():
        raise MissingPathError(root, "the repository root")
    catalog = root / MARKETPLACE_PATH
    if not catalog.is_file():
        raise MissingPathError(catalog, "the marketplace catalog")
    findings: list[Finding] = []
    for plugin_id in plugin_ids(root):
        findings.extend(check_manifest(root, plugin_id))
    findings.extend(check_generated(root))
    findings.extend(check_coverage(root))
    findings.extend(check_renames(root))
    findings.extend(check_links(root))
    return findings


def registry_lines() -> list[str]:
    """Render the invariant registry one line per rule.

    Returns:
        The lines `--list` prints.
    """
    return [f"{ident}  {check} — {defect}" for ident, check, defect in MARKETPLACE_INVARIANTS]


def parse_args(argv: Sequence[str] | None) -> tuple[bool, Path | None]:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        Whether to print the registry, and the root to check instead of this working tree.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.marketplace.validate_marketplace",
        description="Check the marketplace catalog and every plugin manifest (M1-M10).",
    )
    _ = parser.add_argument("--list", action="store_true", help="print the invariant registry")
    _ = parser.add_argument("--root", default=None, help="check this tree instead of this one")
    values: dict[str, object] = vars(parser.parse_args(argv))
    raw_root = values["root"]
    return bool(values["list"]), Path(raw_root) if isinstance(raw_root, str) else None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the catalog gate.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when nothing fires, 1 on any error finding, 2 when the inputs are unusable.
    """
    as_list, chosen = parse_args(argv)
    if as_list:
        for line in registry_lines():
            print(line)
        return int(ExitCode.OK)
    try:
        findings = collect(chosen if chosen is not None else repo_root())
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    for finding in findings:
        print(format_finding(finding))
    failed = any(finding.severity == "error" for finding in findings)
    if not failed:
        print("marketplace catalog: M1-M10 pass")
    return int(ExitCode.FINDINGS if failed else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
