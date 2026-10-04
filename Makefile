# One entry point for every gate. CI runs exactly these targets (docs/testing.md).
# The repository has no dependency manifest: tools are resolved by name on PATH
# locally and installed at these pinned versions on CI runners (`make ci-tools`).

CLAUDE_CODE_VERSION := 2.1.289
PRETTIER_VERSION := 3.9.9
ACTIONLINT_VERSION := 1.7.12
ACTIONLINT_SCRIPT_SHA := 914e7df21a07ef503a81201c76d2b11c789d3fca
RUFF_VERSION := 0.16.10
BASEDPYRIGHT_VERSION := 1.40.1
CHECK_JSONSCHEMA_VERSION := 0.38.2
ZIZMOR_VERSION := 1.30.1

PLUGIN_DIRS := $(wildcard plugins/*)
WORKFLOWS := $(wildcard .github/workflows/*.yml)
ISSUE_FORMS := $(filter-out .github/ISSUE_TEMPLATE/config.yml,$(wildcard .github/ISSUE_TEMPLATE/*.yml))

.PHONY: check validate repo readmes tests format python workflows schemas test-install release-dry-run ci-tools help

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

check: validate repo readmes tests format python workflows schemas ## Run every gate (same as CI)
	@echo "make check: all gates passed"

validate: ## Official validator on the marketplace and on each plugin (--strict)
	claude plugin validate . --strict
	@for dir in $(PLUGIN_DIRS); do claude plugin validate "$$dir" --strict || exit 1; done

repo: ## Repository gates: catalog, names, versions, changelogs, portability, labels, tags
	uv run scripts/check_repo.py

readmes: ## Generated README content is up to date
	uv run scripts/sync_readmes.py --check

tests: ## Unit tests, including the deliberately broken fixtures
	uv run python -m unittest discover -s tests -t . -v

format: ## Prettier check for Markdown, JSON and YAML
	prettier --check .

python: ## Ruff lint and format check, basedpyright with warnings as errors
	ruff check .
	ruff format --check .
	basedpyright --warnings

workflows: ## actionlint and the zizmor security audit for GitHub Actions
	actionlint
	uvx zizmor@$(ZIZMOR_VERSION) --offline --collect=workflows .github/workflows

schemas: ## GitHub workflow and issue-form files against their JSON Schemas
	check-jsonschema --builtin-schema vendor.github-workflows $(WORKFLOWS)
	check-jsonschema --builtin-schema vendor.github-issue-forms $(ISSUE_FORMS)
	check-jsonschema --builtin-schema vendor.github-issue-config .github/ISSUE_TEMPLATE/config.yml

test-install: ## Install every plugin in an isolated config (in place, cache copy, session)
	uv run scripts/test_install.py

release-dry-run: ## Preview a plugin release: make release-dry-run PLUGIN=<name> LEVEL=<major|minor|patch>
	uv run scripts/release.py plugin $(PLUGIN) $(LEVEL) --dry-run

ci-tools: ## CI only: install the pinned tool versions on the runner
	npm install --global --no-fund --no-audit prettier@$(PRETTIER_VERSION)
	uv tool install ruff==$(RUFF_VERSION)
	uv tool install basedpyright==$(BASEDPYRIGHT_VERSION)
	uv tool install check-jsonschema==$(CHECK_JSONSCHEMA_VERSION)
	curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/$(ACTIONLINT_SCRIPT_SHA)/scripts/download-actionlint.bash | bash -s -- $(ACTIONLINT_VERSION) "$$HOME/.local/bin"
	curl -fsSL https://claude.ai/install.sh | bash -s $(CLAUDE_CODE_VERSION)
