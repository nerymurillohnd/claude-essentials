"""The negative probes: each defect fires with its own ID, and stops once it is removed.

A gate nobody has seen refuse anything is a gate nobody can trust (P14). Every row of the
table below seeds one defect in the scratch marketplace, asserts the matching invariant ID
appears, removes the defect, and asserts the ID is gone. The probe's own ID is what is
asserted, not the whole finding list, so an unrelated finding in the fixture can never make
a probe look like it passed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import Finding
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import load_json, repo_root
from scripts.github import labels
from scripts.github.labels import LABELS_PATH
from scripts.plugin_validation.conftest import PLUGIN_ID, RELEASE_DATE, SKILL_ID, VERSION, track
from scripts.plugin_validation.validate_plugins import (
    DEFERRED_INVARIANTS,
    GITHUB_INVARIANTS,
    PLUGIN_INVARIANTS,
    check_plugin,
    collect,
    registry_lines,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

pytestmark = pytest.mark.slow

Probe = tuple[str, str, "Callable[[Path], None]"]
"""A probe: its name, the invariant it must fire, and the edit that seeds it."""


def ids_for(root: Path) -> list[str]:
    """Run every per-plugin invariant and list the IDs that fired.

    Args:
        root: The scratch repository root.

    Returns:
        The invariant IDs, with duplicates kept so a count can be compared.
    """
    return [finding.invariant_id for finding in check_plugin(root, PLUGIN_ID, [])]


def plugin_path(root: Path, *parts: str) -> Path:
    """Build a path inside the scratch plugin.

    Args:
        root: The scratch repository root.
        *parts: Path segments below the plugin directory.

    Returns:
        The absolute path.
    """
    return root.joinpath("plugins", PLUGIN_ID, *parts)


def _edit(path: Path, old: str, new: str) -> None:
    """Replace a unique fragment of a file.

    Args:
        path: The file to change.
        old: The fragment to replace; it must appear exactly once.
        new: What replaces it.
    """
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path}: expected one occurrence of {old!r}"
    _ = path.write_text(text.replace(old, new), encoding="utf-8")


def seed_bad_matcher(root: Path) -> None:
    """Give the hook a regular expression V8 refuses (H2).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "hooks", "hooks.json"), '"Edit|Write"', '"Write|Edit["')


def seed_empty_command(root: Path) -> None:
    """Leave the hook's `command` present but empty (H4).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "hooks", "hooks.json")
    _edit(path, 'bash \\"${CLAUDE_PLUGIN_ROOT}/scripts/handler.sh\\"', "")


def seed_missing_fragment_target(root: Path) -> None:
    """Point the settings fragment at a file the plugin does not ship (H5).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "skills", SKILL_ID, "assets", "settings-fragment.json")
    _edit(path, "scripts/handler.sh", "scripts/absent.sh")


def seed_unparseable_description(root: Path) -> None:
    """Make the skill's `description` a plain scalar YAML cannot read (S1).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "skills", SKILL_ID, "SKILL.md")
    _edit(path, "description: Check one thing", "description: a: b Check one thing")


def seed_no_must_not_fire(root: Path) -> None:
    """Remove the only case that proves the plugin can stay quiet (E1).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "evals", "90-stays-quiet", "graders", "fired.md")
    _edit(path, "min: 0\nmax: 0\narm: both\n", "")


def seed_uv_shebang(root: Path) -> None:
    """Ship a script that assumes the maintainer's environment (B1).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "scripts", "handler.sh")
    _edit(path, "#!/usr/bin/env bash", "#!/usr/bin/env -S uv run --script")


def seed_workflow_syntax_error(root: Path) -> None:
    """Break the workflow body's syntax (W1).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "workflows", "scratch.js"), "const report =", "const report ===")


def seed_workflow_impure_meta(root: Path) -> None:
    """Make `meta` read an identifier instead of being a literal (W1).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "workflows", "scratch.js"), 'name: "scratch"', "name: SCRATCH_NAME")


def seed_workflow_undeclared_phase(root: Path) -> None:
    """Use a phase the metadata never declares (W1).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "workflows", "scratch.js"), 'phase: "Check"', 'phase: "Undeclared"')


def seed_workflow_dynamic_import(root: Path) -> None:
    """Use a dynamic import the runtime does not provide (W1).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "workflows", "scratch.js")
    _edit(path, 'log("done");', 'await import("node:fs");\nlog("done");')


def seed_rewritten_release(root: Path) -> None:
    """Rewrite a released CHANGELOG body after its tag (C2).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "CHANGELOG.md")
    _edit(path, "- The first release.", "- The first release, with a claim that was never shipped.")


def seed_eval_table(root: Path) -> None:
    """Put an eval score table with a delta column back into the README (R9).

    Args:
        root: The scratch repository root.
    """
    path = plugin_path(root, "README.md")
    _edit(
        path,
        "## 🧭 Compatibility",
        (
            "| Case | Checks | With | Without | Δ | Last run |\n"
            "| --- | --- | ---: | ---: | ---: | --- |\n"
            "| `fires` | It fires | 1.00 | 0.00 | +1.00 | 2026-09-20 |\n\n"
            "## 🧭 Compatibility"
        ),
    )


