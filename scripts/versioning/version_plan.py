"""The one home of the runtime-vs-exempt rule, the bump plan and the push route (ADR-0003).

Three questions are answered here, each against its own base (§A11):

1. **Did a plugin change at runtime?** Compared against its latest `<name>--v*` tag, or the
   latest tag of a predecessor the marketplace `renames` map points at. A plugin with neither
   is new.
2. **Is a bump owed?** The runtime changed, the manifest version still equals the tagged one,
   and the change was not declared deferred.
3. **Which route does this push take?** A pull request as soon as anything touches a plugin's
   runtime, a version, the `renames` map, or any path outside the closed direct-push
   allowlist; a direct push to `main` otherwise.

Two paths on that allowlist are decided by their *content* rather than by their name, because
both are files whose interesting part is generated or purely descriptive:

* `plugins/<id>/.claude-plugin/plugin.json` is exempt for the route when its runtime view
  (the parsed object minus `METADATA_KEYS`) equals the base's. A `description`, `keywords` or
  `author` edit, and a pure reformat, therefore push directly; touching anything Claude acts
  on does not.
* `.claude-plugin/marketplace.json` is exempt for the route when, parsed, it differs from the
  base in nothing but the generated `plugins` array. A change to `renames` or to any other
  top-level field takes the pull request route, and `renames` additionally forces it through
  `renames_changed`.

Both comparisons are against the **base ref**, not against the plugin's tag: the question is
what this push adds to `main`, not what the published version contains.

`EXEMPT_FILE` is the single copy of the exempt rule. `.claude/hooks/lib/plugin-paths.sh`
mirrors it for the shell hooks, and `scripts/harness/test_plugin_paths.py` runs both over one
table so the two can never drift. The defect all of this catches is a plugin whose runtime
content changes without its `version` changing: Claude Code keys its plugin cache on
`version`, so installed users keep the old copy while new installs get the new one, and both
call themselves the same version.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
from typing import TYPE_CHECKING, Final, Literal, TypeIs

from scripts.common.errors import Finding
from scripts.common.plugins import (
    MANIFEST_RELATIVE_PATH,
    PLUGINS_DIRNAME,
    as_mapping,
    as_str,
    git_output,
    git_output_or_none,
    load_json,
    parse_json,
    plugin_ids,
)
from scripts.versioning.changelog import announces_deprecation, released_body_at_tag
from scripts.versioning.semver import InvalidVersionError, Version, bump_level, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

Route = Literal["pr", "direct"]
"""Where a change may be pushed."""

PlanLevel = Literal[
    "major",
    "minor",
    "patch",
    "prerelease",
    "none",
    "invalid",
    "initial",
    "removal",
]
"""A plugin's contribution to the pull request's `bump:` label."""

EXEMPT_FILE: Final = re.compile(
    r"(?:README\.md"
    r"|CHANGELOG\.md"
    r"|LICENSE"
    r"|LICENSE\.[^/]+"
    r"|docs/.+"
    r"|evals/.+"
    r"|(?:.*/)?tests/.+"
    r"|(?:.*/)?test-[^/]+\.sh)\Z",
)
"""Paths inside `plugins/<name>/` that Claude never loads, so changing them owes no bump.

Anchored with `\\Z` rather than `$` so a stray trailing newline cannot make a path exempt.
`docs/` and `evals/` count only at the plugin root; `tests/` and `test-*.sh` count at any
depth. The list is closed: anything not matched here is runtime.
"""

METADATA_KEYS: Final = (
    "$schema",
    "version",
    "description",
    "displayName",
    "keywords",
    "author",
    "homepage",
    "repository",
    "license",
    "metadata",
)
"""`plugin.json` keys Claude does not act on, so changing one alone owes no bump."""

RUNTIME_SURFACES: Final = (
    ".claude-plugin/plugin.json",
    ".lsp.json",
    ".mcp.json",
    "agents/",
    "assets/",
    "bin/",
    "commands/",
    "hooks/",
    "monitors/",
    "output-styles/",
    "scripts/",
    "settings.json",
    "skills/",
    "workflows/",
)
"""Documentation only: what a plugin ships that Claude loads.

