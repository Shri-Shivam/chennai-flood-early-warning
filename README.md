# Chennai Flood Early Warning — SIH26071

AI/ML-based Integrated Heavy Rainfall Early Warning and Inundation
Prediction System, built for Smart India Hackathon 2026 (Problem
SIH26071, MoES).

RAIN → TERRAIN → RISK → VALIDATE → IMPACT → ACT

## Status

Retrospective, proof-of-concept system, validated against **two**
independently verified historical Chennai flood episodes (November
2021). Not operationally validated. See `AUDIT_REPORT.md` and
`docs/reproducibility.md` for the full audit trail, and
`data/processed/stage7_model_comparison.csv` / `stage8_report.txt` for
actual validation results — including where AI#1 rainfall integration
did **not** show a consistent benefit to AI#2, reported honestly rather
than hidden.

## What's here

- **AI#1** (`src/rainfall_model/`): XGBoost rainfall classifier,
  predicts P(6-hour rainfall ≥ 20mm — a project-defined significant
  rainfall target, not an IMD category).
- **AI#2** (`src/models/`, `src/features/`): XGBoost inundation-risk
  classifier over a 250m spatial grid (rainfall + terrain + drainage
  features — the 250m grid is the *risk* resolution, not the *rainfall*
  resolution, since rainfall comes from a single weather station).
- **Stage 6/7/8** (`src/rainfall_model/`, `src/models/`,
  `src/validation/`): leakage-safe walk-forward evaluation, AI#1→AI#2
  integration experiments, and an end-to-end retrospective backtest.
- **Backend** (`src/inference/`, `src/api/`, `src/services/`,
  `src/ingestion/`): a real, tested inference API. See
  `docs/backend.md` for the full architecture and an honest list of
  what's still missing.

## Quick start

```
pip install -r requirements.txt
python -m pytest tests -q        # 87 tests
uvicorn src.api.app:app --reload # backend API, see docs/backend.md
```

## Key documents

- `docs/backend.md` — backend architecture, API surface, what's built vs. deferred
- `docs/reproducibility.md` — environment pinning, a real cross-machine determinism investigation and fix
- `docs/flood_event_inventory.md` — search for additional independent flood events (in progress)
- `AUDIT_REPORT.md` — repository-wide scientific/reproducibility audit
- `RECOVERY.md` — history of an earlier data-integrity incident and how it was resolved
- `PROJECT_PROGRESS.md`, `CHANGELOG.md`, `DECISIONS.md` — project history and standing decisions

## Scientific guardrails this project holds itself to

No exact flood depth or arrival time is claimed. Exposure is reported as
"estimated population/infrastructure within a modeled risk zone," never
"will flood." The ≥20mm/6h rainfall target is project-defined, not an
IMD category. Validation results from only two flood episodes are never
presented as general operational accuracy. See `DECISIONS.md` for the
full list.
