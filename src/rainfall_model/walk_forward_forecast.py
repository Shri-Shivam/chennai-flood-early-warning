"""
SIH26071 - STAGE 6
Leakage-safe walk-forward forecasting pipeline and pre-event model training for AI #1.
"""
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
OUT_RETRO = REPO_ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
OUT_METRICS = REPO_ROOT / "data/processed/ai1_walk_forward_metrics.csv"
OUT_REPORT = REPO_ROOT / "data/processed/ai1_stage6_report.txt"

FEATURE_COLS = [
    "temperature_2m", "relative_humidity_2m", "surface_pressure", "wind_speed_10m",
    "precipitation", "rain_lag_1h", "rain_lag_3h", "rain_lag_6h", "rain_1h", "rain_3h",
    "rain_6h", "rain_12h", "rain_24h", "pressure_change_3h", "pressure_change_6h",
    "humidity_change_3h", "humidity_change_6h", "hour", "month", "day_of_year",
]
TARGET_COL = "target"
TOLERANCE = 1e-6
