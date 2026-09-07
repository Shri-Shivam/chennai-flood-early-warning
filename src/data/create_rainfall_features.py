import pandas as pd
import os

# =========================================================
# 1. LOAD DATA
# =========================================================

input_file = "data/raw/chennai_weather_2016_2025.csv"

df = pd.read_csv(input_file, parse_dates=["time"])

df = df.sort_values("time").reset_index(drop=True)

print("=" * 60)
print("RAINFALL FEATURE ENGINEERING")
print("=" * 60)

print(f"\nOriginal rows: {len(df)}")


# =========================================================
# 2. RAINFALL LAG FEATURES
# =========================================================
#
# These tell the model how much rain recently occurred.
#
# Example:
#
# rain_lag_1 = rainfall 1 hour ago
# rain_lag_3 = rainfall 3 hours ago
# rain_lag_6 = rainfall 6 hours ago
#
# IMPORTANT:
# We only use PAST information here.
#


df["rain_lag_1h"] = df["precipitation"].shift(1)
df["rain_lag_3h"] = df["precipitation"].shift(3)
df["rain_lag_6h"] = df["precipitation"].shift(6)


# =========================================================
# 3. ROLLING RAINFALL FEATURES
# =========================================================
#
# Total rainfall accumulated during previous:
#
# 1 hour
# 3 hours
# 6 hours
# 12 hours
# 24 hours
#
# closed="left" means the CURRENT hour is NOT included.
#
# This is critical because at prediction time we cannot
# use rainfall that hasn't happened yet.
#

df["rain_1h"] = (
    df["precipitation"]
    .rolling(1, closed="left")
    .sum()
)

df["rain_3h"] = (
    df["precipitation"]
    .rolling(3, closed="left")
    .sum()
)

df["rain_6h"] = (
    df["precipitation"]
    .rolling(6, closed="left")
    .sum()
)

df["rain_12h"] = (
    df["precipitation"]
    .rolling(12, closed="left")
    .sum()
)

df["rain_24h"] = (
    df["precipitation"]
    .rolling(24, closed="left")
    .sum()
)


# =========================================================
# 4. PRESSURE TREND
# =========================================================
#
# Falling atmospheric pressure can sometimes be associated
# with approaching weather systems.
#
# Positive value  -> pressure increased
# Negative value  -> pressure decreased
#

df["pressure_change_3h"] = (
    df["surface_pressure"]
    - df["surface_pressure"].shift(3)
)

df["pressure_change_6h"] = (
    df["surface_pressure"]
    - df["surface_pressure"].shift(6)
)


# =========================================================
# 5. HUMIDITY TREND
# =========================================================

df["humidity_change_3h"] = (
    df["relative_humidity_2m"]
    - df["relative_humidity_2m"].shift(3)
)

df["humidity_change_6h"] = (
    df["relative_humidity_2m"]
    - df["relative_humidity_2m"].shift(6)
)


# =========================================================
# 6. TIME FEATURES
# =========================================================

df["hour"] = df["time"].dt.hour

df["month"] = df["time"].dt.month

df["day_of_year"] = df["time"].dt.dayofyear


# =========================================================
# 7. FUTURE 6-HOUR RAINFALL
# =========================================================
#
# TARGET INFORMATION
#
# At time t:
#
# future_6h_rain =
# rainfall at t+1
# + t+2
# + t+3
# + t+4
# + t+5
# + t+6
#
# This is what the model is trying to predict.
#

df["future_6h_rain"] = sum(
    df["precipitation"].shift(i)
    for i in range(-6, 0)
)


# =========================================================
# 8. CREATE TARGET
# =========================================================
#
# Our project-defined significant rainfall threshold:
#
# >= 20 mm in the next 6 hours
#
# 1 = significant rainfall event
# 0 = otherwise
#

threshold = 20

df["target"] = (
    df["future_6h_rain"] >= threshold
).astype(int)


# =========================================================
# 9. REMOVE INVALID ROWS
# =========================================================
#
# Lag and rolling features create NaN values at the
# beginning of the dataset.
#
# The final 6 hours also cannot have a complete future
# rainfall target.
#

before = len(df)

df = df.dropna().reset_index(drop=True)

after = len(df)

print(f"\nRows removed: {before - after}")
print(f"Final rows: {after}")


# =========================================================
# 10. CHECK TARGET DISTRIBUTION
# =========================================================

positive = df["target"].sum()

negative = len(df) - positive

event_rate = positive / len(df) * 100

print("\nTarget distribution:")
print("-" * 40)

print(f"Negative samples: {negative}")
print(f"Positive samples: {positive}")
print(f"Event rate:       {event_rate:.2f}%")


# =========================================================
# 11. SHOW FEATURES
# =========================================================

feature_columns = [
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

print("\nFeatures:")
print("-" * 40)

for feature in feature_columns:
    print(feature)


# =========================================================
# 12. SAVE DATASET
# =========================================================

output_file = "data/processed/rainfall_ml_dataset.csv"

os.makedirs("data/processed", exist_ok=True)

df.to_csv(output_file, index=False)

print("\n" + "=" * 60)
print("FEATURE ENGINEERING COMPLETE")
print("=" * 60)

print(f"\nSaved to:")
print(output_file)