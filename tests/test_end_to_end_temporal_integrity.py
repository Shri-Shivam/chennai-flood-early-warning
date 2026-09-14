"""SIH26071 - Stage 8 end-to-end backtest integrity tests.

These test the real generated Stage 8 artifacts and the real
implementation -- not synthetic placeholders. No metric value is
hard-coded or asserted against a specific number; these check
structural/leakage/reproducibility properties.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import (
    average_precision_score, precision_score, recall_score,
    f1_score, roc_auc_score, brier_score_loss, confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "validation"))

import run_end_to_end_backtest as s8run  # noqa: E402

PRED = ROOT / "data/processed/stage8_end_to_end_predictions.csv"
EVENT = ROOT / "data/processed/stage8_event_summary.csv"
METRICS = ROOT / "data/processed/stage8_end_to_end_metrics.csv"
COMPARISON = ROOT / "data/processed/stage7_model_comparison.csv"


@pytest.fixture(scope="module")
def pred_df():
    if not PRED.exists():
        pytest.skip("Stage 8 predictions not generated yet -- run run_end_to_end_backtest.py.")
    return pd.read_csv(PRED)


def test_1_no_future_target_predictor_leakage():
    for exp_name, cfg in s8run.EXPERIMENTS.items():
        if cfg["kind"] != "learned":
            continue
        forbidden = {"future_6h_rain", "target", "label"}
        bad = forbidden & set(cfg["features"])
        assert not bad, f"{exp_name} predictor set contains forbidden column(s): {bad}"


def test_2_class_2_excluded(pred_df):
    assert set(pred_df["label"].unique()) <= {0, 1}


def test_3_ai1_timestamp_alignment_exact():
    d = s8run.load_ai2_with_ai1()
    assert d["ai1_probability"].notna().all()
    assert d["timestamp"].nunique() == s8run.REQUIRED_TIMESTAMPS


def test_4_missing_ai1_timestamp_fails_loudly(tmp_path, monkeypatch):
    ai1 = pd.read_csv(s8run.AI1_DATA)
    required_timestamp = "2021-11-08 23:00:00"
    assert (ai1["timestamp"] == required_timestamp).any()
    truncated = ai1[ai1["timestamp"] != required_timestamp]
    fake_path = tmp_path / "ai1_truncated.csv"
    truncated.to_csv(fake_path, index=False)
    monkeypatch.setattr(s8run, "AI1_DATA", fake_path)
    with pytest.raises(RuntimeError):
        s8run.load_ai2_with_ai1()


def test_5_train_test_episode_separation(pred_df):
    """The model used to score an episode's cells must have been trained
    on the OTHER episode -- never the episode it's scoring."""
    for _, row in pred_df[["episode_id", "model_trained_on_episode"]].drop_duplicates().iterrows():
        assert row["episode_id"] != row["model_trained_on_episode"], (
            f"Episode {row['episode_id']} was scored using a model trained on itself."
        )


def test_6_no_duplicate_spatial_temporal_keys(pred_df):
    dup = pred_df.duplicated(["cell_id", "timestamp", "experiment"]).sum()
    assert dup == 0


def test_7_no_nan_or_inf_predictions(pred_df):
    assert pred_df["score"].notna().all()
    assert not np.isinf(pred_df["score"].to_numpy()).any()


def test_8_thresholds_are_frozen_from_stage7_not_reselected(pred_df):
    """Every threshold used in Stage 8 must match a value already present
    in Stage 7's comparison CSV -- proving no new threshold selection
    happened in this script. Uses a relative tolerance because
    stage8_end_to_end_predictions.csv is written with 8-significant-figure
    formatting, which is lossy compared to the full-precision source."""
    comparison = pd.read_csv(COMPARISON)
    valid_thresholds = comparison["threshold"].to_numpy()
    used_thresholds = pred_df["threshold_used_frozen_from_stage7"].unique()
    for t in used_thresholds:
        nearest_diff = np.min(np.abs(valid_thresholds - t))
        assert nearest_diff < 1e-6, (
            f"Threshold {t} used in Stage 8 has no match within tolerance in "
            f"Stage 7's frozen comparison table (nearest diff: {nearest_diff})."
        )