The rule is `EXEMPT_FILE`, not this tuple. It is written down so a reader of §A11 can see the
surfaces the closed exempt list leaves behind, and `test_version_plan` asserts that none of
them is exempt, which is what keeps the two descriptions honest.
"""

MARKETPLACE_PATH: Final = ".claude-plugin/marketplace.json"
"""Where the `renames` map lives."""

VERSIONING_INVARIANTS: Final[tuple[tuple[str, str], ...]] = (
    ("V1", "a runtime file changed since the plugin's tag but `version` did not (ADR-0003)"),
    ("V2", "a manifest version lower than the one already published"),
    ("V3", "a plugin's first release numbered something other than 0.1.0"),
    ("V4", "a plugin directory removed with no `renames` entry mapping it to null"),
    ("V5", "a removal with no prior deprecation release (warning)"),
    ("V6", "`claude plugin tag --dry-run` would refuse an untagged version"),
)
"""The invariants this area speaks with, each next to the defect it catches (P14).

V6 is emitted by `check_versions --verify-tag`; the rest come from `build_plan`.
"""

ROOT_DOCUMENTS: Final = frozenset(
    {
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CLAUDE.md",
    }
)
"""Repository-root prose a direct push to `main` may carry."""

DIRECT_PUSH_TREES: Final = (
    "docs/",
    "templates/",
    ".claude/rules/",
    ".github/ISSUE_TEMPLATE/",
    ".vscode/",
)
"""Whole trees a direct push to `main` may carry."""

DIRECT_PUSH_FILES: Final = frozenset({".github/pull_request_template.md"})
"""Single files outside those trees that a direct push to `main` may carry."""

SKILLS_TREE: Final = ".claude/skills/"
"""Repo skills may be pushed directly, except the checklists their Stop hooks enforce."""

CHECKLIST_BASENAME: Final = "checklist.json"
"""A Stop-hook checklist is a gate input, so it takes the pull request route."""

_LEVEL_ORDER: Final[tuple[PlanLevel, ...]] = (
    "none",
    "initial",
    "prerelease",
    "patch",
    "minor",
    "major",
    "removal",
)
"""Ascending precedence for the label of a pull request that touches several plugins."""


@dataclass(frozen=True, slots=True)
class TagRef:
    """The newest release tag a plugin (or one of its predecessors) carries.

    Attributes:
        tag: The tag name, for example `block-no-verify--v0.1.2`.
        version: The version the tag publishes.
        owner: The plugin directory name that tag was created for.
    """

    tag: str
    version: Version
    owner: str


@dataclass(frozen=True, slots=True)
class PluginPlan:
    """What one plugin owes, and why.

    Attributes:
        name: The plugin directory name; for a removed plugin, the name it had.
        predecessor: The name it was renamed from, or None.
        tagged: The latest published version, or None when nothing is tagged yet.
        version: The manifest version; the empty string when the plugin no longer ships.
        runtime_changed: Whether a file Claude loads differs from the tag.
        first_runtime_path: The first such file, relative to the plugin directory.
        required: Whether a bump is owed and missing.
        ok: Whether this plugin passes the gate.
        reason: One sentence a maintainer can act on.
        level: This plugin's contribution to the pull request label; never serialised.
    """

    name: str
    predecessor: str | None
    tagged: str | None
    version: str
    runtime_changed: bool
    first_runtime_path: str | None
    required: bool
    ok: bool
    reason: str
    level: PlanLevel


@dataclass(frozen=True, slots=True)
class Plan:
    """The whole answer for one working tree against one base.

    Attributes:
        route: Whether the change may be pushed to `main` directly.
        label: The `bump: <level>` label the pull request carries.
        deferred: Whether the caller declared the runtime drift deliberate.
        plugins: One entry per plugin, including the ones that were removed.
        findings: Every violation, printed by the entrypoint; never serialised.
    """

    route: Route
    label: str
    deferred: bool
    plugins: tuple[PluginPlan, ...]
    findings: tuple[Finding, ...]


def is_exempt(rel: str) -> bool:
    """Report whether a path inside a plugin is one Claude never loads.

    Args:
        rel: A path relative to `plugins/<name>/`.

    Returns:
        True when changing that file owes no version bump.
    """
    return EXEMPT_FILE.match(rel) is not None


def _is_mapping(value: object) -> TypeIs[Mapping[str, object]]:
    """Narrow a parsed JSON value to an object without inspecting its contents.

    JSON objects always have string keys, so the claim holds for anything `json.loads`
    produced. `scripts.common.plugins.as_mapping` is the raising, checked narrowing used
    wherever a bad shape must be reported against a file.

    Args:
        value: The parsed value.

    Returns:
        True when the value is a mapping.
    """
    return isinstance(value, Mapping)


def manifest_runtime_view(obj: object) -> object:
    """Return a manifest without the keys Claude does not act on.

    Args:
        obj: The parsed `plugin.json`; anything that is not an object is returned unchanged.

    Returns:
        The same document minus `METADATA_KEYS`.
    """
    if not _is_mapping(obj):
        return obj
    return {key: value for key, value in obj.items() if key not in METADATA_KEYS}


def manifest_runtime_text(obj: object) -> str:
    """Serialise the runtime view with sorted keys, mirroring the shell hook's `jq -S`.

    Args:
        obj: The parsed `plugin.json`.

    Returns:
        Canonical JSON text, stable under key reordering and reformatting.
    """
    return json.dumps(manifest_runtime_view(obj), sort_keys=True)


def changed_paths(root: Path, base: str, *pathspecs: str) -> list[str]:
    """List every repository path that differs from a base ref.

    The set is the union of what `git diff` reports between the base tree and the working
    tree (so committed and uncommitted changes both count, deletions included) and the
    untracked files git does not ignore. Renames are never followed, because a renamed
    runtime file is a runtime change.

    Args:
        root: The repository root.
        base: The ref to compare against: a tag, a branch or a commit.
        *pathspecs: Limit the answer to these paths; no pathspec means the whole tree.

    Returns:
        Sorted repository-relative paths.

    Raises:
        GitCommandFailedError: If the base ref cannot be resolved.
    """
    limit = ["--", *pathspecs] if pathspecs else []
    tracked = git_output(root, ["diff", "--name-only", "--no-renames", base, *limit])
    untracked = git_output(root, ["ls-files", "--others", "--exclude-standard", *limit])
    return sorted({line for line in (tracked + untracked).splitlines() if line})


def read_renames(root: Path, *, ref: str | None = None) -> dict[str, str | None]:
    """Read the marketplace `renames` map from the working tree or from a ref.

    Args:
        root: The repository root.
        ref: The ref to read the catalog at; the working tree when None.

    Returns:
        Old name to new name, with None marking a removal; empty when the key is absent.

    Raises:
        UnexpectedShapeError: If `renames` is not an object of strings and nulls.
    """
    path = root / MARKETPLACE_PATH
    parsed: object = {}
    if ref is None:
        if path.is_file():
            parsed = load_json(path)
    else:
        text = git_output_or_none(root, ["show", f"{ref}:{MARKETPLACE_PATH}"])
        if text is not None:
            parsed = parse_json(text, path=path)
    catalog = as_mapping(parsed, path=path)
    raw = catalog.get("renames")
    if raw is None:
        return {}
    return {
        key: None if value is None else as_str(value, path=path)
        for key, value in as_mapping(raw, path=path).items()
    }


def predecessors(name: str, renames: Mapping[str, str | None]) -> list[str]:
    """Return the names a plugin was renamed from, newest first.

    Args:
        name: The plugin's current directory name.
        renames: The marketplace `renames` map.

    Returns:
        The chain of former names; empty when the plugin was never renamed.
    """
    backwards = {new: old for old, new in renames.items() if new is not None}
    chain: list[str] = []
    current = name
    while current in backwards and backwards[current] not in chain:
        current = backwards[current]
        chain.append(current)
    return chain


def plugin_tags(root: Path, name: str) -> list[TagRef]:
    """List the release tags one plugin name carries.

    Args:
        root: The repository root.
        name: The plugin directory name the tags were created for.

    Returns:
        Every `<name>--v<version>` tag whose version is canonical, unordered.
    """
    prefix = f"{name}--v"
    output = git_output(root, ["tag", "--list", f"{prefix}*"])
    refs: list[TagRef] = []
    for line in output.splitlines():
        tag = line.strip()
        if not tag.startswith(prefix):
            continue
        try:
            version = parse(tag[len(prefix) :])
        except InvalidVersionError:
            continue
        refs.append(TagRef(tag=tag, version=version, owner=name))
    return refs


def tag_exists(root: Path, tag: str) -> bool:
    """Report whether a tag exists in this working tree.

    Args:
        root: The repository root.
        tag: The tag name, for example `block-no-verify--v0.1.2`.

    Returns:
        True when git resolves the tag.
    """
    listing = git_output(root, ["tag", "--list", tag])
    return any(line.strip() == tag for line in listing.splitlines())


def latest_tag(root: Path, *, names: Sequence[str]) -> TagRef | None:
    """Return the newest release tag across a plugin and its former names.

    Args:
        root: The repository root.
        names: The plugin's name followed by its predecessors.

    Returns:
        The tag publishing the highest version, or None when nothing is tagged.
    """
    refs = [ref for name in names for ref in plugin_tags(root, name)]
    if not refs:
        return None
    return max(refs, key=lambda ref: ref.version.sort_key())


def _relative_to_plugin(path: str, names: Sequence[str]) -> str | None:
    """Strip the `plugins/<name>/` prefix a changed path carries.

    Args:
        path: A repository-relative path.
        names: The plugin directory names that count as this plugin.

    Returns:
        The path relative to the plugin directory, or None when it belongs to another.
    """
    for name in names:
        prefix = f"{PLUGINS_DIRNAME}/{name}/"
        if path.startswith(prefix):
            return path[len(prefix) :]
    return None


def _manifest_changed(root: Path, *, tag: str, path: str) -> bool:
    """Report whether a manifest differs from its tag in anything Claude acts on.

    Args:
        root: The repository root.
        tag: The tag to compare against.
        path: The repository-relative path of the manifest in the changed set.

    Returns:
        True when the runtime view differs, so formatting and metadata edits alone are not
        enough to owe a bump.
    """
    old = git_output_or_none(root, ["show", f"{tag}:{path}"])
    full = root / path
    new = full.read_text(encoding="utf-8") if full.is_file() else None
    if old is None or new is None:
        return old != new
    before = manifest_runtime_text(parse_json(old, path=full))
    after = manifest_runtime_text(parse_json(new, path=full))
    return before != after


def first_runtime_change(root: Path, *, tag: str, names: Sequence[str]) -> str | None:
    """Return the first file Claude loads that differs between a tag and the working tree.

    Args:
        root: The repository root.
        tag: The tag that published the current version.
        names: The plugin's name followed by its predecessors, so a rename is seen as one
            plugin moving rather than as one plugin vanishing and another appearing.

    Returns:
        The path relative to the plugin directory, or None when only exempt files changed.
    """
    pathspecs = [f"{PLUGINS_DIRNAME}/{name}" for name in names]
    for path in changed_paths(root, tag, *pathspecs):
        rel = _relative_to_plugin(path, names)
        if rel is None or is_exempt(rel):
            continue
        if rel == MANIFEST_RELATIVE_PATH.as_posix() and not _manifest_changed(
            root, tag=tag, path=path
        ):
            continue
        return rel
    return None


def _plugin_path_allowed(path: str, *, known: Sequence[str]) -> bool:
    """Report whether a path under `plugins/` may be pushed to `main` directly.

    Args:
        path: A repository-relative path starting with `plugins/`.
        known: The plugin directory names that currently exist.

    Returns:
        True only for an exempt file of a plugin that still ships, or for prose sitting
        directly in `plugins/`.
    """
    rest = path[len(PLUGINS_DIRNAME) + 1 :]
    head, separator, tail = rest.partition("/")
    if not separator:
        return is_exempt(rest)
    if head not in known:
        return False
    return is_exempt(tail)


CATALOG_GENERATED_KEY: Final = "plugins"
"""The one `marketplace.json` key `generate_marketplace` owns, so a diff confined to it is
mechanical rather than a policy change."""


def _manifest_is_metadata_only(root: Path, *, base: str, path: str) -> bool:
    """Report whether a manifest differs from the base in nothing Claude acts on.

    Args:
        root: The repository root.
        base: The ref the push is measured against.
        path: The repository-relative path of the manifest.

    Returns:
        True when the runtime views are equal, so only metadata or formatting moved.
    """
    old_text = git_output_or_none(root, ["show", f"{base}:{path}"])
    full = root / path
    if old_text is None or not full.is_file():
        return False
    before = manifest_runtime_text(parse_json(old_text, path=full))
    return before == manifest_runtime_text(load_json(full))


def _catalog_is_generated_only(root: Path, *, base: str) -> bool:
    """Report whether the catalog differs from the base only in its generated array.

    Args:
        root: The repository root.
        base: The ref the push is measured against.

    Returns:
        True when every top-level key but `plugins` is unchanged.
    """
    path = root / MARKETPLACE_PATH
    old_text = git_output_or_none(root, ["show", f"{base}:{MARKETPLACE_PATH}"])
    if old_text is None or not path.is_file():
        return False
    old = parse_json(old_text, path=path)
    new = load_json(path)
    if not _is_mapping(old) or not _is_mapping(new):
        return False
    authored_old = {key: value for key, value in old.items() if key != CATALOG_GENERATED_KEY}
    authored_new = {key: value for key, value in new.items() if key != CATALOG_GENERATED_KEY}
    return authored_old == authored_new


def _is_content_exempt(root: Path, *, base: str, path: str) -> bool:
    """Report whether one changed path is cleared by its contents rather than by its name.

    Args:
        root: The repository root.
        base: The ref the push is measured against.
        path: A repository-relative path that differs from that ref.

    Returns:
        True for a metadata-only manifest, or a catalog whose only diff is `plugins`.
    """
    if path == MARKETPLACE_PATH:
        return _catalog_is_generated_only(root, base=base)
    manifest_suffix = f"/{MANIFEST_RELATIVE_PATH.as_posix()}"
    if path.startswith(f"{PLUGINS_DIRNAME}/") and path.endswith(manifest_suffix):
        return _manifest_is_metadata_only(root, base=base, path=path)
    return False


def content_exempt_paths(root: Path, *, base: str, changed: Sequence[str]) -> frozenset[str]:
    """Return the changed paths the route treats as exempt because of what they contain.

    This is the single home of the content half of the direct-push rule; the name half is
    `is_direct_push_allowed`, which takes this set and never recomputes it.

    Args:
        root: The repository root.
        base: The ref the push is measured against.
        changed: Every path that differs from that ref.

    Returns:
        The subset that carries no runtime and no policy change.
    """
    return frozenset(path for path in changed if _is_content_exempt(root, base=base, path=path))


def is_direct_push_allowed(
    path: str,
    *,
    known_plugins: Sequence[str],
    content_exempt: Collection[str] = (),
) -> bool:
    """Report whether one changed path keeps a push on the direct route (§A11).

    Args:
        path: A repository-relative path.
        known_plugins: The plugin directory names that currently exist.
        content_exempt: Paths `content_exempt_paths` cleared by comparing their contents
            against the base; passing none applies the name rule alone.

    Returns:
        True when the path is on the closed allowlist, by name or by content.
    """
    if path in content_exempt:
        return True
    if path in ROOT_DOCUMENTS or path in DIRECT_PUSH_FILES:
        return True
    if path.rpartition("/")[2] == "CLAUDE.md":
        return True
    if path.startswith(SKILLS_TREE):
        return path.rpartition("/")[2] != CHECKLIST_BASENAME
    if path.startswith(f"{PLUGINS_DIRNAME}/"):
        return _plugin_path_allowed(path, known=known_plugins)
    return any(path.startswith(tree) for tree in DIRECT_PUSH_TREES)


def route(
    *,
    plugins: Sequence[PluginPlan],
    changed: Sequence[str],
    known_plugins: Sequence[str],
    renames_changed: bool,
    content_exempt: Collection[str] = (),
) -> Route:
    """Decide whether a change may be pushed to `main` or must open a pull request.

    Args:
        plugins: The per-plugin plans.
        changed: Every path that differs from the base ref.
        known_plugins: The plugin directory names that currently exist.
        renames_changed: Whether the marketplace `renames` map differs from the base.
        content_exempt: The paths `content_exempt_paths` cleared by their contents.

    Returns:
        `"direct"` only when nothing touches a plugin's runtime, a version, the `renames`
        map or a path outside the allowlist.
    """
    if renames_changed:
        return "pr"
    for plugin in plugins:
        if plugin.runtime_changed or plugin.version != (plugin.tagged or ""):
            return "pr"
    if any(
        not is_direct_push_allowed(path, known_plugins=known_plugins, content_exempt=content_exempt)
        for path in changed
    ):
        return "pr"
    return "direct"


def label_for(plugins: Sequence[PluginPlan]) -> str:
    """Return the `bump:` label of a pull request covering several plugins.

    Args:
        plugins: The per-plugin plans.

    Returns:
        `bump: <level>`, the highest level any plugin contributes.
    """
    ranks = [_LEVEL_ORDER.index(p.level) for p in plugins if p.level in _LEVEL_ORDER]
    return f"bump: {_LEVEL_ORDER[max(ranks)] if ranks else 'none'}"


def plugin_json_obj(plugin: PluginPlan) -> dict[str, object]:
    """Render one plugin entry of the JSON contract.

    `level` is deliberately absent: it is how the label is computed, not part of the shape
    consumers read.

    Args:
        plugin: The plugin's plan.

    Returns:
        A dictionary with exactly the nine documented keys, in the documented order.
    """
    return {
        "name": plugin.name,
        "predecessor": plugin.predecessor,
        "tagged": plugin.tagged,
        "version": plugin.version,
        "runtime_changed": plugin.runtime_changed,
        "first_runtime_path": plugin.first_runtime_path,
        "required": plugin.required,
        "ok": plugin.ok,
        "reason": plugin.reason,
    }


def to_json_obj(plan: Plan) -> dict[str, object]:
    """Render a plan as the JSON contract `guard-push.sh`, CI and `repo-auditor` read.

    Args:
        plan: The plan to serialise.

    Returns:
        A dictionary with exactly the documented keys, in the documented order.
    """
    return {
        "route": plan.route,
        "label": plan.label,
        "deferred": plan.deferred,
        "plugins": [plugin_json_obj(plugin) for plugin in plan.plugins],
    }


INITIAL_VERSION: Final = "0.1.0"
"""What a plugin's first release is numbered (`bump: initial`)."""


