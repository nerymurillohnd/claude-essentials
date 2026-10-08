#!/usr/bin/env bash
# Writes a minimal SvelteKit 2 project, not installed: package.json pins @sveltejs/kit 2,
# svelte.config.js holds the config, and one route needs a param matcher.
set -euo pipefail

mkdir -p "src/routes/items/[id]" src/lib
cat >package.json <<'JSON'
{
  "name": "kit2-app",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"
  },
  "devDependencies": {
    "@sveltejs/adapter-auto": "^6.0.0",
    "@sveltejs/kit": "^2.22.0",
    "@sveltejs/vite-plugin-svelte": "^6.0.0",
    "svelte": "^5.36.0",
    "svelte-check": "^4.3.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0"
  }
}
JSON
cat >svelte.config.js <<'JS'
import adapter from "@sveltejs/adapter-auto";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

export default {
  preprocess: vitePreprocess(),
  kit: { adapter: adapter() },
};
JS
cat >"src/routes/items/[id]/+page.svelte" <<'SVELTE'
<script lang="ts">
  import { page } from "$app/state";
</script>

<h1>Item {page.params.id}</h1>
SVELTE

# A first commit, so the plugin's Stop hook can tell this session's changes apart.
printf '%s\n' node_modules/ .svelte-kit/ >.gitignore
git init -q
git add -A
git -c user.name=eval -c user.email=eval@example.com -c commit.gpgsign=false \
  commit -q -m "baseline"
