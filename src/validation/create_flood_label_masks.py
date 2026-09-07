"""
create_flood_label_masks.py

SIH26071 - Step 8 / 8.1
Prepares satellite-derived inundation reference labels for the Chennai
Metropolitan Region (CMR) study area, for AI #2 (inundation-risk model)
development. This script does NOT train any model. It only prepares
spatial label masks.

For each of the five Chennai-relevant NDEM event timestamps, three
mutually-exclusive spatial classes are produced that partition the
study area:

  CLASS 1 - OBSERVED_INUNDATION
      Area explicitly observed as inundated by the NDEM event
      footprint at that specific timestamp, intersected with the
      study area.

  CLASS 2 - UNCERTAIN
      Area inside the 2021 yearly aggregate inundation footprint
      (intersected with the study area) that was NOT observed in the
      event footprint at that timestamp. This must NOT be treated as
      a negative / non-flooded class - it means "not observed at this
      snapshot, but flagged by the broader yearly layer."

  CLASS 0 - NO_INUNDATION_EVIDENCE
      The remainder of the study area after removing CLASS 1 and
      CLASS 2. This means "no inundation observed within the
      available NDEM evidence" - it does NOT mean the location was
      proven dry.

KEY FIX from the previous (Step 8) version
-------------------------------------------
The earlier script computed:

    class_0 = study_area - yearly_aggregate        (WRONG)

independent of class_1 for that timestamp. Because a meaningful part
of the event-observed footprint (class_1) lies OUTSIDE the yearly
aggregate footprint (the two layers only have ~0.15 IoU on this
dataset), that sliver of class_1 was being double-counted: once in
class_1, and again inside the fixed class_0. That is why class_0 was
IDENTICAL across every timestamp in the previous run, and why
class_1 + class_2 + class_0 exceeded the study area by an amount that
tracked (but was not proportional to) the size of class_1.

The fix here builds the three classes SEQUENTIALLY, each one directly
carved out of what remains, so they form a partition of the study
area by construction:

    class_1 = dissolve(event_at_timestamp)  ∩ study_area
    class_2 = (dissolve(yearly_aggregate)   ∩ study_area) - class_1
    class_0 = study_area - (class_1 union class_2)

This guarantees zero overlap between class_0 and class_1 regardless
of how much of class_1 falls outside the yearly aggregate.

A secondary source of noise - self-overlapping components WITHIN each
multi-feature layer (1658 event features / 1614 yearly-aggregate
features can contain overlapping tiles) - is handled by dissolving
(unary_union) each layer before any difference/intersection step, and
by repairing invalid geometries before that dissolve.

Do NOT modify the rainfall model (AI #1). Do NOT proceed to AI #2,
DEM, drainage, or land-cover integration from this script.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

try:
    from shapely.validation import make_valid
    HAVE_MAKE_VALID = True
except ImportError:
    HAVE_MAKE_VALID = False

# ---------------------------------------------------------------------------
# CONFIG - adjust paths only if your repo layout differs
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/validation/ -> repo root

STUDY_AREA_PATH = REPO_ROOT / "data" / "processed" / "chennai_cmr_study_area.geojson"
EVENTS_PATH = REPO_ROOT / "data" / "processed" / "chennai_nov2021_flood_events.geojson"
YEARLY_PATH = REPO_ROOT / "data" / "processed" / "chennai_2021_yearly_aggregate.geojson"

OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "flood_labels"
SUMMARY_CSV = OUTPUT_DIR / "label_summary.csv"

# Projected CRS used ONLY for area calculation and geometry cleanup.
# UTM zone 44N covers Chennai / Tamil Nadu and gives near-equal-area
# accuracy at this scale.
PROJECTED_CRS = "EPSG:32644"
OUTPUT_CRS = "EPSG:4326"  # geometry in output files stays in WGS84

# The five Chennai-relevant NDEM event timestamps (kept).
KEEP_TIMESTAMPS = [
    "2021-11-08 23:00",
    "2021-11-10 11:00",
    "2021-11-10 18:00",
    "2021-11-12 00:00",
    "2021-11-28 06:00",
]

# The timestamp that must be explicitly excluded (southern Tamil Nadu,
# verified to not intersect the Chennai CMR study area).
EXCLUDED_TIMESTAMP = "2021-11-16 06:00"

# Tolerance for partition / overlap checks, in km^2. Anything above
# this is reported as a WARNING, not silently ignored.
AREA_TOLERANCE_KM2 = 0.01

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(msg, flush=True)


def km2(area_m2: float) -> float:
    return area_m2 / 1_000_000.0


def repair_geometry_column(gdf: gpd.GeoDataFrame, label: str) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Reports invalid / empty / duplicate geometries, and repairs invalid
    geometries. Returns the cleaned GeoDataFrame plus a report dict.
    Nothing is silently dropped except exact duplicate geometries and
    geometries that are empty AFTER repair (these are reported).
    """
    report = {
        "layer": label,
        "n_input": len(gdf),
        "n_invalid_before": 0,
        "n_repaired": 0,
        "n_still_invalid_after_repair": 0,
        "n_empty_dropped": 0,
        "n_duplicate_dropped": 0,
        "n_output": 0,
    }

    invalid_mask = ~gdf.geometry.is_valid
    report["n_invalid_before"] = int(invalid_mask.sum())

    if report["n_invalid_before"] > 0:
        def _fix(geom: BaseGeometry) -> BaseGeometry:
            if geom is None or geom.is_valid:
                return geom
            if HAVE_MAKE_VALID:
                return make_valid(geom)
            return geom.buffer(0)

        gdf = gdf.copy()
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].apply(_fix)
        report["n_repaired"] = report["n_invalid_before"]

    still_invalid = ~gdf.geometry.is_valid
    report["n_still_invalid_after_repair"] = int(still_invalid.sum())
    if report["n_still_invalid_after_repair"] > 0:
        log(f"  WARNING [{label}]: {report['n_still_invalid_after_repair']} "
            f"geometries remain invalid after repair attempt.")

    empty_mask = gdf.geometry.is_empty | gdf.geometry.isna()
    report["n_empty_dropped"] = int(empty_mask.sum())
    if report["n_empty_dropped"] > 0:
        log(f"  NOTE [{label}]: dropping {report['n_empty_dropped']} empty/null geometries.")
        gdf = gdf.loc[~empty_mask].copy()

    before_dedup = len(gdf)
    gdf["_wkb"] = gdf.geometry.apply(lambda g: g.wkb)
    gdf = gdf.drop_duplicates(subset="_wkb").drop(columns="_wkb")
    report["n_duplicate_dropped"] = before_dedup - len(gdf)
    if report["n_duplicate_dropped"] > 0:
        log(f"  NOTE [{label}]: dropped {report['n_duplicate_dropped']} exact duplicate geometries.")

    report["n_output"] = len(gdf)
    return gdf, report


