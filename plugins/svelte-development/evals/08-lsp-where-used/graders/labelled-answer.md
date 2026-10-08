---
type: llm
---

PASS if the reply lists exactly three places where `label` is passed - Dynamic.svelte line 14
(label="dynamic"), Dynamic.svelte line 17 (label="lazy", the lazily imported component) and
src/routes/+page.svelte line 13 (label={42}) - and says which results came from the language
server and which, if any, are text matches.
FAIL if a site is missing, a comment or the prop declaration is listed as a place where the
prop is passed, or text-search results are presented as complete without saying so.
