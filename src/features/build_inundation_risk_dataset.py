"""
SIH26071 - STAGE 1
Build AI #2 inundation-risk dataset.

Reads existing spatial features, corrected flood labels, and rainfall
features. Builds one row per (cell_id, timestamp).

This script:
- does NOT train AI #2
- does NOT modify AI #1 inputs
- does NOT delete existing files
- requires exact rainfall timestamp matches
- requires exactly one flood-label match per cell
- preserves class 2 (uncertain)
"""

from pathlib import Path
import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_PATH = REPO_ROOT / "data/processed/chennai_spatial_features_final.geojson"
LABEL_DIR = REPO_ROOT / "data/processed/flood_labels"
RAINFALL_PATH = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
OUTPUT_PATH = REPO_ROOT / "data/processed/inundation_risk_ml_dataset.csv"

EVENTS = [
    ("2021-11-08 23:00:00", "Episode_1", "flood_labels_20211108_2300.geojson"),
    ("2021-11-10 11:00:00", "Episode_1", "flood_labels_20211110_1100.geojson"),
    ("2021-11-10 18:00:00", "Episode_1", "flood_labels_20211110_1800.geojson"),
    ("2021-11-12 00:00:00", "Episode_1", "flood_labels_20211112_0000.geojson"),
    ("2021-11-28 06:00:00", "Episode_2", "flood_labels_20211128_0600.geojson"),
]

SPATIAL_FEATURES = [
    "cell_id", "centroid_lon", "centroid_lat",
    "elevation", "slope_degrees", "distance_to_drainage",
]

WEATHER_FEATURES = [
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "wind_speed_10m", "precipitation",
    "rain_lag_1h", "rain_lag_3h", "rain_lag_6h",
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "pressure_change_3h", "pressure_change_6h",
    "humidity_change_3h", "humidity_change_6h",
    "hour", "month", "day_of_year",
]

MODEL_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]

def fail(message):
    raise RuntimeError("\nSTAGE 1 VALIDATION FAILED:\n" + message)

def load_spatial():
    if not SPATIAL_PATH.exists():
        fail(f"Missing spatial file: {SPATIAL_PATH}")

    gdf = gpd.read_file(SPATIAL_PATH)

    if len(gdf) != 70626:
        fail(f"Expected 70,626 spatial cells, found {len(gdf)}")

    missing = [c for c in SPATIAL_FEATURES if c not in gdf.columns]
    if missing:
        fail(f"Missing spatial columns: {missing}")

    if gdf["cell_id"].duplicated().any():
        fail("Duplicate cell_id values found in spatial grid.")

    if gdf.crs is None:
        fail("Spatial grid has no CRS.")

    gdf = gdf.to_crs("EPSG:4326")
    gdf = gdf.copy()
    gdf["geometry"] = gpd.points_from_xy(
        gdf["centroid_lon"], gdf["centroid_lat"]
    )
    gdf = gdf.set_geometry("geometry")

    return gdf

def load_rainfall():
    if not RAINFALL_PATH.exists():
        fail(f"Missing rainfall dataset: {RAINFALL_PATH}")

    df = pd.read_csv(RAINFALL_PATH, parse_dates=["time"])

    missing = [c for c in WEATHER_FEATURES if c not in df.columns]
    if missing:
        fail(f"Missing rainfall/weather columns: {missing}")

    if df["time"].duplicated().any():
        fail("Duplicate timestamps found in rainfall dataset.")

    return df.set_index("time").sort_index()

def build_event(spatial, rainfall, ts_text, episode_id, filename):
    ts = pd.Timestamp(ts_text)
    path = LABEL_DIR / filename

    if not path.exists():
        fail(f"Missing label file: {path}")

    # Exact timestamp requirement.
    if ts not in rainfall.index:
        fail(
            f"Exact rainfall timestamp missing: {ts}. "
            "No nearest-hour fallback is allowed."
        )

    labels = gpd.read_file(path)

    required = {"label", "label_meaning", "geometry"}
    missing = required - set(labels.columns)
    if missing:
        fail(f"{filename}: missing label columns: {sorted(missing)}")

    if labels.crs is None:
        fail(f"{filename}: CRS is missing.")

    labels = labels.to_crs("EPSG:4326")

    found = set(pd.to_numeric(labels["label"], errors="coerce").dropna().astype(int))
    if found != {0, 1, 2}:
        fail(f"{filename}: expected labels {{0,1,2}}, found {found}")

    # Count spatial matches BEFORE collapsing anything.
    matches = gpd.sjoin(
        spatial[["cell_id", "geometry"]],
        labels[["label", "label_meaning", "geometry"]],
        how="left",
        predicate="within",
    )

    # A left spatial join keeps unmatched cells as rows with a null label.
    # We explicitly fail on unmatched cells and on cells with multiple matches.
    match_counts = matches.groupby("cell_id").size()
    multiple = match_counts[match_counts > 1].index.tolist()
    unmatched = matches.loc[matches["label"].isna(), "cell_id"].unique().tolist()

    if unmatched:
        fail(
            f"{filename}: {len(unmatched)} cells have NO label match. "
            f"Example cell_ids: {unmatched[:10]}"
        )

    if multiple:
        fail(
            f"{filename}: {len(multiple)} cells have MULTIPLE label matches. "
            f"Example cell_ids: {multiple[:10]}"
        )

    if len(matches) != len(spatial):
        fail(
            f"{filename}: expected exactly {len(spatial)} spatial matches, "
            f"got {len(matches)}."
        )

    result = matches[
        ["cell_id", "label", "label_meaning"]
    ].copy()

    # Restore spatial attributes by cell_id.
    spatial_attrs = spatial[SPATIAL_FEATURES].copy()
    result = spatial_attrs.merge(result, on="cell_id", how="inner", validate="one_to_one")

    weather = rainfall.loc[ts, WEATHER_FEATURES]
    for col in WEATHER_FEATURES:
        result[col] = weather[col]

    result["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")
    result["episode_id"] = episode_id

    result["label"] = pd.to_numeric(result["label"]).astype(int)

    return result

