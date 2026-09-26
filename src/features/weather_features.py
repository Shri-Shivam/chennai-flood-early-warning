"""SIH26071 - Reusable weather feature engineering for AI#1 model.

Extracts the exact 20 features required by the AI#1 rainfall model from
Open-Meteo hourly weather data using the same logic as the historical
training data processing.
"""
from __future__ import annotations

import pandas as pd


def engineer_ai1_features(weather_df: pd.DataFrame) -> pd.DataFrame:
    """Engineer the 20 AI#1 features from Open-Meteo hourly weather data.

    Args:
        weather_df: DataFrame with Open-Meteo hourly data containing at least:
                   ['temperature_2m', 'relative_humidity_2m', 'surface_pressure',
                    'wind_speed_10m', 'precipitation', 'time']

    Returns:
        DataFrame with the original columns plus the engineered AI#1 features.
        Returns DataFrame sorted by time with reset index.

    Note:
        This function implements the exact same feature engineering logic
        used in src/data/create_rainfall_features.py to ensure consistency
        between training and inference.
    """
    # Make a copy to avoid modifying the original
    df = weather_df.copy()

    # Ensure data is sorted by time (oldest first)
    df = df.sort_values("time").reset_index(drop=True)

    # =========================================================
    # 2. RAINFALL LAG FEATURES
    # =========================================================
    df["rain_lag_1h"] = df["precipitation"].shift(1)
    df["rain_lag_3h"] = df["precipitation"].shift(3)
    df["rain_lag_6h"] = df["precipitation"].shift(6)

    # =========================================================
    # 3. ROLLING RAINFALL FEATURES
    # =========================================================
    df["rain_1h"] = df["precipitation"].rolling(1, closed="left").sum()
    df["rain_3h"] = df["precipitation"].rolling(3, closed="left").sum()
    df["rain_6h"] = df["precipitation"].rolling(6, closed="left").sum()
    df["rain_12h"] = df["precipitation"].rolling(12, closed="left").sum()
    df["rain_24h"] = df["precipitation"].rolling(24, closed="left").sum()

    # =========================================================
    # 4. PRESSURE TREND
    # =========================================================
    df["pressure_change_3h"] = df["surface_pressure"] - df["surface_pressure"].shift(3)
    df["pressure_change_6h"] = df["surface_pressure"] - df["surface_pressure"].shift(6)

    # =========================================================
    # 5. HUMIDITY TREND
    # =========================================================
    df["humidity_change_3h"] = df["relative_humidity_2m"] - df["relative_humidity_2m"].shift(3)
    df["humidity_change_6h"] = df["relative_humidity_2m"] - df["relative_humidity_2m"].shift(6)

    # =========================================================
    # 6. TIME FEATURES
    # =========================================================
    df["hour"] = df["time"].dt.hour
    df["month"] = df["time"].dt.month
    df["day_of_year"] = df["time"].dt.dayofyear

    return df


def get_latest_complete_features(weather_df: pd.DataFrame) -> pd.Series:
    """Extract the latest complete feature row for AI#1 inference.

    Args:
        weather_df: DataFrame with Open-Meteo hourly data that has been
                   processed by engineer_ai1_features()

    Returns:
        Series containing the latest complete row with ONLY the 20 AI#1 features,
        or empty Series if no complete rows exist.

    Note:
        Drops rows with NaN values created by lag/rolling operations
        to ensure only complete feature vectors are returned.
    """
    # Engineer features if not already done
    featured_df = engineer_ai1_features(weather_df)

    # Remove rows with NaN values (from lag/rolling operations)
    clean_df = featured_df.dropna().reset_index(drop=True)

    if len(clean_df) == 0:
        return pd.Series(dtype=float)

    # Return ONLY the AI#1 features from the most recent complete row
    latest_row = clean_df.iloc[-1]
    return latest_row[AI1_FEATURE_NAMES]


# Define the exact feature names expected by the AI#1 model
AI1_FEATURE_NAMES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "precipitation",
    "rain_lag_1h",
    "rain_lag_3h",
    "rain_lag_6h",
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",
    "pressure_change_3h",
    "pressure_change_6h",
    "humidity_change_3h",
    "humidity_change_6h",
    "hour",
    "month",
    "day_of_year"
]