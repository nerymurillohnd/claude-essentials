#!/usr/bin/env bash
# Installs the shared SvelteKit 3 fixture, then declares @sveltejs/kit 3.0.1 in package.json.
# The declared 3.0.1 is newer than the installed 3.0.0, as after an unfinished upgrade, so the
# task asks about a feature of a release the installed package does not have.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
"$(dirname "${case_dir}")/shared/kit3-app.sh"
node -e '
const fs = require("fs");
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
pkg.devDependencies["@sveltejs/kit"] = "3.0.1";
fs.writeFileSync("package.json", JSON.stringify(pkg, null, 2) + "\n");
'
