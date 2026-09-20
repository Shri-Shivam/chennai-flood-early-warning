"""SIH26071 API - Pydantic schemas.

Field constraints are deliberately conservative and documented, not
arbitrary. Where a physically meaningful range exists (e.g. relative
humidity 0-100%) it is enforced; where it doesn't (e.g. a rainfall
accumulation with no fixed upper bound), only non-negativity is
enforced.
"""
from typing import List

from pydantic import BaseModel, Field, field_validator


class RainfallFeatures(BaseModel):
    """The 20 causal AI#1 predictors, exactly as documented in
    src/data/create_rainfall_features.py. future_6h_rain and target are
    deliberately absent from this schema -- they are not predictors."""

    temperature_2m: float
    relative_humidity_2m: float = Field(ge=0, le=100)
    surface_pressure: float
    wind_speed_10m: float = Field(ge=0)
    precipitation: float = Field(ge=0)
    rain_lag_1h: float = Field(ge=0)
    rain_lag_3h: float = Field(ge=0)
    rain_lag_6h: float = Field(ge=0)
    rain_1h: float = Field(ge=0)
    rain_3h: float = Field(ge=0)
    rain_6h: float = Field(ge=0)
    rain_12h: float = Field(ge=0)
    rain_24h: float = Field(ge=0)
    pressure_change_3h: float
    pressure_change_6h: float
    humidity_change_3h: float
    humidity_change_6h: float
    hour: int = Field(ge=0, le=23)
    month: int = Field(ge=1, le=12)
    day_of_year: int = Field(ge=1, le=366)


class RainfallPredictionResponse(BaseModel):
    model_version: str
    forecast_horizon: str = "next 6 hours"
    significant_rainfall_probability: float
    threshold_note: str = (
        "Probability that future_6h_rain >= 20mm, a project-defined "
        "significant-rainfall target -- not an IMD Heavy Rainfall category, "
        "which uses a 24-hour convention."
    )


class InundationCellFeatures(BaseModel):
    """The 8 AI#2 baseline predictors for a single spatial cell."""

    cell_id: str
    rain_1h: float = Field(ge=0)
    rain_3h: float = Field(ge=0)
    rain_6h: float = Field(ge=0)
    rain_12h: float = Field(ge=0)
    rain_24h: float = Field(ge=0)
    elevation: float
    slope_degrees: float = Field(ge=0)
    distance_to_drainage: float = Field(ge=0)


class InundationRequest(BaseModel):
    cells: List[InundationCellFeatures] = Field(min_length=1, max_length=10000)

    @field_validator("cells")
    @classmethod
    def unique_cell_ids(cls, cells):
        ids = [c.cell_id for c in cells]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate cell_id values in request.")
        return cells


class InundationCellResult(BaseModel):
    cell_id: str
    inundation_risk_probability: float


class InundationResponse(BaseModel):
    model_version: str
    results: List[InundationCellResult]
    limitation_note: str = (
        "Retrospective, proof-of-concept model validated via leave-one-episode-out "
        "evaluation on only two independently verified historical flood episodes "
        "(see data/processed/stage7_model_comparison.csv). This is a risk score, "
        "not a prediction of exact inundation depth, arrival time, or a guarantee "
        "that flagged cells will flood. No independently-validated production "
        "operating threshold currently exists for this model."
    )


class ModelInfo(BaseModel):
    name: str
    path: str
    description: str
    feature_names: List[str]


class ModelInfoResponse(BaseModel):
    models: List[ModelInfo]


class HealthResponse(BaseModel):
    status: str = "ok"
