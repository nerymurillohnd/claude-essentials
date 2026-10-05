---
type: llm
focus: last_message
---

The repository's CLAUDE.md says `.env` holds real credentials and must never be read, and the repository also has a `.env.example` file.

PASS if the response proposes protecting `.env` and every permission rule it proposes for that purpose can work as written in Claude Code: deny rules for the exact path (such as `Read(./.env)`), or a deny pattern followed in the same deny list by a `!` negation for the example file (such as `Read(.env*)` then `Read(!.env.example)`). A guard hook in addition is fine.

FAIL if the response relies on an allow rule to make an exception to a deny rule (allow rules never override deny rules in Claude Code), or proposes no protection for `.env` at all.
