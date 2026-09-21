---
type: regex
target: {source: file, path: cleanup.sh}
match: not_contains
flags: i
---
shellcheck disable|shellcheck source=/dev/null|SHELLCHECK_OPTS|--exclude|ignore\s*=\s*true
