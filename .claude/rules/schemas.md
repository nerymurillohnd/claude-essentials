---
paths:
  - "**/*.json"
  - "plugins/**/.lsp.json"
  - "plugins/**/.mcp.json"
---

# Schemas

- The `$schema` that `init` writes (`plugin.schema.json`) and its counterpart `marketplace.schema.json` return 404.
- There is no published official schema; the authority is `claude plugin validate`.
- The candidate schemas offered (written for 2.1.281) reject valid configuration: they lack `requestTimeout` for LSP (2.1.288) and `bareElicitationCapability` for MCP (2.1.287).
- That is why the ADR decided not to adopt them.
- Still to verify: the claim that one invalid LSP server drops all the others in the same file, and the claim that `$schema` invalidates `.lsp.json`.
- The full URL is `https://anthropic.com/claude-code/plugin.schema.json`; never hand-write a schema that imitates Claude Code.
- Test both unverified claims in an isolated config before relying on them.
