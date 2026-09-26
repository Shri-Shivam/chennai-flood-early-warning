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
        "that flagged cells will flood. Its operating threshold (used to derive a "
        "risk_class elsewhere in this API) was selected via spatial-block OOF CV, "
        "not validated against an independent flood episode."
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


# --- Risk / end-to-end / risk-map / alerts ---

class CellRiskResult(BaseModel):
    cell_id: str
    inundation_risk_probability: float
    risk_class: str


class RiskRequest(BaseModel):
    rainfall_features: RainfallFeatures | None = None
    cells: List[InundationCellFeatures] = Field(min_length=1, max_length=10000)

    @field_validator("cells")
    @classmethod
    def unique_cell_ids(cls, cells):
        ids = [c.cell_id for c in cells]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate cell_id values in request.")
        return cells


class RiskResponse(BaseModel):
    rainfall_significant_probability: float | None
    cells: List[CellRiskResult]
    limitation_note: str = (
        "AI#1 (rainfall) and AI#2 (inundation) are reported separately, never "
        "blended into one number -- Stage 7/8 found no consistent benefit from "
        "combining them. risk_class boundaries are engineering/demo thresholds, "
        "not independently validated."
    )


class ExposureCellResult(BaseModel):
    cell_id: str
    estimated_population_exposed: int | None
    affected_facilities: List[str] | None
    data_available: bool
    reason_if_unavailable: str | None


class AlertResult(BaseModel):
    cell_id: str
    risk_class: str
    recommended_actions: dict


class EndToEndResponse(BaseModel):
    rainfall_significant_probability: float | None
    cells: List[CellRiskResult]
    exposure: List[ExposureCellResult]
    alerts: List[AlertResult]
    limitation_note: str = (
        "Retrospective proof-of-concept system. Exposure is not currently "
        "available for any cell (see docs/backend.md) -- estimated_population_exposed "
        "and affected_facilities are null, not zero. Alerts are recommendations "
        "for human decision-makers, never autonomous actions."
    )


class RiskMapRequest(BaseModel):
    """NOTE: implemented as POST, not GET as originally sketched -- a real
    risk map needs per-cell feature data as input, and no live spatial
    data source exists yet to serve a parameterless GET honestly."""
    cells: List[InundationCellFeatures] = Field(min_length=1, max_length=10000)


class RiskMapCell(BaseModel):
    cell_id: str
    inundation_risk_probability: float
    risk_class: str


class RiskMapResponse(BaseModel):
    cells: List[RiskMapCell]
    note: str = (
        "Implemented as POST, not GET, because per-cell feature data must be "
        "supplied by the caller -- no live spatial data source is integrated yet."
    )


class AlertsRequest(BaseModel):
    cells: List[CellRiskResult] = Field(min_length=1, max_length=10000)


class AlertsResponse(BaseModel):
    alerts: List[AlertResult]


# --- Live Weather to AI#2 Prediction ---


class LiveWeatherRequest(BaseModel):
    """Request for live weather-based inundation prediction."""
    latitude: float = Field(default=13.0827, ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(default=80.2707, ge=-180, le=180, description="Longitude in decimal degrees")
    past_days: int = Field(default=2, ge=0, le=30, description="Number of past days of weather data to fetch")
    forecast_days: int = Field(default=1, ge=0, le=10, description="Number of forecast days of weather data to fetch")


class LiveInundationCellResult(BaseModel):
    """Result for a single spatial cell from live weather prediction."""
    cell_id: str
    inundation_risk_probability: float


class LiveInundationResponse(BaseModel):
    """Response for live weather-based inundation prediction."""
    model_version: str
    rainfall_probability: float  # AI#1 prediction: P[≥20mm rainfall in next 6h]
    timestamp: str  # ISO format timestamp of the weather data used
    cells: List[LiveInundationCellResult]
    limitation_note: str = (
        "Live weather prediction uses current Open-Meteo data. "
        "AI#1 predicts P[≥20mm rainfall in next 6h]. "
        "AI#2 predicts inundation risk using live rainfall features (rain_1h..rain_24h) "
        "combined with static spatial features (elevation, slope, distance_to_drainage). "
        "This is a retrospective proof-of-concept model. "
        "See AI#1 and AI#2 limitation notes for details."
    )
