import requests
import pandas as pd
from pathlib import Path
import time


# ============================================
# CHENNAI LOCATION
# ============================================

LATITUDE = 13.0827
LONGITUDE = 80.2707


# ============================================
# DATA PERIOD
# ============================================

START_YEAR = 2016
END_YEAR = 2025


# ============================================
# OPEN-METEO API
# ============================================

URL = "https://archive-api.open-meteo.com/v1/archive"


# ============================================
# OUTPUT DIRECTORY
# ============================================

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# DOWNLOAD ONE YEAR
# ============================================

def download_year(year):

    print(f"\nDownloading {year}...")

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",

        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "wind_speed_10m",
            "precipitation"
        ]),

        "timezone": "Asia/Kolkata"
    }

    response = requests.get(
        URL,
        params=params,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df["time"] = pd.to_datetime(df["time"])

    print(f"{year}: {len(df)} rows")

    return df


# ============================================
# DOWNLOAD ALL YEARS
# ============================================

all_years = []

for year in range(START_YEAR, END_YEAR + 1):

    try:

        df_year = download_year(year)

        all_years.append(df_year)

        # Small pause between API requests
        time.sleep(1)

    except Exception as error:

        print(f"ERROR downloading {year}: {error}")


# ============================================
# COMBINE DATA
# ============================================

if not all_years:

    raise RuntimeError("No weather data was downloaded.")


df = pd.concat(
    all_years,
    ignore_index=True
)


# ============================================
# SORT DATA
# ============================================

df = df.sort_values("time")

df = df.drop_duplicates(
    subset=["time"]
)


# ============================================
# SAVE DATA
# ============================================

output_file = (
    OUTPUT_DIR /
    "chennai_weather_2016_2025.csv"
)

df.to_csv(
    output_file,
    index=False
)


# ============================================
# FINAL REPORT
# ============================================

print("\n============================================")
print("DOWNLOAD COMPLETE")
print("============================================")

print(f"Total rows: {len(df)}")

print(
    f"Start: {df['time'].min()}"
)

print(
    f"End: {df['time'].max()}"
)

print(
    f"\nSaved to: {output_file}"
)

print("\nMissing values:")

print(
    df.isnull().sum()
)