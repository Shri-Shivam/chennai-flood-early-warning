"""SIH26071 - Weather to AI#1 service chain.

Chains Open-Meteo ingestion → feature engineering → AI#1 inference
to provide live rainfall predictions from current weather conditions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from src.features.weather_features import (
    AI1_FEATURE_NAMES,
    engineer_ai1_features,
    get_latest_complete_features,
)
from src.ingestion.open_meteo import ChennaiPoint, fetch_weather, IngestionError
from src.services.rainfall_service import RainfallResult, predict_rainfall
from src.config import settings


class WeatherToAI1Error(Exception):
    """Base class for errors in the weather-to-AI#1 service chain."""


class IngestionFailedError(WeatherToAI1Error):
    """Raised when Open-Meteo ingestion fails after retries."""


class InsufficientWeatherDataError(WeatherToAI1Error):
    """Raised when insufficient weather data is available for feature engineering."""


@dataclass(frozen=True)
class WeatherToAI1Result:
    """Result from the weather → AI#1 service chain."""
    timestamp: datetime  # Timestamp of the prediction (when the features were measured)
    features: dict[str, float]  # The 20 AI#1 features used for prediction
    significant_rainfall_probability: float  # P[≥20mm rainfall in next 6h]
    model_version: str  # AI#1 model file name
    model_threshold: float = 0.5  # Default classification threshold (can be overridden)
    limitation_note: str = (
        "Predictions are probabilistic estimates based on historical patterns. "
        "Actual rainfall may vary due to unmodeled meteorological factors. "
        "This model predicts the probability of ≥20mm rainfall in the next 6 hours, "
        "not the exact rainfall amount or flood occurrence."
    )


def predict_rainfall_from_weather(
    point: ChennaiPoint = ChennaiPoint(),
    past_days: int = 2,
    forecast_days: int = 1,
) -> WeatherToAI1Result:
    """Execute the complete weather → AI#1 prediction chain.

    Args:
        point: Geographic coordinates for weather prediction (default: Chennai center)
        past_days: Number of past days of weather data to fetch
        forecast_days: Number of forecast days of weather data to fetch

    Returns:
        WeatherToAI1Result containing timestamp, features, probability, and metadata

    Raises:
        IngestionFailedError: If Open-Meteo data cannot be fetched
        InsufficientWeatherDataError: If insufficient data for feature engineering
    """
    try:
        # Step 1: Ingest live weather data from Open-Meteo
        weather_df = fetch_weather(point=point, past_days=past_days, forecast_days=forecast_days)
    except Exception as e:
        raise IngestionFailedError(f"Failed to ingest weather data: {e}") from e

    # Validate we have enough data for feature engineering
    if len(weather_df) < 24:
        raise InsufficientWeatherDataError(
            f"Insufficient weather data for feature engineering: {len(weather_df)} hours available, "
            f"need at least 24 hours for rain_24h features"
        )

    # Step 2: Engineer AI#1 features from weather data
    featured_df = engineer_ai1_features(weather_df)

    # Step 3: Extract latest complete feature row
    latest_features = get_latest_complete_features(featured_df)

    if len(latest_features) == 0:
        raise InsufficientWeatherDataError(
            "No complete feature rows available after engineering (all rows contain NaN values)"
        )

    # Extract just the AI#1 features in the correct order
    ai1_features_dict = {}
    for feature_name in AI1_FEATURE_NAMES:
        ai1_features_dict[feature_name] = float(latest_features[feature_name])

    # Step 4: Get AI#1 prediction
    try:
        rainfall_result = predict_rainfall(ai1_features_dict)
    except Exception as e:
        raise WeatherToAI1Error(f"AI#1 prediction failed: {e}") from e

    # Determine timestamp of the prediction (when the features were measured)
    # This is the timestamp of the latest complete row
    prediction_timestamp = featured_df.iloc[-1]["time"].to_pydatetime()

    return WeatherToAI1Result(
        timestamp=prediction_timestamp,
        features=ai1_features_dict,
        significant_rainfall_probability=rainfall_result.significant_rainfall_probability,
        model_version=rainfall_result.model_version,
        model_threshold=settings.ai2_default_threshold,  # Note: This is AI#2 threshold, but keeping for API consistency
        limitation_note=(
            "Predictions are probabilistic estimates based on historical patterns. "
            "Actual rainfall may vary due to unmodeled meteorological factors. "
            "This model predicts the probability of ≥20mm rainfall in the next 6 hours, "
            "not the exact rainfall amount or flood occurrence. "
            f"Model: {rainfall_result.model_version}"
        )
    )