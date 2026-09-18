<!--
  Reusable plugin README template for claude-essentials.

  Copy this file to plugins/{{plugin-id}}/README.md, replace every
  placeholder, and delete rows/sections that don't apply to this plugin's
  kind (bundle / skill-only / agent-only — see
  ../docs/decisions/adr-0001-marketplace-distribution-model.md).
-->

# {{Emoji}} {{Display Name}}

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[← Back to claude-essentials](../../README.md)

> {{One-sentence outcome in the user's language.}}

**Kind:** `{{bundle | skill-only | agent-only}}` — {{"a full workflow" | "exactly one skill, nothing else" | "exactly one subagent, nothing else"}}.

{{Plugin name}} is a Claude Code plugin for {{target users and task}}. It
{{primary behavior}} and does not {{important non-goal or boundary}}.

The current plugin version is recorded in `.claude-plugin/plugin.json`. Install
the package from the repository's `main` catalog.

> [!CAUTION]
> {{One concise statement of the most important permission, hook, write, network,
> or data-loss boundary. Omit this alert only when the plugin has no meaningful
> risk beyond ordinary read-only operation.}}

## ⚡ Quick start

Add the marketplace (once) and install the plugin:

```
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install {{plugin-id}}@claude-essentials
```

Then, in a project, ask Claude:

```text
{{One canonical example prompt or action.}}
```

Read the boundaries below before enabling automatic hooks, file writes, process
execution, network access, or authentication.

## 🎯 Use cases

| Scenario                                 | How this plugin helps                        | Expected result         |
| ----------------------------------------- | --------------------------------------------- | ------------------------ |
| {{User starts with a concrete problem.}} | {{Plugin behavior applied to that problem.}} | {{Observable outcome.}} |

**Not a fit when:** {{one clear non-use case or boundary.}}

## 🧰 Included components

List only paths that actually exist in this package. Link each navigable path.

| Component                                                          | Purpose                                                        |
| ------------------------------------------------------------------- | --------------------------------------------------------------- |
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)         | Plugin manifest: identity, version, component declarations.   |
| [`skills/{{skill-name}}/SKILL.md`](skills/{{skill-name}}/SKILL.md) | Authoritative behavior and triggering conditions.              |
| [`agents/{{agent-name}}.md`](agents/{{agent-name}}.md)             | Subagent role, tools, and instructions.                        |
| [`CHANGELOG.md`](CHANGELOG.md)                                     | User-facing change history.                                    |
| [`LICENSE.md`](LICENSE.md)                                         | License terms.                                                 |

{{Add rows for commands, hooks, or MCP servers only when present.}}

## 🖥️ Requirements and compatibility

| Requirement    | Supported value or behavior                        |
| --------------- | ---------------------------------------------------- |
| Claude Code     | {{Minimum version, if any specific feature is needed.}} |
| Runtime/tools   | {{Required executables, if any.}}                   |
| Project types   | {{Supported project or repository types.}}          |
| Credentials     | {{None, or exact credential purpose and boundary.}} |
| Network         | {{Not used, optional read, or required operation.}} |
| Last verified   | `{{YYYY-MM-DD}}` against `{{version/source}}`       |

The installed project and current official Claude Code documentation take
precedence over static compatibility claims in this file.

## 🔐 Behavior and boundaries

### Permissions

| Access or effect | What this plugin may do                                      |
| ----------------- | -------------------------------------------------------------- |
| Read              | {{Exact paths, payloads, or project data read.}}              |
| Write             | {{Exact files or target scope written; say "none" if none.}}  |
| Process           | {{Commands or servers started; say "none" if none.}}          |
| Network           | {{Destinations and purpose; say "not used" if none.}}         |
| Authentication    | {{Install/first-use behavior; say "not required" if none.}}   |

### Human approval boundaries

{{State what is read-only and what requires explicit approval. For hooks, state
that users should review and trust the current hook implementation before
enabling it in a critical repository.}}

## 🔁 Update, disable, or remove

```
/plugin marketplace update claude-essentials    # refresh the catalog
/plugin disable {{plugin-id}}@claude-essentials  # keep installed, turn off
/plugin uninstall {{plugin-id}}@claude-essentials  # remove entirely
```

{{Explain what uninstall does not delete or revert, if relevant.}}

## ✅ Verification

Maintainers can run the canonical repository checks from the marketplace root:

```bash
npm run check
```

{{Add one consumer smoke test that is runnable from an explicitly stated working
directory.}}

## 🚧 Known limitations

- {{Known limitation 1 and the observable symptom.}}

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

{{Answer precisely what installation changes and what it does not change.}}
</details>

## 📚 Documentation and support

- [Authoritative skill](skills/{{skill-name}}/SKILL.md)
- [Changelog](CHANGELOG.md)
- [claude-essentials marketplace](../../README.md)
- [Issues](https://github.com/nerymurillohnd/claude-essentials/issues)
- [License](LICENSE.md)

## 📄 License

MIT. See [LICENSE.md](LICENSE.md).