def dissolve_all(gdf: gpd.GeoDataFrame) -> BaseGeometry:
    """Union all geometries in a layer into a single (Multi)Polygon,
    removing internal self-overlaps between features."""
    geom = unary_union(gdf.geometry.values)
    if not geom.is_valid:
        geom = make_valid(geom) if HAVE_MAKE_VALID else geom.buffer(0)
    return geom


def find_timestamp_field(gdf: gpd.GeoDataFrame) -> str:
    """
    Locate the timestamp field. Prefers 'from_time' per the documented
    NDEM schema, but checks alternatives rather than assuming.
    """
    candidates = ["from_time", "to_time", "timestamp", "datetime", "date_time"]
    for c in candidates:
        if c in gdf.columns:
            return c
    raise ValueError(
        f"Could not find a recognizable timestamp field in event data. "
        f"Available columns: {list(gdf.columns)}"
    )


def normalize_timestamp_series(s: pd.Series) -> pd.Series:
    """Parse to pandas datetime, tolerant of multiple string formats."""
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> int:
    log("=" * 70)
    log("STEP 8.1 - Flood label mask generation (corrected partition logic)")
    log("=" * 70)

    warnings_list: list[str] = []

    # -- 1. Load inputs -----------------------------------------------------
    for p in (STUDY_AREA_PATH, EVENTS_PATH, YEARLY_PATH):
        if not p.exists():
            log(f"ERROR: required input not found: {p}")
            return 1

    log(f"\nLoading study area:   {STUDY_AREA_PATH}")
    study_gdf = gpd.read_file(STUDY_AREA_PATH)
    log(f"Loading event data:   {EVENTS_PATH}")
    events_gdf = gpd.read_file(EVENTS_PATH)
    log(f"Loading yearly aggregate: {YEARLY_PATH}")
    yearly_gdf = gpd.read_file(YEARLY_PATH)

    log(f"\nstudy area features: {len(study_gdf)}, CRS: {study_gdf.crs}")
    log(f"event features:      {len(events_gdf)}, CRS: {events_gdf.crs}")
    log(f"yearly features:     {len(yearly_gdf)}, CRS: {yearly_gdf.crs}")

    # -- 2. CRS confirmation --------------------------------------------------
    for name, gdf in [("study area", study_gdf), ("events", events_gdf), ("yearly", yearly_gdf)]:
        if gdf.crs is None:
            msg = f"{name} layer has no CRS defined - assuming EPSG:4326, but this should be verified."
            log(f"  WARNING: {msg}")
            warnings_list.append(msg)
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_epsg() != 4326:
            msg = f"{name} layer CRS is {gdf.crs}, not EPSG:4326 - reprojecting to EPSG:4326 first."
            log(f"  NOTE: {msg}")
            warnings_list.append(msg)
            gdf.to_crs("EPSG:4326", inplace=True)

    if len(study_gdf) != 1:
        msg = f"Study area layer has {len(study_gdf)} features, expected 1. Dissolving into one polygon."
        log(f"  WARNING: {msg}")
        warnings_list.append(msg)

    # -- 3. Repair / validate geometries -------------------------------------
    log("\n--- Geometry validity checks ---")
    study_gdf, study_report = repair_geometry_column(study_gdf, "study_area")
    events_gdf, events_report = repair_geometry_column(events_gdf, "events")
    yearly_gdf, yearly_report = repair_geometry_column(yearly_gdf, "yearly_aggregate")

    for r in (study_report, events_report, yearly_report):
        log(f"  {r}")

    study_geom_4326 = unary_union(study_gdf.geometry.values)
    if not study_geom_4326.is_valid:
        study_geom_4326 = make_valid(study_geom_4326) if HAVE_MAKE_VALID else study_geom_4326.buffer(0)

    # -- 4. Identify timestamp field & filter --------------------------------
    ts_field = find_timestamp_field(events_gdf)
    log(f"\nUsing timestamp field: '{ts_field}'")
    events_gdf["_ts_parsed"] = normalize_timestamp_series(events_gdf[ts_field])

    if events_gdf["_ts_parsed"].isna().any():
        n_bad = int(events_gdf["_ts_parsed"].isna().sum())
        msg = f"{n_bad} event features had an unparseable timestamp in '{ts_field}'."
        log(f"  WARNING: {msg}")
        warnings_list.append(msg)

    unique_ts = sorted(events_gdf["_ts_parsed"].dropna().unique())
    log(f"\nUnique timestamps found in event data: {len(unique_ts)}")
    for t in unique_ts:
        log(f"    {t}")

    keep_ts_parsed = [pd.Timestamp(t) for t in KEEP_TIMESTAMPS]
    excluded_ts_parsed = pd.Timestamp(EXCLUDED_TIMESTAMP)

    unexpected = [t for t in unique_ts if pd.Timestamp(t) not in keep_ts_parsed
                  and pd.Timestamp(t) != excluded_ts_parsed]
    if unexpected:
        msg = f"Unexpected timestamp(s) found in event data not in the documented set: {unexpected}"
        log(f"  WARNING: {msg}")
        warnings_list.append(msg)

    # -- 5/6/7. Verify excluded timestamp does not intersect study area ------
    excluded_subset = events_gdf[events_gdf["_ts_parsed"] == excluded_ts_parsed]
    log(f"\nExcluded timestamp {EXCLUDED_TIMESTAMP}: {len(excluded_subset)} feature(s) in raw data.")
    if len(excluded_subset) > 0:
        excluded_geom = unary_union(excluded_subset.geometry.values)
        intersects_study = excluded_geom.intersects(study_geom_4326)
        inter_area_km2 = 0.0
        if intersects_study:
            # measure in projected CRS to be safe
            excluded_gs = gpd.GeoSeries([excluded_geom], crs="EPSG:4326").to_crs(PROJECTED_CRS)
            study_gs = gpd.GeoSeries([study_geom_4326], crs="EPSG:4326").to_crs(PROJECTED_CRS)
            inter_area_km2 = km2(excluded_gs.iloc[0].intersection(study_gs.iloc[0]).area)
        log(f"  Excluded timestamp intersects study area: {intersects_study} "
            f"(intersection area = {inter_area_km2:.6f} km^2)")
        if intersects_study and inter_area_km2 > AREA_TOLERANCE_KM2:
            msg = (f"Excluded timestamp {EXCLUDED_TIMESTAMP} intersects the study area with "
                   f"{inter_area_km2:.4f} km^2 - this contradicts the documented assumption "
                   f"that it belongs to southern Tamil Nadu. Re-verify before proceeding.")
            log(f"  WARNING: {msg}")
            warnings_list.append(msg)
        else:
            log("  Confirmed: excluded timestamp has (near) zero intersection with study area, as expected.")
    else:
        log("  Excluded timestamp not present in this dataset extract - nothing to verify.")

    # -- 9. Reproject to projected CRS for all area/geometry operations -----
    study_gs_proj = gpd.GeoSeries([study_geom_4326], crs="EPSG:4326").to_crs(PROJECTED_CRS)
    study_geom_proj = study_gs_proj.iloc[0]
    study_area_km2 = km2(study_geom_proj.area)
    log(f"\nStudy area (projected {PROJECTED_CRS}): {study_area_km2:.6f} km^2")

    yearly_geom_4326 = dissolve_all(yearly_gdf)
    yearly_gs_proj = gpd.GeoSeries([yearly_geom_4326], crs="EPSG:4326").to_crs(PROJECTED_CRS)
    yearly_geom_proj = yearly_gs_proj.iloc[0]

    # -- 11. Yearly aggregate clipped to study area (projected) --------------
    yearly_in_study_proj = yearly_geom_proj.intersection(study_geom_proj)
    if not yearly_in_study_proj.is_valid:
        yearly_in_study_proj = make_valid(yearly_in_study_proj) if HAVE_MAKE_VALID else yearly_in_study_proj.buffer(0)
    yearly_in_study_km2 = km2(yearly_in_study_proj.area)
    n_yearly_intersecting = int(yearly_gdf.geometry.intersects(
        gpd.GeoSeries([study_geom_4326], crs="EPSG:4326").iloc[0]
    ).sum())

    log(f"Yearly aggregate features intersecting CMR: {n_yearly_intersecting}")
    log(f"Yearly aggregate area within study area: {yearly_in_study_km2:.6f} km^2")

    # -- 12. Build classes per timestamp (SEQUENTIAL -> guaranteed partition) --
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for ts in KEEP_TIMESTAMPS:
        ts_parsed = pd.Timestamp(ts)
        log(f"\n--- Processing timestamp {ts} ---")

        subset = events_gdf[events_gdf["_ts_parsed"] == ts_parsed]
        n_event_polygons = len(subset)
        log(f"  Event polygons at this timestamp: {n_event_polygons}")

        if n_event_polygons == 0:
            msg = f"No event polygons found for expected timestamp {ts}."
            log(f"  WARNING: {msg}")
            warnings_list.append(msg)
            event_geom_4326 = None
        else:
            event_geom_4326 = dissolve_all(subset)

        # --- CLASS 1: event footprint (dissolved) intersected with study area
        if event_geom_4326 is not None:
            event_gs_proj = gpd.GeoSeries([event_geom_4326], crs="EPSG:4326").to_crs(PROJECTED_CRS)
            event_geom_proj = event_gs_proj.iloc[0]
            class1_proj = event_geom_proj.intersection(study_geom_proj)
        else:
            from shapely.geometry import Polygon
            class1_proj = Polygon()

        if not class1_proj.is_valid:
            class1_proj = make_valid(class1_proj) if HAVE_MAKE_VALID else class1_proj.buffer(0)

        # --- CLASS 2: yearly-in-study MINUS class1 -----------------------
        class2_proj = yearly_in_study_proj.difference(class1_proj)
        if not class2_proj.is_valid:
            class2_proj = make_valid(class2_proj) if HAVE_MAKE_VALID else class2_proj.buffer(0)

        # --- CLASS 0: study area MINUS (class1 UNION class2) -------------
        # This is the corrected step: class_0 is carved directly out of
        # what remains, so it is IMPOSSIBLE for it to overlap class_1,
        # regardless of how much of class_1 falls outside the yearly
        # aggregate footprint.
        class12_union_proj = unary_union([class1_proj, class2_proj])
        class0_proj = study_geom_proj.difference(class12_union_proj)
        if not class0_proj.is_valid:
            class0_proj = make_valid(class0_proj) if HAVE_MAKE_VALID else class0_proj.buffer(0)

        area1 = km2(class1_proj.area)
        area2 = km2(class2_proj.area)
        area0 = km2(class0_proj.area)
        total = area1 + area2 + area0
        diff = total - study_area_km2

        log(f"  Class 1 (observed inundation): {area1:.6f} km^2")
        log(f"  Class 2 (uncertain):           {area2:.6f} km^2")
        log(f"  Class 0 (no evidence):         {area0:.6f} km^2")
        log(f"  Total:                         {total:.6f} km^2  "
            f"(study area = {study_area_km2:.6f} km^2, diff = {diff:+.6f} km^2)")

        # --- Overlap checks --------------------------------------------
        i_01 = km2(class1_proj.intersection(class0_proj).area)
        i_02 = km2(class2_proj.intersection(class0_proj).area)
        i_12 = km2(class1_proj.intersection(class2_proj).area)
        log(f"  Overlap check: class1∩class0={i_01:.8f} km^2, "
            f"class2∩class0={i_02:.8f} km^2, class1∩class2={i_12:.8f} km^2")

        overlap_ok = all(v <= AREA_TOLERANCE_KM2 for v in (i_01, i_02, i_12))
        partition_ok = abs(diff) <= AREA_TOLERANCE_KM2

        if not overlap_ok:
            msg = (f"Timestamp {ts}: class overlap exceeds tolerance "
                   f"({AREA_TOLERANCE_KM2} km^2): "
                   f"class1∩class0={i_01:.6f}, class2∩class0={i_02:.6f}, "
                   f"class1∩class2={i_12:.6f}")
            log(f"  WARNING: {msg}")
            warnings_list.append(msg)
        if not partition_ok:
            msg = f"Timestamp {ts}: partition difference {diff:+.6f} km^2 exceeds tolerance."
            log(f"  WARNING: {msg}")
            warnings_list.append(msg)
        if overlap_ok and partition_ok:
            log("  Partition check PASSED (within tolerance).")

        # --- Build output GeoDataFrame (reprojected back to EPSG:4326) ---
        rows = []
        label_meanings = {
            1: "OBSERVED_INUNDATION - satellite-derived inundation observation at this timestamp",
            2: "UNCERTAIN - within 2021 yearly aggregate footprint but not observed at this timestamp; NOT a negative label",
            0: "NO_INUNDATION_EVIDENCE - no inundation observed within available NDEM evidence at this timestamp; does not confirm dry ground",
        }
        for label, geom_proj in [(1, class1_proj), (2, class2_proj), (0, class0_proj)]:
            if geom_proj.is_empty:
                continue
            area_km2_val = km2(geom_proj.area)
            rows.append({
                "label": label,
                "label_meaning": label_meanings[label],
                "timestamp": ts,
                "area_km2": area_km2_val,
                "geometry": geom_proj,
            })

        out_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=PROJECTED_CRS)
        out_gdf = out_gdf.to_crs(OUTPUT_CRS)

        ts_tag = ts_parsed.strftime("%Y%m%d_%H%M")
        out_path = OUTPUT_DIR / f"flood_labels_{ts_tag}.geojson"
        out_gdf.to_file(out_path, driver="GeoJSON")
        log(f"  Wrote: {out_path}")

        summary_rows.append({
            "timestamp": ts,
            "event_polygons": n_event_polygons,
            "class_1_observed_km2": area1,
            "class_2_uncertain_km2": area2,
            "class_0_no_evidence_km2": area0,
            "total_labelled_km2": total,
            "study_area_km2": study_area_km2,
            "partition_difference_km2": diff,
            "percentage_observed": 100.0 * area1 / study_area_km2,
            "percentage_uncertain": 100.0 * area2 / study_area_km2,
            "percentage_no_inundation_evidence": 100.0 * area0 / study_area_km2,
            "overlap_class1_class0_km2": i_01,
            "overlap_class2_class0_km2": i_02,
            "overlap_class1_class2_km2": i_12,
            "n_output_polygons": len(out_gdf),
        })

    # -- Write summary CSV ----------------------------------------------------
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    log(f"\nWrote summary: {SUMMARY_CSV}")

    # -- Final report -----------------------------------------------------
    log("\n" + "=" * 70)
    log("SUMMARY TABLE")
    log("=" * 70)
    with pd.option_context("display.width", 200, "display.max_columns", None):
        log(str(summary_df))

    log("\n" + "=" * 70)
    log("DATA QUALITY REPORT")
    log("=" * 70)
    log(f"CRS used for area calculations: {PROJECTED_CRS}")
    log(f"Study area geometry report: {study_report}")
    log(f"Event layer geometry report: {events_report}")
    log(f"Yearly aggregate geometry report: {yearly_report}")
    log(f"Yearly aggregate features intersecting CMR: {n_yearly_intersecting}")
    log(f"Yearly aggregate area within study area: {yearly_in_study_km2:.6f} km^2")

    if warnings_list:
        log(f"\n{len(warnings_list)} WARNING(S):")
        for w in warnings_list:
            log(f"  - {w}")
    else:
        log("\nNo warnings raised.")

    log("\nSTEP 8.1 complete. Flood label masks written to:")
    log(f"  {OUTPUT_DIR}")
    log("\nSTOP: do not proceed to AI #2 / DEM / drainage / land-cover / training.")

    return 0


if __name__ == "__main__":
    sys.exit(main())