import pandas as pd


# ============================================
# 1. LOAD WEATHER DATA
# ============================================

file_path = "data/raw/chennai_weather_2021.csv"

df = pd.read_csv(file_path)

df["time"] = pd.to_datetime(df["time"])


# ============================================
# 2. BASIC INFORMATION
# ============================================

print("============================================")
print("CHENNAI WEATHER DATA ANALYSIS")
print("============================================")

print(f"\nTotal rows: {len(df)}")

print("\nDate range:")
print(f"Start: {df['time'].min()}")
print(f"End:   {df['time'].max()}")


# ============================================
# 3. HOURLY RAINFALL
# ============================================

print("\n============================================")
print("HOURLY RAINFALL")
print("============================================")

print(f"Total rainfall: {df['precipitation'].sum():.2f} mm")

print(
    f"Maximum hourly rainfall: "
    f"{df['precipitation'].max():.2f} mm"
)

max_hour = df.loc[df["precipitation"].idxmax()]

print(f"Date of maximum hourly rainfall: {max_hour['time']}")


# ============================================
# 4. ROLLING RAINFALL
# ============================================

df["rain_3h"] = (
    df["precipitation"]
    .rolling(window=3)
    .sum()
)

df["rain_6h"] = (
    df["precipitation"]
    .rolling(window=6)
    .sum()
)

df["rain_12h"] = (
    df["precipitation"]
    .rolling(window=12)
    .sum()
)

df["rain_24h"] = (
    df["precipitation"]
    .rolling(window=24)
    .sum()
)


# ============================================
# 5. MAXIMUM ACCUMULATIONS
# ============================================

print("\n============================================")
print("RAINFALL ACCUMULATION")
print("============================================")

for column in [
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h"
]:

    maximum = df[column].max()

    index = df[column].idxmax()

    timestamp = df.loc[index, "time"]

    print(
        f"Maximum {column}: "
        f"{maximum:.2f} mm "
        f"at {timestamp}"
    )


# ============================================
# 6. HEAVY RAINFALL HOURS
# ============================================

print("\n============================================")
print("RAINFALL DISTRIBUTION")
print("============================================")

thresholds = [2.5, 15, 64.5, 115.5, 204.5]

for threshold in thresholds:

    count = (df["precipitation"] >= threshold).sum()

    print(
        f"Hours with rainfall >= {threshold} mm: "
        f"{count}"
    )


# ============================================
# 7. TOP 10 RAINFALL HOURS
# ============================================

print("\n============================================")
print("TOP 10 RAINFALL HOURS")
print("============================================")

top_10 = df.nlargest(10, "precipitation")[
    ["time", "precipitation"]
]

print(top_10.to_string(index=False))