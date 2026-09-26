"""Tests for the reusable weather feature engineering function."""
import pandas as pd
import numpy as np
from src.features.weather_features import engineer_ai1_features, get_latest_complete_features, AI1_FEATURE_NAMES


def test_engineer_ai1_features_normal_data():
    """Test feature engineering with normal hourly data."""
    # Create test data with known values
    times = pd.date_range('2023-01-01 00:00:00', periods=10, freq='h')
    data = {
        'time': times,
        'temperature_2m': [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0],
        'relative_humidity_2m': [60.0, 62.0, 64.0, 66.0, 68.0, 70.0, 72.0, 74.0, 76.0, 78.0],
        'surface_pressure': [1010.0, 1011.0, 1012.0, 1013.0, 1014.0, 1015.0, 1016.0, 1017.0, 1018.0, 1019.0],
        'wind_speed_10m': [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5],
        'precipitation': [0.0, 0.2, 0.5, 0.1, 0.3, 0.0, 0.4, 0.2, 0.1, 0.0]
    }
    df = pd.DataFrame(data)

    # Engineer features
    result_df = engineer_ai1_features(df)

    # Check that all expected features are present
    for feature in AI1_FEATURE_NAMES:
        assert feature in result_df.columns, f"Missing feature: {feature}"

    # Check that we have the same number of rows
    assert len(result_df) == len(df)

    # Check some specific known values
    # rain_lag_1h at index 1 should be precipitation[0] = 0.0
    assert result_df.iloc[1]['rain_lag_1h'] == 0.0
    # rain_lag_3h at index 3 should be precipitation[0] = 0.0
    assert result_df.iloc[3]['rain_lag_3h'] == 0.0
    # rain_1h at index 1 should be precipitation[0] = 0.0 (window=1, closed='left')
    assert result_df.iloc[1]['rain_1h'] == 0.0
    # rain_3h at index 3 should be sum of precipitation[1:3] = 0.2 + 0.5 = 0.7
    # (indices 1 and 2: 0.2 + 0.5 = 0.7)
    assert result_df.iloc[3]['rain_3h'] == 0.7

    # Check time features
    assert result_df.iloc[0]['hour'] == 0
    assert result_df.iloc[0]['month'] == 1
    assert result_df.iloc[0]['day_of_year'] == 1


def test_engineer_ai1_features_insufficient_history():
    """Test feature engineering with insufficient history for lag features."""
    # Create test data with only 2 rows (not enough for 6-hour lag)
    times = pd.date_range('2023-01-01 00:00:00', periods=2, freq='h')
    data = {
        'time': times,
        'temperature_2m': [20.0, 21.0],
        'relative_humidity_2m': [60.0, 62.0],
        'surface_pressure': [1010.0, 1011.0],
        'wind_speed_10m': [5.0, 5.5],
        'precipitation': [0.0, 0.2]
    }
    df = pd.DataFrame(data)

    # Engineer features
    result_df = engineer_ai1_features(df)

    # Check that all expected features are present
    for feature in AI1_FEATURE_NAMES:
        assert feature in result_df.columns, f"Missing feature: {feature}"

    # Check that lag features are NaN for insufficient history
    assert pd.isna(result_df.iloc[0]['rain_lag_1h'])  # No previous hour
    assert pd.isna(result_df.iloc[0]['rain_lag_3h'])  # No 3 hours previous
    assert pd.isna(result_df.iloc[0]['rain_lag_6h'])  # No 6 hours previous


