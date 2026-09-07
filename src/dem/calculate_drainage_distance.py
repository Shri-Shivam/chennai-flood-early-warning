from pathlib import Path

import geopandas as gpd
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRID_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "chennai_250m_spatial_features.geojson"
)

DRAINAGE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "chennai_drainage.geojson"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "chennai_spatial_features_final.geojson"
)


# ============================================================
# LOAD GRID
# ============================================================

print("=" * 60)
print("STEP 1 — Loading 250m grid")
print("=" * 60)

grid = gpd.read_file(GRID_PATH)

print(f"Grid cells: {len(grid):,}")
print("Grid CRS:", grid.crs)


# ============================================================
# LOAD DRAINAGE
# ============================================================

print("\n" + "=" * 60)
print("STEP 2 — Loading drainage network")
print("=" * 60)

drainage = gpd.read_file(DRAINAGE_PATH)

print(f"Drainage features: {len(drainage):,}")
print("Drainage CRS:", drainage.crs)


# ============================================================
# PROJECT BOTH TO METRES
# ============================================================

print("\n" + "=" * 60)
print("STEP 3 — Projecting to EPSG:32644")
print("=" * 60)

grid = grid.to_crs("EPSG:32644")
drainage = drainage.to_crs("EPSG:32644")


# ============================================================
# MERGE DRAINAGE INTO ONE GEOMETRY
# ============================================================

print("\n" + "=" * 60)
print("STEP 4 — Preparing drainage network")
print("=" * 60)

drainage = drainage[
    ~drainage.geometry.is_empty
].copy()

drainage = drainage[
    drainage.geometry.notna()
].copy()

drainage_union = drainage.geometry.union_all()

print("Drainage network prepared.")


# ============================================================
# CALCULATE CENTROID → NEAREST DRAINAGE DISTANCE
# ============================================================

print("\n" + "=" * 60)
print("STEP 5 — Calculating distance to drainage")
print("=" * 60)

centroids = grid.geometry.centroid

# ------------------------------------------------------------
# Spatial index nearest-neighbour query
# ------------------------------------------------------------

nearest_indices = drainage.sindex.nearest(
    centroids,
    return_all=False
)

# Depending on GeoPandas version, nearest() returns
# an array shaped (2, number_of_points).
source_indices = nearest_indices[0]
drainage_indices = nearest_indices[1]

distances = []

for source_idx, drainage_idx in zip(
    source_indices,
    drainage_indices
):

    point = centroids.iloc[source_idx]
    nearest_line = drainage.geometry.iloc[drainage_idx]

    distance = point.distance(nearest_line)

    distances.append(distance)


# ============================================================
# STORE DISTANCE
# ============================================================

grid["distance_to_drainage"] = np.array(
    distances,
    dtype="float32"
)


# ============================================================
# QUALITY CHECK
# ============================================================

print("\n" + "=" * 60)
print("STEP 6 — Quality checks")
print("=" * 60)

print(
    "Missing distances:",
    grid["distance_to_drainage"].isna().sum()
)

print(
    "Minimum distance:",
    grid["distance_to_drainage"].min(),
    "m"
)

print(
    "Maximum distance:",
    grid["distance_to_drainage"].max(),
    "m"
)

print(
    "Mean distance:",
    grid["distance_to_drainage"].mean(),
    "m"
)

print(
    "Median distance:",
    grid["distance_to_drainage"].median(),
    "m"
)


# ============================================================
# SAVE FINAL SPATIAL DATASET
# ============================================================

print("\n" + "=" * 60)
print("STEP 7 — Saving final spatial features")
print("=" * 60)

grid_output = grid.to_crs("EPSG:4326")

grid_output.to_file(
    OUTPUT_PATH,
    driver="GeoJSON"
)

print("\nSUCCESS!")
print(f"Cells: {len(grid_output):,}")
print(f"Output: {OUTPUT_PATH}")

print("\nFinal columns:")

for column in grid_output.columns:
    print(" -", column)