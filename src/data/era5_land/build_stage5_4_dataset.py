"""Build the Stage 5.4 ERA5-Land spatial rainfall proof of concept.

This script requests only the four November 2021 target hours, then maps the
native ERA5-Land field to the existing 250 m model-cell centroids by nearest
native rainfall cell. The mapped value remains explicitly labelled as an
approximately 9 km ERA5-Land forcing value; it is not a 250 m observation.

Prerequisites:
    pip install cdsapi netCDF4
    Configure the CDS API using the official account/token workflow:
    https://cds.climate.copernicus.eu/how-to-api

Run:
    python src/data/era5_land/build_stage5_4_dataset.py

The script does not modify AI #1, AI #2, models, or existing datasets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[3]
GRID_PATH = REPO_ROOT / "data/processed/chennai_spatial_features_final.geojson"
STUDY_AREA_PATH = REPO_ROOT / "data/processed/chennai_cmr_study_area.geojson"
OUTPUT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall"
DOWNLOAD_PATH = OUTPUT_DIR / "era5_land_november_2021.nc"
CSV_PATH = OUTPUT_DIR / "era5_land_spatial_rainfall.csv"
GEOJSON_PATH = OUTPUT_DIR / "era5_land_spatial_rainfall.geojson"
METADATA_PATH = OUTPUT_DIR / "metadata.json"

TARGET_TIMESTAMPS_UTC = pd.to_datetime(
    [
        "2021-11-08 23:00:00",
        "2021-11-10 11:00:00",
        "2021-11-10 18:00:00",
        "2021-11-12 00:00:00",
    ],
    utc=True,
)

VARIABLE = "total_precipitation"
SOURCE_RESOLUTION = "ERA5-Land native approximately 0.1 degree / approximately 9 km"
MODEL_CRS = "EPSG:4326"


def load_grid() -> gpd.GeoDataFrame:
    grid = gpd.read_file(GRID_PATH)
    required = {"cell_id", "centroid_lon", "centroid_lat", "geometry"}
    missing = required.difference(grid.columns)
    if missing:
        raise ValueError(f"Model grid is missing required columns: {sorted(missing)}")
    if grid.crs is None:
        raise ValueError("Model grid has no CRS.")
    if grid.crs.to_string() != MODEL_CRS:
        grid = grid.to_crs(MODEL_CRS)
    if not grid["cell_id"].is_unique:
        raise ValueError("Model grid has duplicate cell_id values.")
    return grid


def request_era5_land() -> None:
    """Request only the four target hours from CDS; never requests a global file."""
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError(
            "cdsapi is required. Install it in .venv and configure CDS credentials "
            "before running this acquisition step."
        ) from exc

    grid = load_grid()
    west, south, east, north = grid.total_bounds
    # Expand to native 0.1-degree cell centers so edge model cells are covered.
    west = math.floor(west * 10) / 10
    south = math.floor(south * 10) / 10
    east = math.ceil(east * 10) / 10
    north = math.ceil(north * 10) / 10
    dates = sorted({timestamp.strftime("%Y-%m-%d") for timestamp in TARGET_TIMESTAMPS_UTC})
    times = sorted({timestamp.strftime("%H:00") for timestamp in TARGET_TIMESTAMPS_UTC})
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        client = cdsapi.Client()
    except Exception as exc:
        raise RuntimeError(
            "CDS API credentials are not configured. Create the official "
            "~/.cdsapirc configuration before running this acquisition step. "
            "No ERA5-Land request was submitted."
        ) from exc
    client.retrieve(
        "reanalysis-era5-land",
        {
            "variable": [VARIABLE],
            "year": ["2021"],
            "month": ["11"],
            "day": [date[-2:] for date in dates],
            "time": times,
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [float(north), float(west), float(south), float(east)],
        },
        str(DOWNLOAD_PATH),
    )


def find_coordinate(dataset: xr.Dataset, names: tuple[str, ...]) -> str:
    for name in names:
        if name in dataset.coords:
            return name
    raise ValueError(f"Could not find any coordinate named {names} in {list(dataset.coords)}")


def canonicalize_time_coordinate(rainfall: xr.DataArray, time_name: str) -> xr.DataArray:
    """Canonicalize decoded dataset times as exact UTC hour labels."""
    if time_name != "time":
        rainfall = rainfall.rename({time_name: "time"})

    actual_utc = pd.DatetimeIndex(pd.to_datetime(rainfall["time"].values, utc=True))
    if actual_utc.has_duplicates:
        raise ValueError("Downloaded ERA5-Land time coordinate contains duplicates.")
    missing = TARGET_TIMESTAMPS_UTC.difference(actual_utc)
    if not missing.empty:
        missing_text = ", ".join(timestamp.isoformat() for timestamp in missing)
        raise ValueError(f"Downloaded ERA5-Land data is missing exact UTC targets: {missing_text}")

    # NetCDF datetime coordinates are timezone-naive after decoding. Keep their
    # exact UTC instant and make the timezone convention explicit in metadata.
    rainfall = rainfall.assign_coords(time=actual_utc.tz_localize(None).to_numpy())
    rainfall["time"].attrs = {"standard_name": "time", "timezone": "UTC"}
    return rainfall


def build_dataset() -> pd.DataFrame:
    if not DOWNLOAD_PATH.exists():
        request_era5_land()

    grid = load_grid()
    with xr.open_dataset(DOWNLOAD_PATH) as dataset:
        variable_name = VARIABLE if VARIABLE in dataset.data_vars else next(iter(dataset.data_vars))
        latitude_name = find_coordinate(dataset, ("latitude", "lat"))
        longitude_name = find_coordinate(dataset, ("longitude", "lon"))
        time_name = find_coordinate(dataset, ("time", "valid_time"))
        rainfall = dataset[variable_name]
        rainfall = canonicalize_time_coordinate(rainfall, time_name)
        rainfall = rainfall.sel(
            time=TARGET_TIMESTAMPS_UTC.tz_localize(None), method=None
        )
        grid_lats = grid["centroid_lat"].to_numpy()
        grid_lons = grid["centroid_lon"].to_numpy()
        if (
            grid_lats.min() < float(rainfall[latitude_name].min())
            or grid_lats.max() > float(rainfall[latitude_name].max())
            or grid_lons.min() < float(rainfall[longitude_name].min())
            or grid_lons.max() > float(rainfall[longitude_name].max())
        ):
            raise ValueError(
                "Downloaded ERA5-Land spatial extent does not cover every model-grid centroid."
            )
        rainfall = rainfall.transpose("time", latitude_name, longitude_name)
        native_values = rainfall.to_numpy()
        native_latitudes = rainfall[latitude_name].to_numpy()
        native_longitudes = rainfall[longitude_name].to_numpy()
        valid_native = np.isfinite(native_values).all(axis=0)
        if not valid_native.any():
            raise ValueError("No finite ERA5-Land native cells cover all target hours.")
        native_lat_grid, native_lon_grid = np.meshgrid(
            native_latitudes, native_longitudes, indexing="ij"
        )
        valid_indices = np.flatnonzero(valid_native.ravel())
        valid_latitudes = native_lat_grid.ravel()[valid_indices]
        valid_longitudes = native_lon_grid.ravel()[valid_indices]
        distance = (
            (valid_latitudes[:, None] - grid_lats[None, :]) ** 2
            + (valid_longitudes[:, None] - grid_lons[None, :]) ** 2
        )
        nearest_valid = valid_indices[np.argmin(distance, axis=0)]
        values = native_values.reshape(native_values.shape[0], -1)[:, nearest_valid]
        times = pd.to_datetime(rainfall["time"].to_numpy(), utc=True)

    # CDS total precipitation is metres of water equivalent; expose millimetres.
    values_mm = np.asarray(values, dtype=float) * 1000.0
    rows = []
    for time_index, timestamp in enumerate(times):
        frame = grid[["cell_id", "centroid_lon", "centroid_lat"]].copy()
        frame["timestamp"] = timestamp
        frame["rainfall"] = values_mm[time_index]
        frame["source"] = "ERA5-Land"
        frame["source_resolution"] = SOURCE_RESOLUTION
        rows.append(frame)
    output = pd.concat(rows, ignore_index=True)
    validate_output(output, grid)
    return output


def validate_output(output: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    key = ["cell_id", "timestamp"]
    if len(output) != len(grid) * len(TARGET_TIMESTAMPS_UTC):
        raise ValueError(f"Unexpected row count: {len(output)}")
    if output.duplicated(key).any():
        raise ValueError("Duplicate cell_id + timestamp rows found.")
    if output["rainfall"].isna().any() or not np.isfinite(output["rainfall"]).all():
        raise ValueError("Rainfall contains missing or non-finite values.")
    if (output["rainfall"] < 0).any():
        raise ValueError("Rainfall contains negative values.")
    if output["timestamp"].nunique() != len(TARGET_TIMESTAMPS_UTC):
        raise ValueError("Unexpected timestamp coverage.")
    if output["cell_id"].nunique() != grid["cell_id"].nunique():
        raise ValueError("Output does not cover every model cell.")
    spatial_counts = output.groupby("timestamp")["rainfall"].nunique()
    if (spatial_counts < 2).any():
        raise ValueError("At least one rainfall field is spatially constant.")


def write_outputs(output: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(CSV_PATH, index=False)
    if not GEOJSON_PATH.exists():
        grid = load_grid()[["cell_id", "geometry"]]
        geometry = grid.merge(output, on="cell_id", validate="one_to_many")
        geometry = gpd.GeoDataFrame(geometry, geometry="geometry", crs=MODEL_CRS)
        geometry.to_file(GEOJSON_PATH, driver="GeoJSON")

    summary = output.groupby("timestamp")["rainfall"].agg(
        ["min", "max", "mean", "median", "std", "nunique"]
    )
    summary["coefficient_of_variation"] = summary["std"] / summary["mean"].replace(0, np.nan)
    with xr.open_dataset(DOWNLOAD_PATH) as dataset:
        variable_name = VARIABLE if VARIABLE in dataset.data_vars else next(iter(dataset.data_vars))
        time_name = find_coordinate(dataset, ("time", "valid_time"))
        native_rainfall = canonicalize_time_coordinate(dataset[variable_name], time_name)
        native_rainfall = native_rainfall.sel(
            time=TARGET_TIMESTAMPS_UTC.tz_localize(None), method=None
        )
        native_missing_cells = int(
            (~np.isfinite(native_rainfall.to_numpy()).all(axis=0)).sum()
        )
    metadata = {
        "stage": "5.4",
        "source": "ERA5-Land",
        "variable": VARIABLE,
        "units": "mm per hourly interval after conversion from CDS metres of water equivalent",
        "source_resolution": SOURCE_RESOLUTION,
        "model_grid": "existing 250 m grid; rainfall values are nearest-native-cell forcing values, not 250 m observations",
        "mapping_method": "nearest finite native ERA5-Land cell; missing native cells are not imputed as zero",
        "native_grid_dimensions": {
            "latitude": int(dataset.sizes["latitude"] if "latitude" in dataset.sizes else dataset.sizes["lat"]),
            "longitude": int(dataset.sizes["longitude"] if "longitude" in dataset.sizes else dataset.sizes["lon"]),
        },
        "native_missing_cells": native_missing_cells,
        "crs": MODEL_CRS,
        "timestamps_utc": [timestamp.isoformat() for timestamp in TARGET_TIMESTAMPS_UTC],
        "n_cells": int(output["cell_id"].nunique()),
        "n_rows": int(len(output)),
        "spatial_summary": json.loads(summary.reset_index().to_json(orient="records", date_format="iso")),
        "comparison_scope": "consistency check only; not accuracy validation",
        "outputs": [str(path.relative_to(REPO_ROOT)) for path in (CSV_PATH, GEOJSON_PATH)],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    output = build_dataset()
    write_outputs(output)
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {GEOJSON_PATH}")
    print(f"Wrote {METADATA_PATH}")
    print(f"rows={len(output):,}; cells={output['cell_id'].nunique():,}; timestamps={output['timestamp'].nunique()}")


if __name__ == "__main__":
    main()
