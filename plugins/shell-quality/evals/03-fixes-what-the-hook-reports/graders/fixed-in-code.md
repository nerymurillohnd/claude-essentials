---
type: llm
focus: {source: file, path: deploy.sh}
weight: 1
---
PASS if `deploy.sh` ends by printing the date and time, and the two findings the script started with are fixed in the script itself: the `$dir` expansion is quoted (SC2086) and a failed `cd` is handled, for example `cd "$dir" || exit` (SC2164). The script must still change into the directory given as its first argument and print where it deploys from.
FAIL if the date line is missing, if either finding remains, if either was silenced with a `# shellcheck disable` directive, an rc file or `SHELLCHECK_OPTS` instead of fixed, or if the script's behaviour changed.
