# File hygiene and tooling alignment

`scripts/hygiene/`. Two checks that belong to no domain and guard the bytes and
the toolchain rather than any plugin.

## Tests

### `test_text_files.py`

- Fails when a tracked text file carries a raw control character.
- An editor or a tool can turn a written escape into the byte itself. The file still looks correct in a diff and breaks silently downstream: jq programs stop parsing, JSON becomes invalid, Markdown renders wrong.
- This happened twice while building `block-no-verify`, which is why it is a gate and not a convention.
- The matching working rule is to check the bytes on disk after writing any file that contains escape sequences.

### `test_tooling_alignment.py`

- Fails when the analyzer behind the project-scoped MCP server is not the same version the local gate and CI run.
- The server resolves its analyzer from its own install location, so it stays aligned only while the dependency tree keeps one copy. A second copy makes the MCP server and the gate disagree about the same file.
- The failure mode is a tool that reports clean while the gate fails, which costs more time than the drift itself.
