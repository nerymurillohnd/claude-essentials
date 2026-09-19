---
description: Cleaning up a shell script triggers the shell-lint skill, which fixes findings instead of silencing them.
tags: [trigger]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Clean up this bash script so it would pass ShellCheck. Reply with the corrected script and a one-line note per change; don't run anything.

```bash
#!/usr/bin/env bash
dir=$1
cd $dir
files=$(ls *.log)
for f in $files; do
  local size=$(wc -c < $f)
  echo "$f: $size"
done
if [ $? -ne 0 ]; then echo failed; fi
```
