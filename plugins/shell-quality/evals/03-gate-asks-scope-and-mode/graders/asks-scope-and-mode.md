---
type: llm
focus: last_message
weight: 1
---
PASS on either correct path, and in both cases nothing may be installed. (a) Prerequisites present: it stops and asks the user for both a scope and a configuration mode, showing what each mode would apply, and describes what the gate will do — deny edits that add `shellcheck disable` directives, format and check each shell script Claude touches, block the turn from ending while findings remain. (b) A prerequisite is missing, such as `shellcheck`, `shfmt` or `jq` not being installed: it names what is missing, explains that the gate fails closed without it, and stops there rather than installing.
FAIL if it installs the gate, writes any settings or tool configuration, chooses scope or mode on the user's behalf, asks for only one of the two while prerequisites are present, or claims a prerequisite is missing without having checked.
