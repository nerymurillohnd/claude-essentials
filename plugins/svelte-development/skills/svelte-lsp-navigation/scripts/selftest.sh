#!/usr/bin/env bash
# Proves that the project check sees deliberate breakage, on a scratch copy of the
# bundled SvelteKit 3 fixture. It never touches the user's project.
#
# Steps (expected results come from fixtures/kit3-app/README.md, "Mutations"):
#   1. baseline    svelte-check reports exactly the fixture's deliberate error
#   2. mutation 1  rename the `label` prop inside CounterButton only: every parent
#                  that passes `label` must fail, at the sites findReferences lists
#   3. mutation 2  rename CounterButton.svelte: the import sites must fail, while the
#                  import.meta.glob pattern changes silently (a blind spot Grep finds)
#   4. restored    the check is back to the baseline
#
# Needs bash, node and npm, and network access to the npm registry (it installs the
# fixture's pinned devDependencies into the scratch copy). Exit codes: 0 every step
# passed, 1 a step did not match, 2 a requirement or the setup failed. The scratch
# directory is removed on exit.
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
skill_dir="$(dirname "${script_dir}")"
fixture="${skill_dir}/fixtures/kit3-app"

for tool in node npm; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "selftest: ${tool} is not on PATH; install Node.js to run the self-test" >&2
    exit 2
  fi
done
if [[ ! -d "${fixture}" ]]; then
  echo "selftest: fixture not found at ${fixture}" >&2
  exit 2
fi

tmp_root="${TMPDIR:-/tmp}"
work="$(mktemp -d "${tmp_root%/}/svelte-development-selftest-XXXXXX")"
cleanup() {
  rm -rf "${work}"
  if [[ -e "${work}" ]]; then
    echo "selftest: could not remove ${work}" >&2
  fi
}
trap cleanup EXIT

failures=0

# Prints one "file line:col" per svelte-check error, sorted. svelte-check exits 1 when it
# finds errors, which several steps expect, so its exit code is not a failure here.
check_errors() {
  { npx --no-install svelte-check --tsconfig ./tsconfig.json --output machine 2>&1 || true; } |
    awk '$2 == "ERROR" { gsub(/"/, "", $3); print $3 " " $4 }' | LC_ALL=C sort
}

# Prints each line of $2 prefixed with $1.
indent() {
  local line
  while IFS= read -r line; do
    printf '%s%s\n' "$1" "${line}"
  done <<<"$2"
}

expect_errors() {
  local step="$1" expected="$2" actual
  actual="$(check_errors)"
  if [[ "${actual}" == "${expected}" ]]; then
    echo "PASS ${step}"
    indent "     " "${actual}"
  else
    echo "FAIL ${step}"
    echo "     expected:"
    indent "       " "${expected}"
    echo "     reported:"
    indent "       " "${actual:-<no errors>}"
    failures=$((failures + 1))
  fi
}

# Replaces every occurrence of $2 with $3 in file $1, without sed -i (BSD and GNU differ).
replace_in() {
  local file="$1" from="$2" to="$3" content
  content="$(<"${file}")"
  printf '%s\n' "${content//"${from}"/"${to}"}" >"${file}"
}

echo "selftest: installing a scratch copy of the fixture in ${work} (needs the npm registry)"
cp -R "${fixture}/." "${work}"
cd "${work}"
for name in package.json tsconfig.json vite.config.ts; do
  mv "${name}.example" "${name}"
done
if ! npm install --include=dev --ignore-scripts --no-audit --no-fund --loglevel=error >npm-install.log 2>&1; then
  echo "selftest: npm install failed:" >&2
  tail -n 20 npm-install.log >&2
  exit 2
fi
if ! npx --no-install svelte-kit sync >/dev/null 2>&1; then
  echo "selftest: svelte-kit sync failed" >&2
  exit 2
fi

baseline='src/routes/+page.svelte 13:26'
expect_errors "1 baseline: only the deliberate error (label={42})" "${baseline}"

button="src/lib/components/CounterButton.svelte"
cp "${button}" "${button}.orig"
replace_in "${button}" "label: string;" "caption: string;"
replace_in "${button}" "let { counter, label, children }" "let { counter, caption, children }"
replace_in "${button}" "{label}:" "{caption}:"
expect_errors "2 mutation 1: label renamed in CounterButton only; every parent passing label fails" \
  "$(printf '%s\n' \
    'src/lib/components/Dynamic.svelte 14:19' \
    'src/lib/components/Dynamic.svelte 17:26' \
    'src/routes/+page.svelte 13:26')"
mv "${button}.orig" "${button}"

mv "${button}" "src/lib/components/Button.svelte"
expect_errors "3 mutation 2: CounterButton.svelte renamed; every import of it fails" \
  "$(printf '%s\n' \
    'src/lib/components/Dynamic.svelte 2:29' \
    'src/lib/components/Dynamic.svelte 8:23' \
    'src/routes/+page.svelte 2:29')"
if grep -n 'import.meta.glob("./\*.svelte")' src/lib/components/Dynamic.svelte >/dev/null; then
  echo "NOTE 3 blind spot: src/lib/components/Dynamic.svelte:9 import.meta.glob(\"./*.svelte\") now loads Button.svelte instead,"
  echo "     with no diagnostic; only a text search (Grep) finds it"
else
  echo "FAIL 3 blind spot: the import.meta.glob line is missing from the fixture"
  failures=$((failures + 1))
fi
mv "src/lib/components/Button.svelte" "${button}"

expect_errors "4 restored: back to the baseline" "${baseline}"

if [[ "${failures}" -gt 0 ]]; then
  echo "selftest: ${failures} step(s) did not match; the project check or the language tools are not seeing changes as expected"
  exit 1
fi
echo "selftest: every step matched; the project check sees deliberate breakage"
