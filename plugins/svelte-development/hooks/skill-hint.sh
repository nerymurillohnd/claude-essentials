#!/usr/bin/env bash
# PreToolUse hint: names the svelte-development skill that fits the tool Claude is about
# to call, once per session and kind. A hook cannot load a skill; it can only say which.
# Reads no input and no network; prints one fixed JSON object or nothing.
set -euo pipefail

kind="${1:-}"
plugin="svelte-development"

case "${kind}" in
lsp)
  # Grep and Glob run in every project: speak only where package.json mentions svelte.
  grep -qs '"svelte"' "${CLAUDE_PROJECT_DIR:-.}/package.json" || exit 0
  text="${plugin}: for the definition, references, callers or type of a symbol of this Svelte project, use the LSP tool first when the language server answers (findReferences, goToDefinition, hover, incomingCalls from a .svelte position), with the skill ${plugin}:svelte-lsp-navigation. Grep and Glob are for strings, routes, file names and what the language server cannot see."
  ;;
docs)
  text="${plugin}: if the skill ${plugin}:svelte-docs-and-autofixer is not loaded in this session, load it with the Skill tool: it holds the tool calls, the autofixer parameters and the fallbacks when the server is unavailable. Load ${plugin}:svelte-best-practices too before writing Svelte code."
  ;;
check)
  text="${plugin}: if the skill ${plugin}:svelte-lsp-navigation is not loaded in this session, load it with the Skill tool: its project check procedure says how to read the result (the COMPLETED line, the tsconfig include, and the generated types a SvelteKit project needs first) and how to prove a rename by comparing the new errors with findReferences."
  ;;
edit)
  text="${plugin}: before writing Svelte code, load the skill ${plugin}:svelte-best-practices with the Skill tool if it is not loaded in this session: it holds the current Svelte 5 and SvelteKit 3 rules, the docs to fetch and the autofixer step. Unless you already are the svelte-component-editor agent, hand changes beyond a line or two to it (Agent tool, without a name)."
  ;;
cli)
  text="${plugin}: if the skill ${plugin}:svelte-best-practices is not loaded in this session, load it with the Skill tool: its sv CLI reference lists the current commands, add-ons and flags."
  ;;
*)
  exit 0
  ;;
esac

data="${CLAUDE_PLUGIN_DATA:-}"
session="${CLAUDE_CODE_SESSION_ID:-}"
if [[ -n "${data}" && -n "${session}" ]]; then
  mark="${data}/hint-${kind}-${session}"
  [[ -e "${mark}" ]] && exit 0
  mkdir -p "${data}" && : >"${mark}"
fi

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "${text}"
