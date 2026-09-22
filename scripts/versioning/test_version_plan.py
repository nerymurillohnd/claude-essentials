"""Tests for the exempt rule, the bump plan and the §A11 route matrix.

The route table is fourteen named cases, each built in a real temporary repository with a
real tag, because the answer depends on `git diff`, `git ls-tree` and `git tag` behaving the
way the shell hook's mirror expects.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import as_mapping, load_json
from scripts.versioning.changelog import announces_deprecation, parse_changelog
from scripts.versioning.conftest import (
    changelog_text,
    commit_all,
    fetch_as_pull_request,
    git_in,
    make_plugin,
    manifest_text,
    marketplace_text,
    write_file,
)
from scripts.versioning.version_plan import (
    METADATA_KEYS,
    RUNTIME_SURFACES,
    VERSIONING_INVARIANTS,
    Plan,
    PlanLevel,
    PluginPlan,
    build_plan,
    changed_paths,
    content_exempt_paths,
    is_direct_push_allowed,
    is_exempt,
    label_for,
    manifest_runtime_text,
    manifest_runtime_view,
    plugin_json_obj,
    predecessors,
    read_renames,
    to_json_obj,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from scripts.common.errors import Finding

TODAY: Final = "2026-09-21"
JSON_KEYS: Final = (
    "name",
    "predecessor",
    "tagged",
    "version",
    "runtime_changed",
    "first_runtime_path",
    "required",
    "ok",
    "reason",
)


def plan_both(repo: Path, *, base: str, deferred: bool = False) -> Plan:
    """Plan the working tree, and the same change read as a fetched head ref; they must agree.

    Every route-table case therefore runs twice: once as `guard-push.sh` sees it (working
    tree, untracked files included) and once as `triage.yml` sees it (`--head FETCH_HEAD` in a
    base-only clone whose working tree never holds the change).

    Args:
        repo: The source repository.
        base: The ref the route is measured against.
        deferred: Whether the pull request carries `bump: deferred`.

    Returns:
        The working-tree plan, for the case's own assertions.
    """
    from_tree = build_plan(repo, base=base, deferred=deferred)
    scratch = Path(tempfile.mkdtemp(prefix="head-probe-"))
    try:
        clone = fetch_as_pull_request(repo, scratch / "base")
        from_head = build_plan(clone, base=base, deferred=deferred, head="FETCH_HEAD")
    finally:
        shutil.rmtree(scratch)
    assert to_json_obj(from_head) == to_json_obj(from_tree)
    assert from_head.findings == from_tree.findings
    return from_tree


def _deprecate_alpha(root: Path) -> None:
    """Publish `alpha--v0.2.0`, a deprecation release, on top of the fixture.

    Args:
        root: The repository root.
    """
    base = root / "plugins" / "alpha"
    write_file(base / ".claude-plugin" / "plugin.json", manifest_text("alpha", "0.2.0"))
    write_file(base / "CHANGELOG.md", changelog_text("alpha", "0.2.0", deprecated=True))
    _ = commit_all(root, "deprecate alpha")
    _ = git_in(root, "tag", "alpha--v0.2.0")


def _plan_of(plan: Plan, name: str) -> PluginPlan:
    """Return one plugin's entry.

    Args:
        plan: The whole plan.
        name: The plugin id to look up.

    Returns:
        That plugin's plan.
    """
    for plugin in plan.plugins:
        if plugin.name == name:
            return plugin
    message = f"{name} is not in the plan"
    raise AssertionError(message)


def _ids(findings: Sequence[Finding]) -> list[str]:
    """Collect the invariant ids of a finding sequence.

    Args:
        findings: The findings to read.

    Returns:
        Their ids, in order.
    """
    return [finding.invariant_id for finding in findings]


# ---------------------------------------------------------------------------
# The exempt rule and the pure helpers
# ---------------------------------------------------------------------------


def test_no_runtime_surface_is_exempt() -> None:
    """The documented runtime surfaces and the closed exempt list must not overlap."""
    for surface in RUNTIME_SURFACES:
        probe = surface if not surface.endswith("/") else f"{surface}thing.md"
        assert not is_exempt(probe), probe


def test_manifest_runtime_view_drops_every_metadata_key() -> None:
    """Metadata edits alone never owe a bump, so they leave the runtime view untouched."""
    manifest: dict[str, object] = dict.fromkeys(METADATA_KEYS, "x")
    manifest["hooks"] = {"PreToolUse": []}
    assert manifest_runtime_view(manifest) == {"hooks": {"PreToolUse": []}}


def test_manifest_runtime_view_passes_a_non_object_through() -> None:
    """A manifest that is not an object is handed back for the shape check to report."""
    assert manifest_runtime_view([1, 2]) == [1, 2]


def test_manifest_runtime_text_is_stable_under_reordering() -> None:
    """Key order and indentation are formatting; the runtime comparison ignores both."""
    first = manifest_runtime_text({"name": "a", "hooks": {"b": 1, "a": 2}})
    second = manifest_runtime_text({"hooks": {"a": 2, "b": 1}, "name": "a"})
    assert first == second


def test_predecessors_walks_a_rename_chain() -> None:
    """A plugin renamed twice still finds the tags of both former names."""
    renames: dict[str, str | None] = {"one": "two", "two": "three", "gone": None}
    assert predecessors("three", renames) == ["two", "one"]
    assert predecessors("one", renames) == []


ALLOWED_PATHS: Final = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CLAUDE.md",
    "plugins/CLAUDE.md",
    "docs/decisions/adr-0003.md",
    "templates/plugin-bundle/README.md",
    ".claude/rules/plugin-delivery.md",
    ".claude/skills/pr-delivery/SKILL.md",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".vscode/settings.json",
    "plugins/alpha/README.md",
    "plugins/alpha/docs/design.md",
    "plugins/alpha/evals/cases/a.md",
    "plugins/alpha/tests/run.sh",
)
"""Everything the §A11 allowlist names, which may be pushed straight to `main`."""

DENIED_PATHS: Final = (
    ".claude/skills/pr-delivery/checklist.json",
    "plugins/alpha/skills/demo/SKILL.md",
    "plugins/alpha/.claude-plugin/plugin.json",
    "plugins/ghost/README.md",
    "scripts/versioning/version_plan.py",
    "Makefile",
    ".github/workflows/ci.yml",
    ".claude/hooks/guard-push.sh",
    ".claude-plugin/marketplace.json",
)
"""Paths the allowlist does not name, each of which forces the pull request route."""


@pytest.mark.parametrize("path", ALLOWED_PATHS)
def test_direct_push_allowlist_admits_what_it_names(path: str) -> None:
    """Prose, templates, rules, skills and a plugin's exempt files stay on the direct route."""
    assert is_direct_push_allowed(path, known_plugins=["alpha"])


