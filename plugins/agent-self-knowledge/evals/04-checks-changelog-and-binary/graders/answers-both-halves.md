---
type: llm
focus: last_message
weight: 1
---
PASS if the answer both names the release that introduced AGENTS.md support and states whether the machine's own installed build includes it, having read the installed version rather than assuming it.
FAIL if it answers only when the feature shipped and never compares it against the installed build, if it asserts the installed version without having read it, or if it reports a release number it did not source from the changelog.
