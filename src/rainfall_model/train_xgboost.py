import pandas as pd
import numpy as np
import os

from xgboost import XGBClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix
)

# =========================================================
# 1. LOAD DATA
# =========================================================

file_path = "data/processed/rainfall_ml_dataset.csv"

df = pd.read_csv(file_path, parse_dates=["time"])

df = df.sort_values("time").reset_index(drop=True)

print("=" * 70)
print("XGBOOST RAINFALL PREDICTION MODEL")
print("=" * 70)


# =========================================================
# 2. DEFINE FEATURES
# =========================================================
#
# IMPORTANT:
#
# future_6h_rain = future information
# target         = answer
#
# Neither can be used as input to the model.
#

feature_columns = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "precipitation",

    "rain_lag_1h",
    "rain_lag_3h",
    "rain_lag_6h",

    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",

    "pressure_change_3h",
    "pressure_change_6h",

    "humidity_change_3h",
    "humidity_change_6h",

    "hour",
    "month",
    "day_of_year"
]

X = df[feature_columns]
y = df["target"]


# =========================================================
# 3. CHRONOLOGICAL SPLIT
# =========================================================
#
# We DO NOT randomly split the data.
#
# Train:
# 2016-2022
#
# Validation:
# 2023-2024
#
# Test:
# 2025
#
# This prevents future storms from leaking into training.
#

train = df[df["time"].dt.year <= 2022]

validation = df[
    (df["time"].dt.year >= 2023)
    & (df["time"].dt.year <= 2024)
]

test = df[df["time"].dt.year == 2025]

X_train = train[feature_columns]
y_train = train["target"]

X_val = validation[feature_columns]
y_val = validation["target"]

X_test = test[feature_columns]
y_test = test["target"]


print("\nDataset split:")
print("-" * 50)

print(
    f"Training   : {len(train):6} rows | "
    f"Positive: {y_train.sum()}"
)

print(
    f"Validation : {len(validation):6} rows | "
    f"Positive: {y_val.sum()}"
)

print(
    f"Test       : {len(test):6} rows | "
    f"Positive: {y_test.sum()}"
)


# =========================================================
# 4. HANDLE CLASS IMBALANCE
# =========================================================

negative_count = (y_train == 0).sum()
positive_count = (y_train == 1).sum()

scale_pos_weight = negative_count / positive_count

print("\nClass imbalance:")
print("-" * 50)

print(f"Negative samples: {negative_count}")
print(f"Positive samples: {positive_count}")
print(f"scale_pos_weight: {scale_pos_weight:.2f}")


# =========================================================
# 5. CREATE XGBOOST MODEL
# =========================================================

model = XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,

    objective="binary:logistic",

    scale_pos_weight=scale_pos_weight,

    eval_metric="aucpr",

    random_state=42,
    n_jobs=-1
)


# =========================================================
# 6. TRAIN
# =========================================================

print("\nTraining XGBoost...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

print("Training complete.")


# =========================================================
# 7. VALIDATION PREDICTIONS
# =========================================================

val_probability = model.predict_proba(X_val)[:, 1]


# =========================================================
# 8. FIND BEST CLASSIFICATION THRESHOLD
# =========================================================
#
# XGBoost gives probabilities.
#
# Example:
#
# 0.12
# 0.47
# 0.81
#
# We need a threshold to convert probability into:
#
# 0 or 1
#
# We select this threshold ONLY using validation data.
#

thresholds = np.arange(0.05, 0.96, 0.05)

best_threshold = 0.50
best_f1 = 0

for threshold in thresholds:

    val_prediction = (
        val_probability >= threshold
    ).astype(int)

    f1 = f1_score(
        y_val,
        val_prediction,
        zero_division=0
    )

    if f1 > best_f1:
        best_f1 = f1
        best_threshold = threshold


# =========================================================
# 9. VALIDATION METRICS
# =========================================================

val_prediction = (
    val_probability >= best_threshold
).astype(int)

val_precision = precision_score(
    y_val,
    val_prediction,
    zero_division=0
)

val_recall = recall_score(
    y_val,
    val_prediction,
    zero_division=0
)

val_f1 = f1_score(
    y_val,
    val_prediction,
    zero_division=0
)

val_pr_auc = average_precision_score(
    y_val,
    val_probability
)


print("\n" + "=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

print(f"\nBest probability threshold: {best_threshold:.2f}")

print(f"\nPrecision : {val_precision:.4f}")
print(f"Recall    : {val_recall:.4f}")
print(f"F1 Score  : {val_f1:.4f}")
print(f"PR-AUC    : {val_pr_auc:.4f}")

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_val,
        val_prediction
    )
)


# =========================================================
# 10. TEST SET
# =========================================================
#
# IMPORTANT:
#
# We do NOT tune the threshold using the test set.
#
# The threshold chosen from validation is now fixed.
#

test_probability = model.predict_proba(X_test)[:, 1]

test_prediction = (
    test_probability >= best_threshold
).astype(int)


test_precision = precision_score(
    y_test,
    test_prediction,
    zero_division=0
)

test_recall = recall_score(
    y_test,
    test_prediction,
    zero_division=0
)

test_f1 = f1_score(
    y_test,
    test_prediction,
    zero_division=0
)

test_pr_auc = average_precision_score(
    y_test,
    test_probability
)


print("\n" + "=" * 70)
print("FINAL TEST RESULTS")
print("=" * 70)

print(f"\nPrecision : {test_precision:.4f}")
print(f"Recall    : {test_recall:.4f}")
print(f"F1 Score  : {test_f1:.4f}")
print(f"PR-AUC    : {test_pr_auc:.4f}")

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        test_prediction
    )
)


# =========================================================
# 11. FEATURE IMPORTANCE
# =========================================================

importance = pd.Series(
    model.feature_importances_,
    index=feature_columns
)

importance = importance.sort_values(
    ascending=False
)

print("\n" + "=" * 70)
print("TOP FEATURE IMPORTANCE")
print("=" * 70)

print(
    importance.head(10)
)


# =========================================================
# 12. SAVE MODEL
# =========================================================

os.makedirs("models", exist_ok=True)

model_path = "models/xgboost_rainfall_model.json"

model.save_model(model_path)

print("\n" + "=" * 70)
print("MODEL SAVED")
print("=" * 70)

print(f"\n{model_path}")