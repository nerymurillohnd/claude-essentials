"""Integrity tests: the test suite and the scripts carry no silent defects.

A test that unittest never collects, one that asserts nothing, one whose assertion cannot fail,
and a script function nothing uses all pass every gate without checking anything. These tests read
the sources with `ast` and fail for each of them. Each rule also has a negative test on a
synthetic source, so a rule that stops detecting its defect fails here too.

Run: python3 scripts/check.py tests
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING
import unittest

import check
import repo

if TYPE_CHECKING:
    from pathlib import Path

TESTS = repo.ROOT / "tests"
SCRIPTS = repo.ROOT / "scripts"
LIFECYCLE = frozenset({"setUp", "tearDown", "setUpClass", "tearDownClass"})
MAX_TEXT_BYTES = 1_000_000


def _base_names(cls: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for base in cls.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _is_test_case(cls: ast.ClassDef, classes: dict[str, ast.ClassDef], seen: set[str]) -> bool:
    """Whether the class derives from unittest.TestCase, directly or through the module."""
    seen.add(cls.name)
    for base in _base_names(cls):
        if base == "TestCase":
            return True
        parent = classes.get(base)
        if parent is not None and base not in seen and _is_test_case(parent, classes, seen):
            return True
    return False


def _methods(cls: ast.ClassDef) -> list[ast.FunctionDef]:
    return [node for node in cls.body if isinstance(node, ast.FunctionDef)]


def _is_overriding(method: ast.FunctionDef) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "override" for d in method.decorator_list)


def _is_vacuous(condition: ast.expr) -> bool:
    """An assertion condition that cannot be false: a constant, `x or True`, or `x == x`."""
    if isinstance(condition, ast.Constant):
        return bool(condition.value)
    if isinstance(condition, ast.BoolOp) and isinstance(condition.op, ast.Or):
        return any(_is_vacuous(value) for value in condition.values)
    if isinstance(condition, ast.Compare) and len(condition.ops) == 1:
        same = ast.dump(condition.left) == ast.dump(condition.comparators[0])
        return same and isinstance(condition.ops[0], ast.Eq | ast.Is | ast.LtE | ast.GtE)
    return False


def _real_assertions(method: ast.FunctionDef) -> int:
    """Assert statements that can fail, plus calls to `assert*` helpers and TestCase methods."""
    count = 0
    for node in ast.walk(method):
        if (isinstance(node, ast.Assert) and not _is_vacuous(node.test)) or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("assert")
        ):
            count += 1
    return count


def _vacuous_assertions(tree: ast.Module) -> list[int]:
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert) and _is_vacuous(n.test)]


def _is_unused(method: ast.FunctionDef, used: set[str]) -> bool:
    return method.name not in LIFECYCLE and not _is_overriding(method) and method.name not in used


def _class_problems(
    name: str, cls: ast.ClassDef, by_name: dict[str, ast.ClassDef], used: set[str]
) -> list[str]:
    methods = _methods(cls)
    names = [m.name for m in methods]
    problems = [
        f"{name}: {cls.name}.{duplicate} is defined twice"
        for duplicate in sorted({n for n in names if names.count(n) > 1})
    ]
    if not _is_test_case(cls, by_name, set()):
        if any(n.startswith("test") for n in names):
            problems.append(f"{name}: {cls.name} has tests but is not a TestCase")
        return problems
    for method in methods:
        if method.name.startswith("test") and _real_assertions(method) == 0:
            problems.append(f"{name}: {cls.name}.{method.name} asserts nothing")
        elif method.name.startswith("assert") and _real_assertions(method) == 0:
            problems.append(f"{name}: helper {cls.name}.{method.name} asserts nothing")
        elif not method.name.startswith(("test", "assert")) and _is_unused(method, used):
            problems.append(
                f"{name}: {cls.name}.{method.name} is never used (renamed test, or dead)"
            )
    return problems


def suite_problems(sources: dict[str, str]) -> list[str]:
    """Silent defects across the given test modules (name -> source)."""
    trees = {name: ast.parse(text, filename=name) for name, text in sources.items()}
    used = {
        node.attr
        for tree in trees.values()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    problems: list[str] = []
    for name, tree in trees.items():
        problems.extend(
            f"{name}:{line}: an assertion that cannot fail" for line in _vacuous_assertions(tree)
        )
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        by_name = {cls.name: cls for cls in classes}
        if len(by_name) != len(classes):
            problems.append(f"{name}: a class name is defined twice, so the first never runs")
        for cls in classes:
            problems.extend(_class_problems(name, cls, by_name, used))
    return problems


def defined_names(source: str) -> list[str]:
    """Module-level functions, classes and constants, without dunder names.

    A TestCase class is found by unittest through inheritance, never by name, so it is left out.
    """
    names: list[str] = []
    body = ast.parse(source).body
    classes = {node.name: node for node in body if isinstance(node, ast.ClassDef)}
    for node in body:
        if isinstance(node, ast.ClassDef):
            if not _is_test_case(node, classes, set()):
                names.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names.extend(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return [n for n in names if not (n.startswith("__") and n.endswith("__"))]


def orphans(modules: dict[str, str], corpus: str) -> list[str]:
    """Names defined at module level that occur nowhere in the corpus but their definition.

    The scan is textual on purpose: a name read through `getattr`, a string table or a document
    counts as used, so a hit is a name nothing mentions at all.
    """
    return [
        f"{module}: {name} is defined and never used"
        for module, source in modules.items()
        for name in defined_names(source)
        if len(re.findall(rf"\b{re.escape(name)}\b", corpus)) < 2
    ]


def tracked_files() -> list[Path]:
    """Files git tracks or would track (not ignored)."""
    result = repo.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    return [
        repo.ROOT / name
        for name in result.stdout.split("\0")
        if name and (repo.ROOT / name).is_file()
    ]


def read_text_files(paths: list[Path]) -> str:
    """The concatenated text of the files that are small text."""
    contents = [path.read_bytes() for path in paths]
    return "\n".join(
        data.decode("utf-8", errors="ignore")
        for data in contents
        if len(data) <= MAX_TEXT_BYTES and b"\0" not in data
    )


GOOD_SUITE = """\
import unittest


