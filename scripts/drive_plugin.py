#!/usr/bin/env python3
"""Drive a plugin in a real headless Claude Code session, as a user would.

Run: python3 scripts/drive_plugin.py <plugin> [--prompt TEXT] [--source checkout|head]
                                     [--expect REGEX ...] [--model MODEL] [--budget USD]

`test_install.py` proves that every plugin installs and loads; this script uses
one: it sends a prompt (by default the plugin's first skill as a slash command)
to a `claude -p` session with only that plugin loaded and checks the reply.

The session never touches the real configuration: `--restricted` loads neither
user nor project settings (so none of the maintainer's plugins, hooks or MCP
servers), `--strict-mcp-config` drops the account's claude.ai connectors,
`--no-session-persistence` writes no transcript, and the fingerprints of the
real configuration are compared before and after. Authentication is the
maintainer's own login: an isolated CLAUDE_CONFIG_DIR has no credentials.

Sources:
  checkout  the working tree's plugins/<name> (default; covers uncommitted work)
  head      the copy a user receives: HEAD is cloned bare, installed through a
            git-subdir marketplace in a throwaway config, and the session loads
            that installed copy (commit first)

Every run is a real model call billed to the maintainer's plan; --budget caps it.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import repo
from repo import JSON
import test_install

TEMP_PREFIX = "claude-essentials-drive-"
DEFAULT_MODEL = "haiku"
DEFAULT_BUDGET_USD = "0.50"
# The default preset does not bring back what --restricted removes; naming the
# tools does (observed on 2.1.289, matching the CLI reference for --restricted).
DEFAULT_TOOLS = "default,Bash,WebFetch"


@dataclass
class Outcome:
    """What the session did, and every way it fell short."""

    errors: list[str] = field(default_factory=list)
    reply: str = ""
    cost: float = 0.0
    loaded: list[str] = field(default_factory=list)


def default_prompt(plugin: Path) -> str | None:
    """The plugin's first skill as a slash command, or None when it has no skills."""
    skills = sorted((plugin / "skills").glob("*/SKILL.md"))
    if not skills:
        return None
    match = re.search(r"^name:\s*(\S+)\s*$", skills[0].read_text(encoding="utf-8"), re.MULTILINE)
    skill = match.group(1) if match else skills[0].parent.name
    return f"/{plugin.name}:{skill}"


def installed_copy(tmp: Path, name: str, errors: list[str]) -> Path | None:
    """Install the plugin from a bare clone of HEAD and return its cache path."""
    bare = tmp / "repo.git"
    _ = repo.run(["git", "clone", "--quiet", "--bare", str(repo.ROOT), str(bare)])
    marketplace = tmp / "marketplace"
    (marketplace / ".claude-plugin").mkdir(parents=True)
    source = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    entry: JSON = {
        "name": name,
        "source": {"source": "git-subdir", "url": bare.as_uri(), "path": f"plugins/{name}"},
    }
    catalog: dict[str, JSON] = {
        "name": repo.MARKETPLACE_NAME,
        "owner": source.get("owner"),
        "plugins": [entry],
    }
    repo.dump_json(marketplace / ".claude-plugin" / "marketplace.json", catalog)
    env = test_install.isolated_env(tmp / "config")
    for args in (
        ["plugin", "marketplace", "add", str(marketplace)],
        ["plugin", "install", f"{name}@{repo.MARKETPLACE_NAME}"],
    ):
        code, output = test_install.claude(args, env)
        if code != 0:
            errors.append(f"head: {' '.join(args)} failed: {output}")
            return None
    code, output = test_install.claude(["plugin", "list", "--json"], env)
    if code != 0:
        errors.append(f"head: plugin list failed: {output}")
        return None
    listed: JSON = json.loads(output)  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
    for raw in repo.as_list(listed) or []:
        item = repo.as_dict(raw) or {}
        if item.get("id") == f"{name}@{repo.MARKETPLACE_NAME}":
            path = repo.as_str(item.get("installPath"))
            return Path(path) if path else None
    errors.append(f"head: {name} is not listed after install")
    return None


def _read_init(event: dict[str, JSON], name: str, outcome: Outcome) -> None:
    for raw in repo.as_list(event.get("plugins")) or []:
        plugin = repo.as_dict(raw) or {}
        source = repo.as_str(plugin.get("source")) or ""
        outcome.loaded.append(source)
        if not source.endswith("@builtin") and plugin.get("name") != name:
            outcome.errors.append(f"unexpected plugin loaded: {source}")
    if not any(repo.as_str(item) == f"{name}@inline" for item in outcome.loaded):
        outcome.errors.append(f"{name} did not load into the session")
    if event.get("plugin_errors"):
        outcome.errors.append(f"plugin load errors: {event.get('plugin_errors')}")
    servers = repo.as_list(event.get("mcp_servers")) or []
    if servers:
        outcome.errors.append(f"MCP servers leaked into the session: {len(servers)}")


