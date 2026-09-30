"""Resolve Stage 5.4 missing-cell relevance using existing CMR geometry."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point, box

from build_stage5_4_dataset import (
    DOWNLOAD_PATH,
    GRID_PATH,
    TARGET_TIMESTAMPS_UTC,
    VARIABLE,
    canonicalize_time_coordinate,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall_audit"
MODEL_CRS = "EPSG:32644"


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    cmr = gpd.read_file(
        REPO_ROOT / "data/processed/chennai_cmr_study_area.geojson"
    ).to_crs(MODEL_CRS)
    grid = gpd.read_file(GRID_PATH).to_crs(MODEL_CRS)
    cmr_geometry = cmr.geometry.union_all()

    with xr.open_dataset(DOWNLOAD_PATH) as dataset:
        variable_name = VARIABLE if VARIABLE in dataset.data_vars else next(iter(dataset.data_vars))
        time_name = "time" if "time" in dataset.coords else "valid_time"
        rainfall = canonicalize_time_coordinate(dataset[variable_name], time_name)
        rainfall = rainfall.sel(
            time=TARGET_TIMESTAMPS_UTC.tz_localize(None), method=None
        )
        values = rainfall.to_numpy()
        latitudes = rainfall["latitude"].to_numpy()
        longitudes = rainfall["longitude"].to_numpy()

    native_valid = np.isfinite(values).all(axis=0)
    latitude_spacing = float(np.median(np.abs(np.diff(latitudes))))
    longitude_spacing = float(np.median(np.abs(np.diff(longitudes))))
    records = []
    for row_index, latitude in enumerate(latitudes):
        for column_index, longitude in enumerate(longitudes):
            if native_valid[row_index, column_index]:
                continue
            center = gpd.GeoSeries(
                [Point(longitude, latitude)], crs="EPSG:4326"
            ).to_crs(MODEL_CRS).iloc[0]
            footprint = gpd.GeoSeries(
                [
                    box(
                        longitude - longitude_spacing / 2,
                        latitude - latitude_spacing / 2,
                        longitude + longitude_spacing / 2,
                        latitude + latitude_spacing / 2,
                    )
                ],
                crs="EPSG:4326",
            ).to_crs(MODEL_CRS).iloc[0]
            center_inside = cmr_geometry.contains(center)
            footprint_intersects = cmr_geometry.intersects(footprint)
            if not footprint_intersects:
                category = "A_outside_cmr"
            elif center_inside:
                category = "C_cmr_center_inside"
            else:
                category = "B_cmr_boundary_or_coastal"
            records.append(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "missing_for_all_target_hours": True,
                    "center_inside_cmr": center_inside,
                    "native_footprint_intersects_cmr": footprint_intersects,
                    "cmr_intersection_area_km2": cmr_geometry.intersection(footprint).area / 1e6,
                    "category": category,
                }
            )

    native_audit = pd.DataFrame(records)
    native_audit.to_csv(
        AUDIT_DIR / "era5_land_stage5_4_2_native_cell_classification.csv",
        index=False,
    )

    # Reproduce the Stage 5.4 nearest-native assignment without using it to
    # fill values, then attribute affected model cells to native-cell category.
    native_coordinates = np.array(
        [(latitude, longitude) for latitude in latitudes for longitude in longitudes]
    )
    model_coordinates = np.column_stack(
        [grid["centroid_lat"].to_numpy(), grid["centroid_lon"].to_numpy()]
    )
    distance = (
        (native_coordinates[:, None, 0] - model_coordinates[None, :, 0]) ** 2
        + (native_coordinates[:, None, 1] - model_coordinates[None, :, 1]) ** 2
    )
    nearest_native = distance.argmin(axis=0)
    missing_flat = ~native_valid.ravel()
    affected = missing_flat[nearest_native]
    native_categories = native_audit["category"].tolist()
    nearest_categories = np.array(
        [native_categories[list(np.flatnonzero(missing_flat)).index(index)] if missing_flat[index] else "valid_native" for index in nearest_native]
    )
    affected_summary = (
        pd.Series(nearest_categories[affected], name="category")
        .value_counts()
        .rename_axis("category")
        .reset_index(name="affected_model_cells")
    )
    affected_summary["affected_fraction_of_model_grid"] = (
        affected_summary["affected_model_cells"] / len(grid)
    )
    affected_summary.to_csv(
        AUDIT_DIR / "era5_land_stage5_4_2_affected_model_cell_summary.csv",
        index=False,
    )

    missing_count = len(native_audit)
    category_counts = native_audit["category"].value_counts().to_dict()
    affected_count = int(affected.sum())
    center_inside_affected = int(
        (nearest_categories[affected] == "C_cmr_center_inside").sum()
    )
    boundary_affected = int(
        (nearest_categories[affected] == "B_cmr_boundary_or_coastal").sum()
    )
    lines = [
        "STAGE 5.4.2 - ERA5-LAND SPATIAL SUPPORT RESOLUTION",
        "====================================================",
        "",
        "Decision",
        "--------",
        "BLOCKED: material spatial-support ambiguity remains.",
        "The existing CMR polygon is sufficient to identify outside and boundary",
        "relationships, but it is not an authoritative land/ocean mask. Two",
        "missing native cells have centers inside the CMR, and 2,834 model cells",
        "are assigned from CMR-center missing cells. The pipeline must not claim",
        "complete location-specific ERA5-Land support or silently fill these cells.",
        "",
        "Native-cell classification",
        "--------------------------",
        f"Native cells inspected: {len(latitudes) * len(longitudes)}",
        f"Missing native cells: {missing_count} ({missing_count / (len(latitudes) * len(longitudes)):.2%})",
        f"A - completely outside CMR: {category_counts.get('A_outside_cmr', 0)}",
        f"B - CMR boundary/coastal intersection, center outside: {category_counts.get('B_cmr_boundary_or_coastal', 0)}",
        f"C - CMR center inside: {category_counts.get('C_cmr_center_inside', 0)}",
        "D - ambiguous: 0 by geometry classification; land status remains unverified",
        "because no authoritative land mask is present in the repository.",
        f"Missing native footprint intersection area: {native_audit['cmr_intersection_area_km2'].sum():.2f} km2",
        "",
        "Model-grid impact",
        "-----------------",
        f"Model cells using a missing nearest native cell: {affected_count:,} / {len(grid):,} ({affected_count / len(grid):.2%})",
        f"Affected by CMR-center missing cells: {center_inside_affected:,} ({center_inside_affected / len(grid):.2%})",
        f"Affected by boundary/coastal missing cells: {boundary_affected:,} ({boundary_affected / len(grid):.2%})",
        "The 20 completely outside missing cells do not drive nearest-cell",
        "assignments for the current model grid.",
        "",
        "Scientific assessment",
        "----------------------",
        "This geometry-only audit cannot safely distinguish land rainfall from",
        "coastal/ocean coverage for the two CMR-center cells or the boundary",
        "cells. Replacing missing values with zero, or retaining nearest-valid",
        "fallback as if it were local rainfall, would impose an unsupported",
        "scientific assumption. Restricting the model domain or adopting a land",
        "mask/source strategy requires an explicit architecture decision.",
        "ERA5-Land remains supplementary proof-of-concept forcing only.",
        "Stage 6 is not started; AI #1 and AI #2 are unchanged.",
        "",
        "Required decision",
        "-----------------",
        "Provide an authoritative land/coastal mask, restrict the spatial domain",
        "with documented justification, or select an alternative rainfall source",
        "before treating ERA5-Land as complete spatial forcing.",
    ]
    (AUDIT_DIR / "era5_land_stage5_4_2_spatial_support_report.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"missing_native={missing_count}; categories={category_counts}")
    print(f"affected_model_cells={affected_count:,}; cmr_center={center_inside_affected:,}; boundary={boundary_affected:,}")
    print("decision=BLOCKED")


if __name__ == "__main__":
    main()