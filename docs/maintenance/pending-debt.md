# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0039 — H2 checks a `SubagentStop` matcher against tool names, but `SubagentStop` matches agent types

- **Status:** Pending
- **Category:** tooling
- **Evidence:**
  - **Confirmed facts:** `plugins/evidence-reader/hooks/hooks.json`'s `SubagentStop` matcher `^evidence-reader:(document-reader|tabular-auditor|image-inspector)$` triggers `H2 ...: matcher '...' matches no known tool` (warning) from `scripts/plugin_validation/hook_contract.py:254-299` (`check_matchers`/`_regex_findings`), which tests every event's regex matcher against `KNOWN_TOOLS` regardless of event. The official docs settle what `SubagentStop`'s matcher actually filters on: "Matches on agent type, same values as SubagentStart... The `agent_type` field is the value used for matcher filtering" (`https://code.claude.com/docs/en/hooks#subagentstop`, verified 2026-09-22 against Claude Code 2.1.278). `agent_type` for a custom subagent is the plugin-qualified name (`evidence-reader:document-reader`), never a tool name, so evidence-reader's matcher is correct and H2's check is testing it against the wrong list for this event. `evidence-reader` is the first plugin in this repo to use `SubagentStop` with an agent-type matcher (no other plugin exercises this path, so the gap was previously unobserved).
  - **Inferences:** Every future plugin that scopes a `SubagentStop` (or `SubagentStart`) hook to specific agent types will get the same spurious warning, training maintainers to ignore H2 output for those two events.
  - **Open questions:** Whether `SubagentHandback` (a `PreToolUse`/`PostToolUse` matcher, which genuinely does match a tool name) needs any change, or only `SubagentStop`/`SubagentStart`. Whether "known agent types" should be validated at all for these two events, given a plugin's own `agents/*.md` files are a real, checkable source for its own agent names (but a matcher can legitimately reference a *different* plugin's or a built-in agent's type too).
- **Impact / risk:** Low; a misleading non-blocking warning, not a functional defect — `make validate`'s exit code isn't driven by this warning alone.
- **Owner or responsible area:** `scripts/plugin_validation/hook_contract.py`
- **Next action:** Either exempt `SubagentStop`/`SubagentStart` matchers from the tool-name check entirely, or add a second check that validates them against the plugin's own `agents/*.md` names (accepting a matcher naming a different plugin or a built-in agent without a warning).
- **Review condition:** Close when a `SubagentStop` matcher naming a real custom agent type no longer produces an H2 warning, verified with evidence-reader's `hooks.json` as the reproduction, covered by a validator test case.
- **Related records:** `plugins/evidence-reader/hooks/hooks.json`

### DEBT-0035 — Rewritten eval cases of three plugins were never measured, and their "Last verified" dates predate their releases

