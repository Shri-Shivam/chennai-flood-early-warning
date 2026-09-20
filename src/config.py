"""SIH26071 - centralized configuration.

Single source of truth for paths, thresholds, and API settings. No
credentials live here -- there are none needed by anything currently
implemented (the only external adapter, Open-Meteo, uses a public,
keyless endpoint). Environment variables override the defaults below,
using the `SIH26071_` prefix, so deployment-specific values never need
to be hard-coded or committed.
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SIH26071_", extra="ignore")

    # --- Model paths (relative to repo root) ---
    ai1_rainfall_model_path: str = "models/xgboost_rainfall_model.json"
    ai2_production_model_path: str = "models/production/ai2_baseline.json"
    ai2_production_metadata_path: str = "models/production/ai2_baseline_metadata.json"

    # --- AI#2 operating threshold ---
    # Default mirrors models/production/ai2_baseline_metadata.json's
    # production_operating_threshold.threshold, selected by
    # src/models/select_production_threshold.py via spatial-block OOF CV
    # (see docs/backend.md for the limitation of this threshold: it is
    # not validated against an independent flood episode). Override via
    # SIH26071_AI2_DEFAULT_THRESHOLD for experimentation -- the API
    # always also returns the raw probability, never only a class label,
    # so a caller can apply their own operating point regardless.
    ai2_default_threshold: float = Field(default=0.9014831182804323)

    # --- Alert engine thresholds (engineering/demo, not officially validated) ---
    alert_watch_threshold: float = 0.10
    alert_warning_threshold: float = 0.30
    alert_high_risk_threshold: float = 0.60

    # --- Spatial / study area ---
    study_area_path: str = "data/processed/chennai_cmr_study_area.geojson"
    spatial_grid_resolution_m: int = 250
    spatial_block_size_m: float = 5000.0
    spatial_buffer_m: float = 500.0

    # --- Data ingestion ---
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_timeout_s: float = 10.0
    open_meteo_max_retries: int = 3
    open_meteo_retry_backoff_s: float = 1.0

    # --- API ---
    api_title: str = "SIH26071 Chennai Flood Early Warning - Inference API"
    api_max_cells_per_request: int = 10000

    def resolve(self, relative_path: str) -> Path:
        return ROOT / relative_path


settings = Settings()
