from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import box


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

STUDY_AREA = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "chennai_cmr_study_area.geojson"
)

DEM_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "chennai_cop30.tif"
)

OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "chennai_250m_spatial_features.geojson"
)


# ============================================================
# SETTINGS
# ============================================================

GRID_SIZE = 250

# UTM Zone 44N.
# This gives us coordinates in metres.
METRIC_CRS = "EPSG:32644"

# WGS84 latitude/longitude
OUTPUT_CRS = "EPSG:4326"


# ============================================================
# 1. LOAD STUDY AREA
# ============================================================

print("=" * 60)
print("STEP 1 — Loading Chennai study area")
print("=" * 60)

study_area = gpd.read_file(STUDY_AREA)

if study_area.empty:
    raise RuntimeError("Study area is empty.")

print("Original CRS:", study_area.crs)

# Project to metres
study_area = study_area.to_crs(METRIC_CRS)

study_geom = study_area.geometry.union_all()

print("Metric CRS:", study_area.crs)


# ============================================================
# 2. CREATE 250m GRID
# ============================================================

print("\n" + "=" * 60)
print("STEP 2 — Creating 250m × 250m grid")
print("=" * 60)

minx, miny, maxx, maxy = study_geom.bounds

x_values = np.arange(
    minx,
    maxx + GRID_SIZE,
    GRID_SIZE
)

y_values = np.arange(
    miny,
    maxy + GRID_SIZE,
    GRID_SIZE
)

cells = []

for x in x_values[:-1]:
    for y in y_values[:-1]:

        cell = box(
            x,
            y,
            x + GRID_SIZE,
            y + GRID_SIZE
        )

        # Keep cells whose CENTRE lies inside the CMR.
        if study_geom.contains(cell.centroid):
            cells.append(cell)

print(f"Grid cells: {len(cells):,}")

if len(cells) == 0:
    raise RuntimeError("No grid cells were created.")


grid = gpd.GeoDataFrame(
    geometry=cells,
    crs=METRIC_CRS
)

# Unique cell identifier
grid["cell_id"] = np.arange(len(grid))


# ============================================================
# 3. CALCULATE CENTROIDS
# ============================================================

print("\n" + "=" * 60)
print("STEP 3 — Calculating cell centroids")
print("=" * 60)

centroids = grid.geometry.centroid

grid["centroid_x"] = centroids.x
grid["centroid_y"] = centroids.y

# Convert centroids to latitude/longitude
centroid_gdf = gpd.GeoDataFrame(
    geometry=centroids,
    crs=METRIC_CRS
).to_crs(OUTPUT_CRS)

grid["centroid_lon"] = centroid_gdf.geometry.x
grid["centroid_lat"] = centroid_gdf.geometry.y


# ============================================================
# 4. LOAD COP30 DEM
# ============================================================

print("\n" + "=" * 60)
print("STEP 4 — Loading COP30 DEM")
print("=" * 60)

if not DEM_PATH.exists():
    raise FileNotFoundError(
        f"DEM not found: {DEM_PATH}"
    )

with rasterio.open(DEM_PATH) as dem:

    print("DEM CRS:", dem.crs)
    print("DEM resolution:", dem.res)
    print("DEM size:", dem.width, "×", dem.height)

    # Reproject grid into DEM CRS
    grid_dem_crs = grid.to_crs(dem.crs)

    # --------------------------------------------------------
    # Extract elevation at cell centres
    # --------------------------------------------------------

    print("\nExtracting elevation...")

    coordinates = [
        (point.x, point.y)
        for point in grid_dem_crs.geometry.centroid
    ]

    elevations = []

    for value in dem.sample(coordinates):
        elevation = float(value[0])

        if not np.isfinite(elevation):
            elevation = np.nan

        elevations.append(elevation)

    grid["elevation"] = elevations


# ============================================================
# 5. CALCULATE SLOPE
# ============================================================

print("\n" + "=" * 60)
print("STEP 5 — Calculating slope")
print("=" * 60)

with rasterio.open(DEM_PATH) as dem:

    # Read DEM
    elevation_array = dem.read(1).astype("float64")

    # Pixel dimensions in degrees because COP30 is EPSG:4326.
    pixel_width = abs(dem.transform.a)
    pixel_height = abs(dem.transform.e)

    # --------------------------------------------------------
    # Convert approximate degree resolution to metres.
    # At Chennai latitude:
    #   longitude degree ≈ 108 km
    #   latitude degree ≈ 111 km
    # --------------------------------------------------------

    mean_lat = (
        dem.bounds.bottom + dem.bounds.top
    ) / 2

    meters_per_degree_lat = 111320.0

    meters_per_degree_lon = (
        111320.0 * np.cos(np.radians(mean_lat))
    )

    dx = pixel_width * meters_per_degree_lon
    dy = pixel_height * meters_per_degree_lat

    print(f"DEM pixel size ≈ {dx:.2f}m × {dy:.2f}m")

    # --------------------------------------------------------
    # Gradient
    # --------------------------------------------------------

    gy, gx = np.gradient(
        elevation_array,
        dy,
        dx
    )

    # Slope in degrees
    slope_radians = np.arctan(
        np.sqrt(gx ** 2 + gy ** 2)
    )

    slope_degrees = np.degrees(
        slope_radians
    )

    # --------------------------------------------------------
    # Create temporary slope raster
    # --------------------------------------------------------

    slope_transform = dem.transform

    # Extract mean slope inside each 250m cell
    print("Extracting slope for each grid cell...")

    slope_values = []

    for geometry in grid_dem_crs.geometry:

        mask = geometry_mask(
            [geometry],
            transform=slope_transform,
            invert=True,
            out_shape=slope_degrees.shape
        )

        values = slope_degrees[mask]

        values = values[
            np.isfinite(values)
        ]

        if len(values) == 0:
            slope_values.append(np.nan)
        else:
            slope_values.append(
                float(np.mean(values))
            )

    grid["slope_degrees"] = slope_values


# ============================================================
# 6. QUALITY CHECK
# ============================================================

print("\n" + "=" * 60)
print("STEP 6 — Quality checks")
print("=" * 60)

print(
    "Elevation missing:",
    grid["elevation"].isna().sum()
)

print(
    "Slope missing:",
    grid["slope_degrees"].isna().sum()
)

print(
    "Elevation min:",
    grid["elevation"].min()
)

print(
    "Elevation max:",
    grid["elevation"].max()
)

print(
    "Elevation mean:",
    grid["elevation"].mean()
)

print(
    "Slope min:",
    grid["slope_degrees"].min()
)

print(
    "Slope max:",
    grid["slope_degrees"].max()
)

print(
    "Slope mean:",
    grid["slope_degrees"].mean()
)


# ============================================================
# 7. SAVE
# ============================================================

print("\n" + "=" * 60)
print("STEP 7 — Saving spatial feature dataset")
print("=" * 60)

# Save as WGS84 GeoJSON
output_grid = grid.to_crs(OUTPUT_CRS)

output_grid.to_file(
    OUTPUT,
    driver="GeoJSON"
)

print("\nSUCCESS!")
print(f"Cells: {len(output_grid):,}")
print(f"Output: {OUTPUT}")
print(f"CRS: {output_grid.crs}")

print("\nColumns:")
for column in output_grid.columns:
    print(" -", column)