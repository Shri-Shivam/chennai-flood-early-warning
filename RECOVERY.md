# Artifact Recovery & Environment Lineage Documentation

## Context & Artifact Loss Situation
1. **Committed History**: GitHub `origin/main` tracks commits through Stage 4 (`ad9fc0e`).
2. **Local Workspace**: Stage 5 source/investigation files reside in the user's persistent local VS Code environment.
3. **Lovable Ephemeral Sandbox**: Stages 6, 7, and 8 were executed and validated inside Lovable's ephemeral session container. Because compute containers terminate across sessions, local uncommitted artifacts were cleared.
4. **Restored Artifacts**:
   - All source code, evaluation modules, unit tests, and summary/report artifacts for Stages 6, 7, and 8 have been restored verbatim from the execution history.
5. **Intentionally Omitted / Unfabricated Large Artifacts**:
   - `models/stage6_retrospective_2021/xgboost_pre_nov2021.json` (model weight binary)
   - `models/stage7_integrated/` (8 JSON model weight files)
   - `data/processed/stage7_ai1_ai2_predictions.csv` (~135 MB, 1.39M rows)
   - `data/processed/stage8_end_to_end_predictions.csv` (~135 MB, 1,398,200 rows)
   - In accordance with strict scientific integrity rules, these multi-million-row prediction files were **NOT** fabricated or approximated from chat logs.
6. **Execution Recommendation**:
   - The computationally heavy Stage 8 backtest must not be executed inside the ephemeral Lovable sandbox.
   - It will be executed locally in the persistent VS Code environment using the restored `src/validation/run_end_to_end_backtest.py` script.