@dataclass(frozen=True, slots=True)
class _PluginContext:
    """Everything the two planners need about one plugin that still ships.

    Attributes:
        name: The plugin directory name.
        names: That name followed by its predecessors, newest first.
        version: The manifest version exactly as written.
        parsed: The parsed version, or None when it is not canonical SemVer.
        deferred: Whether the caller declared the runtime drift deliberate.
    """

    name: str
    names: tuple[str, ...]
    version: str
    parsed: Version | None
    deferred: bool

    def predecessor(self) -> str | None:
        """Return the name this plugin was renamed from.

        Returns:
            The immediate predecessor, or None when the plugin was never renamed.
        """
        return self.names[1] if len(self.names) > 1 else None


def _manifest_path(name: str) -> str:
    """Return the repository-relative path of a plugin's manifest.

    Args:
        name: The plugin directory name.

    Returns:
        The path a finding points at.
    """
    return f"{PLUGINS_DIRNAME}/{name}/{MANIFEST_RELATIVE_PATH.as_posix()}"


def _manifest_version(root: Path, name: str) -> tuple[str, Version | None, list[Finding]]:
    """Read and parse a plugin's declared version.

    Args:
        root: The repository root.
        name: The plugin directory name.

    Returns:
        The raw text, the parsed version (None when it is not canonical) and any findings.
    """
    rel = _manifest_path(name)
    full = root / rel
    manifest = as_mapping(load_json(full), path=full)
    raw = manifest.get("version")
    if raw is None:
        return "", None, [Finding("M4", rel, "the manifest declares no `version`")]
    text = as_str(raw, path=full)
    try:
        return text, parse(text), []
    except InvalidVersionError as error:
        return text, None, [Finding("M5", rel, str(error))]


