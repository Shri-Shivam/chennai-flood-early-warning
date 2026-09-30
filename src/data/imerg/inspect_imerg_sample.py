"""
SIH26071 - STAGE 5.2
Spatial Rainfall Data Acquisition and Feasibility Test — GPM IMERG Final Run.

Purpose: determine whether NASA GPM IMERG V07B Final Run (GPM_3IMERGHH) is a
defensible spatial rainfall input candidate for a small controlled sample
around the verified Episode 1 flood period (2021-11-08 to 2021-11-12).

This script does NOT:
- modify AI #1 or AI #2
- retrain any model
- modify Stage 1-4 datasets, flood labels, or the 250m grid
- integrate IMERG into the ML dataset
- replace Open-Meteo

WHY THIS SCRIPT DID NOT RUN END-TO-END IN THE SANDBOX THAT WROTE IT:
Two independent blockers, both documented in stage5_spatial_rainfall_audit.txt:
  1. No NASA Earthdata Login credentials are available in that sandbox
     environment (no EARTHDATA_USERNAME/EARTHDATA_PASSWORD, no ~/.netrc).
  2. That sandbox's network egress is restricted to an allowlist that does
     NOT include NASA's servers (confirmed: HTTP 403, x-deny-reason:
     host_not_allowed, against urs.earthdata.nasa.gov and
     gpm1.gesdisc.eosdis.nasa.gov) — so even with credentials, download
     would fail there.
This script is written to run correctly in YOUR local environment, which has
neither restriction, once you've created a free Earthdata Login account.

SETUP (run locally):
    pip install earthaccess h5py xarray numpy pandas
    # optional, only needed for real CMR-polygon pixel intersection (item 4):
    pip install geopandas shapely
    # then either:
    earthaccess login          # interactive, saves to ~/.netrc
    # or set environment variables EARTHDATA_USERNAME / EARTHDATA_PASSWORD

RUN:
    python src/data/imerg/inspect_imerg_sample.py
"""

from __future__ import annotations

from pathlib import Path
from datetime import timedelta
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = REPO_ROOT / "data/raw/imerg"
OUT_DIR = REPO_ROOT / "data/processed/stage5_spatial_rainfall_audit"
RAINFALL_PATH = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
STUDY_AREA_PATH = REPO_ROOT / "data/processed/chennai_cmr_study_area.geojson"

# CMR bounding box (as supplied for Stage 5.2; matches chennai_cmr_study_area.geojson)
BBOX = {"west": 79.7306278, "east": 80.3465467, "south": 12.467462, "north": 13.5646282}

# Verified Episode 1 flood timestamps (UTC) — the actual test targets.
# NOTE: confirm whether project timestamps are IST or UTC before running —
# if IST, subtract 5:30 to get the UTC half-hour granule to request. This
# script assumes the timestamps below are already UTC; adjust TARGET_TIMESTAMPS
# if that assumption is wrong for your data. Do NOT silently guess — verify
# against src/data/create_rainfall_features.py / download_weather.py first.
TARGET_TIMESTAMPS_UTC = [
    "2021-11-08 23:00:00",
    "2021-11-10 11:00:00",
    "2021-11-10 18:00:00",
    "2021-11-12 00:00:00",
]

# rain_1h in the existing pipeline is the PREVIOUS 1 hour of rainfall
# (rolling(..., closed="left")), i.e. the hour ending at (not including) the
# target timestamp. To build a matching IMERG hourly amount for target t, we
# need the two half-hour periods starting at (t - 1:00:00) and (t - 0:30:00).
# This assumption is stated explicitly, not silently applied.
HALF_HOUR = timedelta(minutes=30)

SHORT_NAME = "GPM_3IMERGHH"
VERSION = "07"  # earthaccess/CMR version string; product is V07B Final Run

# Documented IMERG V07 fill value, used ONLY as an explicit fallback if a
# granule's own _FillValue attribute cannot be read (see read_fill_value()).
DOCUMENTED_FALLBACK_FILL_VALUE = -9999.9


def log(msg=""):
    print(msg)


