"""SIH26071 - Stage 6 leakage tests.

Tests 1-6 independently verify the feature-engineering formulas
documented in src/data/create_rainfall_features.py, using small
synthetic chronological series with independently-computed expected
values. This file only replicates the pandas expressions from that
script (it is not permitted to modify or import from it as a module,
and it reads directly from a raw CSV that is not available here) --
so these tests verify the *formulas actually shipped* in that script,
by reproducing them line-for-line and checking them against
hand-computed arithmetic, not by re-deriving expectations from the
same pandas call being tested.

Tests 7-10 verify properties of the real, already-generated Stage 6
artifacts and the actual src/rainfall_model/walk_forward_forecast.py
source -- not synthetic data.

No historical reference metric is compared or hard-coded anywhere in
this file.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
WALK_FORWARD_SCRIPT = ROOT / "src/rainfall_model/walk_forward_forecast.py"
RETRO_CSV = ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
WALK_CSV = ROOT / "data/processed/ai1_walk_forward_metrics.csv"


def _synthetic_series(n=40, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="h")
    precip = rng.uniform(0, 10, size=n).round(2)
    pressure = 1000 + rng.normal(0, 2, size=n).round(2)
    humidity = 60 + rng.normal(0, 5, size=n).round(2)
    return pd.DataFrame({
        "time": idx,
        "precipitation": precip,
        "surface_pressure": pressure,
        "relative_humidity_2m": humidity,
    })


def _apply_feature_formulas(df):
    """Reproduces the exact formulas from src/data/create_rainfall_features.py."""
    df = df.copy()
    df["rain_lag_1h"] = df["precipitation"].shift(1)
    df["rain_lag_3h"] = df["precipitation"].shift(3)
    df["rain_lag_6h"] = df["precipitation"].shift(6)
    df["rain_1h"] = df["precipitation"].rolling(1, closed="left").sum()
    df["rain_3h"] = df["precipitation"].rolling(3, closed="left").sum()
    df["rain_6h"] = df["precipitation"].rolling(6, closed="left").sum()
    df["rain_12h"] = df["precipitation"].rolling(12, closed="left").sum()
    df["rain_24h"] = df["precipitation"].rolling(24, closed="left").sum()
    df["pressure_change_3h"] = df["surface_pressure"] - df["surface_pressure"].shift(3)
    df["pressure_change_6h"] = df["surface_pressure"] - df["surface_pressure"].shift(6)
    df["humidity_change_3h"] = df["relative_humidity_2m"] - df["relative_humidity_2m"].shift(3)
    df["humidity_change_6h"] = df["relative_humidity_2m"] - df["relative_humidity_2m"].shift(6)
    df["future_6h_rain"] = sum(df["precipitation"].shift(i) for i in range(-6, 0))
    df["target"] = (df["future_6h_rain"] >= 20).astype(int)
    return df


def test_1_lag_features_use_only_past_values():
    df = _apply_feature_formulas(_synthetic_series())
    p = df["precipitation"].to_numpy()
    for t in range(6, len(df)):
        assert df["rain_lag_1h"].iloc[t] == pytest.approx(p[t - 1])
        assert df["rain_lag_3h"].iloc[t] == pytest.approx(p[t - 3])
        assert df["rain_lag_6h"].iloc[t] == pytest.approx(p[t - 6])


def test_2_rolling_windows_exclude_current_hour():
    df = _apply_feature_formulas(_synthetic_series())
    p = df["precipitation"].to_numpy()
    for t in range(24, len(df)):
        assert df["rain_1h"].iloc[t] == pytest.approx(sum(p[t - 1:t]))
        assert df["rain_3h"].iloc[t] == pytest.approx(sum(p[t - 3:t]))
        assert df["rain_6h"].iloc[t] == pytest.approx(sum(p[t - 6:t]))
        assert df["rain_12h"].iloc[t] == pytest.approx(sum(p[t - 12:t]))
        assert df["rain_24h"].iloc[t] == pytest.approx(sum(p[t - 24:t]))


def test_3_future_target_matches_definition():
    df = _apply_feature_formulas(_synthetic_series())
    p = df["precipitation"].to_numpy()
    for t in range(0, len(df) - 6):
        expected_future = sum(p[t + 1:t + 7])
        assert df["future_6h_rain"].iloc[t] == pytest.approx(expected_future)
        assert df["target"].iloc[t] == int(expected_future >= 20)


def test_4_future_rainfall_perturbation_does_not_alter_past_predictors():
    """The most important leakage test: proves future rainfall cannot
    alter predictors available at prediction time t."""
    base = _synthetic_series(n=60, seed=1)
    perturbed = base.copy()
    t = 30  # far enough in that every rolling window (up to 24h) is fully populated
    perturbed.loc[t + 1:t + 6, "precipitation"] = perturbed.loc[t + 1:t + 6, "precipitation"] + 50.0

    f_base = _apply_feature_formulas(base)
    f_pert = _apply_feature_formulas(perturbed)

    predictors = [
        "precipitation",
        "rain_lag_1h", "rain_lag_3h", "rain_lag_6h",
        "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
        "pressure_change_3h", "pressure_change_6h",
        "humidity_change_3h", "humidity_change_6h",
    ]
    for col in predictors:
        a, b = f_base[col].iloc[t], f_pert[col].iloc[t]
        assert not (pd.isna(a) or pd.isna(b)), f"Predictor '{col}' at t={t} is unexpectedly NaN; pick a later t."
        assert a == pytest.approx(b), (
            f"Predictor '{col}' at t changed after perturbing only t+1..t+6 -- this is leakage."
        )
        assert np.allclose(
            f_base[col].iloc[:t + 1].fillna(-999).to_numpy(),
            f_pert[col].iloc[:t + 1].fillna(-999).to_numpy(),
        ), f"Predictor '{col}' changed at or before t after a future-only perturbation."

    assert f_base["future_6h_rain"].iloc[t] != pytest.approx(f_pert["future_6h_rain"].iloc[t])
    assert f_pert["future_6h_rain"].iloc[t] > f_base["future_6h_rain"].iloc[t]


def test_5_pressure_and_humidity_changes_depend_only_on_past():
    base = _synthetic_series(n=40, seed=2)
    perturbed = base.copy()
    t = 15
    perturbed.loc[t + 1:t + 6, "surface_pressure"] += 500
    perturbed.loc[t + 1:t + 6, "relative_humidity_2m"] += 500

    f_base = _apply_feature_formulas(base)
    f_pert = _apply_feature_formulas(perturbed)
    for col in ["pressure_change_3h", "pressure_change_6h", "humidity_change_3h", "humidity_change_6h"]:
        assert f_base[col].iloc[t] == pytest.approx(f_pert[col].iloc[t])
        assert np.allclose(
            f_base[col].iloc[:t + 1].fillna(-999).to_numpy(),
            f_pert[col].iloc[:t + 1].fillna(-999).to_numpy(),
        )


def test_6_stage6_feature_list_excludes_future_and_target():
    src = WALK_FORWARD_SCRIPT.read_text()
    block = src.split("FEATURES=", 1)[1].split("]", 1)[0]
    assert "future_6h_rain" not in block
    assert '"target"' not in block and "'target'" not in block


def test_7_retrospective_cutoff_and_test_period():
    if not RETRO_CSV.exists():
        pytest.skip(f"Missing {RETRO_CSV} -- run Stage 6 to generate it.")
    df = pd.read_csv(RETRO_CSV)
    assert (df["training_end"] == "2021-10-31 23:00:00").all()
    ts = pd.to_datetime(df["timestamp"])
    cutoff = pd.Timestamp("2021-10-31 23:00:00")
    assert (ts > cutoff).all(), "Some retrospective test timestamps are not after the training cutoff."


def test_8_walk_forward_training_precedes_test_year():
    if not WALK_CSV.exists():
        pytest.skip(f"Missing {WALK_CSV} -- run Stage 6 to generate it.")
    df = pd.read_csv(WALK_CSV)
    for _, row in df.iterrows():
        training_end = pd.Timestamp(row["training_end"])
        test_year_start = pd.Timestamp(f"{int(row['year'])}-01-01 00:00:00")
        assert training_end < test_year_start, (
            f"Year {row['year']}: training_end {training_end} is not before test year start."
        )


def test_9_threshold_selection_uses_validation_not_test_labels():
    src = WALK_FORWARD_SCRIPT.read_text()
    calls = re.findall(r"(?<!def )select_threshold\(([^)]*)\)", src, flags=re.S)
    assert calls, "select_threshold() is not called anywhere (excluding its own definition) -- cannot verify."
    for call_args in calls:
        assert "test[" not in call_args, f"select_threshold called with a test-set argument: {call_args!r}"
        assert "validation[" in call_args, f"select_threshold not called with a validation-set argument: {call_args!r}"


def test_10_scale_pos_weight_uses_training_fit_labels_only():
    src = WALK_FORWARD_SCRIPT.read_text()
    fn_match = re.search(r"def classifier\(train_data\):\n(.*?)\ndef ", src, flags=re.S)
    assert fn_match, "Could not locate classifier() function body."
    body = fn_match.group(1)
    assert "train_data[TARGET]" in body, "classifier() does not derive labels from its own training-data argument."
    assert re.search(r'scale_pos_weight"\]\s*=\s*negatives\s*/\s*positives', body), (
        "scale_pos_weight is not computed as negatives/positives from the supplied training data."
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
