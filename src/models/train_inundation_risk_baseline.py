"""
SIH26071 - STAGE 3
Train and evaluate the baseline inundation-risk model (AI #2).

Leave-One-Episode-Out outer validation + inner 5 km spatial-block CV.
Does not use AI #1 predictions or future rainfall.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from scipy.spatial import cKDTree
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation.evaluate_inundation_risk_baseline import (  # noqa: E402
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    METADATA_PATH,
    REPORT_TXT,
    RESULTS_CSV,
    assert_no_forbidden_features,
    compute_binary_metrics,
    fail,
    run_leakage_checks,
    select_threshold_max_csi,
    write_report,
)

DATASET_PATH = REPO_ROOT / "data/processed/inundation_risk_ml_dataset.csv"
MODEL_DIR = REPO_ROOT / "models/inundation_risk"

RANDOM_STATE = 42
SPATIAL_BLOCK_CRS = "EPSG:32644"
SPATIAL_BLOCK_SIZE_M = 5000.0
SPATIAL_BUFFER_M = 500.0
N_INNER_FOLDS = 5

EXPECTED_ROWS = 353130
EXPECTED_CELLS = 70626
EXPECTED_TIMESTAMPS = 5
ALLOWED_LABELS = {0, 1, 2}

EPISODE_DEFINITIONS = {
    "Episode_1": [
        "2021-11-08 23:00:00",
        "2021-11-10 11:00:00",
        "2021-11-10 18:00:00",
        "2021-11-12 00:00:00",
    ],
    "Episode_2": [
        "2021-11-28 06:00:00",
    ],
}

LOEO_EXPERIMENTS = [
    {"train": "Episode_1", "test": "Episode_2"},
    {"train": "Episode_2", "test": "Episode_1"},
]

XGB_GRID = [
    {"max_depth": d, "n_estimators": n, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8}
    for d in (3, 4, 5)
    for n in (100, 300)
]


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        fail(f"Missing dataset: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    if "timestamp" not in df.columns:
        fail("Dataset is missing timestamp.")
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    if len(df) != EXPECTED_ROWS:
        fail(f"Expected {EXPECTED_ROWS:,} rows, found {len(df):,}")
    if df["cell_id"].nunique() != EXPECTED_CELLS:
        fail(f"Expected {EXPECTED_CELLS:,} cells, found {df['cell_id'].nunique():,}")
    if df["timestamp"].nunique() != EXPECTED_TIMESTAMPS:
        fail(f"Expected {EXPECTED_TIMESTAMPS} timestamps, found {df['timestamp'].nunique()}")
    if int(df.duplicated(subset=["cell_id", "timestamp"]).sum()) != 0:
        fail("Duplicate cell_id + timestamp rows found.")

    found_labels = set(pd.to_numeric(df["label"], errors="coerce").dropna().astype(int).unique())
    if found_labels != ALLOWED_LABELS:
        fail(f"Unexpected labels: {found_labels}")

    missing_feats = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_feats:
        fail(f"Missing required features: {missing_feats}")
    for col in ["cell_id", "timestamp", "episode_id", "label", "centroid_lon", "centroid_lat"]:
        if col not in df.columns:
            fail(f"Missing required column: {col}")

    na_feats = df[FEATURE_COLUMNS].isna().sum()
    if na_feats.sum() > 0:
        fail(f"Missing values in features:\n{na_feats[na_feats > 0]}")

    actual_map = (
        df[["timestamp", "episode_id"]]
        .drop_duplicates()
        .sort_values("timestamp")
    )
    expected_pairs = []
    for ep, stamps in EPISODE_DEFINITIONS.items():
        for ts in stamps:
            expected_pairs.append((ts, ep))
    actual_pairs = [
        (row["timestamp"], row["episode_id"]) for _, row in actual_map.iterrows()
    ]
    if sorted(actual_pairs) != sorted(expected_pairs):
        fail(f"Episode assignment mismatch.\nexpected={expected_pairs}\nactual={actual_pairs}")

    for ep in EPISODE_DEFINITIONS:
        if ep not in set(df["episode_id"]):
            fail(f"Missing episode: {ep}")

    assert_no_forbidden_features(FEATURE_COLUMNS)
    return df


def filter_binary(df: pd.DataFrame) -> pd.DataFrame:
    labels = pd.to_numeric(df["label"], errors="coerce")
    if labels.isna().any():
        fail("Non-numeric labels found.")
    df = df.copy()
    df["label"] = labels.astype(int)
    binary = df[df["label"].isin([0, 1])].copy()
    if (binary["label"] == 2).any():
        fail("Class 2 leaked into the binary table.")
    if len(binary) == 0:
        fail("Binary table is empty after excluding class 2.")
    return binary.reset_index(drop=True)


def assign_spatial_blocks(df: pd.DataFrame) -> pd.DataFrame:
    try:
        crs = CRS.from_user_input(SPATIAL_BLOCK_CRS)
    except Exception as exc:
        fail(f"Invalid spatial-block CRS {SPATIAL_BLOCK_CRS}: {exc}")
    if crs.is_geographic:
        fail(f"Spatial-block CRS must be projected (metres). Got geographic CRS {crs}.")

    transformer = Transformer.from_crs("EPSG:4326", SPATIAL_BLOCK_CRS, always_xy=True)
    easting, northing = transformer.transform(
        df["centroid_lon"].to_numpy(),
        df["centroid_lat"].to_numpy(),
    )
    easting = np.asarray(easting, dtype=float)
    northing = np.asarray(northing, dtype=float)
    if np.isnan(easting).any() or np.isnan(northing).any():
        fail("Projected coordinates contain NaN.")

    df = df.copy()
    df["easting_m"] = easting
    df["northing_m"] = northing
    df["block_ix"] = np.floor(df["easting_m"] / SPATIAL_BLOCK_SIZE_M).astype(int)
    df["block_iy"] = np.floor(df["northing_m"] / SPATIAL_BLOCK_SIZE_M).astype(int)
    df["spatial_block_id"] = (
        df["block_ix"].astype(str) + "_" + df["block_iy"].astype(str)
    )
    # Projected metres are identifiers for CV only; they are not model features.
    return df


def unique_cell_table(df: pd.DataFrame) -> pd.DataFrame:
    cells = (
        df[["cell_id", "easting_m", "northing_m", "spatial_block_id"]]
        .drop_duplicates(subset=["cell_id"])
        .reset_index(drop=True)
    )
    if len(cells) != df["cell_id"].nunique():
        fail("Cell table construction failed uniqueness check.")
    return cells


def spatial_block_folds(cell_table: pd.DataFrame, n_splits: int = N_INNER_FOLDS):
    blocks = np.array(sorted(cell_table["spatial_block_id"].unique()))
    if len(blocks) < n_splits:
        fail(
            f"Only {len(blocks)} spatial blocks; cannot run {n_splits}-fold block CV."
        )
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    dummy = np.zeros(len(blocks))
    for train_idx, val_idx in splitter.split(dummy):
        train_blocks = set(blocks[train_idx])
        val_blocks = set(blocks[val_idx])
        val_cells = cell_table[cell_table["spatial_block_id"].isin(val_blocks)].copy()
        train_cells = cell_table[cell_table["spatial_block_id"].isin(train_blocks)].copy()
        if len(val_cells) == 0 or len(train_cells) == 0:
            fail("A spatial fold produced an empty train or validation cell set.")

        tree = cKDTree(val_cells[["easting_m", "northing_m"]].to_numpy())
        dist, _ = tree.query(train_cells[["easting_m", "northing_m"]].to_numpy(), k=1)
        keep = dist >= SPATIAL_BUFFER_M
        train_cells = train_cells.loc[keep]
        if len(train_cells) == 0:
            fail("Spatial buffer removed every training cell in a fold.")

        yield set(train_cells["cell_id"].tolist()), set(val_cells["cell_id"].tolist())


def class_counts(y: np.ndarray) -> tuple[int, int, float]:
    y = np.asarray(y).astype(int)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if len(y) == 0:
        fail("Empty label vector.")
    return n_pos, n_neg, n_pos / len(y)


def scale_pos_weight_from_y(y: np.ndarray) -> float:
    n_pos, n_neg, _ = class_counts(y)
    if n_pos == 0:
        fail("Cannot compute scale_pos_weight: training fold has no positives.")
    return n_neg / n_pos


def heuristic_limits(train_df: pd.DataFrame) -> dict:
    elev = train_df["elevation"].to_numpy(dtype=float)
    drain = train_df["distance_to_drainage"].to_numpy(dtype=float)
    elev_min, elev_max = float(np.min(elev)), float(np.max(elev))
    drain_min, drain_max = float(np.min(drain)), float(np.max(drain))
    if elev_max == elev_min:
        fail("Heuristic elevation range is zero; cannot normalize.")
    if drain_max == drain_min:
        fail("Heuristic drainage-distance range is zero; cannot normalize.")
    return {
        "elev_min": elev_min,
        "elev_max": elev_max,
        "drain_min": drain_min,
        "drain_max": drain_max,
    }


def heuristic_scores(df: pd.DataFrame, limits: dict) -> np.ndarray:
    elev_score = (limits["elev_max"] - df["elevation"].to_numpy(dtype=float)) / (
        limits["elev_max"] - limits["elev_min"]
    )
    drain_score = (limits["drain_max"] - df["distance_to_drainage"].to_numpy(dtype=float)) / (
        limits["drain_max"] - limits["drain_min"]
    )
    return np.clip(0.5 * elev_score + 0.5 * drain_score, 0.0, 1.0)


def fit_logistic(X_train, y_train) -> tuple[StandardScaler, LogisticRegression, dict]:
    n_pos, n_neg, _ = class_counts(y_train)
    if n_pos == 0 or n_neg == 0:
        fail("Logistic regression training fold is missing a class.")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    # Balanced weights from this training fit only.
    clf = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        class_weight="balanced",
        max_iter=2000,
        random_state=RANDOM_STATE,
    )
    clf.fit(X_scaled, y_train)
    info = {
        "C": 1.0,
        "penalty": "l2 (sklearn default)",
        "solver": "lbfgs",
        "class_weight": "balanced",
        "n_train_positive": n_pos,
        "n_train_negative": n_neg,
        "scale_pos_weight_equivalent": n_neg / n_pos,
    }
    return scaler, clf, info


def logistic_scores(scaler: StandardScaler, clf: LogisticRegression, X) -> np.ndarray:
    return clf.predict_proba(scaler.transform(X))[:, 1]


def fit_xgboost(X_train, y_train, params: dict) -> tuple[XGBClassifier, dict]:
    spw = scale_pos_weight_from_y(y_train)
    model = XGBClassifier(
        max_depth=params["max_depth"],
        n_estimators=params["n_estimators"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        objective="binary:logistic",
        eval_metric="aucpr",
        scale_pos_weight=spw,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(X_train, y_train)
    info = dict(params)
    info["scale_pos_weight"] = float(spw)
    info["random_state"] = RANDOM_STATE
    return model, info


def xgb_scores(model: XGBClassifier, X) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def oof_frame(train_df: pd.DataFrame) -> pd.DataFrame:
    oof = train_df[["cell_id", "timestamp", "label"]].copy()
    oof["majority"] = np.nan
    oof["heuristic"] = np.nan
    oof["logistic"] = np.nan
    return oof


def collect_oof_scores(train_df: pd.DataFrame) -> tuple[pd.DataFrame, dict, list]:
    """
    Inner spatial-block CV on the OUTER TRAINING episode only.
    Returns OOF scores for thresholding plus the selected XGBoost config.
    """
    cell_table = unique_cell_table(train_df)
    folds = list(spatial_block_folds(cell_table))
    xgb_oof = {i: np.full(len(train_df), np.nan) for i in range(len(XGB_GRID))}
    base_oof = oof_frame(train_df)
    index_map = pd.Series(np.arange(len(train_df)), index=train_df.index)

    fold_summaries = []
    for fold_i, (train_cells, val_cells) in enumerate(folds, start=1):
        overlap = train_cells & val_cells
        if overlap:
            fail(f"Inner fold {fold_i} has train/val cell overlap ({len(overlap)} cells).")
        tr = train_df[train_df["cell_id"].isin(train_cells)]
        va = train_df[train_df["cell_id"].isin(val_cells)]
        if len(tr) == 0 or len(va) == 0:
            fail(f"Inner fold {fold_i} has empty train or validation rows.")
        if set(tr["episode_id"].unique()) != set(train_df["episode_id"].unique()):
            # Train rows are a spatial subset of the same outer-train episode.
            pass
        y_tr = tr["label"].to_numpy(int)
        y_va = va["label"].to_numpy(int)
        n_pos_tr, n_neg_tr, prev_tr = class_counts(y_tr)
        n_pos_va, n_neg_va, prev_va = class_counts(y_va)
        fold_summaries.append(
            {
                "fold": fold_i,
                "n_train_rows": int(len(tr)),
                "n_val_rows": int(len(va)),
                "n_train_cells": int(tr["cell_id"].nunique()),
                "n_val_cells": int(va["cell_id"].nunique()),
                "train_positives": n_pos_tr,
                "val_positives": n_pos_va,
                "train_prevalence": prev_tr,
                "val_prevalence": prev_va,
            }
        )
        if n_pos_tr == 0 or n_neg_tr == 0:
            fail(f"Inner fold {fold_i} training set is missing a class.")
        if n_pos_va == 0:
            print(
                f"    WARNING: inner fold {fold_i} validation set has 0 positives "
                "(positives are spatially clustered; OOF still pooled)."
            )

        val_pos = index_map.loc[va.index].to_numpy()

        base_oof.iloc[val_pos, base_oof.columns.get_loc("majority")] = prev_tr
        limits = heuristic_limits(tr)
        base_oof.iloc[val_pos, base_oof.columns.get_loc("heuristic")] = heuristic_scores(va, limits)

        X_tr = tr[FEATURE_COLUMNS].to_numpy(dtype=float)
        X_va = va[FEATURE_COLUMNS].to_numpy(dtype=float)
        scaler, clf, _ = fit_logistic(X_tr, y_tr)
        base_oof.iloc[val_pos, base_oof.columns.get_loc("logistic")] = logistic_scores(scaler, clf, X_va)

        for cfg_i, cfg in enumerate(XGB_GRID):
            model, _ = fit_xgboost(X_tr, y_tr, cfg)
            xgb_oof[cfg_i][val_pos] = xgb_scores(model, X_va)

        print(
            f"    inner fold {fold_i}/{len(folds)}: "
            f"train_rows={len(tr):,} val_rows={len(va):,} "
            f"train_pos={n_pos_tr} val_pos={n_pos_va}"
        )

    if base_oof[["majority", "heuristic", "logistic"]].isna().any().any():
        fail("Incomplete inner-CV OOF scores for baseline/logistic models.")

    y_oof = train_df["label"].to_numpy(int)
    best_cfg_i = None
    best_pr = -np.inf
    best_complexity = (999, 999)
    cfg_scores = []
    for cfg_i, cfg in enumerate(XGB_GRID):
        scores = xgb_oof[cfg_i]
        if np.isnan(scores).any():
            fail(f"Incomplete XGBoost OOF scores for config {cfg}")
        metrics = compute_binary_metrics(y_oof, scores, (scores >= 0.5).astype(int))
        pr = metrics["PR_AUC"]
        complexity = (cfg["max_depth"], cfg["n_estimators"])
        cfg_scores.append({"config": cfg, "oof_PR_AUC": pr})
        if (pr > best_pr) or (np.isclose(pr, best_pr) and complexity < best_complexity):
            best_pr = pr
            best_cfg_i = cfg_i
            best_complexity = complexity
    if best_cfg_i is None:
        fail("XGBoost inner search failed to select a configuration.")

    base_oof["xgboost"] = xgb_oof[best_cfg_i]
    selected = {
        "params": dict(XGB_GRID[best_cfg_i]),
        "oof_PR_AUC": float(best_pr),
        "all_configs": cfg_scores,
    }
    return base_oof, selected, fold_summaries


def evaluate_on_test(y_true, scores, threshold: float) -> dict:
    pred = (np.asarray(scores) >= threshold).astype(int)
    return compute_binary_metrics(y_true, scores, pred)


def run_loeo_experiment(binary: pd.DataFrame, train_ep: str, test_ep: str) -> dict:
    train_df = binary[binary["episode_id"] == train_ep].copy()
    test_df = binary[binary["episode_id"] == test_ep].copy()
    if len(train_df) == 0:
        fail(f"Empty training set for {train_ep}.")
    if len(test_df) == 0:
        fail(f"Empty test set for {test_ep}.")
    if set(train_df["timestamp"]) & set(test_df["timestamp"]):
        fail("Train and test episodes share timestamps.")

    train_pos, train_neg, train_prev = class_counts(train_df["label"])
    test_pos, test_neg, test_prev = class_counts(test_df["label"])
    print(
        f"\n  class balance: train {train_ep} rows={len(train_df):,} "
        f"pos={train_pos} neg={train_neg} prev={train_prev:.6f}"
    )
    print(
        f"                 test  {test_ep} rows={len(test_df):,} "
        f"pos={test_pos} neg={test_neg} prev={test_prev:.6f}"
    )

    print("  inner spatial-block CV (outer test episode untouched)...")
    oof, xgb_selected, fold_summaries = collect_oof_scores(train_df)
    y_oof = oof["label"].to_numpy(int)

    heur_threshold, _ = select_threshold_max_csi(y_oof, oof["heuristic"].to_numpy())
    log_threshold, _ = select_threshold_max_csi(y_oof, oof["logistic"].to_numpy())
    xgb_threshold, _ = select_threshold_max_csi(y_oof, oof["xgboost"].to_numpy())
    majority_threshold = 1.0  # always predict 0; CSI search is degenerate for a constant score

    print("  fitting final models on the full outer training episode...")
    X_train = train_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train_df["label"].to_numpy(int)
    X_test = test_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(int)

    majority_scores = np.full(len(test_df), train_prev)
    limits = heuristic_limits(train_df)
    heuristic_test = heuristic_scores(test_df, limits)
    scaler, log_clf, log_info = fit_logistic(X_train, y_train)
    logistic_test = logistic_scores(scaler, log_clf, X_test)
    xgb_model, xgb_info = fit_xgboost(X_train, y_train, xgb_selected["params"])
    xgb_test = xgb_scores(xgb_model, X_test)

    exp_dir = MODEL_DIR / f"{train_ep}_to_{test_ep}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "model": log_clf, "features": FEATURE_COLUMNS}, exp_dir / "logistic_regression.joblib")
    xgb_model.save_model(exp_dir / "xgboost.json")
    (exp_dir / "heuristic_limits.json").write_text(json.dumps(limits, indent=2), encoding="utf-8")

    rows = []
    model_payloads = [
        ("majority_baseline", majority_scores, majority_threshold, {"constant_score": "train_prevalence"}),
        ("elevation_drainage_heuristic", heuristic_test, heur_threshold, limits),
        ("logistic_regression", logistic_test, log_threshold, log_info),
        ("xgboost", xgb_test, xgb_threshold, xgb_info),
    ]
    for name, scores, threshold, extra in model_payloads:
        metrics = evaluate_on_test(y_test, scores, threshold)
        row = {
            "model": name,
            "outer_train_episode": train_ep,
            "outer_test_episode": test_ep,
            "threshold": threshold,
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "train_positives": train_pos,
            "train_negatives": train_neg,
            "train_prevalence": train_prev,
            "test_positives": test_pos,
            "test_negatives": test_neg,
            "test_prevalence": test_prev,
            **metrics,
            "extra": extra,
        }
        rows.append(row)
        print(
            f"    {name}: threshold={threshold:.4f} PR-AUC={metrics['PR_AUC']:.4f} "
            f"CSI={metrics['CSI']:.4f} recall={metrics['recall']:.4f}"
        )

    return {
        "rows": rows,
        "xgb_selected": xgb_selected,
        "fold_summaries": fold_summaries,
        "logistic_info": log_info,
        "heuristic_limits": limits,
        "balance": {
            "train_episode": train_ep,
            "test_episode": test_ep,
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "train_positives": train_pos,
            "train_negatives": train_neg,
            "train_prevalence": train_prev,
            "test_positives": test_pos,
            "test_negatives": test_neg,
            "test_prevalence": test_prev,
        },
        "thresholds": {
            "majority_baseline": majority_threshold,
            "elevation_drainage_heuristic": heur_threshold,
            "logistic_regression": log_threshold,
            "xgboost": xgb_threshold,
        },
    }


def main() -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    print("=" * 72)
    print("SIH26071 STAGE 3 - BASELINE INUNDATION-RISK MODEL (AI #2)")
    print("=" * 72)

    raw = load_dataset()
    n_class2 = int((raw["label"] == 2).sum())
    binary = filter_binary(raw)
    binary = assign_spatial_blocks(binary)
    leakage_lines = run_leakage_checks(raw, binary, FEATURE_COLUMNS)

    n_blocks = binary["spatial_block_id"].nunique()
    print(f"Raw rows: {len(raw):,}")
    print(f"Class 2 excluded: {n_class2:,}")
    print(f"Binary rows: {len(binary):,}")
    print(f"Spatial blocks ({SPATIAL_BLOCK_SIZE_M:.0f} m, {SPATIAL_BLOCK_CRS}): {n_blocks}")
    print(f"Spatial buffer: {SPATIAL_BUFFER_M:.0f} m")
    print(f"Features: {FEATURE_COLUMNS}")
    print(f"Forbidden (not used): {FORBIDDEN_FEATURES}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    balances = []
    experiment_meta = []
    for spec in LOEO_EXPERIMENTS:
        print("\n" + "=" * 72)
        print(f"LOEO: train {spec['train']}  ->  test {spec['test']}")
        print("=" * 72)
        result = run_loeo_experiment(binary, spec["train"], spec["test"])
        all_rows.extend(result["rows"])
        balances.append(result["balance"])
        experiment_meta.append(
            {
                "outer_train_episode": spec["train"],
                "outer_test_episode": spec["test"],
                "thresholds": result["thresholds"],
                "xgboost_selected": result["xgb_selected"]["params"],
                "xgboost_inner_oof_PR_AUC": result["xgb_selected"]["oof_PR_AUC"],
                "xgboost_all_configs": result["xgb_selected"]["all_configs"],
                "logistic": result["logistic_info"],
                "heuristic_limits": result["heuristic_limits"],
                "inner_folds": result["fold_summaries"],
                "class_balance": result["balance"],
            }
        )

    results_records = []
    for row in all_rows:
        results_records.append(
            {
                "model": row["model"],
                "outer_train_episode": row["outer_train_episode"],
                "outer_test_episode": row["outer_test_episode"],
                "threshold": row["threshold"],
                "PR_AUC": row["PR_AUC"],
                "CSI": row["CSI"],
                "recall": row["recall"],
                "precision": row["precision"],
                "F1": row["F1"],
                "ROC_AUC": row["ROC_AUC"],
                "Brier": row["Brier"],
                "TP": row["TP"],
                "FP": row["FP"],
                "FN": row["FN"],
                "TN": row["TN"],
                "train_rows": row["train_rows"],
                "test_rows": row["test_rows"],
                "train_positives": row["train_positives"],
                "train_negatives": row["train_negatives"],
                "train_prevalence": row["train_prevalence"],
                "test_positives": row["test_positives"],
                "test_negatives": row["test_negatives"],
                "test_prevalence": row["test_prevalence"],
            }
        )
    results = pd.DataFrame(results_records)
    expected_models = {
        "majority_baseline",
        "elevation_drainage_heuristic",
        "logistic_regression",
        "xgboost",
    }
    if set(results["model"]) != expected_models:
        fail(f"Result models mismatch: {set(results['model'])}")
    if results.groupby(["outer_train_episode", "outer_test_episode"]).ngroups != 2:
        fail("Both LOEO directions were not completed.")
    if len(results) != 8:
        fail(f"Expected 8 result rows (4 models x 2 experiments), found {len(results)}")

    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_CSV, index=False)

    metadata = {
        "stage": 3,
        "task": "baseline_inundation_risk_ai2",
        "dataset_path": str(DATASET_PATH),
        "feature_list": FEATURE_COLUMNS,
        "forbidden_features": FORBIDDEN_FEATURES,
        "random_seed": RANDOM_STATE,
        "episode_definitions": EPISODE_DEFINITIONS,
        "spatial_block_size_m": SPATIAL_BLOCK_SIZE_M,
        "spatial_block_crs": SPATIAL_BLOCK_CRS,
        "spatial_buffer_m": SPATIAL_BUFFER_M,
        "inner_folds": N_INNER_FOLDS,
        "threshold_selection_method": (
            "maximize CSI on inner spatial-block OOF scores from the outer "
            "training episode; majority baseline always predicts 0"
        ),
        "n_raw_rows": int(len(raw)),
        "n_binary_rows": int(len(binary)),
        "n_class2_excluded": n_class2,
        "n_cells": int(raw["cell_id"].nunique()),
        "n_timestamps": int(raw["timestamp"].nunique()),
        "n_spatial_blocks": int(n_blocks),
        "experiments": experiment_meta,
        "results": results_records,
        "leakage_checks": leakage_lines,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    write_report(results, metadata, leakage_lines, balances, REPORT_TXT)

    print("\n" + "=" * 72)
    print("EXPERIMENT SUMMARY")
    print("=" * 72)
    summary_cols = [
        "model", "outer_train_episode", "outer_test_episode",
        "threshold", "PR_AUC", "CSI", "recall", "precision", "F1",
    ]
    print(results[summary_cols].to_string(index=False))
    print("\nMean PR-AUC by model:")
    print(results.groupby("model")["PR_AUC"].mean().sort_values(ascending=False).to_string())
    print("\nMean CSI by model:")
    print(results.groupby("model")["CSI"].mean().sort_values(ascending=False).to_string())
    print(f"\nSaved: {RESULTS_CSV}")
    print(f"Saved: {REPORT_TXT}")
    print(f"Saved: {METADATA_PATH}")
    print("\nSTAGE 3 COMPLETE.")
    print("Interpretation: exploratory event-generalization evidence only.")


if __name__ == "__main__":
    main()