def check_environment():
    """Fail loudly and specifically rather than silently falling back."""
    problems = []
    try:
        import earthaccess  # noqa: F401
    except ImportError:
        problems.append("earthaccess is not installed. Run: pip install earthaccess")
    try:
        import h5py  # noqa: F401
    except ImportError:
        problems.append("h5py is not installed. Run: pip install h5py")
    if problems:
        log("BLOCKED — missing dependencies:")
        for p in problems:
            log(f"  - {p}")
        sys.exit(1)


def authenticate():
    import earthaccess

    try:
        auth = earthaccess.login(
            strategy="netrc",
            persist=False,
        )
    except Exception as e:
        log(f"BLOCKED — Earthdata authentication raised an exception: {e}")
        log("Earthdata interactive authentication failed.")
        sys.exit(1)

    if not auth.authenticated:
        log("BLOCKED — Earthdata authentication failed.")
        sys.exit(1)

    log("Earthdata authentication successful.")
    return auth
# =====================================================================
# Required half-hour periods (item 1 + item 6)
# =====================================================================
def required_half_hours_for_target(target_ts_utc: str):
    """The two half-hour granule start times needed to build the previous-1h
    rainfall AMOUNT ending at target_ts_utc. Returns (half_a_start, half_b_start)
    in chronological order."""
    t = pd.Timestamp(target_ts_utc)
    half_a = t - timedelta(hours=1)       # e.g. 22:00 for a 23:00 target
    half_b = t - HALF_HOUR                # e.g. 22:30 for a 23:00 target
    return half_a, half_b


def build_required_half_hour_set():
    """Deduplicated set of every half-hour start needed across all targets,
    with a record of which target(s) each half-hour serves."""
    needed = {}  # half_hour_start -> set of target timestamps that need it
    for ts in TARGET_TIMESTAMPS_UTC:
        half_a, half_b = required_half_hours_for_target(ts)
        for h in (half_a, half_b):
            needed.setdefault(h, set()).add(ts)
    return needed


# =====================================================================
# Granule search / download (item 6 — explicit, no silent nearest-match)
# =====================================================================
def search_half_hour(half_hour_start: pd.Timestamp):
    """Search for the exact half-hourly Final Run granule starting at
    half_hour_start. Returns (results, actual_start, actual_end, matched_exact)."""
    import earthaccess
    window_end = half_hour_start + HALF_HOUR
    results = earthaccess.search_data(
        short_name=SHORT_NAME,
        version=VERSION,
        temporal=(half_hour_start.isoformat(), window_end.isoformat()),
        bounding_box=(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]),
    )
    exact_matches = []
    requested_start_utc = pd.Timestamp(half_hour_start)
    if requested_start_utc.tzinfo is None:
        requested_start_utc = requested_start_utc.tz_localize("UTC")

    if len(results) > 1:
        log("  CMR returned multiple temporally intersecting results; inspecting all:")

    for result_number, result in enumerate(results, start=1):
        metadata = result.get("meta", {})
        umm = result.get("umm", {})
        temporal_extent = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
        collection_reference = umm.get("CollectionReference", {})
        actual_start = None
        actual_end = None
        try:
            actual_start = pd.Timestamp(temporal_extent["BeginningDateTime"])
            actual_end = pd.Timestamp(temporal_extent["EndingDateTime"])
        except (KeyError, TypeError, ValueError):
            pass

        related_urls = umm.get("RelatedUrls", [])
        browse_urls = [
            url.get("URL")
            for url in related_urls
            if url.get("Type", "").lower() in {"browse", "browse image"}
            and url.get("URL")
        ]
        data_access_urls = [
            url.get("URL")
            for url in related_urls
            if url.get("Type", "").lower() in {
                "get data", "get data via direct access", "data access"
            }
            and url.get("URL")
        ]
        if len(results) > 1:
            log(f"    Result {result_number}:")
            log(f"      concept ID: {metadata.get('concept-id') or 'unavailable'}")
            log(f"      short name: {collection_reference.get('ShortName') or 'unavailable'}")
            log(f"      version: {collection_reference.get('Version') or 'unavailable'}")
            log(f"      title: {umm.get('EntryTitle') or metadata.get('title') or 'unavailable'}")
            log(f"      temporal beginning datetime: {temporal_extent.get('BeginningDateTime')}")
            log(f"      temporal ending datetime: {temporal_extent.get('EndingDateTime')}")
            log(f"      collection/version: {collection_reference or 'unavailable'}")
            log(f"      browse URL: {browse_urls or 'unavailable'}")
            log(f"      data access URL: {data_access_urls or 'unavailable'}")

        if actual_start is not None:
            actual_start_utc = actual_start.tz_convert("UTC") if actual_start.tzinfo else actual_start.tz_localize("UTC")
            if actual_start_utc == requested_start_utc:
                exact_matches.append((result, actual_start, actual_end))

    if len(exact_matches) == 1:
        selected_result, actual_start, actual_end = exact_matches[0]
        return [selected_result], actual_start, actual_end, True

    log(f"  BLOCKED: expected exactly one granule beginning at {half_hour_start}, "
        f"found {len(exact_matches)} exact-start granules among {len(results)} result(s).")
    return [], None, None, False


