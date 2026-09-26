"""SIH26071 - tests for the model loading / schema validation layer.

Uses the real, already-trained model files -- no mocked models.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.inference.model_loader import (  # noqa: E402
    REGISTRY,
    SchemaValidationError,
    load_model,
    load_registered,
    clear_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def test_registered_models_actually_load():
    for name in REGISTRY:
        m = load_registered(name)
        assert len(m.feature_names) > 0


def test_model_is_cached_not_reloaded():
    m1 = load_registered("ai1_rainfall")
    m2 = load_registered("ai1_rainfall")
    assert m1 is m2  # same object -- confirms caching, not a silent reload/retrain


def test_missing_model_file_raises_not_silently_fabricated():
    with pytest.raises(FileNotFoundError):
        load_model("nonexistent", "models/does_not_exist.json", "classifier")


def test_ai1_feature_schema_matches_documented_20_features():
    m = load_registered("ai1_rainfall")
    expected = {
        "temperature_2m", "relative_humidity_2m", "surface_pressure",
        "wind_speed_10m", "precipitation",
        "rain_lag_1h", "rain_lag_3h", "rain_lag_6h",
        "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
        "pressure_change_3h", "pressure_change_6h",
        "humidity_change_3h", "humidity_change_6h",
        "hour", "month", "day_of_year",
    }
    assert set(m.feature_names) == expected
    assert "future_6h_rain" not in m.feature_names
    assert "target" not in m.feature_names


def test_ai2_feature_schema_matches_documented_8_baseline_features():
    m = load_registered("ai2_baseline_production")
    expected = {
        "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
        "elevation", "slope_degrees", "distance_to_drainage",
    }
    assert set(m.feature_names) == expected


def test_missing_required_feature_rejected_not_silently_filled():
    m = load_registered("ai2_baseline_production")
    incomplete = pd.DataFrame([{
        "rain_1h": 1.0, "rain_3h": 2.0, "rain_6h": 3.0, "rain_12h": 4.0,
        "rain_24h": 5.0, "elevation": 10.0, "slope_degrees": 1.0,
        # distance_to_drainage deliberately omitted
    }])
    with pytest.raises(SchemaValidationError):
        m.predict_proba(incomplete)


def test_extra_unexpected_columns_are_ignored_not_used():
    """Callers may send extra fields; the loader must select only the
    model's own required columns, never accidentally use an unexpected one."""
    m = load_registered("ai2_baseline_production")
    df_extra = pd.DataFrame([{
        "rain_1h": 1.0, "rain_3h": 2.0, "rain_6h": 3.0, "rain_12h": 4.0,
        "rain_24h": 5.0, "elevation": 10.0, "slope_degrees": 1.0,
        "distance_to_drainage": 100.0, "future_6h_rain": 999.0, "some_junk": "x",
    }])
    df_clean = df_extra.drop(columns=["future_6h_rain", "some_junk"])
    p_extra = m.predict_proba(df_extra)
    p_clean = m.predict_proba(df_clean)
    assert p_extra[0] == pytest.approx(p_clean[0])


def test_predictions_are_deterministic_across_repeated_calls():
    m = load_registered("ai1_rainfall")
    row = pd.DataFrame([{
        "temperature_2m": 28.0, "relative_humidity_2m": 85.0, "surface_pressure": 1005.0,
        "wind_speed_10m": 10.0, "precipitation": 2.0,
        "rain_lag_1h": 1.0, "rain_lag_3h": 3.0, "rain_lag_6h": 5.0,
        "rain_1h": 1.0, "rain_3h": 3.0, "rain_6h": 5.0, "rain_12h": 8.0, "rain_24h": 15.0,
        "pressure_change_3h": -0.5, "pressure_change_6h": -1.0,
        "humidity_change_3h": 2.0, "humidity_change_6h": 4.0,
        "hour": 18, "month": 11, "day_of_year": 315,
    }])
    p1 = m.predict_proba(row)
    p2 = m.predict_proba(row)
    assert p1[0] == p2[0]
    assert 0.0 <= p1[0] <= 1.0


def test_column_order_does_not_matter():
    """The loader must reorder by name, never trust caller column order."""
    m = load_registered("ai2_baseline_production")
    ordered = {
        "rain_1h": 1.0, "rain_3h": 2.0, "rain_6h": 3.0, "rain_12h": 4.0,
        "rain_24h": 5.0, "elevation": 10.0, "slope_degrees": 1.0, "distance_to_drainage": 100.0,
    }
    reversed_order = dict(reversed(list(ordered.items())))
    p1 = m.predict_proba(pd.DataFrame([ordered]))
    p2 = m.predict_proba(pd.DataFrame([reversed_order]))
    assert p1[0] == pytest.approx(p2[0])