def seed_kind_mismatch(root: Path) -> None:
    """Declare a kind the files do not derive (P1).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "README.md"), "**Kind:** `bundle`", "**Kind:** `skill-only`")


def seed_placeholder(root: Path) -> None:
    """Leave a template placeholder in a shipped file (P4).

    Args:
        root: The scratch repository root.
    """
    _edit(plugin_path(root, "README.md"), "Nothing; it exists for the probes.", "{{What it does}}")


PROBES: Final[tuple[Probe, ...]] = (
    ("matcher `Write|Edit[`", "H2", seed_bad_matcher),
    ('hook `command` set to ""', "H4", seed_empty_command),
    ("fragment command pointing at a missing file", "H5", seed_missing_fragment_target),
    ("`description: a: b`", "S1", seed_unparseable_description),
    ("eval suite with no must-not-fire case", "E1", seed_no_must_not_fire),
    ("`#!/usr/bin/env -S uv run --script` shebang", "B1", seed_uv_shebang),
    ("workflow with a syntax error", "W1", seed_workflow_syntax_error),
    ("workflow whose `meta` is not a literal", "W1", seed_workflow_impure_meta),
    ("workflow using an undeclared phase", "W1", seed_workflow_undeclared_phase),
    ("workflow using `import(`", "W1", seed_workflow_dynamic_import),
    ("rewritten released CHANGELOG body", "C2", seed_rewritten_release),
    ("README with a `Δ` column", "R9", seed_eval_table),
    ("`**Kind:**` line that disagrees with the files", "P1", seed_kind_mismatch),
    ("`{{placeholder}}` in a shipped file", "P4", seed_placeholder),
)
"""Every negative probe this step owns, as Part D section 5 lists them."""


def test_the_fixture_fires_no_probe_invariant(scratch: Path) -> None:
    """The scratch plugin must pass every invariant a probe targets.

    Args:
        scratch: The scratch repository root.
    """
    probed = {invariant for _, invariant, _ in PROBES}
    assert probed.isdisjoint(ids_for(scratch))


@pytest.mark.parametrize(("name", "invariant", "seed"), PROBES, ids=[probe[0] for probe in PROBES])
def test_probe_fires_and_then_stops(
    scratch: Path, name: str, invariant: str, seed: Callable[[Path], None]
) -> None:
    """One defect fires its invariant, and stops firing once it is removed.

    Args:
        scratch: The scratch repository root.
        name: The probe's name, used in the failure message.
        invariant: The ID the defect must raise.
        seed: The edit that introduces it.
    """
    before = plugin_snapshot(scratch)
    seed(scratch)
    assert invariant in ids_for(scratch), f"{name}: {invariant} did not fire"
    restore(scratch, before)
    assert invariant not in ids_for(scratch), f"{name}: {invariant} still fires after removal"


def plugin_snapshot(root: Path) -> dict[str, str]:
    """Record every text file in the scratch plugin.

    Args:
        root: The scratch repository root.

    Returns:
        Repository-relative paths mapped to their contents.
    """
    base = root / "plugins" / PLUGIN_ID
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def restore(root: Path, snapshot: dict[str, str]) -> None:
    """Put the scratch plugin back the way the fixture built it.

    Args:
        root: The scratch repository root.
        snapshot: What `plugin_snapshot` recorded.
    """
    for rel, text in snapshot.items():
        _ = (root / rel).write_text(text, encoding="utf-8")


def test_an_untracked_file_fires_p6_until_it_is_added(scratch: Path) -> None:
    """A file git does not track is invisible to every other check, so P6 names it.

    Args:
        scratch: The scratch repository root.
    """
    extra = plugin_path(scratch, "evals", "01-fires", "scaffold.sh")
    text = "#!/usr/bin/env bash\ngit init -q\n"
    _ = extra.write_text(text, encoding="utf-8")
    assert "P6" in ids_for(scratch)
    track(scratch, extra, text, executable=True)
    assert "P6" not in ids_for(scratch)


def test_registry_lists_every_family() -> None:
    """`--list` prints every ID this repository speaks with."""
    printed = {line.split(maxsplit=1)[0] for line in registry_lines()}
    expected = {
        ident for ident, _, _ in (*PLUGIN_INVARIANTS, *GITHUB_INVARIANTS, *DEFERRED_INVARIANTS)
    }
    assert expected <= printed
    for family, count in (("M", 10), ("P", 6), ("S", 6), ("H", 6), ("R", 14), ("E", 4), ("V", 6)):
        assert (
            sum(1 for ident in printed if ident.startswith(family) and ident[1:].isdigit()) == count
        )


def test_manifest_stays_valid_json(scratch: Path) -> None:
    """The fixture's manifest is the shape the catalog invariants expect.

    Args:
        scratch: The scratch repository root.
    """
    document = load_json(plugin_path(scratch, ".claude-plugin", "plugin.json"))
    assert is_json_object(document)
    assert document["version"] == VERSION
    assert RELEASE_DATE in plugin_path(scratch, "CHANGELOG.md").read_text(encoding="utf-8")


def test_the_repository_checks_emit_g1(monkeypatch: pytest.MonkeyPatch) -> None:
    """G1 reaches `make validate`, not only the label and issue-form unit tests."""
    sentinel = Finding("G1", LABELS_PATH, "seeded by the wiring probe")

    def seeded(_root: Path) -> list[Finding]:
        return [sentinel]

    monkeypatch.setattr(labels, "validate", seeded)
    assert sentinel in collect(repo_root())
