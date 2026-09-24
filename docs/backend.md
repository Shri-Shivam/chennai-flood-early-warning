# Backend / Inference API — SIH26071

Status: a real, tested backend foundation covering model serving,
configuration, live data ingestion, a risk/exposure/alert service layer,
and a small API surface. Still not a complete production system — see
"What remains" at the end for the honest, itemized gap list.

## Layout

```
src/config.py                     -- centralized settings (env-overridable)
src/inference/model_loader.py     -- model I/O + schema validation
src/ingestion/open_meteo.py       -- live weather adapter (mocked in tests)
src/services/rainfall_service.py  -- AI#1 wrapper
src/services/inundation_service.py-- AI#2 wrapper
src/services/risk_engine.py       -- chains AI#1 + AI#2, risk_class
src/services/exposure_service.py  -- honest "not available" exposure
src/services/alert_engine.py      -- role-specific recommended actions
src/api/schemas.py                -- Pydantic request/response models
src/api/app.py                    -- FastAPI app, 8 endpoints
tests/test_config.py              -- 5 tests
tests/test_inference.py           -- 9 tests
tests/test_ingestion.py           -- 10 tests, all network calls mocked
tests/test_services.py            -- 8 tests
tests/test_api.py                 -- 19 tests, FastAPI TestClient
models/production/ai2_baseline.json          -- production AI#2 model
models/production/ai2_baseline_metadata.json -- provenance + threshold
src/models/train_inundation_risk_production.py  -- how the model was trained
src/models/select_production_threshold.py       -- how its threshold was selected
```
87 tests total across the whole repository (36 pre-existing Stage 6/7/8 +
51 backend-layer tests added across this and the prior session).

## Running it locally

```
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```
`GET /health`, `GET /model-info`, or open `/docs` for the interactive
schema explorer.

## API surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/model-info` | GET | Registered models + their feature schemas |
| `/predict/rainfall` | POST | AI#1 alone |
| `/predict/inundation` | POST | AI#2 alone, one or more cells |
| `/predict/risk` | POST | AI#1 (optional) + AI#2, reported separately, with `risk_class` |
| `/predict/end-to-end` | POST | risk + exposure (honestly unavailable) + role-specific alerts |
| `/risk-map` | **POST**, not GET | See note below |
| `/alerts` | POST | Given cell_id + risk_class, returns recommended actions |

**`/risk-map` deviates from the originally sketched `GET` verb.** A real
risk map needs per-cell feature data as input, and no live spatial data
source is integrated yet to serve a parameterless GET honestly — the
response itself documents this (`note` field). Building a fake GET that
secretly required a request body, or that returned canned data, would
have been exactly the "fake enterprise architecture" this project's own
engineering standard explicitly rules out.

## Configuration (`src/config.py`)

Centralizes model paths, the AI#2 default operating threshold, alert
level thresholds, spatial grid settings, and Open-Meteo ingestion
settings (base URL, timeout, retry count/backoff). Every setting has a
safe default and can be overridden with an `SIH26071_<FIELD_NAME>`
environment variable — verified by a direct test
(`test_env_var_overrides_default`), not just documented. No credential
fields exist anywhere in configuration (verified by a test that scans
field names for credential-like substrings) — nothing currently
implemented needs one; the only external adapter (Open-Meteo) is a
public, keyless API.

## Data ingestion (`src/ingestion/open_meteo.py`)

Targets Open-Meteo's *forecast* endpoint (recent + short-term forecast),
distinct from the *archive* endpoint already used to build the
historical training dataset (`src/data/download_weather.py`) — same
variable list, same response shape, same implicit unit convention
(Open-Meteo's defaults; no `units` parameter is set, consistent with how
the training data was built, so live inputs stay compatible with the
trained models). Implements timeout, retry with backoff, and two
distinct structured error types (`UpstreamRequestError` for
network/HTTP failures, `SchemaError` for a malformed response body) so
callers can react differently to each. All 10 tests mock `requests.get`
directly — the suite requires no internet access, verified by patching
the exact call site.

## Service layer (`src/services/`)

- **`risk_engine.assess_risk`**: the single place AI#1 and AI#2 are
  chained. They are *never* blended into one number — Stage 7/8 already
  found no consistent benefit from combining them, so both are reported
  side by side, and `risk_class` is derived from AI#2's probability
  alone.
- **`exposure_service.estimate_exposure`**: returns an explicit
  `data_available=False` result with a stated reason for every cell,
  because no population/building/infrastructure dataset exists anywhere
  in this repository (verified by inspection before writing this
  module — see ROADMAP.md's own unchecked Phase 6 items). Never returns
  a silent zero that could be misread as "zero people exposed."
- **`alert_engine.generate_alert`**: maps a `risk_class` to role-specific
  recommended actions (citizen, municipal authority, disaster
  management, hospitals, electricity operator). Electricity output is
  always phrased as a recommendation ("consider..."), never a command —
  tested directly (`test_electricity_action_is_always_a_recommendation_not_a_command`).

## Production AI#2 model and its threshold

Before this work, every AI#2 model in the repository was a Stage 7 LOEO
validation fold — deliberately missing one episode's data, appropriate
for validation, not for serving. `models/production/ai2_baseline.json`
fixes this: same validated `Exp_A_Baseline` architecture, refit on the
full combined dataset (both episodes, 349,548 rows, 1,004 positive).

Its operating threshold (0.9015) was selected via 5-fold spatial-block
(5km, 500m buffer) OOF cross-validation across the *entire* production
training set, CSI-optimized — the same honest methodology Stage 7 used,
applied once across all available data since no episode remains held
out for a model trained on everything. **This is explicitly not
equivalent to Stage 7/8's LOEO event-generalization evidence** — it has
not been validated against an independent flood episode, because none
remains. This limitation is recorded in
`models/production/ai2_baseline_metadata.json` itself, not just in this
document, so it travels with the model file.

## Design principles actually tested, not just claimed

- Model schema read from the model file's own embedded metadata — one
  source of truth, never a second hand-maintained list.
- Missing required features rejected, never silently filled.
- Extra/unexpected input fields ignored, never accidentally used.
- Column order never matters (always reindexed by name).
- Predictions deterministic, tested at both model-loader and API level.
- Physically meaningless inputs (humidity > 100%, negative rainfall)
  rejected at the API boundary before reaching any model.
- No model ever retrains during inference (cache identity tested
  directly).
- Metadata files are never silently clobbered: retraining the production
  model preserves its previously-selected threshold rather than wiping
  it (a real bug caught and fixed this session — see git history).
- An invalid `risk_class` passed to `/alerts` returns 422, not an
  unhandled 500 (another real bug caught and fixed this session by its
  own test).

## What remains (honest, itemized — not silently dropped)

- No independently-validated (LOEO, cross-episode) production operating
  threshold — only spatial-OOF, documented as such everywhere it appears.
- No exposure data of any kind (population, buildings, roads, critical
  infrastructure) — the interface exists, the data does not.
- Alert-level thresholds (`WATCH`/`WARNING`/`HIGH_RISK` boundaries) are
  engineering/demo defaults, not independently calibrated.
- `/risk-map` has no live spatial data source to draw from — it requires
  the caller to supply cell features, same as `/predict/inundation`.
- No IMERG/ERA5-Land spatial-rainfall ingestion adapter — Stage 5's own
  conclusion (missing native cells, no authoritative land/sea mask) was
  preserved rather than silently overridden.
- No deployment tooling (Dockerfile, process supervision, HTTPS/TLS,
  authentication/authorization on the API itself).
- No dashboard/frontend — only the backend contract these endpoints define.
