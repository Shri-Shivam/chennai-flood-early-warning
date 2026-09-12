"""SIH26071 - Stage 7: controlled AI #1 -> AI #2 integration.

Reconstructed against the NEW (superseding) Stage 7 master specification.
This replaces the earlier Stage7 implementation, which followed the
original spec's experiment definitions and a fixed 0.50 threshold.

Experiments:
  Exp_A_Baseline               : terrain + observed rainfall only
  Exp_B_Baseline_plus_AI1      : Exp A features + AI #1 forecast probability
  Exp_C_AI1_Only                : AI #1 forecast probability only
  Exp_D_NonAI_Rain24h_Baseline : deterministic, non-AI score = raw rain_24h (mm)
                                  No model fitting occurs for this experiment;
                                  it exists purely to check whether Exp B's
                                  apparent value (if any) is more than "more
                                  rainfall information."

Validation design:
  Outer: Leave-One-Episode-Out, both directions (Episode_1 <-> Episode_2).
  Inner (training episode only): 5km x 5km spatial blocks in EPSG:32644,
  K-fold over blocks (K=5, or fewer if too few blocks exist), with training
  candidate cells excluded if they lie within a 500m buffer of the held-out
  fold's validation cells (nearest-cell euclidean distance, not block-box
  adjacency). Out-of-fold scores are collected across all folds and used to
  select a threshold that maximizes CSI (tie-break: higher F1, then the
  smaller threshold value). The threshold is then frozen and applied exactly
  once to the fully held-out test episode. The held-out episode never
  participates in block assignment, model fitting, or threshold selection.

Leakage controls:
  - Class 2 ("uncertain") rows are excluded from this binary experiment and
    are never relabeled as 0 or 1.
  - AI #1 forecast probability/amount are merged on an EXACT timestamp match
    only. A required timestamp missing from the AI #1 forecast file raises a
    hard error rather than silently dropping rows via a default inner join.
  - future_6h_rain, target, and label are never used as AI #2 predictors.
  - AI #1 predictions used here come from data/processed/ai1_retrospective_forecast_2021.csv,
    which Stage 6 generates from a model trained strictly through
    2021-10-31 23:00 -- i.e. causally available at each of the five
    Stage 7 timestamps, not from any model trained across those dates.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from sklearn.model_selection import KFold
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/processed/inundation_risk_ml_dataset.csv"
AI1 = ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
OUT_PRED = ROOT / "data/processed/stage7_ai1_ai2_predictions.csv"
OUT_METRICS = ROOT / "data/processed/stage7_model_comparison.csv"
OUT_REPORT = ROOT / "data/processed/stage7_report.txt"
MODEL_DIR = ROOT / "models/stage7_integrated"

BASE_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]
LEARNED_EXPERIMENTS = {
    "Exp_A_Baseline": BASE_FEATURES,
    "Exp_B_Baseline_plus_AI1": BASE_FEATURES + ["ai1_probability"],
    "Exp_C_AI1_Only": ["ai1_probability"],
}

BLOCK_SIZE_M = 5000.0
BUFFER_M = 500.0
N_INNER_FOLDS = 5
REQUIRED_TIMESTAMPS = 5

XGB_PARAMS = dict(
    n_estimators=250,
    max_depth=5,
    learning_rate=0.08,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="aucpr",
    random_state=42,
    n_jobs=-1,
    tree_method="hist",
)


def load():
    d = pd.read_csv(DATA)
    d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Class 2 ("uncertain") excluded from the primary binary experiment; never relabeled.
    d = d[d["label"].isin([0, 1])].copy()

    ai1 = pd.read_csv(AI1)
    ai1["timestamp"] = pd.to_datetime(ai1["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    ai1 = ai1.rename(columns={
        "predicted_probability": "ai1_probability",
        "predicted_amount_mm": "ai1_amount_mm",
    })

    required_ts = set(d["timestamp"].unique())
    available_ts = set(ai1["timestamp"].unique())
    missing = required_ts - available_ts
    if missing:
        raise RuntimeError(
            f"AI#1 forecast is missing for required timestamp(s): {sorted(missing)}. "
            "Refusing to proceed via a silently-dropping inner join."
        )

    n_before = len(d)
    merged = d.merge(
        ai1[["timestamp", "ai1_probability", "ai1_amount_mm"]],
        on="timestamp", how="left", validate="many_to_one",
    )
    if len(merged) != n_before:
        raise RuntimeError(f"Row count changed during AI#1 merge: {n_before} -> {len(merged)}.")
    if merged["ai1_probability"].isna().any() or merged["ai1_amount_mm"].isna().any():
        raise RuntimeError("AI#1 merge produced missing values despite a complete timestamp check.")
    if merged["timestamp"].nunique() != REQUIRED_TIMESTAMPS:
        raise RuntimeError(
            f"Expected {REQUIRED_TIMESTAMPS} unique timestamps after merge, "
            f"found {merged['timestamp'].nunique()}."
        )

    forbidden = {"future_6h_rain", "target", "label"}
    used_predictor_cols = set(BASE_FEATURES) | {"ai1_probability"}
    bad = used_predictor_cols & forbidden
    if bad:
        raise AssertionError(f"Forbidden leakage columns present in a predictor set: {bad}")

    return merged


def project_unique_cells(d):
    cells = (
        d[["cell_id", "centroid_lon", "centroid_lat"]]
        .drop_duplicates("cell_id")
        .reset_index(drop=True)
    )
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    x, y = transformer.transform(cells["centroid_lon"].to_numpy(), cells["centroid_lat"].to_numpy())
    cells["x"] = x
    cells["y"] = y
    block_i = np.floor(x / BLOCK_SIZE_M).astype(int)
    block_j = np.floor(y / BLOCK_SIZE_M).astype(int)
    cells["block_id"] = block_i.astype(str) + "_" + block_j.astype(str)
    return cells[["cell_id", "x", "y", "block_id"]]


def build_inner_folds(cell_geo, seed=42):
    """Partition the training episode's spatial blocks into inner CV folds,
    enforcing a 500m buffer between each fold's validation cells and the
    candidate training cells used for that fold.
    """
    unique_blocks = np.sort(cell_geo["block_id"].unique())
    n_splits = min(N_INNER_FOLDS, len(unique_blocks))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

    folds = []
    for fold_idx, (_, val_block_idx) in enumerate(kf.split(unique_blocks)):
        val_blocks = set(unique_blocks[val_block_idx])
        val_cells = cell_geo[cell_geo["block_id"].isin(val_blocks)]
        candidate_train_cells = cell_geo[~cell_geo["block_id"].isin(val_blocks)]
        if len(val_cells) == 0 or len(candidate_train_cells) == 0:
            continue

        tree = cKDTree(val_cells[["x", "y"]].to_numpy())
        dist, _ = tree.query(candidate_train_cells[["x", "y"]].to_numpy(), k=1)
        buffered_train_cell_ids = candidate_train_cells.loc[dist > BUFFER_M, "cell_id"].to_numpy()
        val_cell_ids = val_cells["cell_id"].to_numpy()
        folds.append((fold_idx, val_cell_ids, buffered_train_cell_ids))

    return folds


def exp_d_score(df):
    """Non-AI deterministic baseline: raw 24-hour accumulated rainfall (mm).

    No model is fit for this experiment -- the score is the observed
    rain_24h value itself. Only the CSI-optimal threshold is learned, and
    only from training-side, buffer-enforced out-of-fold validation.
    """
    return df["rain_24h"].to_numpy(dtype=float)


def inner_oof(train_df, folds, feature_cols=None, deterministic_score_fn=None):
    oof_rows = []
    for fold_idx, val_cell_ids, buffered_train_cell_ids in folds:
        fold_train = train_df[train_df["cell_id"].isin(buffered_train_cell_ids)]
        fold_val = train_df[train_df["cell_id"].isin(val_cell_ids)]
        if len(fold_train) == 0 or len(fold_val) == 0:
            continue
        if fold_train["label"].astype(int).sum() == 0:
            # No positives on the training side of this fold -- cannot fit
            # or meaningfully threshold-select here; skip this fold's OOF slice.
            continue

        if deterministic_score_fn is not None:
            scores = deterministic_score_fn(fold_val)
        else:
            y_tr = fold_train["label"].astype(int)
            pos, neg = int(y_tr.sum()), int((y_tr == 0).sum())
            params = dict(XGB_PARAMS)
            params["scale_pos_weight"] = max(1.0, neg / max(1, pos))
            model = XGBClassifier(**params)
            model.fit(fold_train[feature_cols], y_tr)
            scores = model.predict_proba(fold_val[feature_cols])[:, 1]

        oof_rows.append(pd.DataFrame({
            "cell_id": fold_val["cell_id"].to_numpy(),
            "timestamp": fold_val["timestamp"].to_numpy(),
            "label": fold_val["label"].astype(int).to_numpy(),
            "score": scores,
            "fold": fold_idx,
        }))

    if not oof_rows:
        return pd.DataFrame(columns=["cell_id", "timestamp", "label", "score", "fold"])
    return pd.concat(oof_rows, ignore_index=True)


def csi(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tp / max(1, tp + fp + fn)


def select_threshold_from_oof(oof_df):
    """Select the CSI-maximizing threshold using OOF predictions only.

    Deterministic tie-break: (1) higher CSI, (2) higher F1, (3) smaller
    threshold value.
    """
    if len(oof_df) == 0 or oof_df["label"].sum() == 0:
        raise RuntimeError("No usable out-of-fold positives available for threshold selection.")

    y = oof_df["label"].to_numpy()
    s = oof_df["score"].to_numpy()
    candidates = np.unique(np.quantile(s, np.linspace(0.0, 0.999, 400)))

    best_key = None
    best_t = None
    for t in candidates:
        pred = (s >= t).astype(int)
        c = csi(y, pred)
        f1 = f1_score(y, pred, zero_division=0)
        key = (c, f1, -t)
        if best_key is None or key > best_key:
            best_key = key
            best_t = float(t)
    return best_t


def full_metrics(y, s, threshold, is_probability=True):
    """is_probability=False for Exp D's raw-mm score: PR-AUC/ROC-AUC/CSI/precision/
    recall/F1 are rank- or threshold-based and remain valid for any monotonic
    score, but Brier score is only defined for a genuine probability in [0,1]
    and is reported as NaN (not fabricated via an arbitrary normalization) for
    the non-probabilistic Exp D baseline.
    """
    pred = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    if is_probability:
        brier = float(brier_score_loss(y, s))
    else:
        brier = float("nan")
    return {
        "threshold": float(threshold),
        "PR_AUC": float(average_precision_score(y, s)),
        "CSI": float(csi(y, pred)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "F1": float(f1_score(y, pred, zero_division=0)),
        "ROC_AUC": float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else float("nan"),
        "Brier": brier,
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
        "n_test": int(len(y)),
        "n_test_positive": int(y.sum()),
        "n_test_negative": int((y == 0).sum()),
    }


def run_direction(d, cell_geo, tr_ep, te_ep, results, pred_rows):
    train = d[d["episode_id"] == tr_ep].copy()
    test = d[d["episode_id"] == te_ep].copy()

    train_cell_geo = cell_geo[cell_geo["cell_id"].isin(train["cell_id"])].reset_index(drop=True)
    folds = build_inner_folds(train_cell_geo)

    for exp_name, feats in LEARNED_EXPERIMENTS.items():
        oof = inner_oof(train, folds, feature_cols=feats)
        threshold = select_threshold_from_oof(oof)

        y_tr = train["label"].astype(int)
        pos, neg = int(y_tr.sum()), int((y_tr == 0).sum())
        params = dict(XGB_PARAMS)
        params["scale_pos_weight"] = max(1.0, neg / max(1, pos))
        final_model = XGBClassifier(**params)
        final_model.fit(train[feats], y_tr)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        final_model.save_model(MODEL_DIR / f"{exp_name}_{tr_ep}_to_{te_ep}.json")

        s_test = final_model.predict_proba(test[feats])[:, 1]
        y_test = test["label"].astype(int).to_numpy()

        m = full_metrics(y_test, s_test, threshold)
        m.update({
            "experiment": exp_name, "train_episode": tr_ep, "test_episode": te_ep,
            "n_inner_oof": len(oof), "n_inner_folds_used": int(oof["fold"].nunique()) if len(oof) else 0,
        })
        results.append(m)

        pred_rows.append(pd.DataFrame({
            "cell_id": test["cell_id"].to_numpy(),
            "timestamp": test["timestamp"].to_numpy(),
            "label": y_test,
            "experiment": exp_name,
            "train_episode": tr_ep,
            "test_episode": te_ep,
            "score": s_test,
            "predicted_class": (s_test >= threshold).astype(int),
            "threshold_used": threshold,
        }))

    # Experiment D: deterministic, non-AI, no model fit at all.
    oof_d = inner_oof(train, folds, deterministic_score_fn=exp_d_score)
    threshold_d = select_threshold_from_oof(oof_d)
    s_test_d = exp_d_score(test)
    y_test = test["label"].astype(int).to_numpy()

    m = full_metrics(y_test, s_test_d, threshold_d, is_probability=False)
    m.update({
        "experiment": "Exp_D_NonAI_Rain24h_Baseline", "train_episode": tr_ep, "test_episode": te_ep,
        "n_inner_oof": len(oof_d), "n_inner_folds_used": int(oof_d["fold"].nunique()) if len(oof_d) else 0,
    })
    results.append(m)
    pred_rows.append(pd.DataFrame({
        "cell_id": test["cell_id"].to_numpy(),
        "timestamp": test["timestamp"].to_numpy(),
        "label": y_test,
        "experiment": "Exp_D_NonAI_Rain24h_Baseline",
        "train_episode": tr_ep,
        "test_episode": te_ep,
        "score": s_test_d,
        "predicted_class": (s_test_d >= threshold_d).astype(int),
        "threshold_used": threshold_d,
    }))


def write_report(res_df):
    lines = [
        "SIH26071 - Stage 7: Controlled AI#1 -> AI#2 Integration (reconstructed)",
        "",
        "Specification: NEW master-prompt Stage 7 spec (explicitly supersedes the",
        "original Stage 7 spec's experiment definitions and fixed-0.50 threshold policy).",
        "",
        "Experiment definitions:",
        "- Exp_A_Baseline: rain_1h, rain_3h, rain_6h, rain_12h, rain_24h, elevation, "
        "slope_degrees, distance_to_drainage",
        "- Exp_B_Baseline_plus_AI1: Exp A features + AI#1 forecast probability",
        "- Exp_C_AI1_Only: AI#1 forecast probability only",
        "- Exp_D_NonAI_Rain24h_Baseline: deterministic score = raw rain_24h (mm); "
        "no model fitting, not AI -- isolates whether Exp B's value (if any) is "
        "more than 'more rainfall information'",
        "",
        "Validation design:",
        "- Outer: Leave-One-Episode-Out, both directions (Episode_1<->Episode_2).",
        f"- Inner: up to {N_INNER_FOLDS}-fold spatial-block CV within the training "
        f"episode only, 5km x 5km blocks in EPSG:32644, {BUFFER_M:.0f}m nearest-cell "
        "buffer excluding candidate training cells near the held-out fold's cells.",
        "- Threshold selected by maximizing CSI on out-of-fold predictions only "
        "(tie-break: higher F1, then smaller threshold), frozen, then applied exactly "
        "once to the fully held-out test episode.",
        "- The held-out test episode never participates in block assignment, model "
        "fitting, or threshold selection.",
        "",
        "Leakage controls:",
        "- Class 2 (uncertain) excluded from this binary experiment; never relabeled.",
        "- AI#1 probability/amount merged on exact timestamp only; a missing required "
        "timestamp raises a hard error instead of silently dropping rows.",
        "- future_6h_rain / target / label are never used as AI#2 predictors.",
        "- AI#1 predictions come from the Stage 6 model trained strictly through "
        "2021-10-31 23:00, causally valid at each Stage 7 timestamp.",
        "",
        "Results (LOEO, both directions, all experiments; independently computed, "
        "not hard-coded):",
        "",
        res_df.to_string(index=False),
        "",
        "Historical reference metrics live separately in data/reference/ and were not "
        "used to tune this implementation in any way.",
        "",
        "Note on Exp_D_NonAI_Rain24h_Baseline's Brier score: reported as NaN. Brier "
        "score is only defined for a genuine probability in [0,1]; Exp D's score is "
        "raw rain_24h in millimetres, not a probability, so no meaningful Brier value "
        "exists for it and none was fabricated via an arbitrary normalization.",
    ]
    OUT_REPORT.write_text("\n".join(str(l) for l in lines) + "\n", encoding="utf-8")


def main():
    d = load()
    cell_geo = project_unique_cells(d)

    results, pred_rows = [], []
    for tr_ep, te_ep in [("Episode_1", "Episode_2"), ("Episode_2", "Episode_1")]:
        run_direction(d, cell_geo, tr_ep, te_ep, results, pred_rows)

    res_df = pd.DataFrame(results)
    cols = [
        "experiment", "train_episode", "test_episode", "threshold",
        "PR_AUC", "CSI", "recall", "precision", "F1", "ROC_AUC", "Brier",
        "TP", "FP", "FN", "TN", "n_test", "n_test_positive", "n_test_negative",
        "n_inner_oof", "n_inner_folds_used",
    ]
    res_df = res_df[cols]
    res_df.to_csv(OUT_METRICS, index=False)

    pred_df = pd.concat(pred_rows, ignore_index=True)
    pred_df.to_csv(OUT_PRED, index=False, float_format="%.8g")

    write_report(res_df)

    print("Stage 7 completed.")
    print(res_df.to_string(index=False))
    print(f"Metrics: {OUT_METRICS}")
    print(f"Predictions: {OUT_PRED}")
    print(f"Report: {OUT_REPORT}")


if __name__ == "__main__":
    main()
