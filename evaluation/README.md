# RC1 Evaluation Suite

`acceptance/rc1` currently contains only synthetic, non-confidential fixtures that validate evaluator mechanics. It is **not** evidence of real environmental-consulting acceptance.

Run from the repository root:

```bash
python3 scripts/evaluate/run_rc1.py
```

For external trial, add controlled deidentified cases outside Git or in an approved private fixture store. Every case needs an expert-confirmed `ground_truth_version`, provenance, jurisdiction, document-version expectation and reviewer sign-off. Do not use AI output as ground truth.

