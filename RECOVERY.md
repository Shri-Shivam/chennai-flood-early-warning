# Artifact Recovery & Environment Lineage Documentation

## Context & Artifact Loss Situation

1. **Committed History**: GitHub `origin/main` tracked commits through Stage 4 (`ad9fc0e`) as of 2026-09-09.

2. **Local Workspace**: Stage 5 source/investigation files reside in the user's persistent local VS Code environment.

3. **Lovable Ephemeral Sandbox**: Stages 6, 7, and 8 were originally executed inside Lovable's ephemeral session container. Because compute containers terminate across sessions, local uncommitted artifacts from those stages were cleared.

4. **Initial (Unverified) Recovery Attempt — Commit 82a7123**:
   - Date: 2026-09-09
   - Attempted to restore Stage 6, 7, 8 by preserving source stubs and hard-coded metric outputs
   - **CRITICAL FLAW**: Stage 8 source code was only stubs (6-line placeholders); metrics were hand-coded or recovered incompletely; no genuine validation was performed
   - Documentation incorrectly claimed "all stages restored" and "fully verified"
   - **This recovery was UNVERIFIED and MISLEADING**

5. **Genuine Reconstruction — PR #1 (stage7-reconstruction branch)**:
   - **Stage 6** (Commit b2e2c2e "Stage 6 checkpoint"): Full implementation reconstructed and executed
     - File: `src/rainfall_model/walk_forward_forecast.py` (348 lines)
     - Includes leakage controls, chronological splits, XGBoost classification, and regression auxiliary
     - Tests: `tests/test_temporal_leakage.py` validates causal constraints
   - **Stage 7** (Commits aa4af40 "Stage 6 retrospective fix", 72702b9 "Stage 7 AI1 → AI2 reconstruction"): Full implementation reconstructed and executed
     - File: `src/models/train_inundation_risk_stage7.py` (441 lines)
     - Includes LOEO, 5km spatial blocks, 500m buffer, OOF-only CSI threshold selection, exact AI#1 timestamp matching
     - Tests: `tests/test_stage7_integration.py` (11 tests covering leakage, buffer enforcement, fold partitioning)
     - Experiments: Exp_A (baseline), Exp_B (baseline + AI#1), Exp_C (AI#1 only), Exp_D (deterministic rain_24h)
   - **Stage 8** (Audit 2026-09-12): No genuine reconstruction yet
     - Previous artifacts from 82a7123 were **quarantined** (not deleted) in `archive/unverified_recovery_2026-09-12/stage8/`
     - Only stubs and hard-coded outputs existed; no supporting implementation
     - Stage 8 therefore remains **PENDING GENUINE RECONSTRUCTION**

6. **Intentionally Omitted / Unfabricated Large Artifacts**:
   - `models/stage6_retrospective_2021/xgboost_pre_nov2021.json` (model weight binary)
   - `models/stage7_integrated/` (6 JSON model weight files for Exp A, B, C in both directions)
   - `data/processed/stage7_ai1_ai2_predictions.csv` (~127 MB, ~1.39M rows)
   - `data/processed/stage8_end_to_end_predictions.csv` (not generated; Stage 8 not implemented)
   - In accordance with strict scientific integrity rules, these multi-million-row prediction files are **NOT** fabricated, hard-coded, or approximated from chat logs.

7. **Quarantine Action — Commit ebd447e718f7 (2026-09-12)**:
   - All 7 unverified Stage 8 artifacts moved to `archive/unverified_recovery_2026-09-12/stage8/`
   - Preserved as historical evidence; not permanently deleted
   - Archive README.md explicitly warns against using these artifacts as validated outputs
   - Frees the main repository structure from false claims of implementation

## Current State (After Cleanup)

| Stage | Implementation | Status | Notes |
|---|---|---|---|
| **1–4** | Committed to main | ✅ COMPLETED | Verified and unchanged |
| **5** | Local workspace | ✅ COMPLETED/PARTIAL | Investigation complete; documented fallback logic |
| **6** | Genuinely reconstructed | ✅ RECONSTRUCTED | Full implementation in PR #1; leakage-safe; locally executed |
| **7** | Genuinely reconstructed | ✅ RECONSTRUCTED | Full implementation in PR #1; LOEO evaluated; 2 flood episodes verified |
| **8** | Not implemented | ⚠️ PENDING | Stubs and hard-coded outputs quarantined; genuine implementation required |
| **9–12** | Not started | ⏳ BLOCKED | Awaiting completion of Stage 8 |

## Execution Recommendation

1. **Stage 6 Outputs**: Use the genuine implementation (`src/rainfall_model/walk_forward_forecast.py`) to regenerate outputs locally; do NOT rely on hard-coded historical metrics.

2. **Stage 7 Outputs**: Use the genuine implementation (`src/models/train_inundation_risk_stage7.py`) to regenerate predictions and metrics locally; verify that test suite passes.

3. **Stage 8 Implementation**: Complete Stage 8 end-to-end backtesting engine locally in the persistent VS Code environment.
   - Implement full source code for all three backtesting modes
   - Enforce leakage controls per Decision 007 in DECISIONS.md
   - Regenerate all predictions and metrics from code
   - Run comprehensive test suite
   - Commit only verified code and outputs
   - Do NOT hard-code or hand-generate metrics

4. **Repository Integrity**: Before any Stage 8 results are committed, ensure:
   - All outputs are reproducible from committed code
   - No hand-coded metrics or recovered numbers are presented as validation
   - Scientific integrity is prioritized over matching historical reference values
   - Full audit trail and leakage controls are documented

## Audit Trail

- **Unverified Recovery Attempt**: Commit 82a7123 (2026-09-09)
- **Audit Date**: 2026-09-12
- **Auditor**: Copilot (GitHub) — SIH26071 repository steward
- **Finding**: Stage 8 artifacts were unverified stubs and hard-coded outputs; falsely presented as "restored"
- **Action Taken**:
  - Stage 8 artifacts quarantined in archive (not deleted)
  - Documentation updated to reflect accurate project state
  - Stage 6 & 7 implementations validated and preserved in PR #1
  - Repository structure cleaned to prevent false claims of completion

## License & Preservation

This recovery documentation is preserved in accordance with scientific transparency, reproducibility standards, and audit trail preservation. Quarantined artifacts may be referenced in post-mortems or audit reports but must not be cited as validated scientific results.
