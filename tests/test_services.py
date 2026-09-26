"""SIH26071 - tests for the service layer (risk engine, exposure, alerts).

Uses real models via the real service functions -- no mocking of the
model layer itself.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.risk_engine import assess_risk, classify_risk, RISK_CLASSES  # noqa: E402
from src.services.exposure_service import estimate_exposure, NO_DATA_REASON  # noqa: E402
from src.services.alert_engine import generate_alert  # noqa: E402
from src.inference.model_loader import clear_cache  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


VALID_RAINFALL = {
    "temperature_2m": 28.0, "relative_humidity_2m": 85.0, "surface_pressure": 1005.0,
    "wind_speed_10m": 10.0, "precipitation": 2.0,
    "rain_lag_1h": 1.0, "rain_lag_3h": 3.0, "rain_lag_6h": 5.0,
    "rain_1h": 1.0, "rain_3h": 3.0, "rain_6h": 5.0, "rain_12h": 8.0, "rain_24h": 15.0,
    "pressure_change_3h": -0.5, "pressure_change_6h": -1.0,
    "humidity_change_3h": 2.0, "humidity_change_6h": 4.0,
    "hour": 18, "month": 11, "day_of_year": 315,
}
VALID_CELL = {
    "cell_id": "cell_0001", "rain_1h": 1.0, "rain_3h": 2.0, "rain_6h": 3.0,
    "rain_12h": 4.0, "rain_24h": 5.0, "elevation": 10.0, "slope_degrees": 1.0,
    "distance_to_drainage": 100.0,
}


def test_classify_risk_boundaries_monotonic():
    assert classify_risk(0.0) == "NORMAL"
    assert classify_risk(0.05) == "NORMAL"
    assert classify_risk(0.15) == "WATCH"
    assert classify_risk(0.35) == "WARNING"
    assert classify_risk(0.99) == "HIGH_RISK"


def test_assess_risk_with_rainfall_reports_both_signals_separately():
    """AI#1 and AI#2 must never be silently blended -- Stage 7/8 found no
    consistent benefit from combining them, so both are reported."""
    result = assess_risk(rainfall_features=VALID_RAINFALL, cells=[VALID_CELL])
    assert result.rainfall is not None
    assert 0.0 <= result.rainfall.significant_rainfall_probability <= 1.0
    assert len(result.cells) == 1
    assert result.cells[0].risk_class in RISK_CLASSES


def test_assess_risk_without_rainfall_features_skips_ai1_cleanly():
    result = assess_risk(rainfall_features=None, cells=[VALID_CELL])
    assert result.rainfall is None
    assert len(result.cells) == 1


def test_assess_risk_multi_cell():
    cells = [VALID_CELL, {**VALID_CELL, "cell_id": "cell_0002", "elevation": 2.0}]
    result = assess_risk(rainfall_features=None, cells=cells)
    assert len(result.cells) == 2
    assert {c.cell_id for c in result.cells} == {"cell_0001", "cell_0002"}


def test_exposure_never_fabricates_a_number():
    results = estimate_exposure(["cell_0001", "cell_0002"])
    assert len(results) == 2
    for r in results:
        assert r.data_available is False
        assert r.estimated_population_exposed is None
        assert r.affected_facilities is None
        assert r.reason_if_unavailable == NO_DATA_REASON


def test_generate_alert_for_each_risk_class():
    for rc in RISK_CLASSES:
        alert = generate_alert("cell_0001", rc)
        assert alert.risk_class == rc
        assert set(alert.recommended_actions.keys()) == {
            "citizen", "municipal_authority", "disaster_management",
            "hospitals", "electricity_operator",
        }


def test_generate_alert_invalid_risk_class_rejected():
    with pytest.raises(ValueError):
        generate_alert("cell_0001", "NOT_A_REAL_CLASS")


def test_electricity_action_is_always_a_recommendation_not_a_command():
    for rc in RISK_CLASSES:
        alert = generate_alert("cell_0001", rc)
        for action in alert.recommended_actions["electricity_operator"]:
            assert "automated" not in action.lower() or "not an automated" in action.lower()
            forbidden = ("shut down now", "disconnecting power automatically", "auto-isolate")
            assert not any(f in action.lower() for f in forbidden)