def _plan_new_plugin(context: _PluginContext) -> tuple[PluginPlan, list[Finding]]:
    """Plan a plugin that has never been tagged.

    Args:
        context: The plugin's name chain and declared version.

    Returns:
        The plan and any findings.
    """
    findings: list[Finding] = []
    ok = context.parsed is not None
    if context.parsed is not None and context.version != INITIAL_VERSION:
        findings.append(
            Finding(
                "V3",
                _manifest_path(context.name),
                f"a plugin's first release is {INITIAL_VERSION}, not {context.version}",
            ),
        )
        ok = False
    plan = PluginPlan(
        name=context.name,
        predecessor=context.predecessor(),
        tagged=None,
        version=context.version,
        runtime_changed=False,
        first_runtime_path=None,
        required=False,
        ok=ok,
        reason=f"new plugin; no {context.name}--v* tag exists yet",
        level="initial",
    )
    return plan, findings


def _tagged_reason(
    context: _PluginContext,
    tag: TagRef,
    *,
    first: str | None,
    required: bool,
    level: PlanLevel,
) -> str:
    """Phrase one sentence a maintainer can act on.

    Args:
        context: The plugin's name chain and declared version.
        tag: The tag the comparison ran against.
        first: The first runtime file that changed, or None.
        required: Whether a bump is owed and missing.
        level: The level the version actually moved by.

    Returns:
        The reason recorded on the plan.
    """
    if first is None:
        return f"no runtime change since {tag.tag}"
    if required:
        return (
            f"runtime file {first} changed since {tag.tag}; bump `version` and add a dated "
            f"CHANGELOG entry"
        )
    if context.deferred and context.version == str(tag.version):
        return f"runtime changed since {tag.tag} ({first}); deferred for this pull request"
    return (
        f"runtime changed since {tag.tag} ({first}); version moved "
        f"{tag.version} to {context.version} ({level})"
    )


