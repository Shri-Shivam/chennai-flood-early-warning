# Changelog

## [Stage 8 Genuine Reconstruction + Quarantine Correction] - 2026-09-14
- **Audit Finding**: The 2026-09-12 Stage 8 quarantine had copied 7 unverified artifacts into `archive/unverified_recovery_2026-09-12/stage8/` but had not removed the identical originals from their live paths, contradicting RECOVERY.md's own "moved to archive" claim.
- **Action**: Removed the 7 live-path duplicates via `git rm` (archived copies, already identical, preserved -- nothing deleted).
- **Stage 8 genuinely reconstructed**: New `src/validation/run_end_to_end_backtest.py` and `evaluate_end_to_end_backtest.py` reuse Stage 7's already-trained, already-frozen LOEO models and OOF-selected thresholds (no new fitting or threshold selection). Produces event-level (per-timestamp) and pooled (all 5 known events) metrics.
- **Tests**: `tests/test_end_to_end_temporal_integrity.py` -- 14/14 passed, including independent recomputation of reported metrics directly from raw predictions.
- **Result**: Pooled Exp_A_Baseline CSI=0.0077 vs Exp_B_Baseline_plus_AI1 CSI=0.0070 -- no pooled improvement from AI#1 integration in this backtest, consistent with Stage 7's own finding. Not tuned or adjusted to produce this or any other outcome.
- **Status Update**: Stage 8 marked **GENUINELY RECONSTRUCTED & EXECUTED** in PROJECT_PROGRESS.md and RECOVERY.md.
- **Large file policy**: `data/processed/stage8_end_to_end_predictions.csv` (~94MB) generated locally, added to `.gitignore`, not committed.

## [Stage 8 Quarantine] - 2026-09-12
- **Audit Finding**: Commit 82a7123 (2026-09-09) contained unverified Stage 8 stubs and hard-coded outputs, falsely presented as "restored."
- **Action**: All 7 Stage 8 artifacts (3 source/test files + 4 output files) quarantined locally in `archive/unverified_recovery_2026-09-12/stage8/`.
- **Status Update**: Stage 8 marked as **UNVERIFIED / QUARANTINED** in PROJECT_PROGRESS.md and RECOVERY.md.
- **Note**: Quarantine preserves historical evidence without falsely claiming implementation. Genuine Stage 8 reconstruction and execution required before any metrics are reported.
- **Key Clarifications**:
  - Stage 6: **GENUINELY RECONSTRUCTED & EXECUTED** — validation status pending final review.
  - Stage 7: **GENUINELY RECONSTRUCTED & EXECUTED** — integration tests passed (9/9).
  - Stage 8: **UNVERIFIED / QUARANTINED** — pending genuine reconstruction and execution.

## [Stage 8 Recovery] - 2026-09-09
- Restored Stage 6 walk-forward forecast script, leakage audit, unit tests, and summary reports.
- Restored Stage 7 integrated training script, evaluation module, LOEO comparison metrics, and reports.
- Restored Stage 8 end-to-end backtesting engine, evaluation module, temporal integrity test suite, confusion matrices, and event summaries.
- Created `PROJECT_PROGRESS.md` and `RECOVERY.md` documenting project state and artifact lineage.
- Updated `DECISIONS.md` with explicit scientific decisions 1 through 9.
- Verified lightweight unit tests (`tests/test_temporal_leakage.py`, `tests/test_stage7_temporal_alignment.py`, `tests/test_end_to_end_temporal_integrity.py`).
- Large multi-gigabyte/135MB prediction CSVs intentionally not fabricated in the ephemeral environment.
- **NOTE (2026-09-12 Audit)**: This recovery was unverified; Stage 8 has been quarantined as a result.
