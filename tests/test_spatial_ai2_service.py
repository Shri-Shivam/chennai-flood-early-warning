"""Tests for the spatial AI#2 inference service."""
from unittest.mock import Mock, patch
import json

import pytest

from src.services.spatial_ai2_service import (
    SpatialAI2Error,
    load_spatial_features,
    predict_spatial_inundation,
    predict_spatial_inundation_from_weather
)


class TestLoadSpatialFeatures:
    """Test loading spatial features from GeoJSON."""

    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_load_spatial_features_file_not_found(self, mock_open):
        """Test handling of missing GeoJSON file."""
        with pytest.raises(SpatialAI2Error, match="not found"):
            load_spatial_features("nonexistent.geojson")

    @patch('builtins.open')
    @patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    def test_load_spatial_features_invalid_json(self, mock_json_load, mock_open):
        """Test handling of invalid GeoJSON format."""
        with pytest.raises(SpatialAI2Error, match="Invalid GeoJSON format"):
            load_spatial_features("invalid.geojson")

    @patch('builtins.open')
    @patch('json.load')
    def test_load_spatial_features_missing_features_key(self, mock_json_load, mock_open):
        """Test handling of GeoJSON missing features key."""
        mock_json_load.return_value = {"type": "FeatureCollection"}  # No "features" key

        with pytest.raises(SpatialAI2Error, match="missing 'features' key"):
            load_spatial_features("test.geojson")

    @patch('builtins.open')
    @patch('json.load')
    def test_load_spatial_features_success(self, mock_json_load, mock_open):
        """Test successful loading of spatial features."""
        # Mock GeoJSON data
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "cell_id": 0,
                        "elevation": 10.0,
                        "slope_degrees": 5.0,
                        "distance_to_drainage": 100.0
                    },
                    "geometry": {"type": "Polygon", "coordinates": []}
                },
                {
                    "type": "Feature",
                    "properties": {
                        "cell_id": 1,
                        "elevation": 20.0,
                        "slope_degrees": 10.0,
                        "distance_to_drainage": 200.0
                    },
                    "geometry": {"type": "Polygon", "coordinates": []}
                }
            ]
        }
        mock_json_load.return_value = mock_geojson

        result = load_spatial_features("test.geojson")

        assert len(result) == 2
        assert result[0]["cell_id"] == 0
        assert result[0]["elevation"] == 10.0
        assert result[1]["cell_id"] == 1
        assert result[1]["elevation"] == 20.0


