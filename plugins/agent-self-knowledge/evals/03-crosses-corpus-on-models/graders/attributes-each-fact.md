---
type: llm
focus: last_message
weight: 1
---
PASS if the answer gives a concrete model identifier for the `opus` alias and a concrete context size, and attributes each one to the source that owns it: the alias mapping to the Claude Code documentation, and the model identifier and context size to the platform documentation.
FAIL if it states a model identifier or a context size with no source at all, presents a platform-documentation fact as if it came from the Claude Code documentation, or answers only one half of the question when both halves were asked.
