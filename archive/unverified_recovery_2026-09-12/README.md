# Unverified Recovery Artifacts — 2026-09-12

## Context

This directory contains historical artifacts from the unverified recovery represented by commit `82a7123`.

These files were committed with the intention of preserving Stage 6–8 implementations and results, but subsequent audit (2026-09-12) revealed:

1. **Stage 6 & 7**: Implementations were stubs only; full verified implementations were reconstructed and committed in PR #1 (commits b2e2c2e, aa4af40, 72702b9).
2. **Stage 8**: No verified implementation exists. Only stubs and hard-coded metric outputs remain.
3. **Recovery Documentation**: Claims of "restoration" were premature and scientifically inaccurate.

## Artifact Status

### `stage6/` (if present)
- **Status**: Superseded by reconstructed implementation in `src/rainfall_model/walk_forward_forecast.py`
- **Action**: Historical reference only; do NOT use these outputs.

### `stage7/` (if present)
- **Status**: Partially superseded. Stage 7 source was a stub; full implementation in `src/models/train_inundation_risk_stage7.py`
- **Action**: Historical reference only; do NOT use these outputs.

### `stage8/`
- **Status**: UNVERIFIED. No supporting implementation code exists in the repository.
- **Files**:
  - `run_end_to_end_backtest.py`: Stub only (6 lines)
  - `evaluate_end_to_end_backtest.py`: Stub only (6 lines)
  - `test_end_to_end_temporal_integrity.py`: Incomplete test suite (12 lines, single file-existence assertion)
  - `stage8_confusion_matrices.csv`: Hard-coded metrics with no derivation code
  - `stage8_end_to_end_metrics.csv`: Hard-coded metrics with no derivation code
  - `stage8_event_summary.csv`: Hard-coded event predictions with no derivation code
  - `stage8_report.txt`: Narrative report with no supporting implementation
- **Action**: MUST NOT be used as validation evidence. Do NOT cite these metrics as verified outputs.
- **Scientific Integrity**: These artifacts violate reproducibility standards. Full Stage 8 implementation must be completed locally and re-integrated before any outputs can be considered verified.

## Audit Record

**Audit Date**: 2026-09-12  
**Auditor**: Copilot (GitHub) as SIH26071 repository steward  
**Finding**: Unverified artifacts present a scientific integrity risk if left in the repository's normal structure.  
**Action Taken**: Quarantined in this archive; updated documentation to reflect accurate project state.

---

## Next Steps

1. **Stage 6 Verification**: Run `python src/rainfall_model/walk_forward_forecast.py` locally to regenerate `data/processed/ai1_retrospective_forecast_2021.csv` and `data/processed/ai1_stage6_report.txt`. Verify outputs match or explain divergence.

2. **Stage 7 Verification**: Run `python src/models/train_inundation_risk_stage7.py` locally to regenerate Stage 7 predictions and metrics. Ensure `test_stage7_integration.py` passes all 11 tests.

3. **Stage 8 Implementation**: Complete Stage 8 end-to-end backtesting locally. Preserve full source code for all outputs. Do NOT commit unverified metrics to the repository.

4. **Repository State**: When Stage 6 & 7 outputs are regenerated and verified, update `PROJECT_PROGRESS.md` and `RECOVERY.md` to reflect accurate state.

---

## License & Preservation

These artifacts are preserved as historical audit records in accordance with scientific transparency and reproducibility standards. They may be referenced in audit trails or post-mortems but must not be cited as validated scientific results.
