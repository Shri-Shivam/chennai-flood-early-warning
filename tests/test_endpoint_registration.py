"""Quick verification test for the live inundation endpoint."""
from src.api.app import app


def test_endpoint_registered():
    """Test that the live inundation endpoint is registered in the app."""
    # Get all routes
    routes = [route.path for route in app.routes]

    # Check that our new endpoint is registered
    assert "/predict/live-inundation" in routes
    assert app.routes[routes.index("/predict/live-inundation")].methods == {"POST"}

    print("✅ Live inundation endpoint is properly registered")


if __name__ == "__main__":
    test_endpoint_registered()