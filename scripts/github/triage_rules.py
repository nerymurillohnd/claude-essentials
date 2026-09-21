"""What labels an issue, a comment or a pull request earns — as pure functions (ADR-0004).

Nothing here touches the network, the filesystem or the clock. `triage` reads the event,
narrows it, calls these functions and applies what they return, so every rule in this file is
testable from a table rather than from a live repository.

Three rules, one per event shape:

* **An issue opened from a form** carries an **Affected plugin** answer. It becomes
  `plugin: <id>` for a plugin that ships, `area: catalog` for a marketplace-wide problem, and
  nothing at all for "Not sure" or for a name the repository does not know. An invented label
  is worse than no label: it cannot be filtered on and the taxonomy no longer matches code.
* **A comment by the issue's author on a `status: needs-info` issue** is a reply, so the
  issue goes back to `status: needs-triage` and the stale bot stops counting.
* **A pull request** earns one `area:` label per tree it touches, a `plugin: <id>` per plugin
  directory, and the `bump:` label `check_versions` computed. The computed label replaces any
  other `bump:` label except `bump: deferred`, which the maintainer applies by hand and
  triage must never take away (§A11).

The `### Label` heading format the form answers are read from is pinned by a test: GitHub
renders issue-form answers that way, and a change upstream would silently stop labelling
issues rather than fail anything (ADR-0004's risk table).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Final

from scripts.common.jsontext import is_json_object
from scripts.github.labels import BUMP_LABEL_PREFIX, plugin_label_name
from scripts.marketplace.catalog import PLUGIN_NAME_RE

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

CATALOG_AREA: Final = "area: catalog"
PLUGINS_AREA: Final = "area: plugins"
CI_AREA: Final = "area: ci"
TOOLING_AREA: Final = "area: tooling"
TEMPLATES_AREA: Final = "area: templates"
DOCS_AREA: Final = "area: docs"
COMMUNITY_AREA: Final = "area: community"
"""The seven `area:` labels a pull request can earn."""

NEEDS_INFO: Final = "status: needs-info"
NEEDS_TRIAGE: Final = "status: needs-triage"
"""The two statuses a reply moves an issue between."""

PLUGIN_QUESTION: Final = "Affected plugin"
"""The form field whose answer becomes a `plugin:` or `area: catalog` label."""

CATALOG_ANSWER: Final = "Marketplace catalog / installation"
UNSURE_ANSWER: Final = "Not sure"
"""The two answers that are not a plugin name."""

ANSWER_HEADING: Final = re.compile(r"^###\s+(?P<question>.+?)\s*$")
"""How GitHub renders an issue-form field into the issue body."""

_COMMUNITY_FILES: Final = frozenset(
    {
        ".github/labels.json",
        ".github/pull_request_template.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
    },
)
_COMMUNITY_TREES: Final = (".github/ISSUE_TEMPLATE/", ".github/schemas/")
"""Contribution surfaces: how a problem is reported and how the project is governed."""

_CI_FILES: Final = frozenset({".github/dependabot.yml"})
_CI_TREES: Final = (".github/workflows/", ".github/policy/")
"""Everything that decides what runs on a push."""

_TOOLING_FILES: Final = frozenset(
    {"Makefile", "pyproject.toml", "uv.lock", ".python-version", ".editorconfig"},
)
_TOOLING_TREES: Final = ("scripts/", ".claude/")
"""The maintainer environment (§2.1): never shipped, always gating."""

_PLUGINS_TREE: Final = "plugins/"
_CATALOG_TREE: Final = ".claude-plugin/"
_TEMPLATES_TREE: Final = "templates/"
_DOCS_TREE: Final = "docs/"
"""The remaining trees, each with exactly one area."""


_AREA_RULES: Final[tuple[tuple[str, frozenset[str], tuple[str, ...]], ...]] = (
    (PLUGINS_AREA, frozenset(), (_PLUGINS_TREE,)),
    (CATALOG_AREA, frozenset(), (_CATALOG_TREE,)),
    (COMMUNITY_AREA, _COMMUNITY_FILES, _COMMUNITY_TREES),
    (CI_AREA, _CI_FILES, _CI_TREES),
    (TOOLING_AREA, _TOOLING_FILES, _TOOLING_TREES),
    (TEMPLATES_AREA, frozenset(), (_TEMPLATES_TREE,)),
    (DOCS_AREA, frozenset(), (_DOCS_TREE,)),
)
"""The path rules, in the order they are applied.

