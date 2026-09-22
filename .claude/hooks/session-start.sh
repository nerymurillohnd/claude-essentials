#!/usr/bin/env bash
# SessionStart hook: injects a compact snapshot of repo, toolchain, Claude Code
# CLI, debt ledgers, catalog validity, plugin release state, and relevant
# upstream changelog entries. Only writes to .claude/.cache/hooks/; never
# fails the session. See docs/decisions/adr-0002-project-hooks.md.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/plugin-paths.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/plugin-paths.sh"

readonly CHANGELOG_URL="https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
readonly CHANGELOG_DOCS_URL="https://code.claude.com/docs/en/changelog"
readonly CHANGELOG_TTL_SECONDS=86400
readonly CHANGELOG_FIRST_RUN_VERSIONS=5
readonly CHANGELOG_MAX_BULLETS=25
readonly CHANGELOG_RELEVANT='(^|[^[:alnum:]_])(hooks?|SessionStart|PreToolUse|PostToolUse|plugins?|marketplaces?|skills?|subagents?|MCP|settings\.json|CLAUDE\.md|frontmatter)([^[:alnum:]_]|$)'
readonly OUTPUT_BUDGET=9000

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' "claude-essentials session snapshot skipped: jq is not installed (brew install jq)."
  exit 0
fi

input="$(cat)"
root="${CLAUDE_PROJECT_DIR:-$(jq -r '.cwd // empty' <<<"${input}")}"
root="${root:-${PWD}}"
source_kind="$(jq -r '.source // "startup"' <<<"${input}")"
cd "${root}" || exit 0

cache_dir="${root}/.claude/.cache/hooks"
state_file="${cache_dir}/session-start-state.json"
changelog_cache="${cache_dir}/claude-code-changelog.md"
mkdir -p "${cache_dir}"
state="$(jq -c . "${state_file}" 2>/dev/null || echo '{}')"

warnings=()
warn() { warnings+=("$1"); }
first_line() { head -n 1 | tr -d '\r'; }

section_git() {
  local status branch files count path shown tick=$'\x60' # a Markdown code-span backtick
  echo "## Git"
  if ! status="$(git status --porcelain=v1 --branch 2>/dev/null)"; then
    echo "- git status failed"
    return
  fi
  branch="$(first_line <<<"${status}")"
  files="$(tail -n +2 <<<"${status}")"
  echo "- ${branch#\#\# } (local refs; no fetch)"
  if [[ -z "${files}" ]]; then
    echo "- Working tree clean"
  else
    count="$(wc -l <<<"${files}" | tr -d ' ')"
    echo "- ${count} uncommitted path(s):"
    shown=0
    while IFS= read -r path && ((shown < 10)); do
      printf '  - %s%s%s\n' "${tick}" "${path}" "${tick}"
      shown=$((shown + 1))
    done <<<"${files}"
    ((count > 10)) && echo "  - …and $((count - 10)) more"
  fi
}

version_of() { if command -v "$1" >/dev/null 2>&1; then "$@" 2>/dev/null | first_line; else echo MISSING; fi; }

venv_tool() { if [[ -x ".venv/bin/$1" ]]; then ".venv/bin/$1" --version 2>/dev/null | first_line; else echo MISSING; fi; }

section_toolchain() {
  local python uv ruff shellcheck shfmt git gh jq curl
  python="$(venv_tool python)"
  uv="$(version_of uv --version)"
  ruff="$(venv_tool ruff)"
  shellcheck=""
  [[ -x .venv/bin/shellcheck ]] && shellcheck="$(.venv/bin/shellcheck --version 2>/dev/null | sed -n 's/^version: //p')"
  shfmt="$(venv_tool shfmt)"
  git="$(version_of git --version)"
  gh="$(version_of gh --version)"
  jq="$(version_of jq --version)"
  curl="$(version_of curl --version)"
  echo "## Toolchain"
  echo "- ${python} (.venv) | ${uv} | ${git} | ${gh}"
  echo "- gate (.venv): ${ruff} | shellcheck ${shellcheck:-MISSING} | shfmt ${shfmt}"
  echo "- hook deps: bash ${BASH_VERSION} | ${jq} | ${curl%% (*}"
}

check_toolchain() {
  local pinned local_py
  [[ -x .venv/bin/python ]] || warn ".venv missing — run \`make setup\`"
  pinned="$(first_line <.python-version 2>/dev/null)"
  local_py="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)"
  if [[ -n "${pinned}" && -n "${local_py}" && "${pinned}" != "${local_py}" ]]; then
    warn "Python mismatch: .venv ${local_py} vs .python-version ${pinned} — run \`make setup\`"
  fi
}

