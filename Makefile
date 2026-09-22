PY := .venv/bin/python
UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
.PHONY: setup check generate lint lint-staged types test-fast validate validate-cli test-slow versions fix fix-file clean help
setup:         ## create/refresh .venv from uv.lock (the only target that calls uv)
	$(UV) sync --locked
# Every target below runs a binary from .venv, so each one depends on the interpreter being
# there. Without this the recipes would fail with "no such file or directory" and no advice;
# with it they fail closed, naming the one command that fixes it (§A4).
$(PY):
	@echo "error: .venv is missing; run \`make setup\`" >&2; exit 2
check: generate lint types test-fast validate validate-cli test-slow ## the whole gate, in order
generate: $(PY) ## 10 regenerate catalog + issue forms, then fail on diff
	$(PY) -m scripts.marketplace.generate_marketplace
	$(PY) -m scripts.github.generate_issue_forms
	git diff --exit-code -- .claude-plugin/marketplace.json .github/ISSUE_TEMPLATE
PY_FILES := $(shell git ls-files --cached --others --exclude-standard -- 'scripts/*.py')
lint: $(PY)    ## 20 ruff format --check + ruff check (explicit .py list), shell, json, text bytes, actionlint, zizmor
	$(PY) -m ruff format --check $(PY_FILES)
	$(PY) -m ruff check $(PY_FILES)
	$(PY) -m scripts.lint.lint_files
lint-staged: $(PY) ## same checks, only on staged + modified + untracked files (guard-commit)
	$(PY) -m scripts.lint.lint_files --staged
types: $(PY)   ## 30 basedpyright, typeCheckingMode=all + failOnWarnings, venv interpreter, GitHub annotations in CI
	PATH="$(CURDIR)/.venv/bin:$$PATH" .venv/bin/basedpyright --threads
test-fast: $(PY) ## 40 in-process tests
	$(PY) -m pytest -m "not slow and not coverage_matrix"
validate: $(PY) ## 50 catalog + plugin invariants (M P C S H R B W E G T Q X)
	$(PY) -m scripts.marketplace.validate_marketplace
	$(PY) -m scripts.plugin_validation.validate_plugins
validate-cli: $(PY) ## 60 claude plugin validate --strict on marketplace + every plugin
	$(PY) -m scripts.plugin_validation.validate_claude
test-slow: $(PY) ## 70 process-spawning tests + plugin suites under bash and /bin/bash + advisory smoke run of shipped Python
	$(PY) -m pytest -m slow
	$(PY) -m scripts.plugin_validation.run_plugin_suites
versions: $(PY) ## version-bump rules and route vs the latest tags / origin/main
	$(PY) -m scripts.versioning.check_versions $(VERSIONS_ARGS)
fix: $(PY)     ## writer: ruff format, ruff check --fix (safe), shfmt -w, canonical JSON
	$(PY) -m ruff format $(PY_FILES)
	$(PY) -m ruff check --fix $(PY_FILES)
	$(PY) -m scripts.lint.lint_files --fix
fix-file: $(PY) ## writer for one file, on demand: make fix-file FILE=path
	$(PY) -m scripts.lint.lint_files --fix --file "$(FILE)"
clean: $(PY)   ## prune .claude/.cache/hooks stamps and stale state
	$(PY) -m scripts.harness.inventory --clean --apply
help:          ## list every target with what it does
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'