def download_sample():
    """Download exactly the half-hour granules required to build the 4 target
    hourly comparisons (item 1) — not a bulk archive. Returns:
      files_by_half_hour: {half_hour_start: local_filepath or None}
      coverage_records: list of dicts for imerg_temporal_coverage.csv (item 6)
    """
    check_environment()
    authenticate()
    import earthaccess

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    needed = build_required_half_hour_set()

    coverage_records = []
    granule_results_by_half_hour = {}
    for half_hour_start, targets in sorted(needed.items()):
        log(f"Searching {SHORT_NAME} V{VERSION} for half-hour starting {half_hour_start} "
            f"(needed for target(s): {sorted(t for t in targets)}) ...")
        results, actual_start, actual_end, matched_exact = search_half_hour(half_hour_start)
        coverage_records.append({
            "requested_half_hour_start": half_hour_start,
            "requested_half_hour_end": half_hour_start + HALF_HOUR,
            "serves_target_timestamps": ";".join(sorted(targets)),
            "granule_found": len(results) == 1,
            "concept_id": (
                results[0].get("meta", {}).get("concept-id")
                if len(results) == 1 else None
            ),
            "actual_granule_start": actual_start,
            "actual_granule_end": actual_end,
            "matched_exactly": matched_exact,
        })
        if len(results) == 1:
            granule_results_by_half_hour[half_hour_start] = results[0]

    missing = [r["requested_half_hour_start"] for r in coverage_records if not r["granule_found"]]
    if missing:
        log(f"Missing requested half-hour granules (no silent substitution): {missing}")

    if not granule_results_by_half_hour:
        log("No granules found at all. Acquisition status: BLOCKED (no matching granules).")
        return {}, coverage_records

    log(f"Downloading {len(granule_results_by_half_hour)} half-hour granule(s) to {RAW_DIR} "
        f"(subset to required half-hours only — not a bulk archive)...")
    ordered_halves = list(granule_results_by_half_hour.keys())
    ordered_results = [granule_results_by_half_hour[h] for h in ordered_halves]
    downloaded_paths = earthaccess.download(ordered_results, str(RAW_DIR))

    files_by_half_hour = dict(zip(ordered_halves, downloaded_paths))
    return files_by_half_hour, coverage_records


def write_temporal_coverage(coverage_records):
    out = pd.DataFrame(coverage_records)
    out.to_csv(OUT_DIR / "imerg_temporal_coverage.csv", index=False)
    log(f"Wrote {OUT_DIR / 'imerg_temporal_coverage.csv'}")
    return out


# =====================================================================
# Fill value (item 2 — read from file, documented fallback only if missing)
# =====================================================================
def read_fill_value(h5_file, dataset_path="/Grid/precipitation"):
    ds = h5_file[dataset_path]
    if "_FillValue" in ds.attrs:
        return float(ds.attrs["_FillValue"]), "file_attribute"
    log(f"  WARNING: {dataset_path} has no _FillValue attribute in this file. "
        f"Falling back to documented value {DOCUMENTED_FALLBACK_FILL_VALUE} "
        f"— explicitly flagged, not silently assumed.")
    return DOCUMENTED_FALLBACK_FILL_VALUE, "documented_fallback"


