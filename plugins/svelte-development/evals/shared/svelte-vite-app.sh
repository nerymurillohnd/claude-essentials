#!/usr/bin/env bash
# Writes and installs a Svelte 5 app on plain Vite, without SvelteKit, then commits it.
set -euo pipefail

mkdir -p src/lib
cat >package.json <<'JSON'
{
  "name": "svelte-vite-app",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "check": "svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "7.3.1",
    "svelte": "5.57.1",
    "svelte-check": "4.7.6",
    "typescript": "6.0.3",
    "vite": "8.3.2"
  }
}
JSON
cat >tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true
  },
  "include": ["src/**/*.ts", "src/**/*.svelte", "vite.config.ts"]
}
JSON
cat >vite.config.ts <<'TS'
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [svelte()],
});
TS
cat >index.html <<'HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>FAQ</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
HTML
cat >src/main.ts <<'TS'
import { mount } from "svelte";
import App from "./App.svelte";

const target = document.getElementById("app");
if (!target) throw new Error("missing #app");

export default mount(App, { target });
TS
cat >src/App.svelte <<'SVELTE'
<script lang="ts">
  let title = "Frequently asked questions";
</script>

<main>
  <h1>{title}</h1>
</main>
SVELTE
npm install --include=dev --ignore-scripts --no-audit --no-fund --loglevel=error
if [[ ! -x node_modules/.bin/svelte-check ]]; then
  echo "npm install left no svelte-check in node_modules/.bin" >&2
  exit 1
fi

# A first commit, so the plugin's Stop hook can tell this session's changes apart.
printf '%s\n' node_modules/ .svelte-kit/ >.gitignore
git init -q
git add -A
git -c user.name=eval -c user.email=eval@example.com -c commit.gpgsign=false \
  commit -q -m "baseline"
