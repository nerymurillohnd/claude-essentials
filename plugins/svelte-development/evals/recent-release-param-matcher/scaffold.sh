#!/usr/bin/env bash
# Installs the shared SvelteKit 3 fixture, then declares @sveltejs/kit 3.0.1 in package.json.
# 3.0.1 is newer than the "Verified against 3.0.0" line of the plugin's references, so the
# changelog check is due; the installed package stays 3.0.0, as after an unfinished upgrade.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
"$(dirname "${case_dir}")/shared/kit3-app.sh"
node -e '
const fs = require("fs");
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
pkg.devDependencies["@sveltejs/kit"] = "3.0.1";
fs.writeFileSync("package.json", JSON.stringify(pkg, null, 2) + "\n");
'