def test_engineer_ai1_features_zero_precipitation():
    """Test feature engineering with zero precipitation."""
    # Create test data with zero precipitation
    times = pd.date_range('2023-01-01 00:00:00', periods=5, freq='h')
    data = {
        'time': times,
        'temperature_2m': [20.0, 21.0, 22.0, 23.0, 24.0],
        'relative_humidity_2m': [60.0, 62.0, 64.0, 66.0, 68.0],
        'surface_pressure': [1010.0, 1011.0, 1012.0, 1013.0, 1014.0],
        'wind_speed_10m': [5.0, 5.5, 6.0, 6.5, 7.0],
        'precipitation': [0.0, 0.0, 0.0, 0.0, 0.0]  # All zero precipitation
    }
    df = pd.DataFrame(data)

    # Engineer features
    result_df = engineer_ai1_features(df)

    # Check that all expected features are present
    for feature in AI1_FEATURE_NAMES:
        assert feature in result_df.columns

    # Check that precipitation-based features are zero where not NaN due to shift
    # Lag features: first few will be NaN due to shift, but where they have values, they should be zero
    assert pd.isna(result_df.iloc[0]['rain_lag_1h'])  # No previous data
    assert result_df.iloc[1]['rain_lag_1h'] == 0.0    # Equal to precip[0] = 0.0
    assert result_df.iloc[2]['rain_lag_1h'] == 0.0    # Equal to precip[1] = 0.0

    assert pd.isna(result_df.iloc[0]['rain_lag_3h'])  # Not enough history
    assert pd.isna(result_df.iloc[1]['rain_lag_3h'])  # Not enough history
    assert pd.isna(result_df.iloc[2]['rain_lag_3h'])  # Not enough history
    assert result_df.iloc[3]['rain_lag_3h'] == 0.0    # Equal to precip[0] = 0.0

    # Rolling features: with all zero precipitation, should be zero where calculable
    # rain_1h: window=1, closed='left' -> gives the previous hour's precipitation
    assert pd.isna(result_df.iloc[0]['rain_1h'])      # No previous hour
    assert result_df.iloc[1]['rain_1h'] == 0.0        # Equal to precip[0] = 0.0
    assert result_df.iloc[2]['rain_1h'] == 0.0        # Equal to precip[1] = 0.0

    # rain_3h: window=3, closed='left' -> sum of previous 3 hours precipitation
    assert pd.isna(result_df.iloc[0]['rain_3h'])      # Not enough history
    assert pd.isna(result_df.iloc[1]['rain_3h'])      # Not enough history
    assert pd.isna(result_df.iloc[2]['rain_3h'])      # Not enough history (need 3 previous)
    assert result_df.iloc[3]['rain_3h'] == 0.0        # Sum of precip[0:2] = 0+0+0 = 0
    assert result_df.iloc[4]['rain_3h'] == 0.0        # Sum of precip[1:3] = 0+0+0 = 0


def test_get_latest_complete_features():
    """Test extracting the latest complete feature row."""
    # Create test data with enough history for all features
    # We need at least 24 hours of data to get a complete row (due to rain_24h lag/rolling)
    times = pd.date_range('2023-01-01 00:00:00', periods=25, freq='h')  # 25 hours: 00:00 day1 to 00:00 day2
    data = {
        'time': times,
        'temperature_2m': np.linspace(20, 30, 25),  # 20 to 30 over 25 hours
        'relative_humidity_2m': np.linspace(60, 80, 25),
        'surface_pressure': np.linspace(1000, 1020, 25),
        'wind_speed_10m': np.linspace(0, 15, 25),
        'precipitation': np.linspace(0, 5, 25)       # 0 to 5 mm over 25 hours
    }
    df = pd.DataFrame(data)

    # Get latest complete features
    latest = get_latest_complete_features(df)

    # Should return a Series with all AI1_FEATURE_NAMES (just the features, not original columns)
    assert isinstance(latest, pd.Series)
    assert len(latest) == len(AI1_FEATURE_NAMES)

    # Check that all expected features are present
    for feature in AI1_FEATURE_NAMES:
        assert feature in latest.index
        # Check that the value is numeric (not NaN for a complete row)
        assert not pd.isna(latest[feature]), f"Feature {feature} is NaN in latest complete row"

    # Check that it's actually the latest row by comparing time-derived features
    # With 25 hours from 00:00 day1 to 00:00 day2, the last row should be 00:00 day2
    # So hour should be 0, month should be 1 (January), day_of_year should be 2 (Jan 2)
    assert latest['hour'] == 0  # Last hour is 00:00
    assert latest['month'] == 1  # January
    assert latest['day_of_year'] == 2  # January 2nd


def test_get_latest_complete_features_insufficient_data():
    """Test extracting latest complete features with insufficient data."""
    # Create test data with insufficient history (less than 24 hours for rain_24h)
    times = pd.date_range('2023-01-01 00:00:00', periods=10, freq='h')
    data = {
        'time': times,
        'temperature_2m': np.random.uniform(20, 30, 10),
        'relative_humidity_2m': np.random.uniform(60, 80, 10),
        'surface_pressure': np.random.uniform(1000, 1020, 10),
        'wind_speed_10m': np.random.uniform(0, 15, 10),
        'precipitation': np.random.uniform(0, 5, 10)
    }
    df = pd.DataFrame(data)

    # Get latest complete features
    latest = get_latest_complete_features(df)

    # Should return empty series since we don't have 24 hours of history
    assert len(latest) == 0


def test_output_feature_names():
    """Test that the output feature names match expectations."""
    assert len(AI1_FEATURE_NAMES) == 20
    expected_features = [
        "temperature_2m", "relative_humidity_2m", "surface_pressure",
        "wind_speed_10m", "precipitation", "rain_lag_1h", "rain_lag_3h",
        "rain_lag_6h", "rain_1h", "rain_3h", "rain_6h", "rain_12h",
        "rain_24h", "pressure_change_3h", "pressure_change_6h",
        "humidity_change_3h", "humidity_change_6h", "hour", "month",
        "day_of_year"
    ]
    assert AI1_FEATURE_NAMES == expected_features