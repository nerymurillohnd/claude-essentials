---
type: regex
pattern: 'shellcheck\s+(disable|source=/dev/null)'
target: {source: file, path: deploy.sh}
match: not_contains
flags: i
---
