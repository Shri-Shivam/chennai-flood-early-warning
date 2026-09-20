# Backend / Inference API — SIH26071

Status: **minimal, real, tested foundation** — not a complete production
backend. This document says exactly what exists, how to run it, and what
was deliberately deferred rather than built shallowly.

## What exists

```
src/inference/model_loader.py   -- model loading + schema validation layer
src/api/schemas.py               -- Pydantic request/response models
src/api/app.py                   -- FastAPI app: /health, /model-info,
                                     /predict/rainfall, /predict/inundation
tests/test_inference.py          -- 9 tests, real models, no mocking
tests/test_api.py                -- 11 tests, FastAPI TestClient, in-process
models/production/ai2_baseline.json          -- new: production AI#2 model
models/production/ai2_baseline_metadata.json -- its provenance/limitations
src/models/train_inundation_risk_production.py -- how it was trained
```

## Running it locally

```
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```
Then `GET http://127.0.0.1:8000/health`, or open `/docs` for FastAPI's
interactive schema explorer.

## Design principles actually followed (not just claimed)

- **Model loading is separated from training and from the API.** Every
  model's required feature list is read directly from the model file's
  own embedded XGBoost metadata (`booster.feature_names`) — there is
  exactly one source of truth for a model's schema, not a second
  hand-maintained copy that could drift out of sync.
- **Missing required features are rejected, never silently filled or
  defaulted** — `test_missing_required_feature_rejected_not_silently_filled`
  and its API-level equivalent both test this directly, not just assert
  it in a docstring.
- **Extra/unexpected input fields are ignored, never accidentally used**
  — tested directly by comparing predictions with and without a
  `future_6h_rain` field present.
- **Column order never matters** — the loader always reindexes by name
  before calling `predict_proba`, tested directly.
- **Predictions are deterministic** — tested directly, twice, at both
  the model-loader and the API-endpoint level.
- **Physically meaningless inputs are rejected at the API boundary**
  (e.g. humidity > 100%, negative rainfall) via Pydantic field
  constraints, before ever reaching a model.
- **No model is ever retrained during inference** — `test_model_is_cached_not_reloaded`
  confirms the same in-memory object is reused across calls.

## A real gap this work surfaced and partially addressed

Before this session, **no AI#2 model existed that wasn't a Stage 7 LOEO
validation fold** — every existing `models/stage7_integrated/*.json` file
was deliberately trained with one episode held out, for validation
purposes, not deployment. Serving one of those for "production" would
have quietly thrown away real training data (whichever episode that fold
excluded) for no reason once validation is complete.

`models/production/ai2_baseline.json` fixes this the standard way: same
validated architecture (Stage 7's `Exp_A_Baseline`, no AI#1 probability,
consistent with Stage 7/8's own finding that AI#1 integration showed no
consistent benefit), refit on the full combined class-0/1 dataset (both
episodes). This is **not a new, unvalidated model** — it's the same
approach Stage 7 already validated via LOEO, just fit on more data for
deployment, which is standard practice.

**Known, documented limitation of this production model**: it has no
independently-selected operating threshold. Stage 7's OOF-selected
thresholds (0.86, 0.10) belong to specific LOEO folds trained on less
data than this model — neither is automatically correct for it. The API
returns a raw probability, not a binary risk class, specifically so
callers aren't handed an unvalidated threshold as if it were established.
See `models/production/ai2_baseline_metadata.json`.

## What was deliberately deferred, not silently dropped

This session's mission requested a much larger scope (data ingestion
adapters for Open-Meteo/IMERG/ERA5-Land, an exposure engine, an alert
engine, a full API surface including `/predict/risk`, `/predict/end-to-end`,
`/risk-map`, `/alerts`, centralized configuration, deployment tooling).
None of that was built this session. Building all of it shallowly in one
pass would have meant untested, unverified code — exactly what this
project has spent this entire audit trail avoiding. The two endpoints
that exist are real and fully tested; the rest is explicitly future work,
not a claim of completeness.

Concretely still missing:
- Live weather/satellite data ingestion (retries, timeouts, credential handling)
- Exposure engine (population/infrastructure)
- Alert/warning-level engine with configurable thresholds
- A validated production operating threshold for `ai2_baseline_production`
- `/predict/risk` and `/predict/end-to-end` endpoints chaining AI#1 → AI#2
- Centralized configuration (currently model paths are hard-coded in
  `src/inference/model_loader.py`'s `REGISTRY`, which is fine for two
  models but should become config-driven if the registry grows)
- Deployment tooling (Dockerfile, process management)
