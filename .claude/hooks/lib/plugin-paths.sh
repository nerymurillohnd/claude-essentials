#!/usr/bin/env bash
# Sourced by session-start.sh and post-edit.sh (ADR-0003): classifies plugin paths
# as runtime (needs a version bump) or exempt (Claude never loads it). Mirrors
# EXEMPT_FILE and METADATA_KEYS in scripts/versioning/version_plan.py — change
# both together; scripts/harness/test_plugin_paths.py runs these functions and
# the Python constant over one table.

# plugin_path_is_exempt <rel>
# Returns 0 when a path relative to plugins/<name>/ is never loaded by Claude
# (EXEMPT_FILE): README.md, CHANGELOG.md, LICENSE or LICENSE.<ext> at the plugin
# root; anything under docs/ or evals/ at the plugin root; and, at any depth, a
# file named test-*.sh or anything under a directory named tests/ (ADR-0003
# amendment 2026-09-21). In a `case` pattern `*` also matches `/`, so the
# LICENSE.* and test-*.sh arms check the basename explicitly.
plugin_path_is_exempt() {
  local rel="$1" base="${1##*/}"
  case "${rel}" in
  README.md | CHANGELOG.md | LICENSE | docs/?* | evals/?*) return 0 ;;
  tests/?* | */tests/?*) return 0 ;;
  LICENSE.?*) [[ "${rel}" != */* ]] && return 0 ;;
  *) ;;
  esac
  case "${base}" in
  test-?*.sh) return 0 ;;
  *) return 1 ;;
  esac
}

# Reads a plugin.json on stdin; prints it without metadata keys, keys sorted.
plugin_manifest_runtime_json() {
  jq -S 'del(."$schema", .version, .description, .displayName, .keywords, .author, .homepage, .repository, .license, .metadata)'
}

# plugin_runtime_change <root> <name> <tag>
# Prints the first path (relative to plugins/<name>/) that Claude loads at runtime
# and that differs between <tag> and the working tree (committed, uncommitted, or
# untracked). Prints nothing when only exempt files changed. Always returns 0, so
# callers under `set -e` can use it in a plain assignment.
plugin_runtime_change() {
  local root="$1" name="$2" tag="$3" file rel old new changed
  changed="$(
    git -C "${root}" diff --name-only --no-renames "${tag}" -- "plugins/${name}" 2>/dev/null || true
    git -C "${root}" ls-files --others --exclude-standard -- "plugins/${name}" 2>/dev/null || true
  )"
  while IFS= read -r file; do
    [[ -n "${file}" ]] || continue
    rel="${file#plugins/"${name}"/}"
    if plugin_path_is_exempt "${rel}"; then continue; fi
    case "${rel}" in
    .claude-plugin/plugin.json)
      old="$(git -C "${root}" show "${tag}:${file}" 2>/dev/null | plugin_manifest_runtime_json 2>/dev/null || true)"
      new="$(plugin_manifest_runtime_json <"${root}/${file}" 2>/dev/null || true)"
      [[ "${old}" != "${new}" ]] || continue
      ;;
    *) ;;
    esac
    printf '%s\n' "${rel}"
    return 0
  done <<<"${changed}"
  return 0
}
