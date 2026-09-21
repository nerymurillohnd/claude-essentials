---
type: llm
focus: last_message
weight: 1
---
PASS if the answer explains that `absolute` positions the element against its nearest positioned ancestor while `fixed` positions it against the viewport and does not move when the page scrolls, and names a situation where each one is the right choice.
FAIL if it confuses the two containing blocks, omits the scrolling difference, or diverts into Python tooling.
