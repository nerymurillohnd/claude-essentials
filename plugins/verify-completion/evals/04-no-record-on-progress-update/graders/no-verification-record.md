---
type: regex
pattern: 'Verification record|Verdict:\s*VERIFIED|Adversarial review'
target: last_message
match: not_contains
flags: i
---
