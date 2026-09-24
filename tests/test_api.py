"""SIH26071 - API endpoint tests.

Uses FastAPI's TestClient (in-process, no network) against the real app
and real models -- no mocking of the model layer, only no live external
weather/data APIs are involved (there are none in this API's current scope).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from src.api.app import app  # noqa: E402
from src.inference.model_loader import clear_cache  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


VALID_RAINFALL_PAYLOAD = {
    "temperature_2m": 28.0, "relative_humidity_2m": 85.0, "surface_pressure": 1005.0,
    "wind_speed_10m": 10.0, "precipitation": 2.0,
    "rain_lag_1h": 1.0, "rain_lag_3h": 3.0, "rain_lag_6h": 5.0,
    "rain_1h": 1.0, "rain_3h": 3.0, "rain_6h": 5.0, "rain_12h": 8.0, "rain_24h": 15.0,
    "pressure_change_3h": -0.5, "pressure_change_6h": -1.0,
    "humidity_change_3h": 2.0, "humidity_change_6h": 4.0,
    "hour": 18, "month": 11, "day_of_year": 315,
}

VALID_INUNDATION_CELL = {
    "cell_id": "cell_0001",
    "rain_1h": 1.0, "rain_3h": 2.0, "rain_6h": 3.0, "rain_12h": 4.0,
    "rain_24h": 5.0, "elevation": 10.0, "slope_degrees": 1.0, "distance_to_drainage": 100.0,
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_info_lists_both_registered_models():
    r = client.get("/model-info")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()["models"]]
    assert "ai1_rainfall" in names
    assert "ai2_baseline_production" in names
    for m in r.json()["models"]:
        assert len(m["feature_names"]) > 0, f"{m['name']} reported no feature schema"


def test_predict_rainfall_valid_input():
    r = client.post("/predict/rainfall", json=VALID_RAINFALL_PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["significant_rainfall_probability"] <= 1.0
    assert "IMD" in body["threshold_note"]  # guardrail language present


def test_predict_rainfall_missing_field_rejected():
    bad = dict(VALID_RAINFALL_PAYLOAD)
    del bad["rain_24h"]
    r = client.post("/predict/rainfall", json=bad)
    assert r.status_code == 422  # Pydantic validation error, not a 500 or a silent default


def test_predict_rainfall_out_of_range_humidity_rejected():
    bad = dict(VALID_RAINFALL_PAYLOAD)
    bad["relative_humidity_2m"] = 150.0  # >100%, physically invalid
    r = client.post("/predict/rainfall", json=bad)
    assert r.status_code == 422


def test_predict_rainfall_negative_rainfall_rejected():
    bad = dict(VALID_RAINFALL_PAYLOAD)
    bad["rain_24h"] = -5.0
    r = client.post("/predict/rainfall", json=bad)
    assert r.status_code == 422


def test_predict_rainfall_is_deterministic():
    r1 = client.post("/predict/rainfall", json=VALID_RAINFALL_PAYLOAD)
    r2 = client.post("/predict/rainfall", json=VALID_RAINFALL_PAYLOAD)
    assert r1.json()["significant_rainfall_probability"] == r2.json()["significant_rainfall_probability"]


def test_predict_inundation_valid_multi_cell():
    payload = {"cells": [
        VALID_INUNDATION_CELL,
        {**VALID_INUNDATION_CELL, "cell_id": "cell_0002", "elevation": 2.0},
    ]}
    r = client.post("/predict/inundation", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 2
    ids = {res["cell_id"] for res in body["results"]}
    assert ids == {"cell_0001", "cell_0002"}
    for res in body["results"]:
        assert 0.0 <= res["inundation_risk_probability"] <= 1.0
    assert "risk score, not a prediction of exact inundation depth" in body["limitation_note"]


def test_predict_inundation_duplicate_cell_id_rejected():
    payload = {"cells": [VALID_INUNDATION_CELL, VALID_INUNDATION_CELL]}
    r = client.post("/predict/inundation", json=payload)
    assert r.status_code == 422


def test_predict_inundation_empty_cells_rejected():
    r = client.post("/predict/inundation", json={"cells": []})
    assert r.status_code == 422


def test_predict_inundation_missing_field_rejected():
    bad_cell = dict(VALID_INUNDATION_CELL)
    del bad_cell["distance_to_drainage"]
    r = client.post("/predict/inundation", json={"cells": [bad_cell]})
    assert r.status_code == 422


# --- /predict/risk ---

def test_predict_risk_with_rainfall_reports_both_signals():
    r = client.post("/predict/risk", json={
        "rainfall_features": VALID_RAINFALL_PAYLOAD,
        "cells": [VALID_INUNDATION_CELL],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["rainfall_significant_probability"] is not None
    assert 0.0 <= body["rainfall_significant_probability"] <= 1.0
    assert body["cells"][0]["risk_class"] in ("NORMAL", "WATCH", "WARNING", "HIGH_RISK")


def test_predict_risk_without_rainfall_omits_it_cleanly():
    r = client.post("/predict/risk", json={"cells": [VALID_INUNDATION_CELL]})
    assert r.status_code == 200
    assert r.json()["rainfall_significant_probability"] is None


def test_predict_risk_duplicate_cell_rejected():
    r = client.post("/predict/risk", json={"cells": [VALID_INUNDATION_CELL, VALID_INUNDATION_CELL]})
    assert r.status_code == 422


# --- /predict/end-to-end ---

def test_predict_end_to_end_full_chain():
    r = client.post("/predict/end-to-end", json={
        "rainfall_features": VALID_RAINFALL_PAYLOAD,
        "cells": [VALID_INUNDATION_CELL],
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["cells"]) == 1
    assert len(body["exposure"]) == 1
    assert len(body["alerts"]) == 1
    # Exposure must be honestly unavailable, never a fabricated number.
    assert body["exposure"][0]["data_available"] is False
    assert body["exposure"][0]["estimated_population_exposed"] is None
    # Alert must match the risk class computed for the same cell.
    assert body["alerts"][0]["risk_class"] == body["cells"][0]["risk_class"]
    # Every role must be present with at least one recommended action.
    for role_actions in body["alerts"][0]["recommended_actions"].values():
        assert len(role_actions) >= 1


# --- /risk-map ---

def test_risk_map_returns_cells():
    r = client.post("/risk-map", json={"cells": [VALID_INUNDATION_CELL]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["cells"]) == 1
    assert body["cells"][0]["cell_id"] == "cell_0001"
    assert "POST" in body["note"]


def test_risk_map_empty_cells_rejected():
    r = client.post("/risk-map", json={"cells": []})
    assert r.status_code == 422


# --- /alerts ---

def test_alerts_valid_risk_classes():
    payload = {"cells": [
        {"cell_id": "cell_0001", "inundation_risk_probability": 0.9, "risk_class": "HIGH_RISK"},
        {"cell_id": "cell_0002", "inundation_risk_probability": 0.01, "risk_class": "NORMAL"},
    ]}
    r = client.post("/alerts", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert len(body["alerts"]) == 2
    high_risk_alert = next(a for a in body["alerts"] if a["cell_id"] == "cell_0001")
    assert "recommend" in " ".join(high_risk_alert["recommended_actions"]["electricity_operator"]).lower() \
        or "consider" in " ".join(high_risk_alert["recommended_actions"]["electricity_operator"]).lower()


def test_alerts_invalid_risk_class_rejected_not_500():
    payload = {"cells": [
        {"cell_id": "cell_0001", "inundation_risk_probability": 0.5, "risk_class": "NOT_REAL"},
    ]}
    r = client.post("/alerts", json=payload)
    assert r.status_code == 422  # not a 500 -- this was a real bug found and fixed this session
