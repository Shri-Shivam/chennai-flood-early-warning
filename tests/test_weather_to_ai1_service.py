"""Tests for the weather-to-AI#1 service chain."""
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from src.services.weather_to_ai1_service import (
    WeatherToAI1Result,
    WeatherToAI1Error,
    IngestionFailedError,
    InsufficientWeatherDataError,
    predict_rainfall_from_weather
)
from src.ingestion.open_meteo import ChennaiPoint


class TestWeatherToAI1Service:
    """Test the weather-to-AI#1 service chain."""

    @patch('src.services.weather_to_ai1_service.fetch_weather')
    @patch('src.services.weather_to_ai1_service.predict_rainfall')
    def test_predict_rainfall_from_weather_success(
        self, mock_predict_rainfall, mock_fetch_weather
    ):
        """Test successful execution of the weather → AI#1 chain."""
        # Mock Open-Meteo response with sufficient data
        times = pd.date_range('2023-01-01 00:00:00', periods=30, freq='h')
        mock_weather_df = pd.DataFrame({
            'time': times,
            'temperature_2m': [25.0] * 30,
            'relative_humidity_2m': [70.0] * 30,
            'surface_pressure': [1010.0] * 30,
            'wind_speed_10m': [5.0] * 30,
            'precipitation': [0.1] * 30
        })
        mock_fetch_weather.return_value = mock_weather_df

        # Mock AI#1 prediction response
        mock_predict_rainfall.return_value = type('MockRainfallResult', (), {
            'significant_rainfall_probability': 0.75,
            'model_version': 'xgboost_rainfall_model.json'
        })()

        # Execute the service
        result = predict_rainfall_from_weather()

        # Verify the result
        assert isinstance(result, WeatherToAI1Result)
        assert isinstance(result.timestamp, datetime)
        assert result.significant_rainfall_probability == 0.75
        assert result.model_version == 'xgboost_rainfall_model.json'
        assert len(result.features) == 20  # AI#1 has 20 features

        # Verify that all expected features are present
        from src.features.weather_features import AI1_FEATURE_NAMES
        for feature in AI1_FEATURE_NAMES:
            assert feature in result.features
            assert isinstance(result.features[feature], float)

        # Verify mocks were called
        mock_fetch_weather.assert_called_once()
        mock_predict_rainfall.assert_called_once()

    @patch('src.services.weather_to_ai1_service.fetch_weather')
    def test_predict_rainfall_from_weather_ingestion_failed(
        self, mock_fetch_weather
    ):
        """Test handling of Open-Meteo ingestion failures."""
        mock_fetch_weather.side_effect = Exception("API timeout")

        with pytest.raises(IngestionFailedError):
            predict_rainfall_from_weather()

    @patch('src.services.weather_to_ai1_service.fetch_weather')
    @patch('src.services.weather_to_ai1_service.engineer_ai1_features')
    def test_predict_rainfall_from_weather_insufficient_data(
        self, mock_engineer_ai1_features, mock_fetch_weather
    ):
        """Test handling of insufficient weather data."""
        # Mock Open-Meteo response with insufficient data (< 24 hours)
        times = pd.date_range('2023-01-01 00:00:00', periods=10, freq='h')
        mock_weather_df = pd.DataFrame({
            'time': times,
            'temperature_2m': [25.0] * 10,
            'relative_humidity_2m': [70.0] * 10,
            'surface_pressure': [1010.0] * 10,
            'wind_speed_10m': [5.0] * 10,
            'precipitation': [0.1] * 10
        })
        mock_fetch_weather.return_value = mock_weather_df

        # Mock feature engineering to return dataframe that will produce no complete rows
        mock_featured_df = mock_weather_df.copy()
        mock_featured_df['rain_lag_1h'] = [float('nan')] * 10  # All NaN to simulate insufficient history
        mock_engineer_ai1_features.return_value = mock_featured_df

        with pytest.raises(InsufficientWeatherDataError):
            predict_rainfall_from_weather()

    @patch('src.services.weather_to_ai1_service.fetch_weather')
    @patch('src.services.weather_to_ai1_service.get_latest_complete_features')
    def test_predict_rainfall_from_weather_no_complete_rows(
        self, mock_get_latest_complete_features, mock_fetch_weather
    ):
        """Test handling when no complete feature rows are available."""
        # Mock Open-Meteo response with sufficient data
        times = pd.date_range('2023-01-01 00:00:00', periods=30, freq='h')
        mock_weather_df = pd.DataFrame({
            'time': times,
            'temperature_2m': [25.0] * 30,
            'relative_humidity_2m': [70.0] * 30,
            'surface_pressure': [1010.0] * 30,
            'wind_speed_10m': [5.0] * 30,
            'precipitation': [0.1] * 30
        })
        mock_fetch_weather.return_value = mock_weather_df

        # Mock to return empty series (no complete rows)
        mock_get_latest_complete_features.return_value = pd.Series(dtype=float)

        with pytest.raises(InsufficientWeatherDataError):
            predict_rainfall_from_weather()

    @patch('src.services.weather_to_ai1_service.fetch_weather')
    @patch('src.services.weather_to_ai1_service.predict_rainfall')
    def test_predict_rainfall_from_weather_prediction_failed(
        self, mock_predict_rainfall, mock_fetch_weather
    ):
        """Test handling of AI#1 prediction failures."""
        # Mock Open-Meteo response with sufficient data
        times = pd.date_range('2023-01-01 00:00:00', periods=30, freq='h')
        mock_weather_df = pd.DataFrame({
            'time': times,
            'temperature_2m': [25.0] * 30,
            'relative_humidity_2m': [70.0] * 30,
            'surface_pressure': [1010.0] * 30,
            'wind_speed_10m': [5.0] * 30,
            'precipitation': [0.1] * 30
        })
        mock_fetch_weather.return_value = mock_weather_df

        # Mock AI#1 prediction to raise an exception
        mock_predict_rainfall.side_effect = Exception("Model prediction failed")

        with pytest.raises(Exception):  # Will be wrapped in WeatherToAI1Error
            predict_rainfall_from_weather()


if __name__ == "__main__":
    pytest.main([__file__])