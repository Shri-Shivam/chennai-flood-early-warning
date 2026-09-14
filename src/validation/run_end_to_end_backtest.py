"""SIH26071 - Stage 8: end-to-end retrospective backtest.

METHODOLOGICAL SCOPE -- READ BEFORE INTERPRETING RESULTS
==========================================================
This script does NOT retrain or re-tune anything. It reuses the
already-trained, already-frozen Stage 7 models
(models/stage7_integrated/*.json) and their already-selected,
OOF-derived thresholds (data/processed/stage7_model_comparison.csv)
exactly as Stage 7 produced them.

What Stage 8 genuinely adds on top of Stage 7:
  - Stage 7 reports metrics aggregated over an entire held-out
    EPISODE (up to 4 timestamps at once). Stage 8 reports metrics
    at the level of each individual flood EVENT (single timestamp),
    plus a pooled view across all 5 known events together -- neither
    of which Stage 7 computed.
  - Stage 8 is the "would this end-to-end system, as configured and
    frozen by Stage 7, have flagged this specific historical flood
    moment" question, not a re-derivation of whether AI#1 helps.

What this is NOT:
  - This is NOT an independent operational real-time simulation. The
    Experiment B model was trained on AI#1 probability as one of its
    features (a genuinely forecast-driven, forward-looking signal),
    but Experiment A's "rain_1h..rain_24h" features are OBSERVED
    antecedent rainfall available at each timestamp T -- not a
    forecast at all. So "Mode B" here means "AI#1-forecast-augmented",
    and "Mode A" means "observed-antecedent-rainfall-only, no
    forecast integration" -- not "operational" vs "retrospective".
  - LOEO leakage-safety is inherited from Stage 7, not re-verified
    from scratch here: each event uses the frozen model that was
    trained on the OTHER episode (never the episode containing that
    event), which is exactly Stage 7's LOEO discipline.
  - No new spatial block cross-validation happens in this script --
    that responsibility belongs to Stage 7 and was already discharged
    there. Nothing here needs to re-partition space, because nothing
    here is being newly fit.

Experiments (reusing Stage 7's frozen artifacts):
  A: AI#2 baseline (rain_1h..rain_24h + terrain), Stage 7's Exp_A_Baseline
  B: AI#2 baseline + AI#1 forecast probability, Stage 7's Exp_B_Baseline_plus_AI1
  C: simple non-AI rainfall baseline (raw rain_24h mm), Stage 7's Exp_D_NonAI_Rain24h_Baseline

For each of the 5 known flood timestamps, the model/threshold used is
whichever Stage 7 LOEO direction had that timestamp's episode as the
TEST episode (i.e. trained only on the other episode) -- never the
direction trained on that timestamp's own episode.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
AI2_DATA = ROOT / "data/processed/inundation_risk_ml_dataset.csv"
AI1_DATA = ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
STAGE7_COMPARISON = ROOT / "data/processed/stage7_model_comparison.csv"
STAGE7_MODEL_DIR = ROOT / "models/stage7_integrated"
OUT_PRED = ROOT / "data/processed/stage8_end_to_end_predictions.csv"

BASE_FEATURES = [
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "elevation", "slope_degrees", "distance_to_drainage",
]
EXPERIMENTS = {
    "Exp_A_Baseline": {"kind": "learned", "features": BASE_FEATURES,
                        "model_prefix": "Exp_A_Baseline"},
    "Exp_B_Baseline_plus_AI1": {"kind": "learned", "features": BASE_FEATURES + ["ai1_probability"],
                                 "model_prefix": "Exp_B_Baseline_plus_AI1"},
    "Exp_C_NonAI_Rain24h": {"kind": "deterministic", "features": None,
                             "stage7_row_name": "Exp_D_NonAI_Rain24h_Baseline"},
}
REQUIRED_TIMESTAMPS = 5


def load_ai2_with_ai1():
    d = pd.read_csv(AI2_DATA)
    d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    d = d[d["label"].isin([0, 1])].copy()  # class 2 (uncertain) excluded, never relabeled

    ai1 = pd.read_csv(AI1_DATA)
    ai1["timestamp"] = pd.to_datetime(ai1["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    ai1 = ai1.rename(columns={"predicted_probability": "ai1_probability",
                               "predicted_amount_mm": "ai1_amount_mm"})

    required_ts = set(d["timestamp"].unique())
    available_ts = set(ai1["timestamp"].unique())
    missing = required_ts - available_ts
    if missing:
        raise RuntimeError(f"AI#1 forecast missing for required timestamp(s): {sorted(missing)}.")

    n_before = len(d)
    merged = d.merge(
        ai1[["timestamp", "ai1_probability", "ai1_amount_mm"]],
        on="timestamp", how="left", validate="many_to_one",
    )
    if len(merged) != n_before:
        raise RuntimeError(f"Row count changed during AI#1 merge: {n_before} -> {len(merged)}.")
    if merged["ai1_probability"].isna().any():
        raise RuntimeError("AI#1 merge produced missing values despite a complete timestamp check.")
    if merged["timestamp"].nunique() != REQUIRED_TIMESTAMPS:
        raise RuntimeError(
            f"Expected {REQUIRED_TIMESTAMPS} unique timestamps, found {merged['timestamp'].nunique()}."
        )
    return merged


def load_stage7_comparison():
    df = pd.read_csv(STAGE7_COMPARISON)
    return df


def direction_for_episode(comparison_df, episode):
    """The leakage-safe direction for scoring `episode`'s cells is the row
    where test_episode == episode (i.e. trained on the OTHER episode)."""
    rows = comparison_df[comparison_df["test_episode"] == episode]
    if rows.empty:
        raise RuntimeError(f"No Stage 7 LOEO direction found with test_episode={episode}.")
    train_ep = rows["train_episode"].iloc[0]
    return train_ep, episode


def load_frozen_classifier(model_prefix, train_ep, test_ep):
    path = STAGE7_MODEL_DIR / f"{model_prefix}_{train_ep}_to_{test_ep}.json"
    if not path.exists():
        raise RuntimeError(f"Frozen Stage 7 model not found: {path}")
    model = XGBClassifier()
    model.load_model(str(path))
    return model


def frozen_threshold(comparison_df, experiment_row_name, train_ep, test_ep):
    row = comparison_df[
        (comparison_df["experiment"] == experiment_row_name)
        & (comparison_df["train_episode"] == train_ep)
        & (comparison_df["test_episode"] == test_ep)
    ]
    if row.empty:
        raise RuntimeError(f"No frozen threshold found for {experiment_row_name} {train_ep}->{test_ep}.")
    return float(row["threshold"].iloc[0])


def main():
    d = load_ai2_with_ai1()
    comparison = load_stage7_comparison()

    episodes = sorted(d["episode_id"].unique())
    rows = []

    for episode in episodes:
        ep_rows = d[d["episode_id"] == episode]
        train_ep, test_ep = direction_for_episode(comparison, episode)
        # Sanity: the model used for this episode must never have been
        # trained ON this same episode.
        assert train_ep != episode, "About to score an episode with a model trained on itself."

        for exp_name, cfg in EXPERIMENTS.items():
            if cfg["kind"] == "learned":
                model = load_frozen_classifier(cfg["model_prefix"], train_ep, test_ep)
                scores = model.predict_proba(ep_rows[cfg["features"]])[:, 1]
                threshold = frozen_threshold(comparison, cfg["model_prefix"], train_ep, test_ep)
            else:
                scores = ep_rows["rain_24h"].to_numpy(dtype=float)
                threshold = frozen_threshold(comparison, cfg["stage7_row_name"], train_ep, test_ep)

            rows.append(pd.DataFrame({
                "cell_id": ep_rows["cell_id"].to_numpy(),
                "timestamp": ep_rows["timestamp"].to_numpy(),
                "episode_id": episode,
                "label": ep_rows["label"].astype(int).to_numpy(),
                "experiment": exp_name,
                "model_trained_on_episode": train_ep,
                "score": scores,
                "threshold_used_frozen_from_stage7": threshold,
                "predicted_class": (scores >= threshold).astype(int),
            }))

    out = pd.concat(rows, ignore_index=True)
    dup = out.duplicated(["cell_id", "timestamp", "experiment"]).sum()
    if dup:
        raise RuntimeError(f"{dup} duplicate (cell_id, timestamp, experiment) rows produced.")
    if out["score"].isna().any() or np.isinf(out["score"].to_numpy()).any():
        raise RuntimeError("NaN or Inf values found in generated scores.")

    out.to_csv(OUT_PRED, index=False, float_format="%.8g")
    print(f"Stage 8 backtest predictions written: {OUT_PRED} ({len(out)} rows)")
    print(f"Episodes scored: {episodes}")
    print(f"Timestamps covered: {sorted(d['timestamp'].unique())}")


if __name__ == "__main__":
    main()
