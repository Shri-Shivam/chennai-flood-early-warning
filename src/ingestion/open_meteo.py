"""SIH26071 - Open-Meteo live weather ingestion adapter.

Consistent with the existing historical-download script
(src/data/download_weather.py): same variable list, same response shape
(data["hourly"] -> dict of arrays including "time"), same implicit
assumption that Open-Meteo's default units apply (no explicit `units`
API parameter was used to build the training data, so none is used
here either -- using a different unit convention live than what the
models were trained on would silently corrupt every prediction).

This adapter targets Open-Meteo's *forecast* endpoint (recent/current
conditions plus a short forecast), not the *archive* endpoint used for
historical backfill -- the two serve different purposes and this
project already has archive data for training.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List

import pandas as pd
import requests

from src.config import settings

logger = logging.getLogger(__name__)

REQUIRED_HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "precipitation",
]


class IngestionError(Exception):
    """Base class for all ingestion failures. Never silently swallowed --
    every caller either handles this explicitly or lets it propagate."""


class UpstreamRequestError(IngestionError):
    """Network/timeout/HTTP-level failure calling the upstream API."""


class SchemaError(IngestionError):
    """The upstream response did not contain the expected fields."""


@dataclass(frozen=True)
class ChennaiPoint:
    latitude: float = 13.0827
    longitude: float = 80.2707


def fetch_weather(
    point: ChennaiPoint = ChennaiPoint(),
    past_days: int = 2,
    forecast_days: int = 1,
) -> pd.DataFrame:
    """Fetch recent + forecast hourly weather from Open-Meteo.

    Raises UpstreamRequestError on network/timeout/HTTP failure after
    exhausting retries. Raises SchemaError if the response is missing a
    required field. Never returns a DataFrame with fabricated or
    interpolated values for a variable the API didn't actually return.
    """
    params = {
        "latitude": point.latitude,
        "longitude": point.longitude,
        "hourly": ",".join(REQUIRED_HOURLY_VARIABLES),
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Asia/Kolkata",
    }

    last_error: Exception | None = None
    for attempt in range(1, settings.open_meteo_max_retries + 1):
        try:
            response = requests.get(
                settings.open_meteo_base_url,
                params=params,
                timeout=settings.open_meteo_timeout_s,
            )
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(
                "Open-Meteo request failed (attempt %d/%d): %s",
                attempt, settings.open_meteo_max_retries, e,
            )
            if attempt < settings.open_meteo_max_retries:
                time.sleep(settings.open_meteo_retry_backoff_s * attempt)
    else:
        raise UpstreamRequestError(
            f"Open-Meteo request failed after {settings.open_meteo_max_retries} attempts: {last_error}"
        ) from last_error

    return _parse_response(data)


def _parse_response(data: dict) -> pd.DataFrame:
    if "hourly" not in data:
        raise SchemaError(f"Open-Meteo response missing 'hourly' key. Response keys: {list(data.keys())}")

    hourly = data["hourly"]
    missing = [v for v in ["time"] + REQUIRED_HOURLY_VARIABLES if v not in hourly]
    if missing:
        raise SchemaError(f"Open-Meteo response missing required field(s): {missing}")

    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    null_counts = df[REQUIRED_HOURLY_VARIABLES].isna().sum()
    variables_with_nulls: List[str] = null_counts[null_counts > 0].index.tolist()
    if variables_with_nulls:
        logger.warning(
            "Open-Meteo response contains missing values in: %s. "
            "These rows will still be returned -- callers must check for NaN "
            "before using them as model features.",
            variables_with_nulls,
        )

    return df
