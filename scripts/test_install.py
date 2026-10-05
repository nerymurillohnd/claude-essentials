#!/usr/bin/env python3
"""Install every plugin the way a third-party user would, in a throwaway config.

Run: scripts/test_install.py

Nothing touches the real Claude Code configuration: each scenario runs with a
temporary HOME and CLAUDE_CONFIG_DIR, and outside CI the script snapshots the
real configuration before and after and fails if anything changed
(docs/adr/decisions/ADR_2026-10-03_testing-approach.md, docs/testing.md).

Scenarios:
  1. directory: `claude plugin marketplace add <repo>` (accepts the marketplace
     name, loads relative-path plugins in place), install, list, details;
  2. cache copy: a temporary marketplace whose entries use `git-subdir` sources
     over file:// against a bare clone of HEAD, so Claude Code copies each plugin
     into its cache exactly as it does for users of the published repository;
  3. session load: `claude --plugin-dir plugins plugin list --json` loads every
     plugin as a session-only plugin and must report no load errors.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import repo
from repo import JSON


def _real_config_dir() -> Path:
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(configured) if configured else Path.home() / ".claude"


def snapshot() -> dict[str, str]:
    """Fingerprint the parts of the real config an install would change."""
    base = _real_config_dir()
    result: dict[str, str] = {}
    for relative in (
        "settings.json",
        "plugins/known_marketplaces.json",
        "plugins/installed_plugins.json",
    ):
        path = base / relative
        result[relative] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "absent"
        )
    for relative in ("plugins/cache", "plugins/marketplaces", "skills"):
        path = base / relative
        listing = sorted(p.name for p in path.iterdir()) if path.is_dir() else []
        result[relative] = hashlib.sha256("\n".join(listing).encode()).hexdigest()
    return result


def isolated_env(tmp: Path) -> dict[str, str]:
    """An environment whose HOME and Claude Code configuration live under `tmp`."""
    home = tmp / "home"
    config = home / ".claude"
    config.mkdir(parents=True)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["CLAUDE_CONFIG_DIR"] = str(config)
    return env


def claude(args: list[str], env: dict[str, str]) -> tuple[int, str]:
    """Run the Claude Code CLI and return its exit code and combined output."""
    result = repo.run(["claude", *args], env=env, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def plugin_names() -> list[str]:
    """The plugin names the catalog lists, in catalog order."""
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    names: list[str] = []
    for raw in repo.as_list(data.get("plugins")) or []:
        entry = repo.as_dict(raw) or {}
        name = repo.as_str(entry.get("name"))
        if name:
            names.append(name)
    return names


def _cache_problems(name: str, item: dict[str, JSON]) -> list[str]:
    # Runtime-verified on 2.1.289: `installPath` names the cache entry for every
    # marketplace install, even a local-directory marketplace that loads the
    # plugin in place (`plugin list` text shows "Read from: <source>"). So only
    # the cache-copy scenario asserts the location.
    install_path = repo.as_str(item.get("installPath")) or ""
    problems: list[str] = []
    if f"/plugins/cache/{repo.MARKETPLACE_NAME}/{name}/" not in install_path:
        problems.append(f"{name} installPath {install_path} is not a cache copy")
    if not (Path(install_path) / ".claude-plugin" / "plugin.json").is_file():
        problems.append(f"{name} cache copy at {install_path} has no manifest")
    return problems


def _item_problems(name: str, item: dict[str, JSON] | None, *, expect_cache: bool) -> list[str]:
    if item is None:
        return [f"{name} is not listed as installed"]
    problems: list[str] = []
    if item.get("enabled") is not True:
        problems.append(f"{name} is not enabled")
    if item.get("errors"):
        problems.append(f"{name} load errors: {item.get('errors')}")
    if expect_cache:
        problems.extend(_cache_problems(name, item))
    return problems


def check_installed(
    env: dict[str, str],
    names: list[str],
    *,
    expect_cache: bool,
    errors: list[str],
    label: str,
) -> None:
    """Check that every plugin is installed, enabled and loads without errors."""
    code, output = claude(["plugin", "list", "--json"], env)
    if code != 0:
        errors.append(f"{label}: plugin list failed: {output}")
        return
    listed: JSON = json.loads(output)  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
    by_id: dict[str, dict[str, JSON]] = {}
    for raw in repo.as_list(listed) or []:
        item = repo.as_dict(raw) or {}
        by_id[repo.as_str(item.get("id")) or ""] = item
    for name in names:
        item = by_id.get(f"{name}@{repo.MARKETPLACE_NAME}")
        errors.extend(
            f"{label}: {problem}"
            for problem in _item_problems(name, item, expect_cache=expect_cache)
        )


def scenario_directory(tmp: Path, names: list[str], errors: list[str]) -> None:
    """Install every plugin from the repository directory, which loads in place."""
    env = isolated_env(tmp / "directory")
    code, output = claude(["plugin", "marketplace", "add", str(repo.ROOT)], env)
    repo.emit(output)
    if code != 0:
        errors.append(f"directory: marketplace add failed: {output}")
        return
    for name in names:
        code, output = claude(["plugin", "install", f"{name}@{repo.MARKETPLACE_NAME}"], env)
        repo.emit(output)
        if code != 0:
            errors.append(f"directory: install {name} failed")
        code, output = claude(["plugin", "details", name], env)
        if code != 0:
            errors.append(f"directory: details {name} failed: {output}")
    check_installed(env, names, expect_cache=False, errors=errors, label="directory")


def scenario_cache_copy(tmp: Path, names: list[str], errors: list[str]) -> None:
    """Install every plugin from a bare clone of HEAD, copied to the cache as a user's is."""
    bare = tmp / "repo.git"
    _ = repo.run(["git", "clone", "--quiet", "--bare", str(repo.ROOT), str(bare)])
    marketplace = tmp / "copy-marketplace"
    (marketplace / ".claude-plugin").mkdir(parents=True)
    source_data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    entries: list[JSON] = [
        {
            "name": name,
            "source": {
                "source": "git-subdir",
                "url": bare.as_uri(),
                "path": f"plugins/{name}",
            },
        }
        for name in names
    ]
    copy: dict[str, JSON] = {
        "name": repo.MARKETPLACE_NAME,
        "description": repo.as_str(source_data.get("description")) or "",
        "owner": source_data.get("owner"),
        "plugins": entries,
    }
    repo.dump_json(marketplace / ".claude-plugin" / "marketplace.json", copy)
    env = isolated_env(tmp / "cache")
    code, output = claude(["plugin", "marketplace", "add", str(marketplace)], env)
    repo.emit(output)
    if code != 0:
        errors.append(f"cache: marketplace add failed: {output}")
        return
    for name in names:
        code, output = claude(["plugin", "install", f"{name}@{repo.MARKETPLACE_NAME}"], env)
        repo.emit(output)
        if code != 0:
            errors.append(
                f"cache: install {name} failed (HEAD must contain the plugin; commit first)"
            )
    check_installed(env, names, expect_cache=True, errors=errors, label="cache")