The order is the rule: the specific `.github/` surfaces are decided before the general ones,
and the three root governance documents before "any root Markdown file is docs".
"""


def area_for_path(path: str) -> str | None:
    """Return the `area:` label one changed path earns.

    Args:
        path: A repository-relative path.

    Returns:
        The label, or None when the path belongs to no area.
    """
    for area, files, trees in _AREA_RULES:
        if path in files or path.startswith(trees):
            return area
    if "/" not in path and path.endswith(".md"):
        return DOCS_AREA
    return None


def plugin_for_path(path: str) -> str | None:
    """Return the plugin directory a changed path belongs to.

    Args:
        path: A repository-relative path.

    Returns:
        The plugin id, or None when the path is outside a valid plugin directory.

    Note:
        A directory whose name is not a valid plugin name yields None rather than a label:
        creating `plugin: Not A Name` would put an invalid label in a taxonomy kept as code.
    """
    if not path.startswith(_PLUGINS_TREE):
        return None
    rest = path[len(_PLUGINS_TREE) :]
    head, separator, _ = rest.partition("/")
    if not separator or PLUGIN_NAME_RE.match(head) is None:
        return None
    return head


def bump_label(versions_json: object) -> str | None:
    """Read the computed `bump:` label out of `check_versions --json` output.

    Args:
        versions_json: The parsed document, or anything else.

    Returns:
        The label, or None when the document does not carry one.
    """
    if not is_json_object(versions_json):
        return None
    label = versions_json.get("label")
    if isinstance(label, str) and label.startswith(BUMP_LABEL_PREFIX):
        return label
    return None


def labels_for_pr(changed_paths: Iterable[str], versions_json: object) -> set[str]:
    """Return every label a pull request should carry.

    Args:
        changed_paths: The repository-relative paths the pull request touches.
        versions_json: The parsed `check_versions --json` document, or None when the bump
            could not be computed; the `bump:` label is then simply not applied.

    Returns:
        The `area:`, `plugin:` and `bump:` labels, as one set.
    """
    labels: set[str] = set()
    for path in changed_paths:
        area = area_for_path(path)
        if area is not None:
            labels.add(area)
        plugin_id = plugin_for_path(path)
        if plugin_id is not None:
            labels.add(plugin_label_name(plugin_id))
    computed = bump_label(versions_json)
    if computed is not None:
        labels.add(computed)
    return labels


def parse_form_answers(body: str) -> dict[str, str]:
    """Read the answers GitHub rendered into an issue body.

    Args:
        body: The issue body as the form produced it.

    Returns:
        Each `### Question` heading mapped to the text under it, blank answers included.
    """
    answers: dict[str, str] = {}
    question: str | None = None
    collected: list[str] = []
    for line in body.splitlines():
        heading = ANSWER_HEADING.match(line)
        if heading is None:
            if question is not None:
                collected.append(line)
            continue
        if question is not None:
            answers[question] = "\n".join(collected).strip()
        question = heading["question"]
        collected = []
    if question is not None:
        answers[question] = "\n".join(collected).strip()
    return answers


def labels_for_issue(
    form_answers: Mapping[str, str],
    *,
    known_plugins: Collection[str],
) -> set[str]:
    """Return the label an issue earns from its **Affected plugin** answer.

    Args:
        form_answers: The parsed form answers.
        known_plugins: The plugin ids this marketplace ships.

    Returns:
        A single-element set, or an empty set when the answer names nothing known.
    """
    answer = form_answers.get(PLUGIN_QUESTION, "").strip()
    if answer == CATALOG_ANSWER:
        return {CATALOG_AREA}
    if answer in {"", UNSURE_ANSWER} or answer not in known_plugins:
        return set()
    return {plugin_label_name(answer)}


@dataclass(frozen=True, slots=True)
class CommentEvent:
    """One `issue_comment` event, reduced to what the reply rule reads.

    Attributes:
        issue_author: The login that opened the issue.
        comment_author: The login that wrote the comment.
        issue_labels: The labels the issue carries now.
    """

    issue_author: str
    comment_author: str
    issue_labels: frozenset[str]


def needs_info_reply(event: CommentEvent) -> bool:
    """Report whether a comment is the author answering a request for information.

    Args:
        event: The narrowed comment event.

    Returns:
        True when the issue is waiting on its author and the author has just replied.
    """
    return (
        NEEDS_INFO in event.issue_labels
        and bool(event.comment_author)
        and event.comment_author == event.issue_author
    )


def reply_label_changes(event: CommentEvent) -> tuple[set[str], set[str]]:
    """Return the labels to add and remove when an author replies.

    Args:
        event: The narrowed comment event.

    Returns:
        What to add and what to remove; two empty sets when the rule does not apply.
    """
    if not needs_info_reply(event):
        return set(), set()
    return {NEEDS_TRIAGE}, {NEEDS_INFO}
