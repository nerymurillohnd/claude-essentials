# Edits and evidence

- Prefer the Edit tool for exact replacements. After any scripted edit (`sed`,
  `perl`, `python`, heredoc), confirm it landed with `git diff` before moving on;
  a replacement that matches nothing fails silently.
- After writing files that contain escape sequences (`\u0000`, `\t`, regexes),
  check the bytes on disk. A tool may have turned an escape into a literal
  control character.
- Report something as done only with evidence from the current state: command
  output, a check run, or a GitHub read. Nothing is done because it was done
  earlier in the session.
