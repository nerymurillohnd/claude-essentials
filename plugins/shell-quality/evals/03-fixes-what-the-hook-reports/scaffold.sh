#!/usr/bin/env bash
# A deploy script with two findings ShellCheck reports and shfmt cannot fix (SC2086, SC2164),
# plus project-level shfmt and ShellCheck the plugin's hook can run in any sandbox.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
top=$(cd "${here}/../../../.." 2>/dev/null && pwd) || top=""
mkdir -p .venv/bin
for tool in shellcheck shfmt; do
  src=""
  if [[ -n ${top} && -x ${top}/.venv/bin/${tool} ]]; then src="${top}/.venv/bin/${tool}"; fi
  if [[ -z ${src} ]]; then src=$(command -v "${tool}") || src=""; fi
  if [[ -z ${src} ]]; then
    printf "scaffold: no %s to copy; run make setup in the marketplace checkout\n" "${tool}" >&2
    exit 1
  fi
  cp -L "${src}" ".venv/bin/${tool}"
  chmod 755 ".venv/bin/${tool}"
done
cat >deploy.sh <<'SH'
#!/usr/bin/env bash
set -u

dir=$1
cd $dir
echo "deploying from $(pwd)"
SH
chmod 755 deploy.sh
