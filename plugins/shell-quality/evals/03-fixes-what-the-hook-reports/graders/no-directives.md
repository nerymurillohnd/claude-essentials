---
type: regex
target: {source: file, path: deploy.sh}
match: not_contains
flags: i
---
shellcheck\s+(disable|source=/dev/null)