class TestPredictSpatialInundation:
    """Test AI#2 spatial inference predictions."""

    def test_predict_spatial_inundation_missing_rainfall_features(self):
        """Test handling of missing rainfall features."""
        weather_features = {
            "temperature_2m": 25.0,
            # Missing rain_1h, rain_3h, etc.
        }
        spatial_features = [{"cell_id": "0", "elevation": 10.0, "slope_degrees": 5.0, "distance_to_drainage": 100.0}]

        with pytest.raises(SpatialAI2Error, match="Missing required rainfall features"):
            predict_spatial_inundation(weather_features, spatial_features)

    @patch('src.services.spatial_ai2_service.load_registered')
    def test_predict_spatial_inundation_success(self, mock_load_registered):
        """Test successful spatial inference."""
        # Mock AI#2 model
        mock_model = Mock()
        mock_model.predict_proba.return_value = [0.3, 0.7]  # Two predictions
        mock_load_registered.return_value = mock_model

        # Input data
        weather_features = {
            "rain_1h": 0.1,
            "rain_3h": 0.5,
            "rain_6h": 1.0,
            "rain_12h": 2.0,
            "rain_24h": 3.0,
            # Other AI#1 features (not used by AI#2 but required to be present)
            "temperature_2m": 25.0,
            "relative_humidity_2m": 70.0,
            "surface_pressure": 1010.0,
            "wind_speed_10m": 5.0,
            "precipitation": 0.1,
            "rain_lag_1h": 0.0,
            "rain_lag_3h": 0.0,
            "rain_lag_6h": 0.0,
            "pressure_change_3h": 0.0,
            "pressure_change_6h": 0.0,
            "humidity_change_3h": 0.0,
            "humidity_change_6h": 0.0,
            "hour": 12,
            "month": 6,
            "day_of_year": 180
        }

        spatial_features = [
            {
                "cell_id": "cell_0",
                "elevation": 10.0,
                "slope_degrees": 5.0,
                "distance_to_drainage": 100.0
            },
            {
                "cell_id": "cell_1",
                "elevation": 20.0,
                "slope_degrees": 10.0,
                "distance_to_drainage": 200.0
            }
        ]

        # Execute
        result = predict_spatial_inundation(weather_features, spatial_features)

        # Verify
        assert len(result) == 2
        assert result[0]["cell_id"] == "cell_0"
        assert result[0]["inundation_risk_probability"] == 0.3
        assert result[0]["elevation"] == 10.0
        assert result[1]["cell_id"] == "cell_1"
        assert result[1]["inundation_risk_probability"] == 0.7
        assert result[1]["elevation"] == 20.0

        # Verify model was called with correct features
        mock_load_registered.assert_called_once_with("ai2_baseline_production")
        mock_model.predict_proba.assert_called_once()

        # Check the input DataFrame to the model
        call_args = mock_model.predict_proba.call_args[0][0]  # First positional argument
        assert len(call_args) == 2  # Two rows
        assert list(call_args.columns) == [
            "cell_id", "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
            "elevation", "slope_degrees", "distance_to_drainage"
        ]
        # Check first row values
        assert call_args.iloc[0]["rain_1h"] == 0.1
        assert call_args.iloc[0]["elevation"] == 10.0
        assert call_args.iloc[0]["cell_id"] == "cell_0"

    def test_predict_spatial_invalid_spatial_features(self):
        """Test handling of invalid or missing spatial features."""
        weather_features = {
            "rain_1h": 0.1, "rain_3h": 0.5, "rain_6h": 1.0, "rain_12h": 2.0, "rain_24h": 3.0,
            "temperature_2m": 25.0, "relative_humidity_2m": 70.0, "surface_pressure": 1010.0,
            "wind_speed_10m": 5.0, "precipitation": 0.1, "rain_lag_1h": 0.0, "rain_lag_3h": 0.0,
            "rain_lag_6h": 0.0, "pressure_change_3h": 0.0, "pressure_change_6h": 0.0,
            "humidity_change_3h": 0.0, "humidity_change_6h": 0.0, "hour": 12, "month": 6, "day_of_year": 180
        }

        # Missing elevation
        spatial_features = [
            {"cell_id": "0", "slope_degrees": 5.0, "distance_to_drainage": 100.0}  # Missing elevation
        ]

        with pytest.raises(SpatialAI2Error, match="Missing required spatial feature"):
            predict_spatial_inundation(weather_features, spatial_features)


class TestPredictSpatialInundationFromWeather:
    """Test the end-to-end weather → AI#1 → AI#2 service."""

    @patch('src.services.spatial_ai2_service.predict_spatial_inundation')
    @patch('src.services.weather_to_ai1_service.predict_rainfall_from_weather')
    def test_predict_spatial_inundation_from_weather_success(
        self, mock_predict_rainfall, mock_predict_spatial
    ):
        """Test successful end-to-end execution."""
        # Mock weather → AI#1 result
        mock_weather_result = Mock()
        mock_weather_result.features = {
            "rain_1h": 0.1, "rain_3h": 0.5, "rain_6h": 1.0, "rain_12h": 2.0, "rain_24h": 3.0,
            # Other AI#1 features...
            "temperature_2m": 25.0, "relative_humidity_2m": 70.0, "surface_pressure": 1010.0,
            "wind_speed_10m": 5.0, "precipitation": 0.1, "rain_lag_1h": 0.0, "rain_lag_3h": 0.0,
            "rain_lag_6h": 0.0, "pressure_change_3h": 0.0, "pressure_change_6h": 0.0,
            "humidity_change_3h": 0.0, "humidity_change_6h": 0.0, "hour": 12, "month": 6, "day_of_year": 180
        }
        mock_predict_rainfall.return_value = mock_weather_result

        # Mock AI#2 spatial inference result
        mock_predict_spatial.return_value = [
            {"cell_id": "0", "inundation_risk_probability": 0.3, "elevation": 10.0},
            {"cell_id": "1", "inundation_risk_probability": 0.7, "elevation": 20.0}
        ]

        # Execute
        result = predict_spatial_inundation_from_weather()

        # Verify
        assert len(result) == 2
        assert result[0]["inundation_risk_probability"] == 0.3
        assert result[1]["inundation_risk_probability"] == 0.7

        # Verify mocks were called
        mock_predict_rainfall.assert_called_once()
        mock_predict_spatial.assert_called_once()

        # Verify the weather features were passed to AI#2 service
        call_args = mock_predict_spatial.call_args
        assert call_args[1]["weather_features"] == mock_weather_result.features


if __name__ == "__main__":
    pytest.main([__file__])