# Prints subcommand names from a commander-style help screen, one per line.
subcommands() {
  awk '/^Commands:/ { on = 1; next } on && /^  [a-z]/ { sub(/\|.*/, "", $1); if ($1 != "help") print $1 }'
}

cli_version=""
cli_plugin=""
cli_marketplace=""
collect_cli() {
  cli_version="$(claude --version 2>/dev/null | awk '{ print $1 }')"
  cli_plugin="$(claude plugin --help 2>/dev/null | subcommands)"
  cli_marketplace="$(claude plugin marketplace --help 2>/dev/null | subcommands)"
}

join_lines() { paste -sd, - | sed 's/,/, /g'; }

# Prints "plugin +[a]; marketplace -[b]" style drift against the last session, or nothing.
cli_drift() {
  jq -r --arg p "${cli_plugin}" --arg m "${cli_marketplace}" '
    def lines: split("\n") | map(select(. != ""));
    def diff($key; $now):
      (.cli[$key] // null) as $was
      | if $was == null then empty
        else (($now - $was) | select(length > 0) | "\($key) +[\(join(", "))]"),
             (($was - $now) | select(length > 0) | "\($key) -[\(join(", "))]")
        end;
    [diff("plugin"; $p | lines), diff("marketplace"; $m | lines)] | join("; ")
  ' <<<"${state}"
}

section_cli() {
  local prev_version drift plugin_list marketplace_list
  plugin_list="$(join_lines <<<"${cli_plugin}")"
  marketplace_list="$(join_lines <<<"${cli_marketplace}")"
  echo "## Claude Code CLI"
  echo "- version: ${cli_version:-UNAVAILABLE}"
  echo "- \`claude plugin\`: ${plugin_list:-UNAVAILABLE}"
  echo "- \`claude plugin marketplace\`: ${marketplace_list:-UNAVAILABLE}"
  [[ -n "${cli_version}" ]] || return 0
  prev_version="$(jq -r '.cli.version // empty' <<<"${state}")"
  if [[ -n "${prev_version}" && "${prev_version}" != "${cli_version}" ]]; then
    echo "- CLI changed since last session: ${prev_version} → ${cli_version}"
  fi
  drift="$(cli_drift)"
  [[ -n "${drift}" ]] && echo "- Subcommand drift: ${drift}"
  return 0
}

check_cli_drift() {
  local drift
  [[ -n "${cli_version}" ]] || return 0
  drift="$(cli_drift)"
  [[ -n "${drift}" ]] && warn "Claude CLI subcommand drift: ${drift}"
  return 0
}

ledger_items() {
  local file="docs/maintenance/$1" heading="$2"
  [[ -f "${file}" ]] || {
    echo "__MISSING__"
    return
  }
  awk -v h="## ${heading}" '$0 == h { on = 1; next } on && /^## / { exit } on && /^### / { sub(/^### /, ""); print }' "${file}"
}

bullets() { while IFS= read -r line; do printf '  - %s\n' "${line}"; done; }

section_debt() {
  local pending resolved count
  pending="$(ledger_items pending-debt.md "Open Items")"
  resolved="$(ledger_items resolved-debt.md "Resolved Items")"
  echo "## Maintenance ledgers (docs/maintenance/)"
  if [[ "${pending}" == "__MISSING__" ]]; then
    echo "- pending-debt.md MISSING"
  elif [[ -z "${pending}" ]]; then
    echo "- Pending: none"
  else
    count="$(wc -l <<<"${pending}" | tr -d ' ')"
    echo "- Pending (${count}):"
    bullets <<<"${pending}"
  fi
  if [[ "${resolved}" == "__MISSING__" ]]; then
    echo "- resolved-debt.md MISSING"
  elif [[ -z "${resolved}" ]]; then
    echo "- Resolved: none yet"
  else
    count="$(wc -l <<<"${resolved}" | tr -d ' ')"
    echo "- Resolved: ${count} total; latest:"
    tail -n 3 <<<"${resolved}" | bullets
  fi
}

repo_validate_ok=""
repo_validate_out=""
official_report=""
collect_catalog() {
  if [[ -x .venv/bin/python ]]; then
    if repo_validate_out="$(make -s validate 2>&1)"; then repo_validate_ok=1; else repo_validate_ok=0; fi
  fi
  official_report="$(claude plugin validate . --json 2>/dev/null)"
  jq -e . >/dev/null 2>&1 <<<"${official_report}" || official_report=""
}

section_catalog() {
  echo "## Catalog validation"
  if [[ -n "${repo_validate_ok}" ]]; then
    if [[ "${repo_validate_ok}" == 1 ]]; then echo "- make validate: pass"; else
      echo "- make validate: FAIL"
      tail -n 8 <<<"${repo_validate_out}" | sed 's/^/  /'
    fi
  fi
  if [[ -z "${official_report}" ]]; then
    echo "- claude plugin validate: could not run"
    return
  fi
  jq -r '
    "- claude plugin validate .: \(if .success then "pass" else "FAIL" end)",
    ([.manifest, (.contents // [])[]] | map(select(. != null))
      | map((.errors // [] | map("error: \(.path // "") \(.message // .)")),
            (.warnings // [] | map("warning: \(.path // ""): \(.message // .)")))
      | flatten | .[:8][] | "  - \(.)")
  ' <<<"${official_report}"
}

check_catalog() {
  [[ "${repo_validate_ok}" == 0 ]] && warn "Repo catalog validation failing"
  [[ -n "${official_report}" ]] && ! jq -e .success >/dev/null <<<"${official_report}" &&
    warn "\`claude plugin validate .\` failing"
  return 0
}

release_lines=""
collect_release() {
  local dir name version tag dirty runtime
  for dir in plugins/*/; do
    [[ -d "${dir}" ]] || continue
    name="$(basename "${dir}")"
    version="$(jq -r '.version // empty' "${dir}.claude-plugin/plugin.json" 2>/dev/null)"
    if [[ -z "${version}" ]]; then
      release_lines+="- ${name}: NO version — violates ADR-0003 (explicit semver required)"$'\n'
      continue
    fi
    tag="${name}--v${version}"
    dirty="$(git status --porcelain -- "plugins/${name}" 2>/dev/null)"
    if ! git rev-parse -q --verify "refs/tags/${tag}" >/dev/null 2>&1; then
      release_lines+="- ${name}@${version}: untagged (the Tag plugin versions workflow tags it on merge to main; run \`git fetch --tags\` if already merged)"$'\n'
      continue
    fi
    runtime="$(plugin_runtime_change "${PWD}" "${name}" "${tag}")"
    if [[ -n "${runtime}" ]]; then
      release_lines+="- ${name}@${version}: runtime files CHANGED since ${tag} without a version bump (first: ${runtime})"$'\n'
      warn "${name}: runtime files changed since ${tag} without a version bump"
    elif [[ -n "${dirty}" ]] || ! git diff --quiet "${tag}" HEAD -- "plugins/${name}" 2>/dev/null; then
      release_lines+="- ${name}@${version}: docs/metadata changed since ${tag} (no bump needed; note notable changes under [Unreleased])"$'\n'
    else
      release_lines+="- ${name}@${version}: matches ${tag}"$'\n'
    fi
  done
}

section_release() {
  if [[ -z "${release_lines}" ]]; then
    printf '%s\n' "## Plugin release state" "- No plugins under plugins/"
  else
    echo "## Plugin release state (explicit \`version\` pins updates)"
    printf '%s' "${release_lines}"
  fi
}

changelog_note=""
load_changelog() {
  local age now mtime
  if [[ -f "${changelog_cache}" ]]; then
    now="$(date +%s)"
    mtime="$(stat -f %m "${changelog_cache}" 2>/dev/null || stat -c %Y "${changelog_cache}")"
    age=$((now - mtime))
    if ((age < CHANGELOG_TTL_SECONDS)); then
      changelog_note="cached <24h"
      return
    fi
  fi
  if curl -fsSL --max-time 5 -o "${changelog_cache}.tmp" "${CHANGELOG_URL}" 2>/dev/null; then
    mv "${changelog_cache}.tmp" "${changelog_cache}"
    changelog_note="fetched"
  else
    rm -f "${changelog_cache}.tmp"
    changelog_note="fetch failed; using stale cache"
  fi
}

# Newest-first "version<TAB>bullet" lines for releases newer than $1
# (or the first N releases when $1 is empty).
changelog_window() {
  awk -v seen="$1" -v first="${CHANGELOG_FIRST_RUN_VERSIONS}" '
    /^## [0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ {
      v = $2; n++
      if (seen != "" && v == seen) { found = 1; exit }
      if (seen == "" && n > first) exit
      next
    }
    n > 0 && /^- / { lines[++count] = v "\t" substr($0, 3) }
    END { for (i = 1; i <= count; i++) print lines[i] }
  ' "${changelog_cache}"
}

version_gt() {
  local highest
  [[ "$1" != "$2" ]] || return 1
  highest="$(printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)"
  [[ "${highest}" == "$1" ]]
}

latest_upstream=""
section_changelog() {
  local seen window relevant total scope
  load_changelog
  echo "## Claude Code changelog (source: GitHub CHANGELOG.md, ${changelog_note}; dated view: ${CHANGELOG_DOCS_URL})"
  if [[ ! -s "${changelog_cache}" ]]; then
    echo "- Unavailable"
    return
  fi
  latest_upstream="$(awk '/^## [0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ { print $2; exit }' "${changelog_cache}")"
  echo "- Latest upstream: ${latest_upstream:-unknown}; installed: ${cli_version:-unknown}"
  seen="$(jq -r '.changelogSeen // empty' <<<"${state}")"
  if [[ -n "${seen}" ]] && ! grep -qxF "## ${seen}" "${changelog_cache}"; then seen=""; fi
  if [[ -n "${seen}" && "${seen}" == "${latest_upstream}" ]]; then
    echo "- No new releases since ${seen}"
    return
  fi
  scope="last ${CHANGELOG_FIRST_RUN_VERSIONS} releases (first run)"
  [[ -n "${seen}" ]] && scope="since ${seen}"
  window="$(changelog_window "${seen}")"
  relevant="$(grep -v -E $'^[^\t]*\t\\[' <<<"${window}" | grep -E -i "${CHANGELOG_RELEVANT}" || true)"
  echo "- Relevant entries ${scope}:"
  if [[ -z "${relevant}" ]]; then
    echo "  - none matched plugin/hook/skill/subagent/MCP/settings terms"
    return
  fi
  total="$(wc -l <<<"${relevant}" | tr -d ' ')"
  head -n "${CHANGELOG_MAX_BULLETS}" <<<"${relevant}" |
    awk -F'\t' '{ t = $2; if (length(t) > 240) t = substr(t, 1, 237) "…"; print "  - [" $1 "] " t }'
  ((total > CHANGELOG_MAX_BULLETS)) &&
    echo "  - …$((total - CHANGELOG_MAX_BULLETS)) more; read the changelog directly"
  return 0
}

check_changelog() {
  [[ -n "${latest_upstream}" && -n "${cli_version}" ]] && version_gt "${latest_upstream}" "${cli_version}" &&
    warn "Claude Code ${cli_version} is behind upstream ${latest_upstream}"
  return 0
}

save_state() {
  [[ -n "${cli_version}" ]] || return 0
  jq -n \
    --argjson old "${state}" \
    --arg v "${cli_version}" \
    --arg p "${cli_plugin}" \
    --arg m "${cli_marketplace}" \
    --arg seen "${latest_upstream}" '
      def lines: split("\n") | map(select(. != ""));
      $old
      | .cli = {version: $v, plugin: ($p | lines), marketplace: ($m | lines)}
      | if $seen != "" then .changelogSeen = $seen else . end
    ' >"${state_file}.tmp" && mv "${state_file}.tmp" "${state_file}"
}

collect_cli
collect_catalog
collect_release
check_toolchain
check_cli_drift
check_catalog

body="$(
  section_git
  echo
  section_toolchain
  echo
  section_cli
  echo
  section_debt
  echo
  section_catalog
  echo
  section_release
  echo
  section_changelog
)"
# section_changelog ran in the subshell above; recompute what check_changelog needs.
latest_upstream="$(awk '/^## [0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ { print $2; exit }' "${changelog_cache}" 2>/dev/null)"
check_changelog
save_state

header="# claude-essentials session snapshot (${source_kind})"
if ((${#warnings[@]} > 0)); then
  attention="$(printf -- '- %s\n' "${warnings[@]}")"
  context="${header}"$'\n\n'"## Attention"$'\n'"${attention}"$'\n\n'"${body}"
  system_message="claude-essentials: $(printf '%s · ' "${warnings[@]}")"
  system_message="${system_message% · }"
else
  context="${header}"$'\n\n'"${body}"
  system_message=""
fi
if ((${#context} > OUTPUT_BUDGET)); then
  context="${context:0:$((OUTPUT_BUDGET - 20))}"$'\n…[truncated]'
fi

jq -n --arg ctx "${context}" --arg msg "${system_message}" '
  {hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}
  + (if $msg != "" then {systemMessage: $msg} else {} end)
'
