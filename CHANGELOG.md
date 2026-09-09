# Changelog

## [Stage 8 Recovery] - 2026-09-09
- Restored Stage 6 walk-forward forecast script, leakage audit, unit tests, and summary reports.
- Restored Stage 7 integrated training script, evaluation module, LOEO comparison metrics, and reports.
- Restored Stage 8 end-to-end backtesting engine, evaluation module, temporal integrity test suite, confusion matrices, and event summaries.
- Created `PROJECT_PROGRESS.md` and `RECOVERY.md` documenting project state and artifact lineage.
- Updated `DECISIONS.md` with explicit scientific decisions 1 through 9.
- Verified lightweight unit tests (`tests/test_temporal_leakage.py`, `tests/test_stage7_temporal_alignment.py`, `tests/test_end_to_end_temporal_integrity.py`).
- Large multi-gigabyte/135MB prediction CSVs intentionally not fabricated in the ephemeral environment.