def read_stream(stdout: str, name: str) -> Outcome:
    """Collect the init and result events of a stream-json session."""
    outcome = Outcome()
    saw_result = False
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        event = repo.as_dict(json.loads(line)) or {}  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
        if event.get("type") == "system" and event.get("subtype") == "init":
            _read_init(event, name, outcome)
        elif event.get("type") == "result":
            saw_result = True
            outcome.reply = repo.as_str(event.get("result")) or ""
            cost = event.get("total_cost_usd")
            outcome.cost = float(cost) if isinstance(cost, int | float) else 0.0
            if event.get("is_error"):
                outcome.errors.append(f"the session ended with an error: {outcome.reply}")
    if not saw_result:
        outcome.errors.append("the session produced no result event")
    return outcome


def drive(
    plugin_path: Path, name: str, prompt: str, args: argparse.Namespace, workdir: Path
) -> Outcome:
    """Run one headless session with only this plugin and check the reply."""
    command = [
        "claude",
        "--restricted",
        "-p",
        "--no-session-persistence",
        "--strict-mcp-config",
        "--plugin-dir",
        str(plugin_path),
        # --restricted removes Bash and the other code-running tools unless --tools
        # names them; a user's session has them, so the plugin gets them back.
        "--tools",
        str(args.tools),  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        "--permission-mode",
        str(args.permission_mode),  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        "--model",
        str(args.model),  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        "--max-budget-usd",
        str(args.budget),  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        "--output-format",
        "stream-json",
        "--verbose",
        prompt,
    ]
    # An empty stdin keeps `-p` from waiting for piped input. An empty working
    # directory outside the repository keeps the project CLAUDE.md and the git
    # snapshot (with the maintainer's name) out of the session, as for a stranger.
    result = repo.run(command, cwd=workdir, check=False, input_text="")
    outcome = read_stream(result.stdout, name)
    if "Not logged in" in outcome.reply and not os.environ.get("USER"):
        # Observed on macOS: the keychain login is found through USER, not LOGNAME.
        outcome.errors.append("USER is unset, so Claude Code cannot find the login; export USER")
    if result.returncode != 0:
        outcome.errors.append(f"claude exited {result.returncode}: {result.stderr.strip()}")
    expectations: list[str] = args.expect or []  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    outcome.errors.extend(
        f"reply does not match {pattern!r}"
        for pattern in expectations
        if not re.search(pattern, outcome.reply, re.IGNORECASE)
    )
    return outcome


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("plugin", help="plugin name under plugins/")
    _ = parser.add_argument("--prompt", help="prompt to send (default: /<plugin>:<first skill>)")
    _ = parser.add_argument("--source", choices=("checkout", "head"), default="checkout")
    _ = parser.add_argument(
        "--expect", action="append", help="regex the reply must match (repeatable)"
    )
    _ = parser.add_argument("--model", default=DEFAULT_MODEL, help="model alias or id")
    _ = parser.add_argument("--budget", default=DEFAULT_BUDGET_USD, help="spend cap in USD")
    _ = parser.add_argument(
        "--tools",
        default=DEFAULT_TOOLS,
        help="built-in tools; --restricted drops Bash and WebFetch unless named here",
    )
    _ = parser.add_argument(
        "--permission-mode",
        default="default",
        choices=("default", "acceptEdits", "plan", "dontAsk"),
        help="permission mode; in -p a call that would prompt is denied",
    )
    return parser.parse_args()


def run_session(name: str, prompt: str, args: argparse.Namespace, errors: list[str]) -> None:
    """Drive the chosen copy of the plugin inside a temporary directory, then remove it."""
    source: str = args.source  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    with tempfile.TemporaryDirectory(prefix=TEMP_PREFIX) as raw_tmp:
        tmp = Path(raw_tmp)
        target = repo.PLUGINS_DIR / name
        if source == "head":
            target = installed_copy(tmp, name, errors)
        if target is not None:
            workdir = tmp / "workspace"
            workdir.mkdir()
            outcome = drive(target, name, prompt, args, workdir)
            repo.emit(f"source: {source} ({target})")
            repo.emit(f"prompt: {prompt}")
            repo.emit(f"loaded: {', '.join(outcome.loaded)}")
            repo.emit(f"reply:\n{outcome.reply}")
            repo.emit(f"cost: ${outcome.cost:.4f}")
            errors.extend(outcome.errors)
    # Nothing the run created may outlive it (docs/testing.md#cleanup).
    if tmp.exists():
        errors.append(f"temporary directory {tmp} was not removed")


def main() -> int:
    """Drive the plugin and report the reply, the cost and every problem."""
    args = _parse_args()
    name: str = args.plugin  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    checkout = repo.PLUGINS_DIR / name
    if not (checkout / ".claude-plugin" / "plugin.json").is_file():
        repo.emit(f"✘ plugins/{name} is not a plugin")
        return 1
    prompt: str | None = args.prompt or default_prompt(checkout)  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    if prompt is None:
        repo.emit(f"✘ {name} has no skills; pass --prompt")
        return 1
    before = None if os.environ.get("CI") else test_install.snapshot()
    errors: list[str] = []
    run_session(name, prompt, args, errors)
    if before is not None:
        changed = [key for key, value in test_install.snapshot().items() if before[key] != value]
        if changed:
            errors.append(f"the real Claude Code configuration changed: {', '.join(changed)}")
        else:
            repo.emit(f"real configuration unchanged ({len(before)} fingerprints compared)")
    for error in errors:
        repo.emit(f"✘ {error}")
    if errors:
        return 1
    repo.emit(f"drive_plugin: {name} answered as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
