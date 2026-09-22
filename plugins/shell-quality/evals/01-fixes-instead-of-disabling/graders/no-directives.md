---
type: regex
pattern: 'shellcheck disable|shellcheck source=/dev/null|SHELLCHECK_OPTS|--exclude|ignore\s*=\s*true'
target: {source: file, path: cleanup.sh}
match: not_contains
flags: i
---
