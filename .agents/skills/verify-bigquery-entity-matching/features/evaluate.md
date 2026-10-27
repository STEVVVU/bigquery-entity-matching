# Evaluate local matching

## Sub-features
Fixed seeded held-out evaluation, exact and lexical comparators, ambiguity and rejection.
## How to get to it (user POV)
Invoke the evaluate CLI command from the project root.
## Driving it with CLI
Run `python -m entity_matching evaluate --output evidence/disjoint-evaluation.json`; inspect disjoint split IDs and normalized query texts, calibration grid, JSON metrics and predictions across five interleaved runs.
## Gotchas
This synthetic dataset measures only a toy lexical comparator, not Gemini.
