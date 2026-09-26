"""SIH26071 - Spatial AI#2 inference service.

Combines live weather features (rain_1h through rain_24h) with static
spatial features (elevation, slope_degrees, distance_to_drainage) to
run AI#2 inundation risk predictions for all spatial cells.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd

from src.inference.model_loader import load_registered
from src.services.weather_to_ai1_service import WeatherToAI1Result


class SpatialAI2Error(Exception):
    """Base class for errors in the spatial AI#2 service."""


def load_spatial_features(geojson_path: str = "data/processed/chennai_spatial_features_final.geojson") -> List[Dict[str, Any]]:
    """Load spatial features from GeoJSON file.

    Args:
        geojson_path: Path to the GeoJSON file containing spatial features

    Returns:
        List of feature dictionaries with properties containing spatial data

    Raises:
        SpatialAI2Error: If the GeoJSON file cannot be loaded or parsed
    """
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "features" not in data:
            raise SpatialAI2Error(f"GeoJSON file missing 'features' key: {geojson_path}")

        # Extract properties from each feature
        spatial_features = []
        for feature in data["features"]:
            if "properties" not in feature:
                continue  # Skip features without properties
            spatial_features.append(feature["properties"])

        return spatial_features

    except FileNotFoundError:
        raise SpatialAI2Error(f"Spatial features file not found: {geojson_path}")
    except json.JSONDecodeError as e:
        raise SpatialAI2Error(f"Invalid GeoJSON format in {geojson_path}: {e}")
    except Exception as e:
        raise SpatialAI2Error(f"Failed to load spatial features from {geojson_path}: {e}")


def predict_spatial_inundation(
    weather_features: Dict[str, float],
    spatial_features: List[Dict[str, Any]] | None = None
) -> List[Dict[str, Any]]:
    """Run AI#2 inundation risk prediction for all spatial cells.

    Combines live weather features (specifically rain_1h through rain_24h)
    with static spatial features for each cell and runs AI#2 inference.

    Args:
        weather_features: Dictionary containing the 20 AI#1 features,
                         must include rain_1h through rain_24h
        spatial_features: Optional list of spatial feature dictionaries.
                         If None, loads from default GeoJSON path.

    Returns:
        List of dictionaries, each containing:
        - cell_id: Identifier for the spatial cell
        - inundation_risk_probability: Probability of inundation [0,1]
        - Plus all original spatial feature properties

    Raises:
        SpatialAI2Error: If required features are missing or inference fails
    """
    # Load spatial features if not provided
    if spatial_features is None:
        spatial_features = load_spatial_features()

    # Validate that weather_features contains the required rainfall features
    required_rain_features = [f"rain_{h}h" for h in [1, 3, 6, 12, 24]]
    missing_rain_features = [f for f in required_rain_features if f not in weather_features]
    if missing_rain_features:
        raise SpatialAI2Error(
            f"Missing required rainfall features for AI#2: {missing_rain_features}. "
            f"Available features: {list(weather_features.keys())}"
        )

    # Load AI#2 model
    try:
        model = load_registered("ai2_baseline_production")
    except Exception as e:
        raise SpatialAI2Error(f"Failed to load AI#2 model: {e}") from e

    # Prepare input data for AI#2: one row per spatial cell
    # Each row needs: rain_1h, rain_3h, rain_6h, rain_12h, rain_24h, elevation, slope_degrees, distance_to_drainage, cell_id
    input_rows = []

    for spatial_props in spatial_features:
        # Extract required spatial features
        try:
            row = {
                "cell_id": str(spatial_props.get("cell_id", "")),
                "rain_1h": float(weather_features["rain_1h"]),
                "rain_3h": float(weather_features["rain_3h"]),
                "rain_6h": float(weather_features["rain_6h"]),
                "rain_12h": float(weather_features["rain_12h"]),
                "rain_24h": float(weather_features["rain_24h"]),
                "elevation": float(spatial_props["elevation"]),
                "slope_degrees": float(spatial_props["slope_degrees"]),
                "distance_to_drainage": float(spatial_props["distance_to_drainage"]),
            }
            input_rows.append(row)
        except KeyError as e:
            raise SpatialAI2Error(
                f"Missing required spatial feature in cell {spatial_props.get('cell_id', 'unknown')}: {e}"
            )
        except (ValueError, TypeError) as e:
            raise SpatialAI2Error(
                f"Invalid value for spatial feature in cell {spatial_props.get('cell_id', 'unknown')}: {e}"
            )

    if not input_rows:
        return []  # No valid spatial features to process

    # Convert to DataFrame for AI#2 inference
    try:
        input_df = pd.DataFrame(input_rows)

        # Run AI#2 inference
        probabilities = model.predict_proba(input_df)

        # Combine results with original spatial properties
        results = []
        for i, (spatial_props, probability) in enumerate(zip(spatial_features, probabilities)):
            result = {
                "cell_id": str(spatial_props.get("cell_id", "")),
                "inundation_risk_probability": float(probability),
                # Include all original spatial properties
                **{k: v for k, v in spatial_props.items() if k not in ["cell_id"]}
            }
            results.append(result)

        return results

    except Exception as e:
        raise SpatialAI2Error(f"AI#2 inference failed: {e}") from e


def predict_spatial_inundation_from_weather(
    point: Any = None,  # Will use default ChennaiPoint
    past_days: int = 2,
    forecast_days: int = 1,
    spatial_features: List[Dict[str, Any]] | None = None
) -> List[Dict[str, Any]]:
    """End-to-end service: weather → AI#1 features → AI#2 spatial inference.

    Args:
        point: Geographic coordinates for weather prediction (uses service default if None)
        past_days: Number of past days of weather data to fetch
        forecast_days: Number of forecast days of weather data to fetch
        spatial_features: Optional list of spatial feature dictionaries.
                         If None, loads from default GeoJSON path.

    Returns:
        List of dictionaries, each containing inundation risk prediction for a spatial cell

    Raises:
        Various exceptions from the underlying services (see their documentation)
    """
    # Import here to avoid circular dependencies
    from src.services.weather_to_ai1_service import (
        ChennaiPoint,
        predict_rainfall_from_weather,
        WeatherToAI1Result
    )

    # Step 1: Get live weather features and AI#1 prediction
    weather_result: WeatherToAI1Result = predict_rainfall_from_weather(
        point=point or ChennaiPoint(),
        past_days=past_days,
        forecast_days=forecast_days
    )

    # Step 2: Extract the weather features (specifically rain_1h through rain_24h for AI#2)
    weather_features = weather_result.features

    # Step 3: Run AI#2 spatial inference using the weather features
    spatial_predictions = predict_spatial_inundation(
        weather_features=weather_features,
        spatial_features=spatial_features
    )

    return spatial_predictions