def _plan_tagged_plugin(
    root: Path,
    context: _PluginContext,
    tag: TagRef,
) -> tuple[PluginPlan, list[Finding]]:
    """Plan a plugin that already has a published tag.

    Args:
        root: The repository root.
        context: The plugin's name chain and declared version.
        tag: The newest tag across that chain.

    Returns:
        The plan and any findings.
    """
    first = first_runtime_change(root, tag=tag.tag, names=context.names)
    tagged = str(tag.version)
    level: PlanLevel = (
        "invalid" if context.parsed is None else bump_level(tag.version, context.parsed)
    )
    findings: list[Finding] = []
    ok = context.parsed is not None
    if level == "invalid" and context.parsed is not None:
        findings.append(
            Finding(
                "V2",
                _manifest_path(context.name),
                f"{context.version} is lower than the published {tagged}; a version never "
                f"decreases, so ship a new PATCH that states what was reverted",
            ),
        )
        ok = False
    required = first is not None and context.version == tagged and not context.deferred
    if required:
        findings.append(
            Finding(
                "V1",
                f"{PLUGINS_DIRNAME}/{context.name}/{first}",
                f"Claude loads this file and it changed since {tag.tag}, but `version` is still "
                f"{tagged}; installed users would keep the old copy under the same version "
                f"(ADR-0003)",
            ),
        )
        ok = False
    plan = PluginPlan(
        name=context.name,
        predecessor=context.predecessor(),
        tagged=tagged,
        version=context.version,
        runtime_changed=first is not None,
        first_runtime_path=first,
        required=required,
        ok=ok,
        reason=_tagged_reason(context, tag, first=first, required=required, level=level),
        level=level,
    )
    return plan, findings


