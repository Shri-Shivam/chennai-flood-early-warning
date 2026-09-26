"""SIH26071 - tests for the Open-Meteo ingestion adapter.

All external network calls are mocked -- this test file must pass with
no internet access, verified by patching requests.get for every test.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingestion.open_meteo import (  # noqa: E402
    fetch_weather,
    _parse_response,
    IngestionError,
    UpstreamRequestError,
    SchemaError,
    REQUIRED_HOURLY_VARIABLES,
)


def _valid_response(n=3):
    return {
        "hourly": {
            "time": [f"2026-01-01T0{i}:00" for i in range(n)],
            "temperature_2m": [28.0] * n,
            "relative_humidity_2m": [80.0] * n,
            "surface_pressure": [1005.0] * n,
            "wind_speed_10m": [10.0] * n,
            "precipitation": [0.0] * n,
        }
    }


def test_parse_valid_response():
    df = _parse_response(_valid_response())
    assert len(df) == 3
    assert set(REQUIRED_HOURLY_VARIABLES).issubset(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["time"])


def test_parse_response_missing_hourly_key_raises_schema_error():
    with pytest.raises(SchemaError):
        _parse_response({"not_hourly": {}})


def test_parse_response_missing_required_variable_raises_schema_error():
    bad = _valid_response()
    del bad["hourly"]["precipitation"]
    with pytest.raises(SchemaError):
        _parse_response(bad)


def test_parse_response_with_nulls_does_not_raise_but_preserves_nan():
    resp = _valid_response()
    resp["hourly"]["precipitation"][1] = None
    df = _parse_response(resp)
    assert len(df) == 3
    assert df["precipitation"].isna().sum() == 1  # not silently dropped or fabricated


@patch("src.ingestion.open_meteo.requests.get")
def test_fetch_weather_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = _valid_response()
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    df = fetch_weather()
    assert len(df) == 3
    mock_get.assert_called_once()


@patch("src.ingestion.open_meteo.requests.get")
def test_fetch_weather_retries_then_succeeds(mock_get):
    fail_resp = requests.exceptions.ConnectionError("network down")
    ok_resp = MagicMock()
    ok_resp.json.return_value = _valid_response()
    ok_resp.raise_for_status.return_value = None

    mock_get.side_effect = [fail_resp, fail_resp, ok_resp]
    with patch("src.ingestion.open_meteo.time.sleep"):  # don't actually wait in tests
        df = fetch_weather()
    assert len(df) == 3
    assert mock_get.call_count == 3


@patch("src.ingestion.open_meteo.requests.get")
def test_fetch_weather_exhausts_retries_raises_upstream_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("network down")
    with patch("src.ingestion.open_meteo.time.sleep"):
        with pytest.raises(UpstreamRequestError):
            fetch_weather()


@patch("src.ingestion.open_meteo.requests.get")
def test_fetch_weather_http_error_status_raises(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 server error")
    mock_get.return_value = mock_resp
    with patch("src.ingestion.open_meteo.time.sleep"):
        with pytest.raises(UpstreamRequestError):
            fetch_weather()


@patch("src.ingestion.open_meteo.requests.get")
def test_fetch_weather_malformed_response_raises_schema_error_not_upstream_error(mock_get):
    """A 200 OK with a malformed body is a different failure mode than a
    network error -- callers should be able to distinguish them."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"unexpected": "shape"}
    mock_get.return_value = mock_resp

    with pytest.raises(SchemaError):
        fetch_weather()
    mock_get.assert_called_once()  # no retry for a schema problem, only for transport failures


def test_ingestion_error_hierarchy():
    assert issubclass(UpstreamRequestError, IngestionError)
    assert issubclass(SchemaError, IngestionError)