class Base(unittest.TestCase):
    def check_one(self) -> None:
        assert 1 + 1 == 2

    def assert_fine(self, value: int) -> None:
        assert value > 0


class Child(Base):
    def test_ok(self) -> None:
        self.check_one()
        self.assert_fine(1)
"""


class SuiteIntegrityTest(unittest.TestCase):
    """The repository's own tests have none of the silent defects."""

    def test_repository_suite_is_clean(self) -> None:
        sources = {
            path.name: path.read_text(encoding="utf-8") for path in sorted(TESTS.glob("test_*.py"))
        }
        assert sources, "no test modules found"
        problems = suite_problems(sources)
        assert problems == [], problems

    def test_good_suite_passes(self) -> None:
        assert suite_problems({"good.py": GOOD_SUITE}) == []

    def assert_detected(self, old: str, new: str, expected: str) -> None:
        assert old in GOOD_SUITE, old
        problems = suite_problems({"bad.py": GOOD_SUITE.replace(old, new)})
        assert any(expected in p for p in problems), problems

    def test_class_that_is_not_a_test_case_is_found(self) -> None:
        self.assert_detected("class Child(Base):", "class Child:", "is not a TestCase")

    def test_renamed_test_is_found(self) -> None:
        self.assert_detected("def check_one(", "def check_one_unused(", "is never used")

    def test_test_without_assertion_is_found(self) -> None:
        body = "        self.check_one()\n        self.assert_fine(1)\n"
        self.assert_detected(body, "        pass\n", "asserts nothing")

    def test_constant_assertion_is_found(self) -> None:
        self.assert_detected("assert 1 + 1 == 2", "assert True", "cannot fail")

    def test_or_true_assertion_is_found(self) -> None:
        self.assert_detected("assert 1 + 1 == 2", "assert 1 + 1 == 3 or True", "cannot fail")

    def test_tautology_is_found(self) -> None:
        self.assert_detected("assert 1 + 1 == 2", "assert 1 + 1 == 1 + 1", "cannot fail")

    def test_helper_without_assertion_is_found(self) -> None:
        self.assert_detected(
            "assert value > 0", "_ = value", "helper Base.assert_fine asserts nothing"
        )

    def test_duplicate_test_name_is_found(self) -> None:
        duplicate = "\n    def test_ok(self) -> None:\n        self.check_one()\n"
        self.assert_detected(
            "self.assert_fine(1)\n", "self.assert_fine(1)\n" + duplicate, "defined twice"
        )

    def test_duplicate_class_name_is_found(self) -> None:
        second = GOOD_SUITE.split("\n\n\n", 1)[1]
        problems = suite_problems({"bad.py": f"{GOOD_SUITE}\n\n{second}"})
        assert any("defined twice" in p for p in problems), problems


class ScriptIntegrityTest(unittest.TestCase):
    """Every Python file holds no orphan definition, and every extensionless script is gated."""

    def test_no_python_definition_is_orphaned(self) -> None:
        paths = [
            *sorted(SCRIPTS.glob("*.py")),
            *sorted(TESTS.glob("*.py")),
            *(repo.ROOT / name for name in check.EXTENSIONLESS_SCRIPTS),
        ]
        modules = {
            str(path.relative_to(repo.ROOT)): path.read_text(encoding="utf-8") for path in paths
        }
        assert modules, "no Python files found"
        found = orphans(modules, read_text_files(tracked_files()))
        assert found == [], found

    def test_orphan_is_found_and_a_use_clears_it(self) -> None:
        source = "def lonely() -> int:\n    return 1\n"
        assert orphans({"m.py": source}, source) == ["m.py: lonely is defined and never used"]
        assert orphans({"m.py": source}, source + "print(lonely())\n") == []

    def test_constants_and_classes_are_scanned(self) -> None:
        source = "LIMIT = 3\nSIZE: int = 4\n\n\nclass Thing:\n    pass\n"
        assert defined_names(source) == ["LIMIT", "SIZE", "Thing"]
        assert len(orphans({"m.py": source}, source)) == 3

    def test_test_cases_are_not_orphans_but_plain_classes_are(self) -> None:
        source = (
            "import unittest\n\n\nclass FooTest(unittest.TestCase):\n    pass\n\n\n"
            "class Plain:\n    pass\n"
        )
        assert defined_names(source) == ["Plain"]

    def test_extensionless_python_scripts_are_all_gated(self) -> None:
        found: list[str] = []
        for path in tracked_files():
            if path.suffix:
                continue
            with path.open("rb") as handle:
                first = handle.readline()
            if first.startswith(b"#!") and b"python" in first:
                found.append(str(path.relative_to(repo.ROOT)))
        assert sorted(found) == sorted(check.EXTENSIONLESS_SCRIPTS)
