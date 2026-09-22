"""Tests for L3: the byte rules, and that they are read from `.editorconfig` rather than copied."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.lint.conftest import write_file
from scripts.lint.text_files import INVARIANT, check, fix, is_binary, repaired, settings_for

if TYPE_CHECKING:
    from pathlib import Path


def _messages(root: Path, rel: str) -> list[str]:
    """Run the checker over one file and return what it said.

    Args:
        root: The tree to check in.
        rel: The repository-relative path.

    Returns:
        One message per finding.
    """
    findings = check(root, [rel])
    assert all(finding.invariant_id == INVARIANT for finding in findings)
    return [finding.message for finding in findings]


def test_the_rules_come_from_editorconfig(tree: Path) -> None:
    """A second copy of the policy would drift; the file itself is the source."""
    assert settings_for(tree, "a.sh")["trim_trailing_whitespace"] == "true"
    assert settings_for(tree, "a.md")["trim_trailing_whitespace"] == "false"


def test_a_clean_file_passes(tree: Path) -> None:
    """The control: UTF-8, LF, one final newline, nothing trailing."""
    write_file(tree / "a.md", "# Title\n\nBody.\n")
    assert _messages(tree, "a.md") == []


def test_a_missing_final_newline_is_reported(tree: Path) -> None:
    """Without it, appending one line shows as a two-line change forever after."""
    write_file(tree / "a.md", "# Title")
    assert any("no final newline" in message for message in _messages(tree, "a.md"))


def test_a_carriage_return_is_reported(tree: Path) -> None:
    """One CRLF file makes every later diff whole-file and invisible in review."""
    _ = (tree / "a.md").write_bytes(b"# Title\r\n")
    assert any("carriage return" in message for message in _messages(tree, "a.md"))


def test_a_control_character_is_reported_with_its_code_point(tree: Path) -> None:
    r"""A `\u0000` that a writer turned into a literal byte is invisible in a diff."""
    write_file(tree / "a.md", "before\x00after\n")
    assert any("U+0000" in message for message in _messages(tree, "a.md"))


def test_a_tab_is_not_a_control_character_defect(tree: Path) -> None:
    """Makefiles and shell here-documents need tabs; `.editorconfig` allows them."""
    write_file(tree / "a.md", "col\tcol\n")
    assert _messages(tree, "a.md") == []


def test_trailing_whitespace_is_reported_where_editorconfig_says_so(tree: Path) -> None:
    """Every `.sh` and `.py` file is trimmed, so an editor never produces phantom diffs."""
    write_file(tree / "a.sh", "#!/usr/bin/env bash\necho hi   \n")
    assert any("trailing whitespace" in message for message in _messages(tree, "a.sh"))


def test_markdown_keeps_its_trailing_whitespace(tree: Path) -> None:
    """Two trailing spaces are a hard line break in Markdown, which is why the rule is off."""
    write_file(tree / "a.md", "line one  \nline two\n")
    assert _messages(tree, "a.md") == []


def test_invalid_utf8_is_reported(tree: Path) -> None:
    """A file that is neither binary nor decodable is a defect, not something to skip."""
    _ = (tree / "a.md").write_bytes(b"caf\xe9\n")
    assert any("not valid UTF-8" in message for message in _messages(tree, "a.md"))


def test_a_binary_file_is_skipped(tree: Path) -> None:
    """An icon or a font has no line endings to be wrong about."""
    _ = (tree / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    assert _messages(tree, "logo.png") == []


def test_is_binary_needs_a_null_byte_and_an_undecodable_stream() -> None:
    """A null byte inside decodable text is the defect, so it must not count as binary."""
    assert is_binary(b"\x89PNG\x00\x00")
    assert not is_binary(b"text\x00text")
    assert not is_binary(b"a\tb\n")


def test_fix_repairs_what_it_may_and_leaves_the_rest(tree: Path) -> None:
    """A writer that deleted control bytes would destroy content rather than format it."""
    path = tree / "a.sh"
    _ = path.write_bytes(b"#!/usr/bin/env bash\r\necho hi   \nbell\x07")
    assert fix(tree, ["a.sh"]) == ["a.sh"]
    assert path.read_text(encoding="utf-8") == "#!/usr/bin/env bash\necho hi\nbell\x07\n"
    assert any("U+0007" in message for message in _messages(tree, "a.sh"))


def test_a_dry_run_reports_without_writing(tree: Path) -> None:
    """The same measure-first contract as every other writer in this area."""
    path = tree / "a.sh"
    write_file(path, "#!/usr/bin/env bash\necho hi   \n")
    assert fix(tree, ["a.sh"], dry_run=True) == ["a.sh"]
    assert path.read_text(encoding="utf-8").endswith("hi   \n")


def test_repaired_is_idempotent(tree: Path) -> None:
    """`make fix` twice in a row has to leave the tree untouched the second time."""
    once = repaired(tree, "a.sh", "#!/usr/bin/env bash\necho hi   ")
    assert repaired(tree, "a.sh", once) == once
