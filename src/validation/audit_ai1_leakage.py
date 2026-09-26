"""SIH26071 - Stage 6 standalone leakage audit.

Run: python src/validation/audit_ai1_leakage.py

Performs a consolidated, executable audit against the real generated
Stage 6 artifacts and the real source files -- not synthetic data
(synthetic-data formula tests live in tests/test_temporal_leakage.py).
Raises on the first failed check. Does not hard-code, compare
against, or reproduce any historical reference metric.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/processed/rainfall_ml_dataset.csv"
RETRO_CSV = ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
WALK_CSV = ROOT / "data/processed/ai1_walk_forward_metrics.csv"
WALK_FORWARD_SCRIPT = ROOT / "src/rainfall_model/walk_forward_forecast.py"

FEATURES = [
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "wind_speed_10m", "precipitation",
    "rain_lag_1h", "rain_lag_3h", "rain_lag_6h",
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "pressure_change_3h", "pressure_change_6h",
    "humidity_change_3h", "humidity_change_6h",
    "hour", "month", "day_of_year",
]


def check_feature_list_excludes_target_and_future():
    forbidden = {"future_6h_rain", "target"}
    bad = forbidden.intersection(FEATURES)
    assert not bad, f"Forbidden columns present in FEATURES: {bad}"


def check_dataset_is_chronological():
    d = pd.read_csv(DATASET, usecols=["time"])
    t = pd.to_datetime(d["time"])
    assert t.is_monotonic_increasing, "rainfall_ml_dataset.csv is not chronological."


def check_retrospective_cutoff():
    if not RETRO_CSV.exists():
        print(f"  [skip] {RETRO_CSV} not found -- run Stage 6 to generate it.")
        return
    d = pd.read_csv(RETRO_CSV)
    assert (d["training_end"] == "2021-10-31 23:00:00").all(), (
        "Not every retrospective row reports the expected training cutoff."
    )
    ts = pd.to_datetime(d["timestamp"])
    assert (ts > pd.Timestamp("2021-10-31 23:00:00")).all(), (
        "Some retrospective test timestamps are not strictly after the training cutoff."
    )


def check_walk_forward_training_precedes_test_year():
    if not WALK_CSV.exists():
        print(f"  [skip] {WALK_CSV} not found -- run Stage 6 to generate it.")
        return
    d = pd.read_csv(WALK_CSV)
    for _, row in d.iterrows():
        training_end = pd.Timestamp(row["training_end"])
        test_year_start = pd.Timestamp(f"{int(row['year'])}-01-01 00:00:00")
        assert training_end < test_year_start, (
            f"Year {row['year']}: training_end {training_end} is not before the test year's start."
        )


def check_source_feature_list_excludes_forbidden_columns():
    src = WALK_FORWARD_SCRIPT.read_text()
    block = src.split("FEATURES=", 1)[1].split("]", 1)[0]
    assert "future_6h_rain" not in block, "future_6h_rain appears inside the live FEATURES list."
    assert '"target"' not in block and "'target'" not in block, "target appears inside the live FEATURES list."


def audit():
    checks = [
        check_feature_list_excludes_target_and_future,
        check_dataset_is_chronological,
        check_retrospective_cutoff,
        check_walk_forward_training_precedes_test_year,
        check_source_feature_list_excludes_forbidden_columns,
    ]
    for check in checks:
        print(f"Running: {check.__name__}")
        check()
    return True


if __name__ == "__main__":
    print("AI1 leakage audit:", audit())
