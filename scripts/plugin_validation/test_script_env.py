"""Environment-variable extraction: what a script reads, not what it mentions."""

from __future__ import annotations

from scripts.common.plugins import repo_root
from scripts.plugin_validation.script_env import (
    SHARED_TEST_BASH,
    env_vars_for,
    python_env_vars,
    shell_bindings,
    shell_env_vars,
    suite_interpreter_vars,
)


def test_a_read_variable_is_found() -> None:
    """The braced default form is how every shipped suite selects its interpreter."""
    assert shell_env_vars("runner=${BNV_TEST_BASH:-bash}\n") == {"BNV_TEST_BASH"}


def test_a_variable_the_script_sets_is_not_an_input() -> None:
    """A local is not a knob a README has to document."""
    assert shell_env_vars('OUT=x\necho "${OUT}"\n') == set()


def test_every_binding_form_counts() -> None:
    """`local`, `for`, `read` and `printf -v` all make a name the script's own."""
    source = "local A=1\nfor B in x; do :; done\nread -r C\nprintf -v D x\nexport E=1\n"
    assert {"A", "B", "C", "D", "E"} <= shell_bindings(source)


def test_a_variable_named_only_in_a_comment_is_not_a_binding() -> None:
    """A usage note such as `# BNV_TEST_BASH=/bin/bash` must not hide the real read."""
    source = "# e.g. BNV_TEST_BASH=/bin/bash to test 3.2\nrunner=${BNV_TEST_BASH:-bash}\n"
    assert shell_env_vars(source) == {"BNV_TEST_BASH"}


def test_single_quotes_do_not_expand() -> None:
    """In shell, `$MSG` inside single quotes is text, so it is not a read."""
    assert shell_env_vars("want ALLOW 'git commit -m \"$MSG\"'\n") == set()


def test_an_apostrophe_in_a_comment_does_not_swallow_the_code() -> None:
    """Comments are removed before quotes, or one apostrophe would hide the rest."""
    source = "# the repository's runner\nvalue=${REAL_VARIABLE}\n"
    assert shell_env_vars(source) == {"REAL_VARIABLE"}


def test_a_prefix_trim_is_not_a_comment() -> None:
    """`${PATH_LIKE#prefix}` must not blank out the rest of its line."""
    source = "rel=${ABSOLUTE#/tmp/}\nvalue=${REAL_VARIABLE}\n"
    assert "REAL_VARIABLE" in shell_env_vars(source)


def test_the_baseline_is_not_reported() -> None:
    """A README that documented `PATH` would say nothing a reader can act on."""
    assert shell_env_vars('cd "${HOME}" && echo "${PATH}"\n') == set()


def test_host_variables_are_not_reported() -> None:
    """Claude Code provides `CLAUDE_*`; the README documents behaviour, not the host."""
    assert shell_env_vars('bash "${CLAUDE_PLUGIN_ROOT}/x.sh"\n') == set()


def test_python_reads_are_found() -> None:
    """All three spellings a shipped script may use are covered."""
    source = "import os\na = os.environ['ONE']\nb = os.environ.get('TWO')\nc = os.getenv('THREE')\n"
    assert python_env_vars(source) == {"ONE", "TWO", "THREE"}


def test_the_shipped_python_declares_its_own_knobs() -> None:
    """`ccdocs.py` is the one shipped Python script, and R6 holds for it today."""
    path = repo_root() / "plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py"
    assert env_vars_for(path) == {"CCDOCS_CACHE_TTL", "CCDOCS_CORPUS_TTL", "CCDOCS_LANG"}


def test_suite_variables_are_selected_by_suffix() -> None:
    """The `*_TEST_BASH` convention is what R6's second half is written against."""
    assert suite_interpreter_vars({"RQ_TEST_BASH", SHARED_TEST_BASH, "RUFF_BIN"}) == {
        "RQ_TEST_BASH",
        SHARED_TEST_BASH,
    }
