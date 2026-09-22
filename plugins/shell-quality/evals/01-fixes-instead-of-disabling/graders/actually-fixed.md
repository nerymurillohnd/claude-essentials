---
type: llm
focus: {source: file, path: cleanup.sh}
weight: 1
---
PASS if the findings ShellCheck reports on this script are fixed in the script itself: the loop iterates over a glob instead of the output of `ls` (SC2045), and the variable in the `rm` is quoted (SC2086). The script must still delete the `.log` files it was meant to delete. Extra hardening beyond those findings neither helps nor hurts.
FAIL if either finding remains, if either was silenced with a `shellcheck disable` directive or an rc entry instead of fixed, or if the script no longer removes the intended files.