@pytest.mark.parametrize("path", DENIED_PATHS)
def test_direct_push_allowlist_is_closed(path: str) -> None:
    """Anything the name rule does not admit takes the pull request route.

    The gate and its inputs are the case that matters: a change to them must be reviewed. Two
    of these paths, a plugin manifest and the catalog, can still be admitted by the content
    rule; this asserts the name rule alone, with no `content_exempt` set.
    """
    assert not is_direct_push_allowed(path, known_plugins=["alpha"])


def test_content_exempt_admits_a_path_the_name_rule_denies() -> None:
    """The content half is injected, never recomputed inside the name rule."""
    path = "plugins/alpha/.claude-plugin/plugin.json"
    assert not is_direct_push_allowed(path, known_plugins=["alpha"])
    assert is_direct_push_allowed(path, known_plugins=["alpha"], content_exempt={path})


def test_label_for_takes_the_highest_level() -> None:
    """A pull request touching several plugins carries the highest bump they owe."""

    def plan(name: str, level: PlanLevel) -> PluginPlan:
        return PluginPlan(
            name=name,
            predecessor=None,
            tagged="0.1.0",
            version="0.1.1",
            runtime_changed=True,
            first_runtime_path="skills/demo/SKILL.md",
            required=False,
            ok=True,
            reason="",
            level=level,
        )

    assert label_for([plan("a", "patch"), plan("b", "minor")]) == "bump: minor"
    assert label_for([]) == "bump: none"