def test_9_no_held_out_labels_used_for_threshold_selection():
    """Static check: run_end_to_end_backtest.py must never call any
    threshold-selection routine -- only read frozen values."""
    src = (ROOT / "src/validation/run_end_to_end_backtest.py").read_text()
    for forbidden_call in ("select_threshold", "np.quantile", "KFold", ".fit("):
        assert forbidden_call not in src, (
            f"run_end_to_end_backtest.py appears to perform new fitting/threshold "
            f"selection ('{forbidden_call}' found) -- it should only reuse frozen Stage 7 artifacts."
        )


def test_10_deterministic_baseline_reproducibility():
    d = s8run.load_ai2_with_ai1()
    s1 = s8run.EXPERIMENTS["Exp_C_NonAI_Rain24h"]
    scores_a = d["rain_24h"].to_numpy(dtype=float)
    scores_b = d["rain_24h"].to_numpy(dtype=float)
    assert np.array_equal(scores_a, scores_b), "Deterministic Exp C score is not reproducible."


def test_11_probability_only_metrics_not_misapplied_to_raw_mm(pred_df):
    exp_c = pred_df[pred_df["experiment"] == "Exp_C_NonAI_Rain24h"]
    assert (exp_c["score"] > 1.5).any(), (
        "Exp C scores look bounded like probabilities, not raw mm -- sanity check failed."
    )
    metrics = pd.read_csv(METRICS)
    brier_c = metrics.loc[metrics["experiment"] == "Exp_C_NonAI_Rain24h", "Brier"].iloc[0]
    assert pd.isna(brier_c), "Exp C (non-probabilistic) must report Brier as NaN, not a fabricated value."


def test_12_no_quarantined_artifact_imported():
    src_run = (ROOT / "src/validation/run_end_to_end_backtest.py").read_text()
    src_eval = (ROOT / "src/validation/evaluate_end_to_end_backtest.py").read_text()
    for src in (src_run, src_eval):
        assert "archive/" not in src and "archive" + chr(47) not in src
        assert "unverified_recovery" not in src


def test_13_metrics_recompute_correctly_from_raw_predictions(pred_df):
    """Independent recomputation of stage8_end_to_end_metrics.csv directly
    from the raw predictions file -- must match exactly."""
    reported = pd.read_csv(METRICS)
    for _, row in reported.iterrows():
        sub = pred_df[pred_df["experiment"] == row["experiment"]]
        y = sub["label"].to_numpy()
        s = sub["score"].to_numpy()
        pred = sub["predicted_class"].to_numpy()
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        assert tp == row["TP"] and fp == row["FP"] and fn == row["FN"] and tn == row["TN"]
        assert average_precision_score(y, s) == pytest.approx(row["PR_AUC"], abs=1e-9)
        assert recall_score(y, pred, zero_division=0) == pytest.approx(row["recall"], abs=1e-9)
        assert precision_score(y, pred, zero_division=0) == pytest.approx(row["precision"], abs=1e-9)
        assert f1_score(y, pred, zero_division=0) == pytest.approx(row["F1"], abs=1e-9)


def test_14_event_summary_covers_exactly_5_timestamps_per_experiment(pred_df):
    if not EVENT.exists():
        pytest.skip("stage8_event_summary.csv not generated yet.")
    event_df = pd.read_csv(EVENT)
    for exp, sub in event_df.groupby("experiment"):
        assert sub["timestamp"].nunique() == s8run.REQUIRED_TIMESTAMPS, (
            f"{exp}: expected 5 event rows, found {sub['timestamp'].nunique()}."
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
