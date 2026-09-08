"""
SIH26071 - STAGE 4
Diagnostic audit of the existing Stage 3 baseline inundation-risk model.

Read-only with respect to Stage 1-3 artifacts:
- does NOT retrain Stage 3
- does NOT modify Stage 3 model files
- does NOT treat class 2 as class 0
- does NOT use random spatial cell splits (uses existing model as-is)
- does NOT claim universal generalization, exact depth, or exact arrival time
- does NOT call >=20mm/6h an IMD "Heavy Rain" category
- does NOT silently fall back to nearest timestamps
- does NOT overwrite existing Stage 3 outputs

Question this script answers:
"Because current rainfall is city-level and broadcast across the 250m
spatial grid, how much of the predicted flood-risk map is really coming
from static terrain rather than spatial rainfall?"

Data-availability note (see section headers below): sections 1 and 5 use
only files committed to git (models, heuristic limits, rainfall_ml_dataset.csv)
and always run. Sections 2, 3, and 4 need row-level access to
data/processed/inundation_risk_ml_dataset.csv, which is correctly gitignored
(>100MB) and is NOT present in a fresh git clone. When that file exists next
to this script (i.e. run locally where Stage 1-3 were built), sections 2-4
run at full row-level fidelity. When it's absent, those sections are skipped
with an explicit WARNING in the report rather than being silently faked with
invented numbers.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = REPO_ROOT / "data/processed/inundation_risk_ml_dataset.csv"
RAINFALL_PATH = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
MODEL_DIR = REPO_ROOT / "models/inundation_risk"
AUDIT_TXT_PATH = REPO_ROOT / "data/processed/inundation_risk_dataset_audit.txt"

OUT_DIR = REPO_ROOT / "data/processed/stage4_diagnostics"

FEATURE_COLUMNS = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]
RAIN_COLUMNS = ["rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h"]
TERRAIN_COLUMNS = ["elevation", "slope_degrees", "distance_to_drainage"]

EPISODE_DEFINITIONS = {
    "Episode_1": ["2021-11-08 23:00:00", "2021-11-10 11:00:00",
                  "2021-11-10 18:00:00", "2021-11-12 00:00:00"],
    "Episode_2": ["2021-11-28 06:00:00"],
}
LOEO_DIRS = ["Episode_1_to_Episode_2", "Episode_2_to_Episode_1"]

# Terrain reference points sourced from the already-committed, already
# row-level-verified Stage 2 audit report (data/processed/inundation_risk_dataset_audit.txt,
# section "Baseline feature distributions by label"). These are NOT invented
# values. If DATASET_PATH is present, section 5 recomputes these live from
# the real per-cell data instead of trusting this fallback copy.
AUDIT_TERRAIN_REFERENCE = {
    "grid_overall": {"elevation": 22.6085, "slope_degrees": 1.32764, "distance_to_drainage": 1254.3},
    "typical_class0_nonflooded": {"elevation": 22.836, "slope_degrees": 1.34104, "distance_to_drainage": 1252.11},
    "typical_class1_flooded": {"elevation": 8.95818, "slope_degrees": 0.542279, "distance_to_drainage": 1438.0},
    "typical_class2_uncertain": {"elevation": 9.92205, "slope_degrees": 0.573972, "distance_to_drainage": 1352.77},
    "grid_p25": {"elevation": 10.1671, "slope_degrees": 0.753856, "distance_to_drainage": 527.12},
    "grid_p75": {"elevation": 40.3439, "slope_degrees": 2.11001, "distance_to_drainage": 2502.97},
}

report_lines = []


def log(msg=""):
    print(msg)
    report_lines.append(str(msg))


def hr(title):
    log()
    log("=" * 72)
    log(title)
    log("=" * 72)


def load_loeo_model(direction: str):
    """Load the existing Stage 3 XGBoost + logistic + heuristic artifacts. No retraining."""
    exp_dir = MODEL_DIR / direction
    xgb = XGBClassifier()
    xgb.load_model(exp_dir / "xgboost.json")
    logistic_bundle = joblib.load(exp_dir / "logistic_regression.joblib")
    with open(exp_dir / "heuristic_limits.json") as f:
        heuristic_limits = json.load(f)
    return xgb, logistic_bundle, heuristic_limits


# =====================================================================
# 1. FEATURE IMPORTANCE (existing models only, no retraining)
# =====================================================================
def section1_feature_importance():
    hr("1. FEATURE IMPORTANCE (existing Stage 3 XGBoost models, gain)")
    rows = []
    for direction in LOEO_DIRS:
        xgb, _, _ = load_loeo_model(direction)
        booster = xgb.get_booster()
        gain = booster.get_score(importance_type="gain")
        weight = booster.get_score(importance_type="weight")
        # Models were fit on a bare numpy array (train_df[FEATURE_COLUMNS].to_numpy()),
        # so xgboost's internal names are f0..f7 in FEATURE_COLUMNS order.
        for i, feat in enumerate(FEATURE_COLUMNS):
            key = f"f{i}"
            rows.append({
                "loeo_direction": direction,
                "feature": feat,
                "gain": gain.get(key, 0.0),
                "weight_split_count": weight.get(key, 0),
            })
        log(f"[{direction}] loaded xgboost.json, {len(gain)} features with nonzero gain")

    df = pd.DataFrame(rows)
    df["gain_rank_within_direction"] = df.groupby("loeo_direction")["gain"].rank(ascending=False, method="min").astype(int)
    df = df.sort_values(["loeo_direction", "gain_rank_within_direction"])
    df.to_csv(OUT_DIR / "stage4_feature_importance.csv", index=False)

    for direction in LOEO_DIRS:
        sub = df[df["loeo_direction"] == direction].sort_values("gain", ascending=False)
        log(f"\n{direction} — ranked by gain:")
        for _, r in sub.iterrows():
            log(f"  {int(r['gain_rank_within_direction'])}. {r['feature']:<22} gain={r['gain']:.4f}  splits={int(r['weight_split_count'])}")

    log("\nIMPORTANT INTERPRETATION NOTE: gain measures how useful a feature is "
        "across the TRAINING ROWS, which span multiple timestamps. Because rainfall "
        "is broadcast identically to all cells WITHIN a single timestamp (see section "
        "3), rainfall gain here reflects differences BETWEEN timestamps, not spatial "
        "differences within any one predicted risk map. For any single inference "
        "timestamp, rainfall is a constant across all 70,626 cells, so by mathematical "
        "necessity 100% of the SPATIAL variation in that map's predicted risk comes "
        "from terrain features, regardless of rainfall's gain rank. The "
        "Episode_2_to_Episode_1 model illustrates this starkly: trained on a single "
        "timestamp (Episode_2), rainfall was perfectly constant across the entire "
        "training set and got zero splits / zero gain — the model could only ever "
        "learn from terrain.")
    return df


# =====================================================================
# 2 & 3 & 4. Row-level sections — need inundation_risk_ml_dataset.csv
# =====================================================================
def load_full_dataset():
    if not DATASET_PATH.exists():
        return None
    log(f"Found {DATASET_PATH} — running row-level sections at full fidelity.")
    df = pd.read_csv(DATASET_PATH, parse_dates=["timestamp"])
    return df


def get_model_predictions(df: pd.DataFrame, direction: str):
    xgb, _, _ = load_loeo_model(direction)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    return xgb.predict_proba(X)[:, 1]


def section2_spatial_homogeneity(df: pd.DataFrame | None):
    hr("2. SPATIAL HOMOGENEITY (per-timestamp prediction statistics)")
    if df is None:
        log("SKIPPED: inundation_risk_ml_dataset.csv not found next to this script. "
            "Run this script locally (repo root, where Stage 1-3 were built) to "
            "produce stage4_spatial_homogeneity.csv.")
        return None

    rows = []
    for direction in LOEO_DIRS:
        test_episode = direction.split("_to_")[1]
        test_mask = df["episode_id"] == test_episode
        preds = get_model_predictions(df, direction)
        df_dir = df.loc[test_mask].copy()
        df_dir["pred"] = preds[test_mask.to_numpy()]

        for ts, g in df_dir.groupby("timestamp"):
            p = g["pred"].to_numpy()
            rows.append({
                "loeo_direction": direction,
                "timestamp": ts,
                "n_cells": len(p),
                "mean": p.mean(), "median": np.median(p), "std": p.std(),
                "min": p.min(), "max": p.max(),
                "p05": np.percentile(p, 5), "p25": np.percentile(p, 25),
                "p75": np.percentile(p, 75), "p95": np.percentile(p, 95),
            })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "stage4_spatial_homogeneity.csv", index=False)
    log(out.to_string(index=False))

    # Nearest-neighbor spatial autocorrelation (Moran's-I-style, k-NN based)
    # using only numpy/scipy (already a dependency via sklearn/scipy stack) —
    # no new heavy dependency added.
    try:
        from scipy.spatial import cKDTree
        log("\nk-NN spatial autocorrelation (k=8 nearest cells by centroid, per timestamp):")
        autocorr_rows = []
        for direction in LOEO_DIRS:
            test_episode = direction.split("_to_")[1]
            test_mask = df["episode_id"] == test_episode
            preds = get_model_predictions(df, direction)
            df_dir = df.loc[test_mask].copy()
            df_dir["pred"] = preds[test_mask.to_numpy()]
            for ts, g in df_dir.groupby("timestamp"):
                coords = g[["centroid_lon", "centroid_lat"]].to_numpy()
                vals = g["pred"].to_numpy()
                tree = cKDTree(coords)
                _, idx = tree.query(coords, k=9)  # self + 8 neighbors
                neighbor_mean = vals[idx[:, 1:]].mean(axis=1)
                if vals.std() > 0:
                    corr = np.corrcoef(vals, neighbor_mean)[0, 1]
                else:
                    corr = float("nan")
                autocorr_rows.append({"loeo_direction": direction, "timestamp": ts,
                                       "knn_autocorrelation_k8": corr})
                log(f"  [{direction}] {ts}: r={corr:.4f}")
        pd.DataFrame(autocorr_rows).to_csv(OUT_DIR / "stage4_spatial_autocorrelation.csv", index=False)
    except ImportError:
        log("scipy not available — skipped spatial autocorrelation (lightweight fallback not implemented, non-blocking).")

    return out


def section3_rainfall_spatial_variation(df: pd.DataFrame | None):
    hr("3. RAINFALL SPATIAL VARIATION (per historical timestamp)")
    cols = RAIN_COLUMNS + (["precipitation"] if df is not None and "precipitation" in df.columns else [])

    if df is not None:
        rows = []
        for ts, g in df.groupby("timestamp"):
            for c in cols:
                v = g[c].to_numpy()
                cv = (v.std() / v.mean()) if v.mean() != 0 else float("nan")
                rows.append({
                    "timestamp": ts, "feature": c,
                    "unique_count": pd.Series(v).nunique(),
                    "min": v.min(), "max": v.max(), "std": v.std(),
                    "coefficient_of_variation": cv,
                })
        out = pd.DataFrame(rows)
        out.to_csv(OUT_DIR / "stage4_rainfall_spatial_variation.csv", index=False)
        log(out.to_string(index=False))
        all_zero_std = (out["std"] == 0).all()
        log(f"\nAll rainfall/precipitation features have std=0 across all 70,626 cells "
            f"at every timestamp: {all_zero_std}")
        return out

    # Fallback: no row-level file, but rainfall_ml_dataset.csv (committed, small)
    # gives us the exact single source value broadcast to every cell at each
    # timestamp. Because the Stage 1 join broadcasts one city-level row per
    # timestamp to all 70,626 cells (by construction, and independently
    # confirmed row-level in the committed Stage 2 audit report — see
    # inundation_risk_dataset_audit.txt, "weather features constant within
    # timestamp"), unique_count=1 / std=0 follows from that architecture. This
    # is reused evidence, not a fresh row-level scan — rerun locally against
    # inundation_risk_ml_dataset.csv for an independent full re-verification.
    log("inundation_risk_ml_dataset.csv not found — using the smaller committed "
        "rainfall_ml_dataset.csv plus the existing Stage 2 audit's row-level finding.")
    if not RAINFALL_PATH.exists():
        log("SKIPPED: rainfall_ml_dataset.csv also not found.")
        return None

    rdf = pd.read_csv(RAINFALL_PATH, parse_dates=["time"])
    rows = []
    for ts_str in sum(EPISODE_DEFINITIONS.values(), []):
        ts = pd.Timestamp(ts_str)
        match = rdf[rdf["time"] == ts]
        if len(match) != 1:
            log(f"  WARNING: expected exactly 1 rainfall row for {ts}, found {len(match)} — skipping.")
            continue
        r = match.iloc[0]
        for c in RAIN_COLUMNS:
            rows.append({
                "timestamp": ts, "feature": c,
                "unique_count_by_construction": 1,
                "value_broadcast_to_all_cells": r[c],
                "std_by_construction": 0.0,
                "source": "rainfall_ml_dataset.csv exact-timestamp value "
                          "+ Stage 2 audit row-level confirmation",
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "stage4_rainfall_spatial_variation.csv", index=False)
    log(out.to_string(index=False))
    if AUDIT_TXT_PATH.exists():
        txt = AUDIT_TXT_PATH.read_text(encoding="utf-8")
        if "weather features constant within timestamp" in txt:
            log("\nConfirmed: committed Stage 2 audit independently verified "
                "row-level constancy of these columns (see audit report, section J).")
    return out


def section4_rainfall_vs_terrain(df: pd.DataFrame | None):
    hr("4. RAINFALL VS TERRAIN — descriptive association with model predictions")
    if df is None:
        log("SKIPPED (row-level version): inundation_risk_ml_dataset.csv not found. "
            "Run locally for per-cell descriptive correlation between predicted risk "
            "and elevation/slope/distance_to_drainage/rainfall accumulation.")
        log("A model-sensitivity-based substitute is provided in section 5 below, "
            "using real historical rainfall quantiles against fixed, audit-verified "
            "terrain reference points — this is not a replacement for the full "
            "per-cell version, only a descriptive stand-in.")
        return None

    rows = []
    for direction in LOEO_DIRS:
        test_episode = direction.split("_to_")[1]
        test_mask = df["episode_id"] == test_episode
        preds = get_model_predictions(df, direction)
        df_dir = df.loc[test_mask].copy()
        df_dir["pred"] = preds[test_mask.to_numpy()]
        for feat in TERRAIN_COLUMNS + RAIN_COLUMNS:
            corr = df_dir["pred"].corr(df_dir[feat])
            rows.append({"loeo_direction": direction, "feature": feat,
                          "pearson_corr_with_predicted_risk": corr})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "stage4_rainfall_terrain_analysis.csv", index=False)
    log(out.to_string(index=False))
    log("\nLanguage note: these are correlations / model sensitivities, not causal claims.")
    return out


# =====================================================================
# 5. CONTROLLED RAINFALL SENSITIVITY (existing model, terrain fixed)
# =====================================================================
def section5_controlled_sensitivity(df: pd.DataFrame | None):
    hr("5. CONTROLLED RAINFALL SENSITIVITY (existing model, terrain fixed)")

    if df is not None:
        terrain_profiles = {}
        for name, cond in [
            ("typical_class0_nonflooded", df["label"] == 0),
            ("typical_class1_flooded", df["label"] == 1),
            ("typical_class2_uncertain", df["label"] == 2),
            ("grid_overall", pd.Series(True, index=df.index)),
        ]:
            sub = df.loc[cond, TERRAIN_COLUMNS]
            terrain_profiles[name] = sub.median().to_dict()
        log("Terrain profiles computed LIVE from inundation_risk_ml_dataset.csv (median per class).")
    else:
        terrain_profiles = AUDIT_TERRAIN_REFERENCE
        log("Terrain profiles NOT available live — reusing fixed reference points already "
            "row-level-computed in the committed Stage 2 audit report (medians by label). "
            "Source: data/processed/inundation_risk_dataset_audit.txt.")

    # Real historical rainfall quantiles (10-year Chennai record), not invented values.
    if not RAINFALL_PATH.exists():
        log("SKIPPED: rainfall_ml_dataset.csv not found — cannot build real rainfall scenarios.")
        return None
    rdf = pd.read_csv(RAINFALL_PATH)
    quantiles = [0.50, 0.75, 0.90, 0.95, 0.99, 0.999, 1.0]
    rainfall_scenarios = {}
    for q in quantiles:
        rainfall_scenarios[f"p{q * 100:g}"] = {c: rdf[c].quantile(q) for c in RAIN_COLUMNS}
    log(f"\nRainfall scenarios drawn from real 10-year distribution quantiles: {list(rainfall_scenarios.keys())}")
    for qname, vals in rainfall_scenarios.items():
        log(f"  {qname}: " + ", ".join(f"{c}={v:.2f}" for c, v in vals.items()))

    rows = []
    for direction in LOEO_DIRS:
        xgb, _, _ = load_loeo_model(direction)
        for terrain_name, terrain_vals in terrain_profiles.items():
            preds = []
            for qname, rain_vals in rainfall_scenarios.items():
                feat_row = {**rain_vals, **terrain_vals}
                x = np.array([[feat_row[c] for c in FEATURE_COLUMNS]], dtype=float)
                pred = xgb.predict_proba(x)[0, 1]
                preds.append(pred)
                rows.append({
                    "loeo_direction": direction, "terrain_profile": terrain_name,
                    "rainfall_scenario": qname, "predicted_risk": pred,
                    **{f"terrain_{k}": v for k, v in terrain_vals.items()},
                    **{f"rain_{k}": v for k, v in rain_vals.items()},
                })
            preds = np.array(preds)
            log(f"[{direction}] terrain={terrain_name}: risk across rainfall scenarios "
                f"mean={preds.mean():.4f} std={preds.std():.4f} min={preds.min():.4f} "
                f"p50={np.percentile(preds, 50):.4f} max={preds.max():.4f}")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "stage4_controlled_rainfall_sensitivity.csv", index=False)
    log("\nLabelled explicitly as sensitivity analysis of the EXISTING Stage 3 model "
        "under fixed terrain / real historical rainfall scenarios — not a new model, "
        "not retraining.")
    return out


# =====================================================================
# 6. LIMITATIONS REPORT
# =====================================================================
def section6_limitations():
    hr("6. LIMITATIONS")
    limitations = [
        "Rainfall (rain_1h..rain_24h and all other weather columns) is a single "
        "city-level Chennai station value broadcast identically to all 70,626 cells "
        "at each timestamp. The model therefore has zero spatial rainfall signal to "
        "learn from; any spatial pattern in its predictions comes from terrain "
        "(elevation, slope, distance_to_drainage), not from where rain fell.",
        "The 250m spatial grid resolution describes terrain/hydrology resolution "
        "only. Rainfall resolution is effectively a single point for the whole "
        "Chennai Metropolitan Region — the two are not the same resolution and "
        "should not be conflated when describing the system to reviewers.",
        "Stage 3 trains and evaluates on OBSERVED historical rainfall. A future "
        "operational system would need to run on FORECAST rainfall (AI #1's output), "
        "which has its own uncertainty not represented in these Stage 3 numbers.",
        "AI #1 (rainfall model) cannot be used to regenerate forecasts for the "
        "2021 flood dates used here, because AI #1 was trained through 2022 and "
        "using it on 2021 dates it may have seen in training would itself be a "
        "leakage risk; this is why Stage 3 uses observed rainfall, not AI #1 output.",
        "Only two independently verified rainfall/flood episodes exist (Nov 2021 "
        "Episode 1 and Episode 2). Leave-One-Episode-Out results are exploratory "
        "event-level generalization, not a statistically powered validation.",
        "distance_to_drainage is derived from OpenStreetMap waterway line "
        "features, which have unknown and possibly inconsistent survey/edit dates "
        "relative to the 2021 flood events (temporal uncertainty in the drainage "
        "network itself).",
        "Stage 3 is a baseline / proof-of-concept model selected only if it beat "
        "the majority-class, elevation+drainage heuristic, and logistic-regression "
        "baselines on the held-out episode. It has not been operationally validated "
        "against independent flood events, ground-truthed depth data, or a live "
        "forecasting pipeline.",
        "Most impactful next data improvement: a spatially distributed rainfall "
        "product (radar-derived or a gridded reanalysis/satellite rainfall dataset "
        "covering the CMR) would let the model learn genuine spatial rainfall "
        "structure instead of relying entirely on static terrain to differentiate "
        "cells.",
    ]
    for i, l in enumerate(limitations, 1):
        log(f"{i}. {l}")
    return limitations


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hr("SIH26071 STAGE 4 — SPATIAL DIAGNOSTIC AUDIT")
    log(f"Repo root: {REPO_ROOT}")
    log(f"Dataset present (inundation_risk_ml_dataset.csv): {DATASET_PATH.exists()}")

    section1_feature_importance()
    df = load_full_dataset()
    section2_spatial_homogeneity(df)
    section3_rainfall_spatial_variation(df)
    section4_rainfall_vs_terrain(df)
    section5_controlled_sensitivity(df)
    section6_limitations()

    report_path = OUT_DIR / "stage4_diagnostic_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    hr("DONE")
    log(f"Report: {report_path}")
    log(f"Outputs directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