def test_versioning_invariants_are_documented() -> None:
    """P14: every id this area prints has its defect written down next to it."""
    ids = [identifier for identifier, _ in VERSIONING_INVARIANTS]
    assert ids == ["V1", "V2", "V3", "V4", "V5", "V6"]
    assert all(description for _, description in VERSIONING_INVARIANTS)


# ---------------------------------------------------------------------------
# The route table — fourteen cases, one temporary repository each
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_route_runtime(repo: Path) -> None:
    """A skill edit with no bump: pull request, and the bump is owed (V1)."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nChanged.\n")
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "pr"
    assert plan.label == "bump: none"
    assert alpha.runtime_changed
    assert alpha.first_runtime_path == "skills/demo/SKILL.md"
    assert alpha.required
    assert not alpha.ok
    assert _ids(plan.findings) == ["V1"]


@pytest.mark.slow
def test_route_runtime_with_a_bump_passes(repo: Path) -> None:
    """The same edit with a PATCH bump owes nothing and labels the pull request."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nChanged.\n")
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "pr"
    assert plan.label == "bump: patch"
    assert alpha.runtime_changed
    assert not alpha.required
    assert alpha.ok
    assert plan.findings == ()


@pytest.mark.slow
def test_route_exempt_only(repo: Path) -> None:
    """A README edit is exempt, so it may be pushed straight to `main`."""
    write_file(
        repo / "plugins/alpha/README.md", "# alpha\n\n**Kind:** skill-only\n\nBetter prose.\n"
    )
    plan = plan_both(repo, base="main")
    assert plan.route == "direct"
    assert plan.label == "bump: none"
    assert not _plan_of(plan, "alpha").runtime_changed
    assert plan.findings == ()


@pytest.mark.slow
def test_route_evals_only(repo: Path) -> None:
    """Eval cases are never loaded by Claude, so they owe no bump and stay direct."""
    write_file(repo / "plugins/alpha/evals/cases/a.md", "A better case.\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "direct"
    assert not _plan_of(plan, "alpha").runtime_changed


@pytest.mark.slow
def test_route_tests_only(repo: Path) -> None:
    """A plugin's own test suite is exempt at any depth."""
    write_file(repo / "plugins/alpha/tests/run.sh", "#!/usr/bin/env bash\nexit 1\n")
    write_file(repo / "plugins/alpha/skills/demo/tests/unit.sh", "#!/usr/bin/env bash\nexit 0\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "direct"
    assert not _plan_of(plan, "alpha").runtime_changed


@pytest.mark.slow
def test_route_gate_only(repo: Path) -> None:
    """The gate and its inputs are outside the allowlist: pull request, but no bump."""
    write_file(repo / "scripts" / "versioning" / "thing.py", "# @ts-nothing\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"
    assert plan.label == "bump: none"
    assert not _plan_of(plan, "alpha").runtime_changed
    assert plan.findings == ()


@pytest.mark.slow
def test_route_formatting_only_plugin_json(repo: Path) -> None:
    """Reindenting and reordering a manifest changes nothing Claude loads, so it pushes direct."""
    path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(path), path=path)
    reordered = {key: manifest[key] for key in sorted(manifest, reverse=True)}
    write_file(
        repo / "plugins/alpha/.claude-plugin/plugin.json",
        json.dumps(reordered, indent=4) + "\n",
    )
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert not alpha.runtime_changed
    assert alpha.first_runtime_path is None
    assert alpha.ok
    assert plan.route == "direct"
    assert plan.label == "bump: none"


@pytest.mark.slow
def test_content_exempt_paths_clears_only_what_it_should(repo: Path) -> None:
    """The single home of the content rule, exercised directly rather than through `route`."""
    manifest_path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(manifest_path), path=manifest_path)
    manifest["description"] = "Changed prose."
    write_file(manifest_path, json.dumps(manifest, indent=2) + "\n")
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    changed = changed_paths(repo, "main")
    cleared = content_exempt_paths(repo, base="main", changed=changed)
    assert cleared == {"plugins/alpha/.claude-plugin/plugin.json"}
    assert "plugins/alpha/skills/demo/SKILL.md" in changed


@pytest.mark.slow
def test_content_exempt_paths_refuses_a_manifest_that_moved_runtime(repo: Path) -> None:
    """The negative half of the rule, asserted on the helper itself.

    Through `route` this case is masked: a runtime manifest edit is already a pull request
    because the plugin's runtime changed. The helper is the single home of the rule, so it is
    what has to refuse.
    """
    path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(path), path=path)
    manifest["description"] = "Changed prose."
    manifest["hooks"] = "./hooks/hooks.json"
    write_file(path, json.dumps(manifest, indent=2) + "\n")
    changed = changed_paths(repo, "main")
    assert "plugins/alpha/.claude-plugin/plugin.json" in changed
    assert content_exempt_paths(repo, base="main", changed=changed) == frozenset()


