#!/usr/bin/env bash
# Sourced by session-start.sh and post-edit.sh (ADR-0003): classifies plugin paths
# as runtime (needs a version bump) or exempt (Claude never loads it). Mirrors
# EXEMPT_FILE and METADATA_KEYS in scripts/lib/version-plan.mjs — change both together.

# Reads a plugin.json on stdin; prints it without metadata keys, keys sorted.
plugin_manifest_runtime_json() {
  jq -S 'del(."$schema", .version, .description, .displayName, .keywords, .author, .homepage, .repository, .license)'
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
    case "${rel}" in
    README.md | CHANGELOG.md | LICENSE | LICENSE.* | docs/?*) continue ;;
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
