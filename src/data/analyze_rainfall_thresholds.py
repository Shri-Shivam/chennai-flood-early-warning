import pandas as pd

# Load weather data
file_path = "data/raw/chennai_weather_2016_2025.csv"

df = pd.read_csv(file_path, parse_dates=["time"])

# Sort by time
df = df.sort_values("time").reset_index(drop=True)

# ---------------------------------------------------------
# FUTURE 6-HOUR RAINFALL
# ---------------------------------------------------------
# At time t, calculate rainfall from:
# t+1, t+2, t+3, t+4, t+5, t+6
#
# This is important because our ML model will predict
# what happens in the NEXT 6 hours.
# ---------------------------------------------------------

df["future_6h_rain"] = sum(
    df["precipitation"].shift(-i)
    for i in range(1, 7)
)

# Remove the final rows where a complete future 6h window
# cannot be calculated
rain = df["future_6h_rain"].dropna()

print("=" * 60)
print("6-HOUR FUTURE RAINFALL THRESHOLD ANALYSIS")
print("=" * 60)

print(f"\nTotal valid 6-hour windows: {len(rain)}")

# ---------------------------------------------------------
# PERCENTILES
# ---------------------------------------------------------

percentiles = [50, 75, 90, 95, 97, 98, 99, 99.5]

print("\nRainfall percentiles:")
print("-" * 40)

for p in percentiles:
    value = rain.quantile(p / 100)
    print(f"{p:>5}th percentile : {value:6.2f} mm")

# ---------------------------------------------------------
# CANDIDATE THRESHOLDS
# ---------------------------------------------------------

thresholds = [
    20,
    30,
    40,
    50,
    60,
    70,
    80,
    90,
    100
]

print("\nCandidate thresholds:")
print("-" * 60)
print(f"{'Threshold':>12} {'Positive windows':>20} {'Event rate':>15}")
print("-" * 60)

for threshold in thresholds:

    positive = (rain >= threshold).sum()
    event_rate = positive / len(rain) * 100

    print(
        f"{threshold:>9} mm "
        f"{positive:>20} "
        f"{event_rate:>14.2f}%"
    )

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)