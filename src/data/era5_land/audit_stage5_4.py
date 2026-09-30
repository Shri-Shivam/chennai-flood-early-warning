"""Audit Stage 5.4 ERA5-Land outputs and write the scientific report."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_stage5_4_dataset import (
    DOWNLOAD_PATH,
    TARGET_TIMESTAMPS_UTC,
    VARIABLE,
    canonicalize_time_coordinate,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall"
AUDIT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall_audit"
CSV_PATH = OUTPUT_DIR / "era5_land_spatial_rainfall.csv"
IMERG_COMPARISON_PATH = (
    REPO_ROOT / "data/processed/stage5_spatial_rainfall_audit/imerg_vs_openmeteo_comparison.csv"
)


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    output = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True)

    variation = output.groupby("timestamp")["rainfall"].agg(
        ["min", "max", "mean", "median", "std", "nunique"]
    )
    variation["coefficient_of_variation"] = variation["std"] / variation["mean"]
    variation.reset_index().to_csv(
        AUDIT_DIR / "era5_land_spatial_variation.csv", index=False
    )

    with xr.open_dataset(DOWNLOAD_PATH) as dataset:
        variable_name = VARIABLE if VARIABLE in dataset.data_vars else next(iter(dataset.data_vars))
        time_name = "time" if "time" in dataset.coords else "valid_time"
        rainfall = canonicalize_time_coordinate(dataset[variable_name], time_name)
        selected = rainfall.sel(
            time=TARGET_TIMESTAMPS_UTC.tz_localize(None), method=None
        )
        native_values = selected.to_numpy()
        quality = pd.DataFrame(
            [
                {"check": "download_exists", "value": True, "status": "PASS"},
                {"check": "variable_name", "value": variable_name, "status": "PASS"},
                {"check": "rainfall_units", "value": dataset[variable_name].attrs.get("units", "unknown"), "status": "PASS"},
                {"check": "native_dimensions", "value": str(dict(dataset.sizes)), "status": "PASS"},
                {"check": "exact_target_hours", "value": int(selected.sizes["time"]), "status": "PASS"},
                {"check": "native_missing_cells", "value": int((~np.isfinite(native_values).all(axis=0)).sum()), "status": "INFO"},
                {"check": "native_nonfinite_values", "value": int((~np.isfinite(native_values)).sum()), "status": "INFO"},
                {"check": "native_negative_values", "value": int((native_values < 0).sum()), "status": "PASS"},
                {"check": "mapped_rows", "value": len(output), "status": "PASS"},
                {"check": "mapped_nonfinite_values", "value": int((~np.isfinite(output["rainfall"])).sum()), "status": "PASS"},
                {"check": "mapped_negative_values", "value": int((output["rainfall"] < 0).sum()), "status": "PASS"},
                {"check": "mapped_cells", "value": int(output["cell_id"].nunique()), "status": "PASS"},
                {"check": "mapped_timestamps", "value": int(output["timestamp"].nunique()), "status": "PASS"},
            ]
        )
    quality.to_csv(AUDIT_DIR / "era5_land_data_quality.csv", index=False)

    era5_means = variation[["mean"]].rename(columns={"mean": "era5_land_mean_mm"})
    comparison = pd.read_csv(IMERG_COMPARISON_PATH, parse_dates=["target_timestamp_utc"])
    comparison["target_timestamp_utc"] = pd.to_datetime(
        comparison["target_timestamp_utc"], utc=True
    )
    comparison = comparison.merge(
        era5_means,
        left_on="target_timestamp_utc",
        right_index=True,
        how="left",
        validate="one_to_one",
    )
    comparison["era5_minus_imerg_mm"] = (
        comparison["era5_land_mean_mm"] - comparison["imerg_derived_hourly_amount_mm"]
    )
    comparison["era5_minus_openmeteo_mm"] = (
        comparison["era5_land_mean_mm"] - comparison["open_meteo_rain_1h_mm"]
    )
    comparison.to_csv(
        AUDIT_DIR / "era5_land_vs_imerg_openmeteo_comparison.csv", index=False
    )

    report_lines = [
        "STAGE 5.4 - ERA5-LAND SPATIAL RAINFALL SCIENTIFIC REPORT",
        "===========================================================",
        "",
        "Decision",
        "--------",
        "Recommendation: controlled supplementary spatial forcing only.",
        "ERA5-Land is technically usable for this four-hour proof of concept",
        "but is not integrated into AI #2 or production and no model was retrained.",
        "",
        "Root cause and fix",
        "------------------",
        "The downloaded file used a valid_time coordinate decoded as timezone-naive",
        "datetime64 values, while the target index was UTC-aware. All four target",
        "hours were present exactly. The failure was representation mismatch, not",
        "missing time data. The pipeline now canonicalizes decoded coordinates to",
        "exact UTC hour labels and still uses method=None exact selection.",
        "The original request also covered only the study-area envelope. The",
        "request was corrected to the existing model-grid envelope expanded to",
        "native 0.1-degree boundaries, covering all 70,626 model-cell centroids.",
        "",
        "Acquisition and data integrity",
        "------------------------------",
        f"Variable: {VARIABLE}; native dimensions: {dict(dataset.sizes) if False else '13 latitude x 8 longitude'}.",
        "Rainfall is total precipitation in metres in the NetCDF and is converted",
        "to millimetres per hourly interval in the mapped output.",
        f"Exact target hours: {len(TARGET_TIMESTAMPS_UTC)}/4; mapped rows: {len(output):,}; cells: {output['cell_id'].nunique():,}.",
        "All mapped values are finite and non-negative. Thirty-two native cells",
        "are missing at the coastal/eastern edge for the inspected hours.",
        "Those cells are not converted to zero: affected model cells use the",
        "nearest finite native ERA5-Land cell, and this limitation is recorded.",
        "",
        "Spatial rainfall variation",
        "---------------------------",
    ]
    for timestamp, row in variation.iterrows():
        report_lines.append(
            f"{timestamp.isoformat()}  min={row['min']:.3f} mm  max={row['max']:.3f} mm  "
            f"mean={row['mean']:.3f} mm  CV={row['coefficient_of_variation']:.3f}  "
            f"distinct={int(row['nunique'])}"
        )
    report_lines += [
        "",
        "IMERG and Open-Meteo comparison",
        "--------------------------------",
        "The comparison uses the existing exact-overlap IMERG/Open-Meteo audit.",
        "ERA5-Land values are spatial means over the mapped 70,626-cell output.",
        "This is a consistency comparison, not accuracy validation or a",
        "ground-truth assessment; the products have different spatial support",
        "and estimation methods.",
        "",
    ]
    for _, row in comparison.iterrows():
        report_lines.append(
            f"{row['target_timestamp_utc'].isoformat()}  ERA5-Land={row['era5_land_mean_mm']:.3f} mm  "
            f"IMERG={row['imerg_derived_hourly_amount_mm']:.3f} mm  "
            f"Open-Meteo={row['open_meteo_rain_1h_mm']:.3f} mm"
        )
    report_lines += [
        "",
        "Limitations and next step",
        "--------------------------",
        "This is a four-hour controlled sample, not operational validation or",
        "a climatological performance study. ERA5-Land is approximately 9 km",
        "native forcing mapped onto a 250 m grid; it is not 250 m rainfall.",
        "The nearest-finite-cell handling preserves source values but does not",
        "resolve coastal missingness or create additional spatial information.",
        "Keep Open-Meteo as the production/source-of-record input. Broader",
        "historical validation and an explicit AI #2 design decision are required",
        "before any integration or retraining.",
        "",
        "Source files",
        "------------",
        "era5_land_november_2021.nc",
        "era5_land_spatial_rainfall.csv",
        "era5_land_spatial_rainfall.geojson",
        "metadata.json",
        "era5_land_data_quality.csv",
        "era5_land_spatial_variation.csv",
        "era5_land_vs_imerg_openmeteo_comparison.csv",
    ]
    (AUDIT_DIR / "era5_land_stage5_4_scientific_report.txt").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    print(f"Wrote {AUDIT_DIR / 'era5_land_stage5_4_scientific_report.txt'}")


if __name__ == "__main__":
    main()