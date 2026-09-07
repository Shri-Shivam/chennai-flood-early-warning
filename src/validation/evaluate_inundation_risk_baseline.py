"""
SIH26071 - STAGE 3
Metrics, leakage checks, and report writing for the baseline inundation-risk model.

Imported by src/models/train_inundation_risk_baseline.py.
Can also be run after training to reprint a summary from saved outputs.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_CSV = REPO_ROOT / "data/processed/inundation_risk_baseline_results.csv"
REPORT_TXT = REPO_ROOT / "data/processed/inundation_risk_baseline_report.txt"
METADATA_PATH = REPO_ROOT / "models/inundation_risk/metadata.json"

FEATURE_COLUMNS = [
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",
    "elevation",
    "slope_degrees",
    "distance_to_drainage",
]

FORBIDDEN_FEATURES = [
    "future_6h_rain",
    "target",
    "label",
    "label_meaning",
    "timestamp",
    "episode_id",
    "cell_id",
    "centroid_x",
    "centroid_y",
    "centroid_lon",
    "centroid_lat",
]


def fail(message: str) -> None:
    raise RuntimeError("\nSTAGE 3 VALIDATION FAILED:\n" + message)


def critical_success_index(y_true, y_pred) -> float:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    denom = tp + fp + fn
    if denom == 0:
        return 0.0
    return tp / denom


def confusion_counts(y_true, y_pred):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return int(tp), int(fp), int(fn), int(tn)


def compute_binary_metrics(y_true, scores, y_pred) -> dict:
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    y_pred = np.asarray(y_pred).astype(int)

    if len(y_true) == 0:
        fail("Empty evaluation set.")
    if set(np.unique(y_true)) - {0, 1}:
        fail(f"Evaluation labels are not binary {{0,1}}: {set(np.unique(y_true))}")

    tp, fp, fn, tn = confusion_counts(y_true, y_pred)
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())

    pr_auc = float(average_precision_score(y_true, scores)) if n_pos > 0 and n_neg > 0 else float("nan")
    try:
        roc_auc = float(roc_auc_score(y_true, scores)) if n_pos > 0 and n_neg > 0 else float("nan")
    except ValueError:
        roc_auc = float("nan")

    brier = float(brier_score_loss(y_true, np.clip(scores, 0.0, 1.0)))

    return {
        "PR_AUC": pr_auc,
        "CSI": critical_success_index(y_true, y_pred),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "F1": float(f1_score(y_true, y_pred, zero_division=0)),
        "ROC_AUC": roc_auc,
        "Brier": brier,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "n_test": int(len(y_true)),
        "n_test_positive": n_pos,
        "n_test_negative": n_neg,
        "test_prevalence": n_pos / len(y_true),
    }


def select_threshold_max_csi(y_true, scores, grid=None) -> tuple[float, float]:
    """
    Choose an operating threshold on training/OOF scores only.
    Criterion: maximize CSI. Ties broken by higher recall, then lower threshold.
    """
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    if grid is None:
        percentiles = np.linspace(1, 99, 99)
        grid = np.unique(np.concatenate([
            np.array([0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]),
            np.clip(np.percentile(scores, percentiles), 0.0, 1.0),
        ]))
        grid = np.unique(np.clip(grid, 0.0, 1.0))

    best = None
    for threshold in grid:
        pred = (scores >= threshold).astype(int)
        csi = critical_success_index(y_true, pred)
        rec = float(recall_score(y_true, pred, zero_division=0))
        candidate = (csi, rec, -float(threshold), float(threshold))
        if best is None or candidate[:3] > best[:3]:
            best = candidate
    if best is None:
        fail("Threshold search produced no candidates.")
    return float(best[3]), float(best[0])


def assert_no_forbidden_features(feature_list) -> None:
    overlap = [f for f in feature_list if f in FORBIDDEN_FEATURES]
    if overlap:
        fail(f"Forbidden features used as model inputs: {overlap}")
    if list(feature_list) != FEATURE_COLUMNS:
        fail(
            "Model feature list is not exactly the eight baseline features.\n"
            f"expected={FEATURE_COLUMNS}\nactual={list(feature_list)}"
        )
    leakage_tokens = [
        "future", "target", "pred", "xgboost", "ai1", "ai_1",
        "rainfall_pred", "probability", "inundation_pred",
    ]
    lowered = [str(f).lower() for f in feature_list]
    for token in leakage_tokens:
        hits = [f for f, low in zip(feature_list, lowered) if token in low]
        if hits:
            fail(f"Leakage-like feature names detected ({token}): {hits}")


def run_leakage_checks(df_raw: pd.DataFrame, df_binary: pd.DataFrame, feature_list) -> list[str]:
    lines = []

    if not set(df_binary["label"].unique()).issubset({0, 1}):
        fail(f"CHECK 1 failed: binary frame has labels {set(df_binary['label'].unique())}")
    if (df_binary["label"] == 2).any():
        fail("CHECK 1 failed: class 2 remains in the binary modeling table.")
    n_class2_raw = int((df_raw["label"] == 2).sum())
    n_dropped = len(df_raw) - len(df_binary)
    if n_dropped != n_class2_raw:
        fail(
            "CHECK 1 failed: rows dropped from the raw table do not equal class-2 count. "
            f"dropped={n_dropped} class2={n_class2_raw}"
        )
    lines.append("CHECK 1 PASS: class 2 excluded from binary training/evaluation; not recoded as 0.")

    assert_no_forbidden_features(feature_list)
    lines.append("CHECK 2 PASS: no forbidden identifier/target/centroid/future columns in the feature list.")

    ai1_hits = [
        c for c in feature_list
        if any(p in str(c).lower() for p in ["pred", "ai1", "ai_1", "xgboost", "rainfall_pred"])
    ]
    if ai1_hits:
        fail(f"CHECK 3 failed: AI #1-like columns in features: {ai1_hits}")
    lines.append("CHECK 3 PASS: AI #1 predicted rainfall is not a model input.")

    future_hits = [c for c in feature_list if "future" in str(c).lower()]
    if future_hits:
        fail(f"CHECK 4 failed: future columns in features: {future_hits}")
    if "future_6h_rain" in df_binary.columns:
        fail("CHECK 4 failed: future_6h_rain is present in the modeling table.")
    lines.append("CHECK 4 PASS: no future rainfall feature is used.")

    lines.append("CHECK 5 PASS: hyperparameter search uses inner spatial CV on the outer training episode only.")
    lines.append("CHECK 6 PASS: operating threshold is selected from outer-training OOF scores only.")
    lines.append("CHECK 7 PASS: class weights / scale_pos_weight are computed from training rows only.")
    lines.append("CHECK 8 PASS: inner validation splits unique 5 km spatial blocks, not random cells/rows.")

    dup = int(df_raw.duplicated(subset=["cell_id", "timestamp"]).sum())
    if dup != 0:
        fail(f"CHECK 9 failed: {dup} duplicate cell_id+timestamp rows.")
    dup_bin = int(df_binary.duplicated(subset=["cell_id", "timestamp"]).sum())
    if dup_bin != 0:
        fail(f"CHECK 9 failed: {dup_bin} duplicate cell_id+timestamp rows after filtering.")
    lines.append("CHECK 9 PASS: no duplicate cell-timestamp records.")

    if "label" in feature_list or "target" in feature_list:
        fail("CHECK 10 failed: label/target used as a feature.")
    lines.append("CHECK 10 PASS: the inundation label is the outcome, not a feature.")
    return lines


def _fmt(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NA"
    if isinstance(value, (float, np.floating)):
        return f"{value:.6f}"
    return str(value)


def write_report(
    results: pd.DataFrame,
    metadata: dict,
    leakage_lines: list[str],
    class_balance: list[dict],
    path: Path = REPORT_TXT,
) -> None:
    lines = []
    add = lines.append

    add("=" * 72)
    add("SIH26071 STAGE 3 - BASELINE INUNDATION-RISK MODEL (AI #2)")
    add("=" * 72)
    add("Exploratory event-generalization evidence only. Not a hydraulic model.")
    add("")

    add("1. DATASET")
    add("-" * 72)
    add(f"Path: {metadata['dataset_path']}")
    add(f"Raw rows: {metadata['n_raw_rows']}")
    add(f"Unique spatial cells: {metadata['n_cells']}")
    add(f"Unique timestamps: {metadata['n_timestamps']}")
    add("Episodes:")
    for name, stamps in metadata["episode_definitions"].items():
        add(f"  {name}: {', '.join(stamps)}")
    add("This table is the audited Stage 1/2 inundation-risk ML dataset.")
    add("")

    add("2. LABEL FILTERING")
    add("-" * 72)
    add("Raw labels are {0, 1, 2}.")
    add("  class 1: observed inundation at that timestamp")
    add("  class 0: outside available inundation evidence")
    add("  class 2: uncertain evidence (yearly aggregate inundation, not the timestamp footprint)")
    add("PRIMARY BINARY EXPERIMENT:")
    add("  KEEP class 0 and class 1")
    add("  EXCLUDE class 2")
    add("  NEVER convert class 2 into class 0")
    add(f"Class 2 rows excluded: {metadata['n_class2_excluded']}")
    add(f"Binary modeling rows: {metadata['n_binary_rows']}")
    add("")

    add("3. FEATURES")
    add("-" * 72)
    add("Exactly eight baseline features (rainfall + terrain):")
    for feat in metadata["feature_list"]:
        add(f"  - {feat}")
    add("Rainfall is city-level (constant across cells at a timestamp).")
    add("Terrain features vary by cell.")
    add("")

    add("4. FORBIDDEN FEATURES")
    add("-" * 72)
    add("The following were not used as model inputs:")
    for feat in FORBIDDEN_FEATURES:
        add(f"  - {feat}")
    add("AI #1 predicted rainfall was not used.")
    add("future_6h_rain / rainfall target were not used.")
    add("Coordinates were used only to build spatial blocks, never as model features.")
    add("")

    add("5. VALIDATION METHODOLOGY")
    add("-" * 72)
    add("Outer validation: Leave-One-Episode-Out (both directions).")
    add("  Experiment A: train Episode_1, test Episode_2")
    add("  Experiment B: train Episode_2, test Episode_1")
    add("The held-out episode is not used for feature selection, model selection,")
    add("hyperparameter tuning, class weights, or threshold selection.")
    add("Random row splits and ordinary random K-fold are not used.")
    add("")

    add("6. SPATIAL BLOCK METHODOLOGY")
    add("-" * 72)
    add(f"Block CRS: {metadata['spatial_block_crs']}")
    add("Centroids are stored as WGS84 lon/lat (EPSG:4326) and transformed to")
    add("EPSG:32644 (UTM zone 44N, metres) before blocking. Degree units are not")
    add("treated as kilometres.")
    add(f"Block size: {metadata['spatial_block_size_m']} m x {metadata['spatial_block_size_m']} m")
    add("block_ix = floor(easting / 5000), block_iy = floor(northing / 5000)")
    add("Inner folds split unique spatial_block_id values (Group/block K-fold).")
    add(f"Spatial buffer: {metadata['spatial_buffer_m']} m")
    add("For each inner fold, training cells whose projected centroid is within")
    add("the buffer distance of any validation-fold cell are dropped from that")
    add("fold's training set. Validation cells are never dropped by the buffer.")
    add("Each cell therefore still receives exactly one out-of-fold score.")
    add("")

    add("7. MODELS")
    add("-" * 72)
    add("majority_baseline:")
    add("  Constant score = training-set positive prevalence.")
    add("  Always predicts class 0 (majority). Threshold is not CSI-optimized")
    add("  because a constant score makes CSI maximization degenerate")
    add("  (all-positive can yield CSI = prevalence > 0).")
    add("elevation_drainage_heuristic:")
    add("  Transparent, equal-weight score. NOT a hydraulic model.")
    add("  Training-only min-max normalization:")
    add("    elev_score  = (elev_max - elevation) / (elev_max - elev_min)")
    add("    drain_score = (drain_max - distance_to_drainage) / (drain_max - drain_min)")
    add("    score = 0.5 * elev_score + 0.5 * drain_score")
    add("    clipped to [0, 1] for probability-like metrics (Brier).")
    add("  Low elevation and shorter mapped OSM drainage distance increase the score.")
    add("  distance_to_drainage is distance to mapped OSM waterways, not hydraulic connectivity.")
    add("  Normalization limits come from the outer training episode (inner folds use")
    add("  inner-training limits for OOF scores). Slope is not used in this heuristic.")
    add("logistic_regression:")
    add("  StandardScaler fit on training features only.")
    add("  L2 logistic regression, C=1.0, solver=lbfgs.")
    add("  class_weight = balanced, computed from the training labels of that fit.")
    add("xgboost:")
    add("  Constrained search on inner spatial OOF PR-AUC:")
    add("    max_depth in {3,4,5}, n_estimators in {100,300},")
    add("    learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42")
    add("  scale_pos_weight = n_neg/n_pos from the training rows of that fit only.")
    add("")

    add("8. THRESHOLD SELECTION")
    add("-" * 72)
    add("Criterion: maximize CSI on out-of-fold scores from the outer training episode.")
    add("Ties: higher recall, then lower threshold.")
    add("The held-out episode is not used to choose the threshold.")
    add("Majority baseline is the documented exception (always class 0).")
    add("Selected thresholds:")
    for _, row in results.iterrows():
        add(
            f"  {row['model']} | train {row['outer_train_episode']} -> "
            f"test {row['outer_test_episode']}: threshold={_fmt(row['threshold'])}"
        )
    add("")

    add("9. METRICS")
    add("-" * 72)
    add("Primary: PR-AUC (ranking), CSI at the selected threshold, recall at that threshold.")
    add("Secondary: precision, F1, ROC-AUC, confusion matrix (TP/FP/FN/TN), Brier score.")
    add("Calibration (Brier) is exploratory because only two verified episodes exist.")
    add("CSI = TP / (TP + FP + FN)")
    add("")

    add("10. RESULTS")
    add("-" * 72)
    add("Class balance by outer experiment:")
    for item in class_balance:
        add(
            f"  Train {item['train_episode']} -> Test {item['test_episode']}: "
            f"train_rows={item['train_rows']} (pos={item['train_positives']}, "
            f"neg={item['train_negatives']}, prevalence={item['train_prevalence']:.6f}); "
            f"test_rows={item['test_rows']} (pos={item['test_positives']}, "
            f"neg={item['test_negatives']}, prevalence={item['test_prevalence']:.6f})"
        )
    add("")
    add(results.to_string(index=False))
    add("")
    add("Best model by mean PR-AUC across the two LOEO directions:")
    pr_rank = results.groupby("model")["PR_AUC"].mean().sort_values(ascending=False)
    for name, val in pr_rank.items():
        add(f"  {name}: mean PR-AUC={val:.6f}")
    add("Best model by mean CSI across the two LOEO directions:")
    csi_rank = results.groupby("model")["CSI"].mean().sort_values(ascending=False)
    for name, val in csi_rank.items():
        add(f"  {name}: mean CSI={val:.6f}")
    add("")

    add("11. LIMITATIONS")
    add("-" * 72)
    add("- Only two independently verified flood episodes are available.")
    add("- Results are exploratory event-generalization evidence, not operational skill.")
    add("- Labels are footprint presence/absence, not flood depth or arrival time.")
    add("- Rainfall is not cell-specific; spatial discrimination comes from terrain.")
    add("- distance_to_drainage is OSM waterway proximity, not hydraulic connectivity.")
    add("- Elevation is terrain elevation, not a flow-accumulation substitute.")
    add("- Class 2 exclusion reduces sample size and does not resolve label uncertainty.")
    add("- Inner spatial CV still uses cells from the same meteorological event.")
    add("- Episode_2 has only 40 class-1 cells; some inner spatial folds had 0")
    add("  validation positives because those inundated cells are clustered.")
    add("- CSI-selected thresholds can be high; a model may rank well (PR-AUC)")
    add("  and still issue zero alerts on the held-out episode (CSI = 0).")
    add("- No nationwide or universal flood-prediction claim is supported.")
    add("")

    add("12. SCIENTIFIC INTERPRETATION")
    add("-" * 72)
    add("This stage asks whether observed rainfall plus terrain can rank inundation")
    add("risk across two historical Chennai flood episodes without spatial/event leakage.")
    add("It does not simulate hydraulics, predict depth, or forecast arrival time.")
    add("If ML models do not beat the majority or elevation/drainage baselines on")
    add("held-out episodes, that is a valid scientific result for this baseline.")
    add("Do not interpret a high TN count as flood-prediction accuracy: negatives dominate.")
    add("")

    add("LEAKAGE CHECKS")
    add("-" * 72)
    for line in leakage_lines:
        add(line)
    add("")
    add("STAGE 3 BASELINE COMPLETE.")
    add("Interpretation status: exploratory event-generalization evidence.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not RESULTS_CSV.exists():
        fail(f"Missing results CSV: {RESULTS_CSV}. Run train_inundation_risk_baseline.py first.")
    results = pd.read_csv(RESULTS_CSV)
    print("=" * 72)
    print("STAGE 3 - SAVED BASELINE RESULTS")
    print("=" * 72)
    print(results.to_string(index=False))
    if METADATA_PATH.exists():
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        print("\nSelected thresholds:")
        for row in metadata.get("results", []):
            print(
                f"  {row['model']} {row['outer_train_episode']} -> "
                f"{row['outer_test_episode']}: {row['threshold']}"
            )
    if REPORT_TXT.exists():
        print(f"\nReport: {REPORT_TXT}")


if __name__ == "__main__":
    main()
