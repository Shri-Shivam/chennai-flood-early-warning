import pandas as pd


# ============================================
# 1. LOAD DATA
# ============================================

file_path = "data/raw/chennai_weather_2016_2025.csv"

df = pd.read_csv(file_path)

df["time"] = pd.to_datetime(df["time"])


# ============================================
# 2. CREATE RAINFALL ACCUMULATIONS
# ============================================

df["rain_3h"] = (
    df["precipitation"]
    .rolling(3)
    .sum()
)

df["rain_6h"] = (
    df["precipitation"]
    .rolling(6)
    .sum()
)

df["rain_12h"] = (
    df["precipitation"]
    .rolling(12)
    .sum()
)

df["rain_24h"] = (
    df["precipitation"]
    .rolling(24)
    .sum()
)


# ============================================
# 3. BASIC INFORMATION
# ============================================

print("============================================")
print("10-YEAR CHENNAI WEATHER ANALYSIS")
print("============================================")

print(f"\nRows: {len(df)}")

print(f"Start: {df['time'].min()}")

print(f"End:   {df['time'].max()}")


# ============================================
# 4. RAINFALL STATISTICS
# ============================================

print("\n============================================")
print("RAINFALL STATISTICS")
print("============================================")

print(
    f"Total rainfall: "
    f"{df['precipitation'].sum():.2f} mm"
)

print(
    f"Maximum hourly rainfall: "
    f"{df['precipitation'].max():.2f} mm"
)

print(
    f"Maximum 3-hour rainfall: "
    f"{df['rain_3h'].max():.2f} mm"
)

print(
    f"Maximum 6-hour rainfall: "
    f"{df['rain_6h'].max():.2f} mm"
)

print(
    f"Maximum 12-hour rainfall: "
    f"{df['rain_12h'].max():.2f} mm"
)

print(
    f"Maximum 24-hour rainfall: "
    f"{df['rain_24h'].max():.2f} mm"
)


# ============================================
# 5. IMD-STYLE THRESHOLDS
# ============================================

print("\n============================================")
print("RAINFALL THRESHOLD COUNTS")
print("============================================")

thresholds = [
    2.5,
    15,
    64.5,
    115.6,
    204.5
]

for threshold in thresholds:

    count = (
        df["precipitation"] >= threshold
    ).sum()

    print(
        f"Hourly rainfall >= {threshold} mm: "
        f"{count} hours"
    )


# ============================================
# 6. 24-HOUR EVENT COUNTS
# ============================================

print("\n============================================")
print("24-HOUR RAINFALL EVENT COUNTS")
print("============================================")

daily = (
    df.set_index("time")
    ["precipitation"]
    .resample("24h")
    .sum()
)

print(
    f"Days >= 64.5 mm: "
    f"{(daily >= 64.5).sum()}"
)

print(
    f"Days >= 115.6 mm: "
    f"{(daily >= 115.6).sum()}"
)

print(
    f"Days >= 204.5 mm: "
    f"{(daily >= 204.5).sum()}"
)


# ============================================
# 7. TOP 20 RAINFALL EVENTS
# ============================================

print("\n============================================")
print("TOP 20 24-HOUR RAINFALL EVENTS")
print("============================================")

top_events = (
    daily
    .sort_values(ascending=False)
    .head(20)
)

print(top_events.to_string())


# ============================================
# 8. TOP 20 SIX-HOUR PERIODS
# ============================================

print("\n============================================")
print("TOP 20 SIX-HOUR RAINFALL PERIODS")
print("============================================")

top_6h = (
    df[["time", "rain_6h"]]
    .dropna()
    .sort_values(
        "rain_6h",
        ascending=False
    )
    .head(20)
)

print(
    top_6h.to_string(index=False)
)