def _plan_plugin(
    root: Path,
    name: str,
    *,
    renames: Mapping[str, str | None],
    deferred: bool,
) -> tuple[PluginPlan, list[Finding]]:
    """Plan one plugin that currently ships.

    Args:
        root: The repository root.
        name: The plugin directory name.
        renames: The marketplace `renames` map.
        deferred: Whether the caller declared the runtime drift deliberate.

    Returns:
        The plan and any findings.
    """
    version, parsed, findings = _manifest_version(root, name)
    context = _PluginContext(
        name=name,
        names=(name, *predecessors(name, renames)),
        version=version,
        parsed=parsed,
        deferred=deferred,
    )
    tag = latest_tag(root, names=context.names)
    if tag is None:
        plan, more = _plan_new_plugin(context)
    else:
        plan, more = _plan_tagged_plugin(root, context, tag)
    return plan, [*findings, *more]


def _removal_findings(
    root: Path, name: str, tag: TagRef | None, *, declared: bool
) -> list[Finding]:
    """Report what is missing around a plugin whose directory is gone.

    Args:
        root: The repository root.
        name: The name the plugin had.
        tag: Its newest tag, or None when it was never released.
        declared: Whether `renames` carries the `"<name>": null` entry.

    Returns:
        V4 when the removal is undeclared, or a V5 warning when no deprecation preceded it.
    """
    if not declared:
        return [
            Finding(
                "V4",
                MARKETPLACE_PATH,
                f'`{PLUGINS_DIRNAME}/{name}/` is gone but `renames` has no `"{name}": null` '
                f"entry, so the catalog still offers a plugin that no longer exists",
            ),
        ]
    if tag is None:
        return []
    body = released_body_at_tag(root, name, str(tag.version), tag=tag.tag, directory=tag.owner)
    if body is not None and announces_deprecation(body):
        return []
    return [
        Finding(
            "V5",
            MARKETPLACE_PATH,
            f"{name} was removed without a prior deprecation release: {tag.tag} carries no "
            f"`### Deprecated` section, so an emergency removal needs a docs/maintenance/ "
            f"entry and a security advisory",
            "warning",
        ),
    ]


