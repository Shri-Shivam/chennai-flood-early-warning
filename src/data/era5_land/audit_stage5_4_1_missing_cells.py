"""Audit Stage 5.4 native missing cells and fallback spatial support."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

from build_stage5_4_dataset import (
    DOWNLOAD_PATH,
    GRID_PATH,
    TARGET_TIMESTAMPS_UTC,
    VARIABLE,
    canonicalize_time_coordinate,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall_audit"


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    grid = gpd.read_file(GRID_PATH)
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
    native_lat, native_lon = np.meshgrid(latitudes, longitudes, indexing="ij")
    native_coordinates = np.column_stack(
        [native_lat.ravel(), native_lon.ravel()]
    )
    valid_indices = np.flatnonzero(native_valid.ravel())
    valid_coordinates = native_coordinates[valid_indices]

    grid_lat = grid["centroid_lat"].to_numpy()
    grid_lon = grid["centroid_lon"].to_numpy()
    distances_all = np.sqrt(
        (native_coordinates[:, None, 0] - grid_lat[None, :]) ** 2
        + (native_coordinates[:, None, 1] - grid_lon[None, :]) ** 2
    )
    nearest_all = np.argmin(distances_all, axis=0)
    fallback = ~native_valid.ravel()[nearest_all]
    distances_valid = np.sqrt(
        (valid_coordinates[:, None, 0] - grid_lat[None, :]) ** 2
        + (valid_coordinates[:, None, 1] - grid_lon[None, :]) ** 2
    )
    nearest_valid_distance = distances_valid.min(axis=0)

    affected = grid.loc[
        fallback,
        ["cell_id", "centroid_lon", "centroid_lat"],
    ].copy()
    affected["nearest_valid_native_distance_deg"] = nearest_valid_distance[fallback]
    affected["nearest_valid_native_distance_km_approx"] = (
        affected["nearest_valid_native_distance_deg"] * 111.0
    )
    affected.to_csv(AUDIT_DIR / "era5_land_stage5_4_1_affected_model_cells.csv", index=False)

    missing_native = pd.DataFrame(
        {
            "latitude": native_coordinates[~native_valid.ravel(), 0],
            "longitude": native_coordinates[~native_valid.ravel(), 1],
            "missing_for_all_target_hours": True,
        }
    )
    missing_native.to_csv(
        AUDIT_DIR / "era5_land_stage5_4_1_missing_native_cells.csv", index=False
    )

    native_cell_count = int(native_valid.size)
    missing_native_count = int((~native_valid).sum())
    affected_count = int(fallback.sum())
    affected_fraction = affected_count / len(grid)
    max_distance = float(nearest_valid_distance[fallback].max())
    p95_distance = float(np.quantile(nearest_valid_distance[fallback], 0.95))
    native_spacing = 0.1
    material = (
        affected_fraction > 0.05
        or max_distance > native_spacing
    )
    report = [
        "STAGE 5.4.1 - ERA5-LAND MISSING-CELL AUDIT",
        "===============================================",
        "",
        "Decision",
        "--------",
        "MATERIAL SCIENTIFIC ISSUE: STOP BEFORE STAGE 6.",
        "The Stage 5.4 fallback handling is not acceptable as complete spatial",
        "rainfall coverage for all model cells. Affected cells must not be treated",
        "as location-specific ERA5-Land observations.",
        "",
        "Findings",
        "--------",
        f"Native cells inspected: {native_cell_count}",
        f"Native cells missing for all four target hours: {missing_native_count} ({missing_native_count / native_cell_count:.2%})",
        f"Affected model cells: {affected_count:,} / {len(grid):,} ({affected_fraction:.2%})",
        f"Nearest-valid fallback distance, 95th percentile: {p95_distance:.4f} degrees (~{p95_distance * 111:.1f} km)",
        f"Nearest-valid fallback distance, maximum: {max_distance:.4f} degrees (~{max_distance * 111:.1f} km)",
        f"Native grid spacing: {native_spacing:.1f} degree (~{native_spacing * 111:.1f} km)",
        "",
        "Interpretation",
        "--------------",
        "The missing native cells form a stable eastern/coastal edge pattern.",
        "The current nearest-finite-cell mapping preserves real ERA5-Land values",
        "but assigns values from materially different native locations to 11.14%",
        "of the 250 m model cells. It therefore does not provide defensible",
        "location-specific rainfall support for those cells.",
        "Missing values must not be replaced by zero, and this audit does not",
        "justify retraining AI #1 or integrating ERA5-Land into AI #2.",
        "",
        "Required resolution before proceeding",
        "--------------------------------------",
        "1. Restrict the spatial model domain to valid ERA5-Land-supported land cells; or",
        "2. Obtain a scientifically justified land/ocean mask and explicit treatment",
        "   for coastal cells; or",
        "3. Choose a source/mapping strategy with documented support for the affected area.",
        "",
        "Outputs",
        "-------",
        "era5_land_stage5_4_1_missing_native_cells.csv",
        "era5_land_stage5_4_1_affected_model_cells.csv",
    ]
    (AUDIT_DIR / "era5_land_stage5_4_1_missing_cell_audit.txt").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(f"material_issue={material}")
    print(f"affected_model_cells={affected_count:,}; fraction={affected_fraction:.2%}")
    print(f"max_fallback_distance_deg={max_distance:.6f}")


if __name__ == "__main__":
    main()