---
type: llm
focus: last_message
weight: 1
---
PASS if the answer explains that TTL is how long resolvers cache a record, and advises lowering it ahead of the migration so the change propagates quickly, then raising it again once the new provider is serving correctly.
FAIL if it confuses TTL with registrar transfer times, omits the lower-before-migrating advice, or diverts into shell tooling.