def load_precipitation(h5_path: Path):
    """Read the V07 'precipitation' variable, lat/lon grid, and fill value
    from one half-hourly granule."""
    import h5py
    dataset_path = "/Grid/precipitation"
    with h5py.File(h5_path, "r") as f:
        dataset = f[dataset_path]
        precip = dataset[0]  # (lon, lat) per V07 grid layout
        units = dataset.attrs.get("units", "unavailable")
        if isinstance(units, bytes):
            units = units.decode("utf-8", errors="replace")
        lons = f["/Grid/lon"][:]
        lats = f["/Grid/lat"][:]
        fill_value, fill_value_source = read_fill_value(f)
    return precip, lons, lats, fill_value, fill_value_source, dataset_path, units


# =====================================================================
# CMR pixel geometry — bbox vs actual polygon (item 4)
# =====================================================================
def get_cmr_pixel_masks(lons, lats):
    """Returns bbox lon/lat masks always, and polygon-intersecting lon/lat
    index pairs if the real study-area polygon is available. Never confuses
    the two — counts are reported separately."""
    bbox_lon_mask = (lons >= BBOX["west"]) & (lons <= BBOX["east"])
    bbox_lat_mask = (lats >= BBOX["south"]) & (lats <= BBOX["north"])

    result = {
        "bbox_lon_mask": bbox_lon_mask,
        "bbox_lat_mask": bbox_lat_mask,
        "n_bbox_lon_cells": int(bbox_lon_mask.sum()),
        "n_bbox_lat_cells": int(bbox_lat_mask.sum()),
        "n_bbox_pixels": int(bbox_lon_mask.sum() * bbox_lat_mask.sum()),
        "polygon_source": None,
        "n_polygon_intersecting_pixels": None,
        "polygon_cell_mask": None,  # boolean 2D array over (bbox_lons x bbox_lats), if computed
    }

    if not STUDY_AREA_PATH.exists():
        log(f"  CMR polygon intersection PENDING: {STUDY_AREA_PATH} not found here "
            f"(known limitation — gitignored, run locally where it exists). "
            f"Using bbox only as fallback.")
        result["polygon_source"] = "PENDING - file not found, bbox fallback used"
        return result

    try:
        import geopandas as gpd
        from shapely.geometry import box
        from shapely.ops import unary_union
    except ImportError:
        log("  CMR polygon intersection PENDING: geopandas/shapely not installed "
            "(pip install geopandas shapely). Using bbox only as fallback.")
        result["polygon_source"] = "PENDING - geopandas/shapely not installed, bbox fallback used"
        return result

    gdf = gpd.read_file(STUDY_AREA_PATH)
    if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    polygon = unary_union(gdf.geometry.values)

    sub_lons = lons[bbox_lon_mask]
    sub_lats = lats[bbox_lat_mask]
    half_grid = 0.05  # half of the 0.1 deg IMERG grid spacing
    cell_mask = np.zeros((len(sub_lons), len(sub_lats)), dtype=bool)
    for i, lon in enumerate(sub_lons):
        for j, lat in enumerate(sub_lats):
            cell_box = box(lon - half_grid, lat - half_grid, lon + half_grid, lat + half_grid)
            cell_mask[i, j] = polygon.intersects(cell_box)

    result["polygon_source"] = (
        str(STUDY_AREA_PATH.relative_to(REPO_ROOT))
        if REPO_ROOT in STUDY_AREA_PATH.parents
        else str(STUDY_AREA_PATH)
    )
    result["n_polygon_intersecting_pixels"] = int(cell_mask.sum())
    result["polygon_cell_mask"] = cell_mask
    return result


