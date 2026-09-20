"""SIH26071 - Phase 1: production AI#2 operating threshold investigation.

WHY THIS IS NOT AS SIMPLE AS "PICK STAGE 7'S THRESHOLD":
Stage 7's thresholds (e.g. 0.86, 0.10) were each selected via OOF CV
*within a single LOEO training episode* -- they are valid for a model
trained on ONE episode's data, evaluated against the OTHER held-out
episode. The production model (models/production/ai2_baseline.json) is
trained on BOTH episodes combined. Neither LOEO threshold is
automatically correct for it, and there is no held-out episode left to
select a threshold against without either (a) reusing training data for
threshold selection (data leakage) or (b) holding out an episode again
(which would mean the production model is no longer trained on all
available data, defeating its purpose).

METHODOLOGY ACTUALLY USED:
The same honest approach as Stage 7 -- 5km x 5km spatial-block CV with a
500m buffer -- applied once across the FULL combined dataset (all cells,
both episodes) rather than within a single LOEO fold. This produces
out-of-fold predictions for every row in the training set without any
row ever being scored by a model that saw it during that fold's fit.
CSI is optimized on these OOF predictions, exactly as Stage 7 did.

WHAT THIS IS NOT:
This is NOT equivalent to Stage 7/8's LOEO event-generalization
evidence -- the folds here are spatial only, not across independent
flood episodes, because there is no third episode to hold out. This
threshold is scientifically defensible as an honest OOF selection (no
row is ever evaluated by a model fit on that same row), but it has NOT
been validated against a genuinely independent flood event, and that
limitation is documented in the output metadata, not hidden.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from sklearn.model_selection import KFold
from sklearn.metrics import f1_score, confusion_matrix
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/processed/inundation_risk_ml_dataset.csv"
OUT_METADATA = ROOT / "models/production/ai2_baseline_metadata.json"

BASE_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]
BLOCK_SIZE_M = 5000.0
BUFFER_M = 500.0
N_FOLDS = 5

XGB_PARAMS = dict(
    n_estimators=250, max_depth=5, learning_rate=0.08,
    subsample=0.8, colsample_bytree=0.8,
    objective="binary:logistic", eval_metric="aucpr",
    random_state=42, n_jobs=1, tree_method="hist",
)


def csi(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tp / max(1, tp + fp + fn)


def project_unique_cells(d):
    cells = d[["cell_id", "centroid_lon", "centroid_lat"]].drop_duplicates("cell_id").reset_index(drop=True)
    t = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    x, y = t.transform(cells["centroid_lon"].to_numpy(), cells["centroid_lat"].to_numpy())
    cells["x"] = x
    cells["y"] = y
    cells["block_id"] = (np.floor(x / BLOCK_SIZE_M).astype(int).astype(str) + "_"
                          + np.floor(y / BLOCK_SIZE_M).astype(int).astype(str))
    return cells[["cell_id", "x", "y", "block_id"]]


def build_folds(cell_geo, seed=42):
    unique_blocks = np.sort(cell_geo["block_id"].unique())
    kf = KFold(n_splits=min(N_FOLDS, len(unique_blocks)), shuffle=True, random_state=seed)
    folds = []
    for fold_idx, (_, val_idx) in enumerate(kf.split(unique_blocks)):
        val_blocks = set(unique_blocks[val_idx])
        val_cells = cell_geo[cell_geo["block_id"].isin(val_blocks)]
        cand_train_cells = cell_geo[~cell_geo["block_id"].isin(val_blocks)]
        if len(val_cells) == 0 or len(cand_train_cells) == 0:
            continue
        tree = cKDTree(val_cells[["x", "y"]].to_numpy())
        dist, _ = tree.query(cand_train_cells[["x", "y"]].to_numpy(), k=1)
        buffered_train_ids = cand_train_cells.loc[dist > BUFFER_M, "cell_id"].to_numpy()
        folds.append((fold_idx, val_cells["cell_id"].to_numpy(), buffered_train_ids))
    return folds


def main():
    d = pd.read_csv(DATA)
    d = d[d["label"].isin([0, 1])].copy()
    cell_geo = project_unique_cells(d)
    folds = build_folds(cell_geo)

    oof_rows = []
    for fold_idx, val_ids, train_ids in folds:
        fold_train = d[d["cell_id"].isin(train_ids)]
        fold_val = d[d["cell_id"].isin(val_ids)]
        if len(fold_train) == 0 or len(fold_val) == 0 or fold_train["label"].sum() == 0:
            continue
        y_tr = fold_train["label"].astype(int)
        params = dict(XGB_PARAMS)
        params["scale_pos_weight"] = max(1.0, (y_tr == 0).sum() / max(1, y_tr.sum()))
        model = XGBClassifier(**params)
        model.fit(fold_train[BASE_FEATURES], y_tr)
        scores = model.predict_proba(fold_val[BASE_FEATURES])[:, 1]
        oof_rows.append(pd.DataFrame({
            "label": fold_val["label"].astype(int).to_numpy(),
            "score": scores,
            "fold": fold_idx,
        }))
        print(f"Fold {fold_idx}: train={len(fold_train)} val={len(fold_val)}")

    oof = pd.concat(oof_rows, ignore_index=True)
    y, s = oof["label"].to_numpy(), oof["score"].to_numpy()

    candidates = np.unique(np.quantile(s, np.linspace(0.0, 0.999, 400)))
    best_key, best_t = None, None
    for t in candidates:
        pred = (s >= t).astype(int)
        c = csi(y, pred)
        f1 = f1_score(y, pred, zero_division=0)
        key = (c, f1, -t)
        if best_key is None or key > best_key:
            best_key, best_t = key, float(t)

    pred = (s >= best_t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    result = {
        "method": "5-fold spatial-block (5km, 500m buffer) OOF CV on the full "
                  "production training set, CSI-optimized (tie-break: F1, then "
                  "smaller threshold)",
        "threshold": best_t,
        "oof_n": int(len(oof)),
        "oof_csi": float(csi(y, pred)),
        "oof_tp": int(tp), "oof_fp": int(fp), "oof_fn": int(fn), "oof_tn": int(tn),
        "limitation": "Selected via spatial-only OOF CV, not validated against an "
                       "independent flood episode (none remains held out once the "
                       "production model uses both known episodes). Not equivalent "
                       "to Stage 7/8's LOEO event-generalization evidence.",
    }
    print("Selected threshold:", best_t, "OOF CSI:", result["oof_csi"])

    import json
    meta = json.loads(OUT_METADATA.read_text())
    meta["production_operating_threshold"] = result
    OUT_METADATA.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Updated {OUT_METADATA}")


if __name__ == "__main__":
    main()