def _plan_removed(
    root: Path,
    name: str,
    *,
    renames: Mapping[str, str | None],
    declared: bool,
) -> tuple[PluginPlan, list[Finding]]:
    """Plan a plugin whose directory is gone.

    Args:
        root: The repository root.
        name: The name the plugin had.
        renames: The marketplace `renames` map.
        declared: Whether `renames` carries the `"<name>": null` entry that authorises this.

    Returns:
        The plan and any findings.
    """
    names = (name, *predecessors(name, renames))
    tag = latest_tag(root, names=names)
    plan = PluginPlan(
        name=name,
        predecessor=names[1] if len(names) > 1 else None,
        tagged=None if tag is None else str(tag.version),
        version="",
        runtime_changed=False,
        first_runtime_path=None,
        required=False,
        ok=declared,
        reason=(
            "removed; `renames` maps it to null" if declared else "removed with no `renames` entry"
        ),
        level="removal",
    )
    return plan, _removal_findings(root, name, tag, declared=declared)


def plugin_ids_at(root: Path, ref: str) -> list[str]:
    """List the plugins that shipped at a ref.

    Args:
        root: The repository root.
        ref: The ref to inspect.

    Returns:
        Sorted plugin directory names; empty when the ref has no `plugins/` tree.
    """
    listing = git_output_or_none(
        root,
        ["ls-tree", "-r", "--name-only", ref, "--", f"{PLUGINS_DIRNAME}/"],
    )
    if listing is None:
        return []
    prefix = f"{PLUGINS_DIRNAME}/"
    suffix = f"/{MANIFEST_RELATIVE_PATH.as_posix()}"
    names = {
        line[len(prefix) : -len(suffix)]
        for line in listing.splitlines()
        if line.startswith(prefix) and line.endswith(suffix)
    }
    return sorted(name for name in names if "/" not in name)


