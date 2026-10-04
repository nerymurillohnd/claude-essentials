---
paths:
  - "plugins/**/hooks/**"
  - "plugins/**/.mcp.json"
  - "plugins/**/.lsp.json"
  - "plugins/**/bin/**"
  - "plugins/**/monitors/**"
  - ".github/workflows/**"
  - ".github/labeler.yml"
  - ".github/CODEOWNERS"
  - "SECURITY.md"
  - "docs/security-review.md"
---

# Security

- Every PR that touches hooks, `.mcp.json`, `.lsp.json`, `bin/`, `monitors/` or workflows gets the `security-review` label and needs a code owner's approval.
- Downloads at install time, undeclared remote servers, secrets and machine-specific paths are not allowed.
- Vulnerabilities are reported through GitHub's private vulnerability reporting.
