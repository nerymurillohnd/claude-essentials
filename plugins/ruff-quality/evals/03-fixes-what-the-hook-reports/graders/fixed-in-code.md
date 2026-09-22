---
type: llm
focus: {source: file, path: calc.py}
weight: 1
---
PASS if `calc.py` defines `average(values)` returning the mean (0 for an empty list), and the two findings the file started with are fixed in the code itself: the ambiguous variable `l` in `total` is renamed (E741), and the undefined name `totl` in `describe` is corrected so `describe` calls `total` (F821). `total` and `describe` must keep their behaviour.
FAIL if `average` is missing or wrong, if either finding remains, if either was silenced with a suppression comment or a configuration change instead of fixed, or if an existing function's behaviour changed.
