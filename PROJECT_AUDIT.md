# Project Audit

## Current Architecture

The repository is a Python CSV reconciliation pipeline:

- `src/data/loader.py` loads raw CSVs.
- `src/data/validator.py` validates source schemas, primary IDs, and foreign keys.
- `src/data/normalizer.py` creates processed normalized datasets.
- `src/reconciliation/exact_matcher.py` assigns payment candidates to bank transactions.
- `src/reconciliation/reconciler.py` validates amount, date, payment status, and ledger status.
- `src/reconciliation/exception_classifier.py` creates exception categories, risk levels, actions, and flags.
- `src/evaluation/verify_benchmark.py` now verifies transaction-level output against ground truth.

There is no frontend or API yet. `src/agent`, `src/evaluation`, and `src/reports` were mostly empty before this pass.

## Already Complete

- Raw datasets exist for bank transactions, payments, ledger, invoices, and customers.
- Processed reconciliation output exists.
- Exact matching handles duplicate normalized references with transaction/payment identity disambiguation.
- Reconciliation separates `PAYMENT_FAILED` and `PAYMENT_REFUNDED`.
- Existing generated output matches ground truth at transaction level with zero mismatches.
- Core invariants pass on the current output: one row per transaction and no duplicate payment assigned to multiple `MATCHED` rows.

## Issues Found

- Python is not available in the current shell as `python` or `py`, so the pipeline cannot be executed here yet.
- The folder is not currently a Git repository, which makes change tracking and deployment discipline weaker.
- `requirements.txt` and `README.md` were empty.
- Reconciliation validation assumed exactly 500 rows, which would block larger datasets.
- Amount tolerance existed as a magic number and was not consistently used in exact matching.
- There was no repeatable benchmark verification command.
- The saved classified output currently contains 15 stale `UNKNOWN_EXCEPTION` rows for failed/refunded payments. The code is fixed, but `classified_reconciliation_results.csv` must be regenerated.
- Some inspection/debug scripts remain in `src/reconciliation`.
- No dashboard or API layer exists yet.

## Changes Made In This Pass

- Added `src/config.py` for shared paths, amount tolerance, ledger status, benchmark mappings, and risk defaults.
- Added package markers under `src`.
- Updated exact matching to use configured amount tolerance and generic numeric ID extraction.
- Updated reconciliation to preserve amount difference fields and remove the hardcoded 500-row validation.
- Added `src/evaluation/verify_benchmark.py` for transaction-level benchmark checks.
- Added focused tests for exact matching, reconciliation decisions, and benchmark verification.
- Added basic `requirements.txt`, `.gitignore`, and README documentation.

## What To Preserve

- The current deterministic reconciliation status logic.
- The duplicate-reference identity rule.
- The raw data and ground truth files.
- One output row per bank transaction.
- Separation of failed and refunded payment statuses.

## Next Build Steps

1. Install Python 3.11+ and run the full pipeline plus tests.
2. Fix any runtime issues from the static edits in this pass.
3. Convert the remaining debug scripts into tests or remove them after inspection.
4. Add a metrics module for match rate, exception rate, exception value, and data quality metrics.
5. Add an API layer, preferably FastAPI, around the importable pipeline functions.
6. Build the dashboard against the API after the backend has stable response contracts.

## External Help Needed

No external AI, database, or cloud service is needed for the reconciliation engine.

Immediate external need: install/configure Python locally.

Later optional needs:

- GitHub or another remote Git host for deployment workflow.
- A hosting target such as Render, Railway, Azure App Service, or similar.
- Optional frontend hosting such as Vercel/Netlify if a separate web dashboard is built.
