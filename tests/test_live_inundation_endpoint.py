"""Tests for the live inundation prediction FastAPI endpoint."""
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.app import app


class TestLiveInundationEndpoint:
    """Test the /predict/live-inundation endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('src.services.spatial_ai2_service.predict_spatial_inundation_from_weather')
    @patch('src.services.weather_to_ai1_service.predict_rainfall_from_weather')
    def test_predict_live_inundation_success(
        self, mock_predict_rainfall, mock_predict_spatial
    ):
        """Test successful live inundation prediction."""
        # Mock weather → AI#1 result
        mock_weather_result = Mock()
        mock_weather_result.significant_rainfall_probability = 0.75
        mock_predict_rainfall.return_value = mock_weather_result

        # Mock AI#2 spatial inference result
        mock_predict_spatial.return_value = [
            {"cell_id": "0", "inundation_risk_probability": 0.3},
            {"cell_id": "1", "inundation_risk_probability": 0.7}
        ]

        # Make request
        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 13.0827,
                "longitude": 80.2707,
                "past_days": 2,
                "forecast_days": 1
            }
        )

        # Debug information if test fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            print(f"Mock predict_rainfall called: {mock_predict_rainfall.called}")
            print(f"Mock predict_spatial called: {mock_predict_spatial.called}")
            if mock_predict_rainfall.called:
                print(f"predict_rainfall call args: {mock_predict_rainfall.call_args}")
            if mock_predict_spatial.called:
                print(f"predict_spatial call args: {mock_predict_spatial.call_args}")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["model_version"] == "ai2_baseline_production"
        assert data["rainfall_probability"] == 0.75
        assert "timestamp" in data
        assert len(data["cells"]) == 2
        assert data["cells"][0]["cell_id"] == "0"
        assert data["cells"][0]["inundation_risk_probability"] == 0.3
        assert data["cells"][1]["cell_id"] == "1"
        assert data["cells"][1]["inundation_risk_probability"] == 0.7
        assert "limitation_note" in data

        # Verify mocks were called with correct parameters
        mock_predict_rainfall.assert_called_once()
        mock_predict_spatial.assert_called_once()

        # Check that the point was constructed correctly
        call_args = mock_predict_rainfall.call_args
        point_arg = call_args[1]["point"]  # keyword argument 'point'
        assert point_arg.latitude == 13.0827
        assert point_arg.longitude == 80.2707
        assert call_args[1]["past_days"] == 2
        assert call_args[1]["forecast_days"] == 1

    def test_predict_live_inundation_invalid_coordinates(self):
        """Test validation of coordinate parameters."""
        # Test latitude out of range
        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 91.0,  # Invalid: > 90
                "longitude": 80.2707
            }
        )
        assert response.status_code == 422

        # Test longitude out of range
        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 13.0827,
                "longitude": 181.0  # Invalid: > 180
            }
        )
        assert response.status_code == 422

    def test_predict_live_inundation_invalid_days(self):
        """Test validation of day parameters."""
        # Test past_days out of range
        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 13.0827,
                "longitude": 80.2707,
                "past_days": 31  # Invalid: > 30
            }
        )
        assert response.status_code == 422

        # Test forecast_days out of range
        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 13.0827,
                "longitude": 80.2707,
                "forecast_days": 11  # Invalid: > 10
            }
        )
        assert response.status_code == 422

    @patch('src.services.spatial_ai2_service.predict_spatial_inundation_from_weather')
    @patch('src.services.weather_to_ai1_service.predict_rainfall_from_weather')
    def test_predict_live_inundation_service_error(
        self, mock_predict_rainfall, mock_predict_spatial
    ):
        """Test handling of service errors."""
        # Simulate weather service failure
        mock_predict_rainfall.side_effect = Exception("Failed to ingest weather data: Open-Meteo request failed")

        response = self.client.post(
            "/predict/live-inundation",
            json={
                "latitude": 13.0827,
                "longitude": 80.2707
            }
        )

        # Should return 503 Service Unavailable for weather service issues
        assert response.status_code == 503
        assert "Weather service unavailable" in response.json()["detail"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])