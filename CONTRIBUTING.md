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

```bash
npm install
npm run check          # format, lint, unit tests, generate, validate — the CI gate
npm run check:versions  # plugin version-bump rules against origin/main
```

- Adding a plugin: [docs/contributing/plugins.md](docs/contributing/plugins.md).
- Changing a plugin: [docs/contributing/versioning.md](docs/contributing/versioning.md).
  A change to anything Claude loads at runtime bumps the plugin's version and adds a CHANGELOG entry; docs-only changes don't.
- Labels are applied automatically. See [docs/contributing/labels.md](docs/contributing/labels.md).

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