def scenario_session(tmp: Path, names: list[str], errors: list[str]) -> None:
    """Load every plugin in a session with --plugin-dir and check it reports no errors or notes."""
    env = isolated_env(tmp / "session")
    code, output = claude(["--plugin-dir", str(repo.PLUGINS_DIR), "plugin", "list", "--json"], env)
    if code != 0:
        errors.append(f"session: plugin list failed: {output}")
        return
    listed: JSON = json.loads(output)  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
    loaded: dict[str, dict[str, JSON]] = {}
    for raw in repo.as_list(listed) or []:
        item = repo.as_dict(raw) or {}
        loaded[repo.as_str(item.get("id")) or ""] = item
    for name in names:
        item = loaded.get(f"{name}@inline")
        if item is None:
            errors.append(f"session: {name} did not load with --plugin-dir")
        elif item.get("errors") or item.get("notes"):
            errors.append(f"session: {name} errors={item.get('errors')} notes={item.get('notes')}")


def main() -> int:
    """Run the three install scenarios and check the real configuration is unchanged."""
    in_ci = bool(os.environ.get("CI"))
    before = None if in_ci else snapshot()
    names = plugin_names()
    errors: list[str] = []
    if not names:
        errors.append("marketplace.json lists no plugins")
    temp_root = Path(tempfile.gettempdir())
    temp_before = {p.name for p in temp_root.iterdir()}
    with tempfile.TemporaryDirectory(prefix="claude-essentials-install-") as raw_tmp:
        tmp = Path(raw_tmp)
        scenario_directory(tmp, names, errors)
        scenario_cache_copy(tmp, names, errors)
        scenario_session(tmp, names, errors)
    # Nothing the test created may outlive it (docs/testing.md#cleanup).
    if tmp.exists():
        errors.append(f"temporary directory {tmp} was not removed")
    orphans = sorted(
        name
        for name in {p.name for p in temp_root.iterdir()} - temp_before
        if name.startswith("claude-essentials-install-") or "claude" in name.lower()
    )
    if orphans:
        errors.append(f"orphaned temporary entries: {', '.join(orphans)}")
    else:
        repo.emit("no orphaned temporary files or directories")
    if before is not None:
        after = snapshot()
        changed = sorted(key for key in before if before[key] != after[key])
        if changed:
            errors.append(f"the real Claude Code configuration changed: {', '.join(changed)}")
        else:
            repo.emit(f"real configuration unchanged ({len(before)} fingerprints compared)")
    for error in errors:
        repo.emit(f"✘ {error}")
    if errors:
        return 1
    modes = "in place, from a cache copy and per session"
    repo.emit(f"test_install: {len(names)} plugin(s) installed {modes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
