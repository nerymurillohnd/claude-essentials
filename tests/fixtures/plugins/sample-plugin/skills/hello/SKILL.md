---
name: hello
description: Greets the user and confirms that plugins from the Claude Essentials marketplace load correctly. Use when the user runs /sample-plugin:hello to check their installation.
disable-model-invocation: true
argument-hint: "[name]"
---

# Hello

Confirm the installation in two short lines:

1. Greet the user by the name in $ARGUMENTS, or as "there" when no name is given.
2. State that the `sample-plugin` plugin from the `claude-essentials` marketplace is installed and its skills load.

Do not run tools: this skill only proves that the plugin loads.
