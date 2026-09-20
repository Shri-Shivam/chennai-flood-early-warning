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
from src.api.schemas import (
    HealthResponse,
    InundationRequest,
    InundationResponse,
    InundationCellResult,
    ModelInfo,
    ModelInfoResponse,
    RainfallFeatures,
    RainfallPredictionResponse,
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
