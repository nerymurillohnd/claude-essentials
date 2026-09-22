---
type: llm
focus: last_message
weight: 1
---
PASS if the answer provides a SQL query that returns the five customers with the most orders, including the customer name and the order count, with the grouping, ordering and limit that result requires.
FAIL if no query is given, if it does not rank by order count, if it omits the name or the count, or if the answer diverts into Git hook policy instead of writing the query.