def main():
    print("=" * 70)
    print("STAGE 1 - BUILD AI #2 INUNDATION-RISK DATASET")
    print("=" * 70)

    spatial = load_spatial()
    rainfall = load_rainfall()

    print(f"Spatial cells: {len(spatial):,}")
    print(f"Rainfall rows: {len(rainfall):,}")

    parts = []

    for ts, episode, filename in EVENTS:
        print(f"\nProcessing {ts} | {episode}")
        part = build_event(spatial, rainfall, ts, episode, filename)

        counts = part["label"].value_counts().sort_index().to_dict()
        print(f"Label counts: {counts}")

        parts.append(part)

    dataset = pd.concat(parts, ignore_index=True)

    # Final structural checks.
    expected_rows = 70626 * 5

    if len(dataset) != expected_rows:
        fail(f"Expected {expected_rows:,} rows, found {len(dataset):,}")

    if dataset["cell_id"].nunique() != 70626:
        fail("Final dataset does not contain exactly 70,626 unique cells.")

    if dataset["timestamp"].nunique() != 5:
        fail("Final dataset does not contain exactly 5 timestamps.")

    if dataset.groupby(["cell_id", "timestamp"]).size().max() != 1:
        fail("Duplicate cell_id + timestamp combinations found.")

    if set(dataset["label"].unique()) != {0, 1, 2}:
        fail(f"Unexpected final labels: {set(dataset['label'].unique())}")

    required = (
        SPATIAL_FEATURES
        + WEATHER_FEATURES
        + ["timestamp", "episode_id", "label", "label_meaning"]
    )

    missing_values = dataset[required].isna().sum()
    bad_missing = missing_values[missing_values > 0]
    if len(bad_missing):
        fail(f"Missing values found:\n{bad_missing}")

    expected_episode = {
        "2021-11-08 23:00:00": "Episode_1",
        "2021-11-10 11:00:00": "Episode_1",
        "2021-11-10 18:00:00": "Episode_1",
        "2021-11-12 00:00:00": "Episode_1",
        "2021-11-28 06:00:00": "Episode_2",
    }

    actual_episode = (
        dataset[["timestamp", "episode_id"]]
        .drop_duplicates()
    )

    actual_episode = {
        pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"): row["episode_id"]
        for _, row in actual_episode.iterrows()
    }

    if actual_episode != expected_episode:
        fail(f"Incorrect episode assignment: {actual_episode}")

    print("\n" + "=" * 70)
    print("FINAL QUALITY REPORT")
    print("=" * 70)
    print(f"Shape: {dataset.shape}")
    print(f"Unique cells: {dataset['cell_id'].nunique():,}")
    print(f"Unique timestamps: {dataset['timestamp'].nunique()}")
    print(f"Unique episodes: {dataset['episode_id'].nunique()}")

    print("\nPer-timestamp label counts:")
    print(
        dataset.groupby(["timestamp", "episode_id", "label"])
        .size()
        .unstack(fill_value=0)
        .to_string()
    )

    print("\nOverall label counts:")
    print(dataset["label"].value_counts().sort_index().to_dict())

    print("\nClass 2 count:")
    print(int((dataset["label"] == 2).sum()))

    print("\nMissing values:")
    print("None")

    print("\nMODEL_FEATURES:")
    for feature in MODEL_FEATURES:
        print(f" - {feature}")

    # Normalize timestamps before CSV write. Midnight datetimes must not
    # serialize as date-only strings (e.g. "2021-11-12").
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    dataset["timestamp"] = pd.to_datetime(dataset["timestamp"]).dt.strftime(
        TIMESTAMP_FORMAT
    )
    bad_ts = dataset.loc[
        ~dataset["timestamp"].str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"),
        "timestamp",
    ]
    if len(bad_ts):
        fail(
            "Timestamp strings are not YYYY-MM-DD HH:MM:SS. "
            f"Examples: {bad_ts.unique()[:10].tolist()}"
        )

    # Save only the new Stage 1 output.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved: {OUTPUT_PATH}")
    print("\nSTAGE 1 COMPLETE.")
    print("STOP: Do not train AI #2 yet.")

if __name__ == "__main__":
    main()