def extract_valid_values(bbox_sub: np.ndarray, mask_info: dict, fill_value: float):
    """Single shared implementation of 'which pixels count, and which values
    are valid' — used by BOTH analyze_sample() and compare_with_openmeteo() so
    the two can never again silently disagree on spatial support or on what
    counts as a valid value.

    Spatial support: polygon-intersecting pixels if the real CMR polygon mask
    is available, else the bbox fallback (never re-decided independently at
    each call site).

    Validity: np.isfinite(x) & (x != fill_value) — explicitly excludes the
    fill value, NaN, AND Inf. Simple `!= fill_value` alone would let real NaN
    or Inf values through uncounted as "valid", which is the bug being fixed.

    Returns a dict with the raw candidate values (pixels within spatial
    support, before validity filtering) and the filtered valid values, plus
    separate fill/NaN/Inf counts for data-quality reporting.
    """
    polygon_mask = mask_info.get("polygon_cell_mask")
    if polygon_mask is not None:
        candidates = bbox_sub[polygon_mask]
        spatial_support = "polygon-masked (CMR-intersecting pixels only)"
    else:
        candidates = bbox_sub.ravel()
        spatial_support = "bbox-masked (polygon unavailable — see item 4 note)"

    candidates = np.asarray(candidates)
    fill_count = int(np.sum(candidates == fill_value))
    nan_count = int(np.sum(np.isnan(candidates)))
    inf_count = int(np.sum(np.isinf(candidates)))

    valid_mask = np.isfinite(candidates) & (candidates != fill_value)
    valid = candidates[valid_mask]

    return {
        "spatial_support": spatial_support,
        "n_candidates": int(candidates.size),
        "valid": valid,
        "n_valid": int(valid.size),
        "n_fill": fill_count,
        "n_nan": nan_count,
        "n_inf": inf_count,
        "n_excluded_total": int(candidates.size - valid.size),
    }