def build_plan(root: Path, *, base: str, deferred: bool = False) -> Plan:
    """Answer all three §A11 questions for one working tree against one base.

    Args:
        root: The repository root.
        base: The ref the route is measured against, normally `origin/main`.
        deferred: Whether the pull request carries the `bump: deferred` label.

    Returns:
        The plan, with one entry per plugin that ships and per plugin that was removed.

    Raises:
        GitCommandFailedError: If the base ref cannot be resolved.
    """
    renames = read_renames(root)
    known = plugin_ids(root)
    plans: list[PluginPlan] = []
    findings: list[Finding] = []
    for name in known:
        plan, found = _plan_plugin(root, name, renames=renames, deferred=deferred)
        plans.append(plan)
        findings.extend(found)
    for name in plugin_ids_at(root, base):
        if name in known or renames.get(name) is not None:
            continue
        plan, found = _plan_removed(root, name, renames=renames, declared=name in renames)
        plans.append(plan)
        findings.extend(found)
    changed = changed_paths(root, base)
    return Plan(
        route=route(
            plugins=plans,
            changed=changed,
            known_plugins=known,
            renames_changed=renames != read_renames(root, ref=base),
            content_exempt=content_exempt_paths(root, base=base, changed=changed),
        ),
        label=label_for(plans),
        deferred=deferred,
        plugins=tuple(plans),
        findings=tuple(findings),
    )
