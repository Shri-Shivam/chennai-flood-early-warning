"""Tests for the live inundation prediction FastAPI endpoint."""
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.app import app
from src.inference.model_loader import load_registered


class TestLiveInundationEndpoint:
    """Test the /predict/live-inundation endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('src.services.spatial_ai2_service.predict_spatial_inundation')
    @patch('src.services.weather_to_ai1_service.predict_rainfall_from_weather')
    def test_predict_live_inundation_success(
        self, mock_predict_rainfall, mock_predict_spatial
    ):
        """Test successful live inundation prediction."""
        # Mock weather → AI#1 result
        mock_weather_result = Mock()
        mock_weather_result.significant_rainfall_probability = 0.75
        mock_weather_result.features = {
            "rain_1h": 0.1, "rain_3h": 0.5, "rain_6h": 1.0, "rain_12h": 2.0, "rain_24h": 3.0,
        }
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

        # model_version is read from the registered AI#2 model's own metadata
        # via the loader's version accessor -- never a literal in the handler.
        assert data["model_version"] == load_registered("ai2_baseline_production").version
        assert data["rainfall_probability"] == 0.75
        assert "timestamp" in data
        assert len(data["cells"]) == 2
        assert data["cells"][0]["cell_id"] == "0"
        assert data["cells"][0]["inundation_risk_probability"] == 0.3
        assert data["cells"][1]["cell_id"] == "1"
        assert data["cells"][1]["inundation_risk_probability"] == 0.7
        assert "limitation_note" in data

        # Verify mocks were called with correct parameters.
        # The live weather → AI#1 stage must run EXACTLY ONCE per request;
        # this assertion is the regression guard for the duplicated-AI#1 bug.
        assert mock_predict_rainfall.call_count == 1
        mock_predict_spatial.assert_called_once()

        # AI#2 must consume the features from that single AI#1 execution
        # rather than recomputing them.
        assert mock_predict_spatial.call_args[1]["weather_features"] is mock_weather_result.features

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

    @patch('src.services.weather_to_ai1_service.predict_rainfall_from_weather')
    def test_predict_live_inundation_service_error(self, mock_predict_rainfall):
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