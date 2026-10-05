---
type: llm
focus: trace
weight: 2
---

PASS if the first tool used to locate symbols is the LSP tool; if an LSP call returned an error or nothing, the session retried it (for example with documentSymbol or hover, or by loading the LSP tool with ToolSearch) before switching to another tool; and any Grep or Glob search is used only for text the language server cannot see (strings, route paths, configuration) or after the session said the language server was not answering.
FAIL if Grep or reading whole files replaces the LSP tool for finding the prop's or the method's references while the LSP tool was answering, or if the session dropped the LSP tool after a single empty result without retrying.