@pytest.mark.slow
def test_content_exempt_paths_refuses_a_catalog_that_moved_policy(repo: Path) -> None:
    """The same negative for the catalog: only the generated array may differ."""
    path = repo / ".claude-plugin/marketplace.json"
    write_file(path, marketplace_text({"ghost": None}))
    changed = changed_paths(repo, "main")
    assert ".claude-plugin/marketplace.json" in changed
    assert content_exempt_paths(repo, base="main", changed=changed) == frozenset()


@pytest.mark.slow
def test_route_metadata_only_plugin_json(repo: Path) -> None:
    """A description or keywords edit is metadata: no bump, and no pull request either."""
    path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(path), path=path)
    manifest["description"] = "A better sentence about alpha."
    manifest["keywords"] = ["alpha", "demo"]
    write_file(path, json.dumps(manifest, indent=2) + "\n")
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "direct"
    assert plan.label == "bump: none"
    assert not alpha.runtime_changed
    assert alpha.ok
    assert plan.findings == ()


@pytest.mark.slow
def test_route_metadata_edit_that_touches_runtime_is_a_pull_request(repo: Path) -> None:
    """The content rule is not a blanket pass for the manifest: `hooks` is runtime."""
    path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(path), path=path)
    manifest["description"] = "A better sentence about alpha."
    manifest["hooks"] = "./hooks/hooks.json"
    write_file(path, json.dumps(manifest, indent=2) + "\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"
    assert _plan_of(plan, "alpha").runtime_changed


@pytest.mark.slow
def test_route_catalog_plugins_array_only(repo: Path) -> None:
    """`plugins[]` is generated, so regenerating it after a metadata edit stays direct."""
    path = repo / "plugins/alpha/.claude-plugin/plugin.json"
    manifest = as_mapping(load_json(path), path=path)
    manifest["description"] = "A better sentence about alpha."
    write_file(path, json.dumps(manifest, indent=2) + "\n")
    catalog = as_mapping(load_json(repo / ".claude-plugin/marketplace.json"), path=path)
    catalog["plugins"] = [{"name": "alpha", "description": "A better sentence about alpha."}]
    write_file(repo / ".claude-plugin/marketplace.json", json.dumps(catalog, indent=2) + "\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "direct"
    assert plan.label == "bump: none"
    assert plan.findings == ()


@pytest.mark.slow
def test_route_catalog_renames_changed(repo: Path) -> None:
    """`renames` is policy, not generated output: it always takes the pull request route."""
    write_file(repo / ".claude-plugin/marketplace.json", marketplace_text({"ghost": None}))
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"


@pytest.mark.slow
def test_route_catalog_top_level_field_changed(repo: Path) -> None:
    """Any authored catalog field outside `plugins[]` is reviewed, not pushed directly."""
    path = repo / ".claude-plugin/marketplace.json"
    catalog = as_mapping(load_json(path), path=path)
    catalog["name"] = "renamed-market"
    write_file(path, json.dumps(catalog, indent=2) + "\n")
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"


@pytest.mark.slow
def test_route_new_plugin(repo: Path) -> None:
    """A plugin with no tag starts at 0.1.0 and labels the pull request `initial`."""
    make_plugin(repo, "beta", "0.1.0")
    plan = plan_both(repo, base="main")
    beta = _plan_of(plan, "beta")
    assert plan.route == "pr"
    assert plan.label == "bump: initial"
    assert beta.tagged is None
    assert not beta.runtime_changed
    assert beta.ok
    assert plan.findings == ()


@pytest.mark.slow
def test_route_new_plugin_must_start_at_the_initial_version(repo: Path) -> None:
    """V3: a first release numbered anything else fails the gate."""
    make_plugin(repo, "beta", "1.0.0")
    plan = plan_both(repo, base="main")
    assert not _plan_of(plan, "beta").ok
    assert _ids(plan.findings) == ["V3"]


@pytest.mark.slow
def test_route_rename(repo: Path) -> None:
    """A rename keeps the version line, needs MINOR while below 1.0, and finds the old tag."""
    _ = git_in(repo, "mv", "plugins/alpha", "plugins/gamma")
    write_file(repo / "plugins/gamma/.claude-plugin/plugin.json", manifest_text("gamma", "0.2.0"))
    write_file(repo / ".claude-plugin/marketplace.json", marketplace_text({"alpha": "gamma"}))
    plan = plan_both(repo, base="main")
    gamma = _plan_of(plan, "gamma")
    assert plan.route == "pr"
    assert plan.label == "bump: minor"
    assert gamma.predecessor == "alpha"
    assert gamma.tagged == "0.1.0"
    assert gamma.runtime_changed
    assert gamma.ok
    assert [plugin.name for plugin in plan.plugins] == ["gamma"]


@pytest.mark.slow
def test_route_deprecation(repo: Path) -> None:
    """A deprecation release is an ordinary MINOR whose notes carry `### Deprecated`."""
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.2.0"))
    write_file(
        repo / "plugins/alpha/CHANGELOG.md", changelog_text("alpha", "0.2.0", deprecated=True)
    )
    write_file(
        repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nDeprecated.\n"
    )
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "pr"
    assert plan.label == "bump: minor"
    assert alpha.ok
    section = parse_changelog((repo / "plugins/alpha/CHANGELOG.md").read_text()).find("0.2.0")
    assert section is not None
    assert announces_deprecation(section.body)


@pytest.mark.slow
def test_route_removal(repo: Path) -> None:
    """A removal after a deprecation release is labelled `bump: removal`, with no warning."""
    _deprecate_alpha(repo)
    shutil.rmtree(repo / "plugins" / "alpha")
    write_file(repo / ".claude-plugin/marketplace.json", marketplace_text({"alpha": None}))
    plan = plan_both(repo, base="main")
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "pr"
    assert plan.label == "bump: removal"
    assert alpha.version == ""
    assert alpha.tagged == "0.2.0"
    assert alpha.ok
    assert plan.findings == ()


@pytest.mark.slow
def test_route_emergency_removal(repo: Path) -> None:
    """A removal with no deprecation release takes the same route, flagged by a V5 warning."""
    shutil.rmtree(repo / "plugins" / "alpha")
    write_file(repo / ".claude-plugin/marketplace.json", marketplace_text({"alpha": None}))
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"
    assert plan.label == "bump: removal"
    assert _plan_of(plan, "alpha").ok
    assert _ids(plan.findings) == ["V5"]
    assert plan.findings[0].severity == "warning"


@pytest.mark.slow
def test_route_removal_without_a_renames_entry_fails(repo: Path) -> None:
    """V4: a directory that simply disappears leaves the catalog offering a ghost."""
    shutil.rmtree(repo / "plugins" / "alpha")
    plan = plan_both(repo, base="main")
    assert not _plan_of(plan, "alpha").ok
    assert _ids(plan.findings) == ["V4"]


@pytest.mark.slow
def test_route_multi_plugin(repo: Path) -> None:
    """With two bumps in one pull request the label is the higher of the two."""
    make_plugin(repo, "beta", "0.1.0")
    _ = commit_all(repo, "add beta")
    _ = git_in(repo, "tag", "beta--v0.1.0")
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nFixed.\n")
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    write_file(repo / "plugins/beta/skills/demo/SKILL.md", "---\nname: beta\n---\n\nNew skill.\n")
    write_file(repo / "plugins/beta/.claude-plugin/plugin.json", manifest_text("beta", "0.2.0"))
    plan = plan_both(repo, base="main")
    assert plan.route == "pr"
    assert plan.label == "bump: minor"
    assert _plan_of(plan, "alpha").level == "patch"
    assert _plan_of(plan, "beta").level == "minor"
    assert plan.findings == ()


@pytest.mark.slow
def test_route_deferred_merge(repo: Path) -> None:
    """`bump: deferred` allows the drift on purpose: still a pull request, but nothing owed."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nChanged.\n")
    plan = plan_both(repo, base="main", deferred=True)
    alpha = _plan_of(plan, "alpha")
    assert plan.route == "pr"
    assert plan.deferred
    assert alpha.runtime_changed
    assert not alpha.required
    assert alpha.ok
    assert plan.findings == ()
    assert to_json_obj(plan)["deferred"] is True


@pytest.mark.slow
def test_route_post_merge_push(repo: Path) -> None:
    """The push event asks the same question against `BEFORE` and gets the same answer."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nChanged.\n")
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    before = git_in(repo, "rev-parse", "HEAD").strip()
    from_worktree = plan_both(repo, base="main")
    _ = commit_all(repo, "release alpha 0.1.1")
    from_push = plan_both(repo, base=before)
    assert from_push.route == from_worktree.route == "pr"
    assert from_push.label == from_worktree.label == "bump: patch"
    assert to_json_obj(from_push) == to_json_obj(from_worktree)


# ---------------------------------------------------------------------------
# The JSON contract and the catalog reader
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_json_contract_has_exactly_the_documented_keys(repo: Path) -> None:
    """`guard-push.sh`, CI and `repo-auditor` read this shape; it may not grow silently."""
    plan = plan_both(repo, base="main")
    payload = to_json_obj(plan)
    assert list(payload) == ["route", "label", "deferred", "plugins"]
    assert tuple(plugin_json_obj(plan.plugins[0])) == JSON_KEYS
    assert json.loads(json.dumps(payload)) is not None


@pytest.mark.slow
def test_read_renames_defaults_to_an_empty_map(repo: Path) -> None:
    """A catalog with no `renames` key is not an error; nothing has been renamed yet."""
    assert read_renames(repo) == {}
    assert read_renames(repo, ref="main") == {}


@pytest.mark.slow
def test_read_renames_reads_both_the_tree_and_a_ref(repo: Path) -> None:
    """The route needs the map on both sides to tell whether it changed."""
    write_file(repo / ".claude-plugin/marketplace.json", marketplace_text({"alpha": None}))
    assert read_renames(repo) == {"alpha": None}
    assert read_renames(repo, ref="main") == {}


# ---------------------------------------------------------------------------
# The head side read as git objects (triage under pull_request_target, ADR-0004)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_a_head_ref_never_checked_out_is_classified(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The clone's working tree is the base; the runtime change exists only as objects."""
    skill = "plugins/alpha/skills/demo/SKILL.md"
    write_file(repo / skill, "---\nname: alpha\n---\n\nChanged.\n")
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    clone = fetch_as_pull_request(repo, tmp_path_factory.mktemp("probe") / "base")
    assert git_in(clone, "status", "--porcelain") == ""
    assert (clone / skill).read_text(encoding="utf-8").endswith("Do the thing.\n")
    plan = build_plan(clone, base="main", head="FETCH_HEAD")
    alpha = _plan_of(plan, "alpha")
    assert plan.label == "bump: patch"
    assert alpha.first_runtime_path == "skills/demo/SKILL.md"
    assert alpha.version == "0.1.1"


@pytest.mark.slow
def test_the_head_mode_ignores_the_checkout_it_runs_in(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Untracked or edited files in the base checkout must never leak into the head side."""
    clone = fetch_as_pull_request(repo, tmp_path_factory.mktemp("probe") / "base")
    write_file(clone / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nLocal.\n")
    write_file(clone / "plugins/alpha/hooks/hooks.json", "{}\n")
    assert changed_paths(clone, "main", head="FETCH_HEAD") == []
    plan = build_plan(clone, base="main", head="FETCH_HEAD")
    assert plan.label == "bump: none"
    assert not _plan_of(plan, "alpha").runtime_changed
    assert build_plan(clone, base="main").label == "bump: none"
    assert _plan_of(build_plan(clone, base="main"), "alpha").runtime_changed
