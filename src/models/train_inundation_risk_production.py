"""SIH26071 - Production AI#2 model.

IMPORTANT DISTINCTION FROM STAGE 7:
Stage 7's models in models/stage7_integrated/ are LOEO VALIDATION folds
-- each one is deliberately trained with one episode held out, so it can
be tested on that held-out episode. They exist to answer a scientific
question (does AI#1 help AI#2?), not to serve predictions.

This script produces a PRODUCTION model: the same validated
Exp_A_Baseline architecture and features (rain_1h..rain_24h, elevation,
slope_degrees, distance_to_drainage -- no AI#1 probability, consistent
with Stage 7's own finding that AI#1 integration showed no consistent
benefit), refit on ALL available binary-labeled ground truth (both
episodes combined) rather than a held-out fold. This is standard
practice: validate the approach via cross-validation (already done in
Stage 7), then refit on all available data for deployment.

This model has NOT been separately validated beyond what Stage 7 already
established for this exact architecture and feature set on held-out
episodes. It is not a new, unvalidated architecture -- it is the same
validated one, just fit on more data than any single LOEO fold used.
"""
from pathlib import Path

import pandas as pd
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/processed/inundation_risk_ml_dataset.csv"
OUT_DIR = ROOT / "models/production"
OUT_MODEL = OUT_DIR / "ai2_baseline.json"
OUT_METADATA = OUT_DIR / "ai2_baseline_metadata.json"

BASE_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]

XGB_PARAMS = dict(
    n_estimators=250,
    max_depth=5,
    learning_rate=0.08,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="aucpr",
    random_state=42,
    n_jobs=1,  # see docs/reproducibility.md
    tree_method="hist",
)


def main():
    d = pd.read_csv(DATA)
    d = d[d["label"].isin([0, 1])].copy()  # class 2 excluded, never relabeled

    y = d["label"].astype(int)
    pos, neg = int(y.sum()), int((y == 0).sum())
    params = dict(XGB_PARAMS)
    params["scale_pos_weight"] = max(1.0, neg / max(1, pos))

    model = XGBClassifier(**params)
    model.fit(d[BASE_FEATURES], y)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(OUT_MODEL))

    # A fixed operating threshold is selected separately by
    # src/models/select_production_threshold.py (run it after this
    # script). If that script has already run, its
    # production_operating_threshold field is preserved here rather than
    # being silently wiped out by retraining this base model again.
    import json
    existing_threshold_field = None
    if OUT_METADATA.exists():
        try:
            existing_threshold_field = json.loads(OUT_METADATA.read_text()).get(
                "production_operating_threshold"
            )
        except (json.JSONDecodeError, OSError):
            existing_threshold_field = None

    metadata = {
        "model": "ai2_baseline (production)",
        "architecture": "Exp_A_Baseline (Stage 7), no AI#1 probability",
        "features": BASE_FEATURES,
        "training_data": "all available class-0/1 rows from inundation_risk_ml_dataset.csv "
                          "(both Episode_1 and Episode_2 combined, class 2 excluded)",
        "n_train_rows": int(len(d)),
        "n_positive": pos,
        "n_negative": neg,
        "scale_pos_weight": params["scale_pos_weight"],
        "known_limitation": "This exact architecture was validated via LOEO in Stage 7/8 "
                             "(see data/processed/stage7_model_comparison.csv), not "
                             "independently re-validated after refitting on the full "
                             "combined dataset. See production_operating_threshold below "
                             "(and its own limitation note) for the operating threshold, "
                             "if src/models/select_production_threshold.py has been run.",
        "xgb_params": {k: v for k, v in params.items() if k != "n_jobs"},
    }
    if existing_threshold_field is not None:
        metadata["production_operating_threshold"] = existing_threshold_field
        print("NOTE: preserved existing production_operating_threshold from prior metadata. "
              "If the retrained model differs meaningfully from the one it was selected "
              "against, rerun src/models/select_production_threshold.py.")
    OUT_METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Production AI#2 model saved: {OUT_MODEL}")
    print(f"Metadata: {OUT_METADATA}")
    print(f"Trained on {len(d)} rows ({pos} positive, {neg} negative)")


if __name__ == "__main__":
    main()
