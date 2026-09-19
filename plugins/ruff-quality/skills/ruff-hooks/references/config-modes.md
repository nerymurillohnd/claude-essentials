# Configuration modes

The user chooses one. Show them the exact configuration with
`manage.sh show-config --config-mode <mode>` before they choose, and explain it
using `assess`'s baseline counts ("with this mode, this project has N findings
today, mostly X and Y").

| Mode | What the hook runs | Files written | Best for |
| --- | --- | --- | --- |
| `recommended` | Ruff with native discovery, after the bundled profile is written where Ruff finds it | Project/local scope: `<repo>/ruff.toml`. User scope: `~/.config/ruff/ruff.toml` (or `$XDG_CONFIG_HOME/ruff/ruff.toml`). Only when no Ruff configuration exists at that level | New projects, or projects without a Ruff policy that want a strict one |
| `own` | Ruff with native discovery (the project's `ruff.toml`, `.ruff.toml`, or `[tool.ruff]`, else the user-level file) | Nothing | Projects that already have a Ruff policy |
| `own` + `--config-path FILE` | `ruff --config FILE` for every file, overriding discovery | Nothing | A shared policy file kept outside the usual places |
| `defaults` | `ruff --isolated`: Ruff's built-in defaults, every configuration file ignored | Nothing | A quick, zero-configuration gate; note that it also ignores the project's policy |

## How to explain each one

- **recommended** — "The plugin ships a strict profile: Ruff's 413 default rules
  plus naming, docstrings (Google style), type annotations, security,
  exception hygiene, pathlib, logging, complexity ≤ 10, and no commented-out
  code: 701 rules, all compatible with `ruff format`. It is written as a real
  `ruff.toml`, so your editor, CI, and manual `ruff` runs use exactly what the
  gate uses. It is never written over an existing configuration." Show the
  whole file. Point out the rules most likely to fire in this project from the
  baseline, and the per-file relaxations for tests.
- **own** — "The gate uses the configuration you already have, exactly as Ruff
  resolves it." Show the discovered file(s). If none exists, say that `own`
  means Ruff's built-in defaults (or the user-level file) and that this may
  not be what they intend.
- **defaults** — "Ruff's built-in defaults, 413 rules at line length 88,
  ignoring every configuration file, including the project's. Useful as a
  baseline; it will disagree with a project that has its own policy, and
  with your editor if it follows the project."

## Scope interactions

- User scope + `recommended`: the profile goes to the user-level Ruff
  directory, which Ruff uses **only for projects without their own
  configuration**. Projects with a configuration keep theirs; that is the
  intended layering.
- User scope + `defaults`: every project on the machine is checked with
  built-in defaults, ignoring each project's policy. Say this explicitly.
- Project scope + `own --config-path`: the file must live inside the
  repository (it is referenced as `$CLAUDE_PROJECT_DIR/<path>` so teammates
  have it).

## The max-blocks setting

`--max-blocks N` (1–7, default 5) is how many consecutive times the Stop gate
may block one turn. After that the turn ends with a visible warning listing
what is unresolved. Claude Code itself stops honoring a Stop hook after 8
consecutive blocks, without a message; the limit keeps the warning visible.
