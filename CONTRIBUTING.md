# Contributing to claude-essentials

Thanks for helping make this marketplace useful. Everything under `plugins/`
ships to every user who installs it, so contributions are held to a public-API
standard.

- **Found a bug or want a feature?** Open an issue from one of the
  [forms](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose).
  See [docs/contributing/issues.md](docs/contributing/issues.md).
- **Have a question?** Use [Discussions](https://github.com/nerymurillohnd/claude-essentials/discussions).
- **Found a vulnerability?** Report it privately, per [SECURITY.md](SECURITY.md).

## Pull requests

The `check` and `version-check` CI jobs must be green before a pull request
can merge into `main`, and `main` can't be deleted or force-pushed (repository
rulesets).

Local prerequisites: [uv](https://docs.astral.sh/uv/) (it installs the pinned Python and every
tool from `uv.lock`, ShellCheck and shfmt included), GNU Make, `jq`, and the
[Claude Code](https://code.claude.com/docs) CLI on `PATH`.

```bash
make setup
make check      # generate, lint, types, tests, validate, validate-cli — the CI gate
make fix        # apply safe fixes (Ruff, shfmt, canonical JSON) before re-running check
make versions   # plugin version-bump rules against the latest tags
```

- Adding a plugin: [docs/contributing/plugins.md](docs/contributing/plugins.md).
- Changing a plugin: [docs/contributing/versioning.md](docs/contributing/versioning.md).
  A change to anything Claude loads at runtime bumps the plugin's version and adds a CHANGELOG entry; docs-only changes don't.
- Labels are applied automatically. See [docs/contributing/labels.md](docs/contributing/labels.md).

Contributions are licensed under [Apache-2.0](LICENSE), like the rest of the repository (Section 5). The pull request template's public-repository safety checklist applies to every PR.

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
