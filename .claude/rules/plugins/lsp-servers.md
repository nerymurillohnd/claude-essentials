---
paths:
  - "plugins/**/.lsp.json"
  - "plugins/**/.mcp.json"
  - "plugins/**/.claude-plugin/plugin.json"
---

# LSP and MCP servers in plugins

Verified on Claude Code 2.1.289 on 2026-10-05, in clean `--restricted` sessions with only the plugin loaded (svelte-development, svelte-language-server 0.18.4).

- Set `"workspaceFolder": "${CLAUDE_PROJECT_DIR}"` in every server.
- The variable is substituted there (manifest reference, "Where each variable resolves"), and the server worked with it.
- The docs give no default for `workspaceFolder`, so the root stays explicit.
- Claude Code picks the server by a file's last extension only.
- A compound key such as `.svelte.ts` passes `claude plugin validate --strict` but is never used.
- Calls on `counter.svelte.ts` returned `No LSP server available for file type: .ts`.
- Never add compound keys.
- Map only the extensions the server really answers for.
- `svelteserver` mapped to `.ts`/`.js` returned empty results for every operation. That hides symbols instead of reporting a missing server.
- `svelteserver` also takes those extensions from a TypeScript server the user may have.
- One extension, one server.
- Always pass the server's transport arguments (for example `"args": ["--stdio"]`).
- Set the lifecycle keys explicitly: `startupTimeout`, `shutdownTimeout`, `requestTimeout` (default 60000), `restartOnCrash` (default true), `maxRestarts`, `diagnostics` (default true).
- svelte-development uses 30000, 10000, 60000, true, 3, true.
- `requestTimeout` was lowered from 90000 to the documented default on 2026-10-06: nothing justified 90 s.
- Observed with a plugin's stdio MCP server: prefixing `PATH=` to the `claude` test command did not let the server find a binary there.
- An absolute `command` worked.
- Test servers whose binary is not installed globally with an absolute `command` in a scratch copy of the plugin, never in the repository.
- Code intelligence for another language (TypeScript for Svelte projects) belongs in its own plugin.
- `claude plugin validate` does not read `.lsp.json` (components page, "LSP servers").
- One invalid entry makes Claude Code skip the whole file at load, with `Invalid LSP server config for ".lsp.json"` only in the `/plugin` Errors tab.
- Prove every `.lsp.json` change in a real session (the server answers an LSP call), never with the validator alone.
- The unknown-key check applies to the `lspServers` key of `plugin.json`, which the validator does read.
- Keep servers in `.lsp.json` and `.mcp.json` at the plugin root.
- Add no `lspServers` or `mcpServers` key for the same servers.
- Claude Code loads the root file first, then the manifest's declarations.
- A later server with the same name replaces the earlier one (manifest reference, "lspServers", "mcpServers").
- MCP servers (components page, "Reach users on claude.ai and Cowork"): a local stdio server runs only in Claude Code and in Cowork on the user's machine.
- A remote `https://` server is also offered on claude.ai and Cowork as a connector.
- svelte-development's remote server qualifies.
- The plugin has not been tested on those surfaces, so its README does not claim them.
- Extension conflicts: when two enabled servers claim an extension, the first registered handles it and the other is unused for it.
- The Errors tab shows `LSP server "<name>" is not used for <ext> files`.
- This holds whether the servers come from one plugin or two.