- **Status:** Pending
- **Category:** testing
- **Evidence:**
  - **Confirmed facts:** `repo-auditor` on `a58e326` (2026-09-22): agent-self-knowledge cases 01, 02, 03 and 05, block-no-verify 01-04, and verify-completion 01, 03 and 04 were rewritten on that branch and never run; `docs/audits/2026-09-22-final-head-evals.md` measures only ruff-quality, shell-quality, agent-self-knowledge 04 and verify-completion 02. CI's `Eval <plugin>` jobs skip because the repository has no `ANTHROPIC_API_KEY` (log of job 106763388263: "ANTHROPIC_API_KEY is not set; the eval of ruff-quality is skipped") and still report success. The Compatibility "Last verified" dates of agent-self-knowledge (2026-09-20), block-no-verify and verify-completion (2026-09-19) predate their 0.2.0, 0.1.3 and 0.1.2 releases. The PR merged with the auditor's FAIL (maintainer's decision).
  - **Inferences:** A suite that was never run can carry a grader defect like the one verify-completion 02 had (it graded a `CLAUDE.md` rule that eval runs never load).
  - **Open questions:** Whether the maintainer adds `ANTHROPIC_API_KEY` to the `evals` environment, which makes CI measure every runtime change.
- **Impact / risk:** Unmeasured behavior claims; a skipped eval reads as a passed check.
- **Owner or responsible area:** `plugins/*/evals/`, `.github/workflows/evals.yml`, the three plugin READMEs
- **Next action:** Run the listed cases pinned (3 runs per arm) and record them in `docs/audits/`; re-verify each plugin on its new version and update or downgrade its "Last verified" row; make a skipped eval job visible as skipped rather than green.
- **Review condition:** Close when every case has a dated result on the current head and every "Last verified" date is on or after its plugin's current version.
- **Related records:** `docs/audits/2026-09-22-final-head-evals.md`

### DEBT-0036 — Workflows call uv and pytest directly, one pin has no version comment, and gate suites discard stderr

- **Status:** Pending
- **Category:** tooling
- **Evidence:**
  - **Confirmed facts:** `repo-auditor` on `a58e326`: `tag-versions.yml:48`, `labels.yml:37` and `triage.yml:61` run `uv sync --locked --no-build …` instead of `make setup`; `nightly.yml:71` runs `.venv/bin/python -m pytest -m coverage_matrix` with no make target; `ci.yml:145` pins `validate-plugins@a727be1…` with a date comment, not the `# vX.Y.Z` CLAUDE.md asks for, and `check_workflow_pins` accepts it. The ruff-quality and shell-quality suites run the gate with `2>/dev/null` (`test-gate.sh:71` in each), so a "command not found" in the handler would not fail a case.
  - **Inferences:** The CLAUDE.md rule "every make target runs it from .venv" and the pin rule each have an unrecorded exception.
  - **Open questions:** Whether the write-token workflows need `--no-build` wheels that `make setup` does not give.
- **Impact / risk:** Low; drift between the stated rules and the workflows, and a class of handler error the suites would not see.
- **Owner or responsible area:** `.github/workflows/`, `Makefile`, `scripts/plugin_validation/suites/`
- **Next action:** Add `make` targets (or record the exceptions in CLAUDE.md), align the pin rule with its checker, and make both suites fail a case whose stderr contains "command not found".
- **Review condition:** Close when no workflow calls uv or pytest outside a make target, the pin rule and `check_workflow_pins` agree, and a suite case proves the stderr check.
- **Related records:** `.github/workflows/`

### DEBT-0031 — `verify-completion`'s `/tmp` state fallback trusts a directory it did not create

- **Status:** Pending
- **Category:** security
- **Evidence:**
  - **Confirmed facts (re-verified 2026-09-22):** `plugins/verify-completion/scripts/gate.sh:28-34` (`state_dir`, line numbers shifted slightly since this was filed) still accepts `${TMPDIR:-/tmp}/verify-completion-<uid>` on `[[ -d ${dir} && -w ${dir} ]]` alone, without `-O` (owned by current user) or `! -L` (not a symlink), and `gate.sh:88` then writes empty marker files there with `: >`. `ruff-quality`'s equivalent (`plugins/ruff-quality/scripts/ruff-gate.sh:48`) checks `[[ -d ${dir} && ! -L ${dir} && -O ${dir} && -w ${dir} ]]`, with the comment "A fallback directory someone else created (or a symlink to one) is never trusted" — confirming the divergence is real and still unresolved.
  - **Inferences:** On a shared `/tmp`, a directory planted under that name could redirect the marker writes through a symlink and truncate a file the user owns. The path is reached only when `CLAUDE_PLUGIN_DATA` is unset, and macOS gives each user a private `TMPDIR`.
  - **Open questions:** Whether any supported Claude Code build leaves `CLAUDE_PLUGIN_DATA` unset for a plugin hook.
- **Impact / risk:** Low; fallback path on shared-`/tmp` systems only.
- **Owner or responsible area:** `plugins/verify-completion/scripts/gate.sh`
- **Next action:** Require `[[ -O ${dir} && ! -L ${dir} ]]` as the gate plugins do, and create marker files without following a symlink. Runtime change: bump and CHANGELOG.
- **Review condition:** Close when a suite case with a foreign-owned or symlinked fallback directory shows the hook writing nothing there.
- **Related records:** [plugin CHANGELOG](../../plugins/verify-completion/CHANGELOG.md)

### DEBT-0032 — Agent and workflow descriptions in `verify-completion` open with a noun phrase

- **Status:** Pending
- **Category:** documentation
- **Evidence:**
  - **Confirmed facts:** `plugins/verify-completion/agents/completion-verifier.md:3` opens "Independent, read-only verifier…" and `plugins/verify-completion/workflows/deep-verify.js:4` opens "Cross-checked verification…". The plugin-authoring rule asks a skill description to open with the instruction it gives; the skill in this plugin does. Found by the 0.1.2 release review on 2026-09-22; both texts predate it.
  - **Inferences:** A description that opens with what the component is, rather than when to use it, is weaker routing text for Claude's delegation choice.
  - **Open questions:** Whether the rule should extend from skills to agents and workflows; today it names skills only.
- **Impact / risk:** Low; routing quality, no behavior defect observed.
- **Owner or responsible area:** `plugins/verify-completion/agents/`, `plugins/verify-completion/workflows/`, `.claude/rules/plugin-authoring.md`
- **Next action:** Decide whether the rule covers agents and workflows; if it does, rewrite both descriptions from their files and extend `test_frontmatter.py`. Runtime change: bump and CHANGELOG.
- **Review condition:** Close when the rule's scope is decided and both descriptions follow it.
- **Related records:** [plugin-authoring rule](../../.claude/rules/plugin-authoring.md)

### DEBT-0019 — `agent-self-knowledge` ships a URL fetcher with no scheme or host validation

- **Status:** Pending (risk accepted)
- **Category:** security
- **Evidence:**
  - **Confirmed facts:** `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py` defines `cmd_raw`, which passes its argument straight to `fetch()` with no scheme or host check. The skill's `allowed-tools` grants `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *)`, so any argument runs without a per-command approval prompt. Both vectors were reproduced on 2026-09-20: `raw file://<path>` printed a local canary file, and `raw https://example.com` fetched an unrelated host. The cache widens the first vector: a `raw file://` fetch also stores the file's text in `${XDG_CACHE_HOME:-~/.cache}/ccdocs` (reproduced 2026-09-22 at 0644); since 0.2.0 new entries are created 0600, so the copy is no longer readable by other users, but it persists until the cache is cleared.
  - **Inferences:** Content the model reads (a documentation page, an issue, a web result) could induce a `raw` call that exfiltrates local data, since no prompt intervenes. The plugin is published publicly, so every installer inherits the capability.
  - **Open questions:** None. The vector is confirmed and the fix is known.
- **Impact / risk:** Arbitrary local file read and arbitrary outbound request, without user approval, on any machine where the plugin is enabled. The maintainer, Nery Samuel Murillo, accepted this explicitly on 2026-09-20 after seeing the reproduction and the proposed fix, to avoid any change to a retrieval behavior that had just been validated. Evidence that the fix is behaviorally inert: the clean-session test that validated the skill used `find`, `grep`, `outline`, `page`, `changelog` and `version` — `raw` was never called.
- **Owner or responsible area:** `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py`
- **Next action:** Add a host allowlist in `fetch()` restricted to `code.claude.com`, `raw.githubusercontent.com` and `registry.npmjs.org`, rejecting every other host and every non-`https` scheme; or remove `raw`. Either is a runtime change and needs a version bump and a CHANGELOG entry.
- **Review condition:** Close when `raw file:///etc/hosts` and `raw https://example.com` both exit non-zero with an explicit rejection, covered by a case in the plugin's test suite.
- **Related records:** [design spec](../superpowers/specs/2026-09-20-agent-self-knowledge-design.md), [plugin CHANGELOG](../../plugins/agent-self-knowledge/CHANGELOG.md)

### DEBT-0023 — `agent-self-knowledge` can report a settings key as not found when it exists undocumented

- **Status:** Pending
- **Category:** correctness
- **Evidence:**
  - **Confirmed facts:** The settings schema inside the installed Claude Code 2.1.278 binary defines `worktree.location`, described as "Directory under which Claude Code Desktop creates the worktrees of SSH sessions that run on this machine ... The CLI (--worktree, EnterWorktree, agent isolation) does not read it yet." The same key returns 0 hits across the 99,415 lines of `https://code.claude.com/docs/llms-full.txt`, which documents only `baseRef`, `bgIsolation`, `sparsePaths` and `symlinkDirectories` under `worktree`. Both measured on 2026-09-20. In the clean-session test the skill reported the key as non-existent.
  - **Inferences:** `ccdocs.py` reads the published documentation, the upstream changelog and the npm registry. None of the three carries the settings schema, so the skill's three-search negative protocol cannot distinguish "not documented" from "does not exist" for any settings key.
  - **Open questions:** How many other keys are in the shipped schema but not the docs. Whether the schema is exposed anywhere fetchable, or only inside the binary.
- **Impact / risk:** The bounded negative claim is the skill's headline behavior, and for settings keys it can be a false negative — the exact failure mode the plugin exists to prevent. A user told a key does not exist may build a workaround for a problem the product already solves.
- **Owner or responsible area:** `plugins/agent-self-knowledge/skills/claude-code-docs/`
- **Next action:** Decide whether the skill should read the installed binary's settings schema (for example `strings` over the executable, or a documented dump command if one exists) before reporting any settings key as absent, and whether that is worth the scope. Until then the README Limitations row carries the constraint.
- **Review condition:** Close when a settings key that exists only in the shipped schema is reported as undocumented-but-present, verified with `worktree.location` as the reproduction, and covered by an eval case.
- **Related records:** [design spec](../superpowers/specs/2026-09-20-agent-self-knowledge-design.md), [DEBT-0019](#debt-0019--agent-self-knowledge-ships-a-url-fetcher-with-no-scheme-or-host-validation)

### DEBT-0021 — Plugin name restrictions are undocumented upstream

- **Status:** Pending
- **Category:** docs
- **Evidence:**
  - **Confirmed facts:** The maintainer reported on 2026-09-20 that a plugin name containing "Claude" is rejected, while the same word is accepted in a repository name, a marketplace name, and a skill name; the plugin was renamed to `agent-self-knowledge` as a result. A search of the full documentation corpus (99,415 lines of `llms-full.txt`) finds reserved-name rules only for MCP servers ("Claude Browser", "Claude Preview", `workspace`) and for agent names containing `:`. Nothing documents a restriction on plugin names.
  - **Inferences:** Either the restriction is enforced somewhere other than `claude plugin validate` (marketplace submission or claude.ai organization sync), or it comes from a rule that exists in code but not in the docs.
  - **Open questions:** Which surface rejects the name, with which exact message, and whether it applies to any occurrence of "claude" or only to certain forms.
- **Impact / risk:** A contributor can pick a name that passes every local gate and is rejected later, after the README, badges, tags and directory all carry it.
- **Owner or responsible area:** `docs/contributing/plugins.md`
- **Next action:** Reproduce the rejection, capture the exact message and the surface that emits it, then document the constraint in the contributing guide and report the documentation gap upstream.
- **Review condition:** Close when the constraint is reproduced with captured output and written into `docs/contributing/plugins.md`.
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md)

### DEBT-0018 — Plugin release-review checklist records are stale against the plugins' latest commits

- **Status:** Pending — re-verified against current repo state 2026-09-22, evidence refreshed (facts below superseded the original 2026-09-20 measurement; this is the same underlying gap, now against a fifth plugin)
- **Category:** process
- **Evidence:**
  - **Confirmed facts (2026-09-22):** `.claude/state/checklists/` holds `plugin-release-review--*.json` for `agent-self-knowledge` (mtime 2026-09-21T01:07), `ruff-quality` (2026-09-22T06:06), `shell-quality` (2026-09-19T06:08), and `verify-completion` (2026-09-19T03:02); there is still no record for `block-no-verify` at all. `git log -1 --format=%cI -- plugins/<id>/` gives the last commit touching each plugin: `block-no-verify` 2026-09-22T06:53:17-06:00, `ruff-quality` and `shell-quality` and `agent-self-knowledge` 2026-09-22T07:43:10-06:00, `verify-completion` 2026-09-22T07:22:38-06:00. Every existing record predates its plugin's last commit, and `block-no-verify` has never had one.
  - **Inferences:** The gap widened rather than closed: the original report covered four plugins (one with no record, three stale by ~18 hours); today it covers five plugins (one still with no record ever, four stale by hours to over a day), because `agent-self-knowledge` joined the catalog and inherited the same pattern.
  - **Open questions:** Same as originally filed — whether the checklist's newer items (`cross-plugin`, `metadata-fit`, `bundled-reviews`) would surface anything `repo-auditor`'s matrix does not already cover; unresolved because no run has happened since they were added.
- **Impact / risk:** Five plugins are currently published from a state no release review covers post-dates. The maintainer has repeatedly accepted this trade-off (sync `main` first, review afterwards) across at least two prior instances (2026-09-20, and implicitly again through 2026-09-22's PR #19 merge, per `.claude/state/checklists/` timestamps all predating that merge).
- **Owner or responsible area:** `.claude/skills/plugin-release-review/`, `.claude/rules/plugin-authoring.md`
- **Next action:** Run `/plugin-release-review` to completion on all five plugins (`agent-self-knowledge`, `block-no-verify`, `ruff-quality`, `shell-quality`, `verify-completion`) against the content on `main`, and fix whatever they surface in a follow-up change.
- **Review condition:** Close when all five `.claude/state/checklists/plugin-release-review--<id>.json` records are complete and post-date the last commit touching their plugin.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md), [DEBT-0011](resolved-debt.md#debt-0011--2026-09-19--non-runtime-changes-are-pushed-directly-to-main-the-checks-run-before-the-push), [plugin-authoring rule](../../.claude/rules/plugin-authoring.md)

### DEBT-0012 — Plugin hook suites run only against the CI runner's jq

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `verify-completion`'s `analyze.jq` first used `capture(...)?.field` (jq 1.8 syntax) and a variable named `$end` (reserved in jq 1.6). Its 110-case suite passed on the maintainer's jq 1.8.2, failed 55 cases on jq 1.7.1 and failed to compile on jq 1.6 (2026-09-19). After the fix it passes on jq 1.6 (built from the release tarball), 1.7.1, and 1.8.2. Re-verified 2026-09-22: `scripts/plugin_validation/run_plugin_suites.py` (the current Python runner, replacing the removed `npm test` / `scripts/lib/plugin-shell-tests.test.mjs`, wired to `make test-slow`/`make check` at `Makefile:36`) discovers suites via the glob `scripts/plugin_validation/suites/*test-*.sh` (`run_plugin_suites.py:37`) — suites now live at `scripts/plugin_validation/suites/<id>/test-*.sh`, not `plugins/**/test-*.sh` — and runs each against whatever `jq` is first on `PATH`, with no version matrix; grepped every `.github/workflows/*.yml` and the `Makefile` for a jq-version pin or matrix: none exists, so CI still installs and runs against a single `jq`.
  - **Inferences:** Any plugin that claims "jq ≥ 1.6" (verify-completion's README does; `plugins/verify-completion/README.md` still states the range 1.6–1.8.2) can regress on older jq without CI noticing; jq 1.6 is what Ubuntu 22.04 ships.
  - **Open questions:** Whether to download pinned jq 1.6 and 1.7.1 binaries in CI (Linux x86-64 release assets exist for both) or run the suites in an `ubuntu:22.04` container.
- **Impact / risk:** A hook that fails to compile fails open, so users on older jq silently lose enforcement.
- **Owner or responsible area:** `.github/workflows/ci.yml`, `scripts/plugin_validation/run_plugin_suites.py`
- **Next action:** Run every plugin shell suite under each jq version a plugin README claims, with the versions pinned in CI.
- **Review condition:** Close when CI fails on a jq-1.8-only construct in a plugin that claims jq ≥ 1.6.
- **Related records:** [verify-completion design](../superpowers/specs/2026-09-19-verify-completion-design.md)

### DEBT-0007 — The plugin-shape READMEs link to an `evals/` directory the templates don't ship

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `templates/plugin-{bundle,skill-only,agent-only}/README.md` still link to `evals/` in their Verification section (re-verified 2026-09-22, exact text: "**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are ..."). None of the three template directories contains an `evals/` subdirectory (`ls templates/plugin-bundle templates/plugin-skill-only templates/plugin-agent-only` each show only `agents/`|`skills/`, `CHANGELOG.md`, `LICENSE`, `README.md`) — unchanged since the debt was filed. By contrast, all five real plugins (`agent-self-knowledge`, `block-no-verify`, `ruff-quality`, `shell-quality`, `verify-completion`) do carry `evals/`, so the eval requirement is enforced for published plugins but the templates that scaffold new ones don't start with it.
  - **Inferences:** A plugin copied from a template ships a broken link until its author adds an eval suite.
  - **Open questions:** The exact grader-file syntax for "skill must not fire" (`tool_used`, `min`/`max`, `arm`) must be verified against [plugin-evals](https://code.claude.com/docs/en/plugin-evals) before scaffolding it.
- **Impact / risk:** A broken link in every new plugin scaffolded from a template, and no built-in starting point for the eval suite `make validate`'s R-invariants already expect a published plugin to carry.
- **Owner or responsible area:** `templates/`, `scripts/plugin_validation/`
- **Next action:** Add a verified `evals/` skeleton (a trigger case and a non-trigger case) to each shape, plus the structural validator.
- **Review condition:** Close when every shape ships `evals/`, the link resolves, and `make validate` enforces the suite shape.
- **Related records:** [PR #6](https://github.com/nerymurillohnd/claude-essentials/pull/6)
