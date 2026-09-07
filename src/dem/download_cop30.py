import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# Load API key from .env
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("OPEN_TOPOGRAPHY_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPEN_TOPOGRAPHY_API_KEY not found in .env"
    )


# --------------------------------------------------
# Chennai CMR study-area bounding box
# --------------------------------------------------
SOUTH = 12.467462
NORTH = 13.5646282
WEST = 79.7306278
EAST = 80.3465467


# --------------------------------------------------
# Output
# --------------------------------------------------
output_dir = PROJECT_ROOT / "data" / "raw"
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "chennai_cop30.tif"


# --------------------------------------------------
# OpenTopography Global DEM API
# --------------------------------------------------
url = "https://portal.opentopography.org/API/globaldem"

params = {
    "demtype": "COP30",
    "south": SOUTH,
    "north": NORTH,
    "west": WEST,
    "east": EAST,
    "outputFormat": "GTiff",
    "API_Key": api_key,
}


print("Requesting COP30 DEM...")
print(f"Study area: {WEST}, {SOUTH} → {EAST}, {NORTH}")

response = requests.get(
    url,
    params=params,
    timeout=300,
)

print(f"HTTP status: {response.status_code}")

if response.status_code != 200:
    print("OpenTopography request failed.")
    print(response.text[:1000])
    raise SystemExit(1)


# --------------------------------------------------
# Save GeoTIFF
# --------------------------------------------------
output_file.write_bytes(response.content)

print("\nCOP30 DEM downloaded successfully!")
print(f"Saved to: {output_file}")
print(f"File size: {output_file.stat().st_size / (1024 * 1024):.2f} MB")