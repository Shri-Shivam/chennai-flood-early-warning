import pandas as pd
import numpy as np

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score
)

# =========================================================
# LOAD DATA
# =========================================================

file_path = "data/processed/rainfall_ml_dataset.csv"

df = pd.read_csv(
    file_path,
    parse_dates=["time"]
)

df = df.sort_values("time").reset_index(drop=True)


# =========================================================
# TEST SET
# =========================================================

test = df[df["time"].dt.year == 2025].copy()


# =========================================================
# SIMPLE BASELINE
# =========================================================
#
# Baseline idea:
#
# If the previous 6 hours already had significant rainfall,
# predict significant rainfall in the next 6 hours.
#
# We deliberately do NOT use future_6h_rain.
#

baseline_probability = (
    test["rain_6h"] / 20
)

# Cap probability between 0 and 1
baseline_probability = baseline_probability.clip(0, 1)


# =========================================================
# BASELINE THRESHOLD
# =========================================================

threshold = 0.40

baseline_prediction = (
    baseline_probability >= threshold
).astype(int)


# =========================================================
# METRICS
# =========================================================

y_test = test["target"]

precision = precision_score(
    y_test,
    baseline_prediction,
    zero_division=0
)

recall = recall_score(
    y_test,
    baseline_prediction,
    zero_division=0
)

f1 = f1_score(
    y_test,
    baseline_prediction,
    zero_division=0
)

pr_auc = average_precision_score(
    y_test,
    baseline_probability
)


# =========================================================
# RESULTS
# =========================================================

print("=" * 70)
print("BASELINE MODEL EVALUATION")
print("=" * 70)

print("\nBaseline:")
print("If previous 6h rainfall is high, predict future rainfall risk.")

print(f"\nThreshold: {threshold}")

print(f"\nPrecision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")
print(f"PR-AUC    : {pr_auc:.4f}")

print("\nPredicted alerts:", baseline_prediction.sum())

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)