# =====================================================================
# Spatial variation + quality (items 2, 3, 5)
# =====================================================================
def analyze_sample(files_by_half_hour: dict, coverage_records=None):
    """For each downloaded half-hour granule: spatial variation (item 5) and
    data quality (items 2, 3), measured at IMERG's native ~0.1 deg resolution."""
    if not files_by_half_hour:
        log("SKIPPED analysis: no files downloaded.")
        return {}, None

    variation_rows = []
    quality_rows = []
    loaded_by_half_hour = {}  # half_hour_start -> (precip, mask_info, fill_value) for reuse in comparison
    pixel_geometry_logged = False
    coverage_by_half_hour = {
        record["requested_half_hour_start"]: record
        for record in (coverage_records or [])
    }

    for half_hour_start, fpath in files_by_half_hour.items():
        if fpath is None:
            continue
        fpath = Path(fpath)
        (
            precip,
            lons,
            lats,
            fill_value,
            fill_value_source,
            dataset_path,
            units,
        ) = load_precipitation(fpath)
        mask_info = get_cmr_pixel_masks(lons, lats)
        if not pixel_geometry_logged:
            log(f"CMR pixel geometry (native ~0.1 deg IMERG grid): "
                f"bbox={mask_info['n_bbox_pixels']} pixels "
                f"({mask_info['n_bbox_lon_cells']} lon x {mask_info['n_bbox_lat_cells']} lat); "
                f"polygon-intersecting={mask_info['n_polygon_intersecting_pixels']} "
                f"(source: {mask_info['polygon_source']}). These are NOT the same "
                f"number and are reported separately.")
            pixel_geometry_logged = True

        bbox_sub = precip[np.ix_(mask_info["bbox_lon_mask"], mask_info["bbox_lat_mask"])]
        extracted = extract_valid_values(bbox_sub, mask_info, fill_value)
        valid = extracted["valid"]
        full_valid_mask = np.isfinite(precip) & (precip != fill_value)
        full_value_count = int(precip.size)
        full_valid_count = int(full_valid_mask.sum())
        full_missing_count = full_value_count - full_valid_count
        full_missing_percentage = (
            100.0 * full_missing_count / full_value_count if full_value_count else float("nan")
        )
        polygon_cell_mask = mask_info.get("polygon_cell_mask")
        cmr_intersects_valid = (
            None
            if polygon_cell_mask is None
            else bool(np.any(polygon_cell_mask & np.isfinite(bbox_sub) & (bbox_sub != fill_value)))
        )
        longitude_resolution = float(np.median(np.abs(np.diff(lons)))) if len(lons) > 1 else float("nan")
        latitude_resolution = float(np.median(np.abs(np.diff(lats)))) if len(lats) > 1 else float("nan")
        coverage = coverage_by_half_hour.get(half_hour_start, {})
        actual_start = coverage.get("actual_granule_start")
        actual_end = coverage.get("actual_granule_end")

        variation_rows.append({
            "half_hour_start_utc": half_hour_start,
            "file": fpath.name,
            "file_path": str(fpath),
            "concept_id": coverage.get("concept_id"),
            "actual_temporal_beginning": actual_start,
            "actual_temporal_ending": actual_end,
            "dataset_path": dataset_path,
            "precipitation_units": units,
            "array_shape": str(precip.shape),
            "longitude_count": int(len(lons)),
            "longitude_min": float(lons.min()),
            "longitude_max": float(lons.max()),
            "latitude_count": int(len(lats)),
            "latitude_min": float(lats.min()),
            "latitude_max": float(lats.max()),
            "native_longitude_resolution_degrees": longitude_resolution,
            "native_latitude_resolution_degrees": latitude_resolution,
            "fill_value": fill_value,
            "full_granule_finite_non_fill_count": full_valid_count,
            "full_granule_missing_or_fill_count": full_missing_count,
            "full_granule_missing_or_fill_percentage": full_missing_percentage,
            "cmr_polygon_intersects_valid_pixels": cmr_intersects_valid,
            "valid_pixels_inside_cmr": extracted["n_valid"],
            "masked_by": extracted["spatial_support"],
            "resolution_note": "measured at IMERG native ~0.1 deg (~10-11km) resolution, NOT the 250m terrain grid",
            "n_valid_pixels": extracted["n_valid"],
            "n_missing_or_fill_pixels": extracted["n_excluded_total"],
            "unique_count": int(len(np.unique(valid))) if valid.size else 0,
            "min_mm_per_hr": float(valid.min()) if valid.size else float("nan"),
            "max_mm_per_hr": float(valid.max()) if valid.size else float("nan"),
            "mean_mm_per_hr": float(valid.mean()) if valid.size else float("nan"),
            "median_mm_per_hr": float(np.median(valid)) if valid.size else float("nan"),
            "std_mm_per_hr": float(valid.std()) if valid.size else float("nan"),
            "coefficient_of_variation": (
                float(valid.std() / valid.mean()) if valid.size and valid.mean() != 0 else float("nan")
            ),
        })
        quality_rows.append({
            "half_hour_start_utc": half_hour_start,
            "file": fpath.name,
            "n_fill_or_missing": extracted["n_fill"],
            "n_nan": extracted["n_nan"],
            "n_inf": extracted["n_inf"],
            "n_negative_valid": int((valid < 0).sum()) if valid.size else 0,
            "min_valid_precip_mm_per_hr": float(valid.min()) if valid.size else float("nan"),
            "max_valid_precip_mm_per_hr": float(valid.max()) if valid.size else float("nan"),
            "fill_value_used": fill_value,
            "fill_value_source": fill_value_source,
        })

        loaded_by_half_hour[half_hour_start] = (bbox_sub, mask_info, fill_value)

    variation_df = pd.DataFrame(variation_rows)
    variation_df.to_csv(OUT_DIR / "imerg_spatial_variation.csv", index=False)
    log(f"Wrote {OUT_DIR / 'imerg_spatial_variation.csv'}")

    quality_df = pd.DataFrame(quality_rows)
    quality_df.to_csv(OUT_DIR / "imerg_data_quality.csv", index=False)
    log(f"Wrote {OUT_DIR / 'imerg_data_quality.csv'}")

    return loaded_by_half_hour, variation_df


