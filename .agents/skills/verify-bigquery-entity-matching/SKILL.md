---
name: verify-bigquery-entity-matching
description: Drive and verify the local entity matching CLI and its observable results.
---

## Launch
From the project root install with `python -m pip install -e .` in an isolated virtual environment. Each CLI command is short-lived; there is no server.

## Doctor
Run `python -m entity_matching --help` and confirm the evaluate command is listed.

## Drive
Run `python -m entity_matching evaluate --output evidence/disjoint-evaluation.json`. The CLI writes calibration and holdout predictions and evaluation counts. See `features/evaluate.md`. Preserve the earlier receipts.

## Evidence
Keep the command, exit status and output in `evidence/`; inspect the output JSON and check that test entities, predictions, counts, and timings are present. Cloud execution requires separately provisioned credentials and paid resources and is not part of this local drive.

## Cleanup
The CLI creates no processes or scratch state. Keep evidence; remove only temporary files explicitly created by the verifier. Confirm the evidence file remains after cleanup.
