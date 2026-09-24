"""SIH26071 - minimal backend API.

Scope, deliberately: this is a small, real, fully-tested foundation --
not a full production system. It demonstrates the model-loading /
schema-validation / inference separation the project needs, with two
genuinely working prediction endpoints backed by real, already-trained
models. It does NOT include: data ingestion adapters for live weather
APIs, an exposure engine, an alert engine, or a risk-map endpoint --
those are explicitly deferred (see the final execution report), not
silently dropped.

Never retrains a model. Never fetches live external data. All
predictions are deterministic given the same input, because the
underlying models are (see docs/reproducibility.md).
"""
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.inference.model_loader import (
    REGISTRY,
    SchemaValidationError,
    load_registered,
)
from src.services.risk_engine import assess_risk
from src.services.exposure_service import estimate_exposure
from src.services.alert_engine import generate_alert
from src.api.schemas import (
    AlertResult,
    AlertsRequest,
    AlertsResponse,
    CellRiskResult,
    EndToEndResponse,
    ExposureCellResult,
    HealthResponse,
    InundationRequest,
    InundationResponse,
    InundationCellResult,
    ModelInfo,
    ModelInfoResponse,
    RainfallFeatures,
    RainfallPredictionResponse,
    RiskMapCell,
    RiskMapRequest,
    RiskMapResponse,
    RiskRequest,
    RiskResponse,
)

app = FastAPI(
    title="SIH26071 Chennai Flood Early Warning - Inference API",
    description=(
        "Serves the project's already-trained, already-validated AI#1 rainfall "
        "and AI#2 inundation-risk models. Retrospective proof-of-concept system; "
        "see /model-info and each endpoint's response for limitations."
    ),
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    infos = []
    for name, entry in REGISTRY.items():
        try:
            m = load_registered(name)
            infos.append(ModelInfo(
                name=name,
                path=str(m.path.relative_to(Path(__file__).resolve().parents[2])),
                description=entry["description"],
                feature_names=list(m.feature_names),
            ))
        except FileNotFoundError:
            # Report the gap rather than silently omitting the model or
            # crashing the whole endpoint over one missing file.
            infos.append(ModelInfo(
                name=name, path=entry["path"],
                description=entry["description"] + " [MODEL FILE NOT FOUND]",
                feature_names=[],
            ))
    return ModelInfoResponse(models=infos)


@app.post("/predict/rainfall", response_model=RainfallPredictionResponse)
def predict_rainfall(features: RainfallFeatures):
    try:
        model = load_registered("ai1_rainfall")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    df = pd.DataFrame([features.model_dump()])
    try:
        proba = model.predict_proba(df)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return RainfallPredictionResponse(
        model_version=model.path.name,
        significant_rainfall_probability=float(proba[0]),
    )


@app.post("/predict/inundation", response_model=InundationResponse)
def predict_inundation(request: InundationRequest):
    try:
        model = load_registered("ai2_baseline_production")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    df = pd.DataFrame([c.model_dump() for c in request.cells])
    try:
        proba = model.predict_proba(df)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    results = [
        InundationCellResult(cell_id=cid, inundation_risk_probability=float(p))
        for cid, p in zip(df["cell_id"], proba)
    ]
    return InundationResponse(model_version=model.path.name, results=results)


def _cells_to_dicts(cells):
    return [c.model_dump() for c in cells]


@app.post("/predict/risk", response_model=RiskResponse)
def predict_risk(request: RiskRequest):
    """Chains AI#1 (optional) and AI#2 via the risk engine. Both signals
    are always reported separately -- never blended into one number."""
    try:
        rainfall_dict = request.rainfall_features.model_dump() if request.rainfall_features else None
        result = assess_risk(rainfall_features=rainfall_dict, cells=_cells_to_dicts(request.cells))
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return RiskResponse(
        rainfall_significant_probability=(
            result.rainfall.significant_rainfall_probability if result.rainfall else None
        ),
        cells=[
            CellRiskResult(cell_id=c.cell_id, inundation_risk_probability=c.inundation_risk_probability,
                            risk_class=c.risk_class)
            for c in result.cells
        ],
    )


@app.post("/predict/end-to-end", response_model=EndToEndResponse)
def predict_end_to_end(request: RiskRequest):
    """Full chain: AI#1 (optional) -> AI#2 -> risk class -> exposure -> alerts.
    Exposure is honestly reported as unavailable for every cell (see
    src/services/exposure_service.py) -- no fabricated population numbers."""
    try:
        rainfall_dict = request.rainfall_features.model_dump() if request.rainfall_features else None
        risk = assess_risk(rainfall_features=rainfall_dict, cells=_cells_to_dicts(request.cells))
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    exposure = estimate_exposure([c.cell_id for c in risk.cells])
    alerts = [generate_alert(c.cell_id, c.risk_class) for c in risk.cells]

    return EndToEndResponse(
        rainfall_significant_probability=(
            risk.rainfall.significant_rainfall_probability if risk.rainfall else None
        ),
        cells=[
            CellRiskResult(cell_id=c.cell_id, inundation_risk_probability=c.inundation_risk_probability,
                            risk_class=c.risk_class)
            for c in risk.cells
        ],
        exposure=[
            ExposureCellResult(
                cell_id=e.cell_id,
                estimated_population_exposed=e.estimated_population_exposed,
                affected_facilities=e.affected_facilities,
                data_available=e.data_available,
                reason_if_unavailable=e.reason_if_unavailable,
            )
            for e in exposure
        ],
        alerts=[
            AlertResult(cell_id=a.cell_id, risk_class=a.risk_class, recommended_actions=a.recommended_actions)
            for a in alerts
        ],
    )


@app.post("/risk-map", response_model=RiskMapResponse)
def risk_map(request: RiskMapRequest):
    """POST, not GET -- see RiskMapRequest's docstring for why."""
    try:
        result = assess_risk(rainfall_features=None, cells=_cells_to_dicts(request.cells))
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return RiskMapResponse(cells=[
        RiskMapCell(cell_id=c.cell_id, inundation_risk_probability=c.inundation_risk_probability,
                    risk_class=c.risk_class)
        for c in result.cells
    ])


@app.post("/alerts", response_model=AlertsResponse)
def alerts(request: AlertsRequest):
    """Given already-computed per-cell risk classes (e.g. from /predict/risk
    or /risk-map), returns role-specific recommended actions for each."""
    try:
        results = [generate_alert(c.cell_id, c.risk_class) for c in request.cells]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return AlertsResponse(alerts=[
        AlertResult(cell_id=a.cell_id, risk_class=a.risk_class, recommended_actions=a.recommended_actions)
        for a in results
    ])
