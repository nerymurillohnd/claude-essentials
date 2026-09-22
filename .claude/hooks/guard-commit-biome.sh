#!/usr/bin/env bash
# migration shim: settings.json still names this path until the session restarts (step 8)
exec "$(dirname "${BASH_SOURCE[0]}")/guard-commit.sh"
