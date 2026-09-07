from pathlib import Path

import geopandas as gpd
import osmnx as ox


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STUDY_AREA = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "chennai_cmr_study_area.geojson"
)

OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "chennai_drainage.geojson"
)


# --------------------------------------------------
# Load CMR boundary
# --------------------------------------------------

study_area = gpd.read_file(STUDY_AREA)

# OSMnx works with WGS84 coordinates
study_area = study_area.to_crs("EPSG:4326")

# Combine all polygons into one geometry
cmr_polygon = study_area.geometry.union_all()

print("CMR boundary loaded.")
print("Downloading OSM waterways...")


# --------------------------------------------------
# Download waterways from OpenStreetMap
# --------------------------------------------------

tags = {
    "waterway": [
        "river",
        "stream",
        "canal",
        "drain",
        "ditch"
    ]
}

waterways = ox.features_from_polygon(
    cmr_polygon,
    tags
)


# --------------------------------------------------
# Keep line features
# --------------------------------------------------

waterways = waterways[
    waterways.geometry.geom_type.isin(
        ["LineString", "MultiLineString"]
    )
].copy()

print(f"Waterway features found: {len(waterways):,}")


# --------------------------------------------------
# Remove duplicate geometries
# --------------------------------------------------

waterways = waterways.drop_duplicates(
    subset="geometry"
)

# Keep only geometry column
waterways = waterways[["geometry"]].copy()


# --------------------------------------------------
# Save
# --------------------------------------------------

waterways.to_file(
    OUTPUT,
    driver="GeoJSON"
)

print("\nSUCCESS!")
print(f"Drainage features: {len(waterways):,}")
print(f"Saved to: {OUTPUT}")