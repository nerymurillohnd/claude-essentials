PY := .venv/bin/python
UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
.PHONY: setup check generate lint lint-staged types test-fast validate validate-cli test-slow versions fix fix-file clean help
setup:         ## create/refresh .venv from uv.lock (the only target that calls uv)
	$(UV) sync --locked
check: generate lint types test-fast validate validate-cli test-slow
generate:      ## 10 regenerate catalog + issue forms, then fail on diff
#	$(PY) -m scripts.marketplace.generate_marketplace   # ported at step 4
#	$(PY) -m scripts.github.generate_issue_forms        # ported at step 4
	git diff --exit-code -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
PY_FILES := $(shell git ls-files --cached --others --exclude-standard -- 'scripts/*.py')
lint:          ## 20 ruff format --check + ruff check (explicit .py list), shell, json, text bytes, actionlint, zizmor
	$(PY) -m ruff format --check $(PY_FILES)
	$(PY) -m ruff check $(PY_FILES)
#	$(PY) -m scripts.lint.lint_files                    # ported at step 6
lint-staged:   ## same checks, only on staged + modified + untracked files (guard-commit)
#	$(PY) -m scripts.lint.lint_files --staged           # ported at step 6
types:         ## 30 basedpyright, typeCheckingMode=all + failOnWarnings, venv interpreter, GitHub annotations in CI
	PATH="$(CURDIR)/.venv/bin:$$PATH" .venv/bin/basedpyright --threads
test-fast:     ## 40 in-process tests
	$(PY) -m pytest -m "not slow and not coverage_matrix"
validate:      ## 50 catalog + plugin invariants (M P C S H R B W E G T Q X)
#	$(PY) -m scripts.marketplace.validate_marketplace   # ported at step 4
#	$(PY) -m scripts.plugin_validation.validate_plugins # ported at step 5
validate-cli:  ## 60 claude plugin validate --strict on marketplace + every plugin
#	$(PY) -m scripts.plugin_validation.validate_claude  # ported at step 5
test-slow:     ## 70 process-spawning tests + plugin suites under bash and /bin/bash + plugin Python under its floor
	$(PY) -m pytest -m slow
#	$(PY) -m scripts.plugin_validation.run_plugin_suites # ported at step 5
versions:      ## version-bump rules and route vs the latest tags / origin/main
	$(PY) -m scripts.versioning.check_versions $(VERSIONS_ARGS)
fix:           ## writer: ruff format, ruff check --fix (safe), shfmt -w, canonical JSON
	$(PY) -m ruff format $(PY_FILES)
	$(PY) -m ruff check --fix $(PY_FILES)
#	$(PY) -m scripts.lint.lint_files --fix              # ported at step 6
fix-file:      ## writer for one file (post-edit hook): make fix-file FILE=path
#	$(PY) -m scripts.lint.lint_files --fix --file "$(FILE)" # ported at step 6
clean:         ## prune .claude/.cache/hooks stamps and stale state
#	$(PY) -m scripts.harness.inventory --clean          # ported at step 6
help:
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'