# =====================================================================
# Open-Meteo comparison (item 1 — real hourly amount from paired half-hours)
# =====================================================================
def compare_with_openmeteo(loaded_by_half_hour: dict):
    if not RAINFALL_PATH.exists():
        log(f"SKIPPED comparison: {RAINFALL_PATH} not found.")
        return

    rdf = pd.read_csv(RAINFALL_PATH, parse_dates=["time"])
    rows = []
    for ts in TARGET_TIMESTAMPS_UTC:
        half_a, half_b = required_half_hours_for_target(ts)
        match = rdf[rdf["time"] == pd.Timestamp(ts)]
        om_rain_1h = float(match.iloc[0]["rain_1h"]) if len(match) == 1 else None

        have_a = half_a in loaded_by_half_hour
        have_b = half_b in loaded_by_half_hour

        row = {
            "target_timestamp_utc": ts,
            "open_meteo_rain_1h_mm": om_rain_1h,
            "half_hour_a_start": half_a,
            "half_hour_a_available": have_a,
            "half_hour_b_start": half_b,
            "half_hour_b_available": have_b,
        }

        if have_a and have_b:
            precip_a, mask_info, fill_a = loaded_by_half_hour[half_a]
            precip_b, _, fill_b = loaded_by_half_hour[half_b]
            # Same spatial support and same validity rule as analyze_sample()
            # via the shared extract_valid_values() helper — polygon-masked
            # when available, bbox fallback otherwise; never independently
            # decided here (that was the bug being fixed).
            extracted_a = extract_valid_values(precip_a, mask_info, fill_a)
            extracted_b = extract_valid_values(precip_b, mask_info, fill_b)
            valid_a = extracted_a["valid"]
            valid_b = extracted_b["valid"]
            # rate (mm/hr) x 0.5h per half-hour, then sum, per the review's formula.
            # Uses the spatial MEAN rate over the same masked pixels used in
            # imerg_spatial_variation.csv as a single comparable number against
            # Open-Meteo's single-point value — this collapses IMERG's spatial
            # detail for this one comparison row only; the full spatial detail
            # remains in imerg_spatial_variation.csv.
            amount_a_mm = float(valid_a.mean()) * 0.5 if valid_a.size else float("nan")
            amount_b_mm = float(valid_b.mean()) * 0.5 if valid_b.size else float("nan")
            imerg_hourly_amount_mm = amount_a_mm + amount_b_mm
            row.update({
                "imerg_spatial_support": extracted_a["spatial_support"],
                "imerg_half_hour_a_mean_rate_mm_per_hr": float(valid_a.mean()) if valid_a.size else float("nan"),
                "imerg_half_hour_b_mean_rate_mm_per_hr": float(valid_b.mean()) if valid_b.size else float("nan"),
                "imerg_derived_hourly_amount_mm": imerg_hourly_amount_mm,
                "comparison_computed": True,
            })
        else:
            row.update({
                "imerg_spatial_support": None,
                "imerg_half_hour_a_mean_rate_mm_per_hr": None,
                "imerg_half_hour_b_mean_rate_mm_per_hr": None,
                "imerg_derived_hourly_amount_mm": None,
                "comparison_computed": False,
            })

        row["note"] = (
            "Do NOT claim one source is more accurate merely because values differ. "
            "Open-Meteo here is a single reanalysis/model-derived point series; "
            "IMERG's derived hourly amount is the spatial MEAN of a satellite-derived "
            "rate over the CMR footprint. Different estimation methods and different "
            "spatial support, not a ground-truth-vs-error comparison. Comparison is "
            "only computed when BOTH required half-hour periods were available "
            "(never a silent nearest-timestamp substitution)."
        )
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "imerg_vs_openmeteo_comparison.csv", index=False)
    log(f"Wrote {OUT_DIR / 'imerg_vs_openmeteo_comparison.csv'}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("=" * 72)
    log("STAGE 5.2 — IMERG spatial rainfall feasibility test")
    log("=" * 72)
    files_by_half_hour, coverage_records = download_sample()
    write_temporal_coverage(coverage_records)
    loaded_by_half_hour, _ = analyze_sample(files_by_half_hour, coverage_records)
    compare_with_openmeteo(loaded_by_half_hour or {})
    log("\nDone. Review outputs in " + str(OUT_DIR))
    log("This script performed acquisition + read-only analysis only. "
        "It did not touch AI #1, AI #2, Stage 1-4 outputs, flood labels, or the 250m grid.")


if __name__ == "__main__":
    main()