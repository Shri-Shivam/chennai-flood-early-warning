import pandas as pd
import numpy as np

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

df = pd.read_csv(
    file_path,
    parse_dates=["time"]
)

df = df.sort_values("time").reset_index(drop=True)


# =========================================================
# 2. FEATURES
# =========================================================

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


# =========================================================
# 3. CHRONOLOGICAL SPLIT
# =========================================================

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


print("=" * 70)
print("FINAL RAINFALL MODEL EVALUATION")
print("=" * 70)

print("\nData:")
print("-" * 50)

print(f"Training   : {len(train)} rows")
print(f"Validation : {len(validation)} rows")
print(f"Test       : {len(test)} rows")

print(f"\nTest positive events: {y_test.sum()}")


# =========================================================
# 4. CLASS WEIGHT
# =========================================================

negative_count = (y_train == 0).sum()
positive_count = (y_train == 1).sum()

scale_pos_weight = negative_count / positive_count


# =========================================================
# 5. TRAIN MODEL
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

print("\nTraining model...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

print("Training complete.")


# =========================================================
# 6. 2025 TEST PREDICTIONS
# =========================================================

test_probability = model.predict_proba(X_test)[:, 1]


# =========================================================
# 7. FIXED OPERATING THRESHOLD
# =========================================================
#
# This was selected using validation data.
#
# DO NOT optimize it using the test set.
#

threshold = 0.40

test_prediction = (
    test_probability >= threshold
).astype(int)


# =========================================================
# 8. METRICS
# =========================================================

precision = precision_score(
    y_test,
    test_prediction,
    zero_division=0
)

recall = recall_score(
    y_test,
    test_prediction,
    zero_division=0
)

f1 = f1_score(
    y_test,
    test_prediction,
    zero_division=0
)

pr_auc = average_precision_score(
    y_test,
    test_probability
)


print("\n" + "=" * 70)
print("2025 TEST RESULTS")
print("=" * 70)

print(f"\nOperating threshold: {threshold:.2f}")

print(f"\nPrecision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")
print(f"PR-AUC    : {pr_auc:.4f}")


# =========================================================
# 9. CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_test,
    test_prediction
)

tn, fp, fn, tp = cm.ravel()

print("\nConfusion Matrix:")
print(cm)

print("\nDetailed counts:")
print("-" * 50)

print(f"True Negatives  : {tn}")
print(f"False Positives : {fp}")
print(f"False Negatives : {fn}")
print(f"True Positives  : {tp}")


# =========================================================
# 10. EVENT DETECTION
# =========================================================
#
# Determine whether each rainfall episode was detected.
#
# We use the same >=20 mm target definition.
#

test_results = test[
    [
        "time",
        "future_6h_rain",
        "target"
    ]
].copy()

test_results["probability"] = test_probability

test_results["prediction"] = test_prediction


# =========================================================
# 11. FIND DISTINCT ACTUAL EVENTS
# =========================================================

test_results["event_start"] = (
    (test_results["target"] == 1)
    &
    (test_results["target"].shift(1, fill_value=0) == 0)
)

test_results["event_id"] = (
    test_results["event_start"].cumsum()
)

actual_events = test_results[
    test_results["target"] == 1
].copy()

actual_events = actual_events[
    actual_events["event_id"] > 0
]


# =========================================================
# 12. FIND DISTINCT PREDICTED EVENTS
# =========================================================

test_results["prediction_start"] = (
    (test_results["prediction"] == 1)
    &
    (test_results["prediction"].shift(1, fill_value=0) == 0)
)

test_results["prediction_event_id"] = (
    test_results["prediction_start"].cumsum()
)

predicted_events = test_results[
    test_results["prediction"] == 1
].copy()


# =========================================================
# 13. EVENT SUMMARY
# =========================================================

actual_event_count = (
    actual_events["event_id"].nunique()
)

predicted_event_count = (
    predicted_events["prediction_event_id"].nunique()
)


print("\n" + "=" * 70)
print("EVENT-LEVEL SUMMARY")
print("=" * 70)

print(
    f"\nDistinct actual rainfall events   : "
    f"{actual_event_count}"
)

print(
    f"Distinct predicted alert episodes: "
    f"{predicted_event_count}"
)


# =========================================================
# 14. SHOW STRONGEST 2025 EVENTS
# =========================================================

strongest = (
    test_results[test_results["target"] == 1]
    .sort_values(
        "future_6h_rain",
        ascending=False
    )
    .head(15)
)

print("\n" + "=" * 70)
print("STRONGEST 2025 RAINFALL WINDOWS")
print("=" * 70)

print(
    strongest[
        [
            "time",
            "future_6h_rain",
            "probability",
            "prediction"
        ]
    ].to_string(index=False)
)


# =========================================================
# 15. SAVE TEST RESULTS
# =========================================================

output_file = (
    "data/processed/"
    "rainfall_test_predictions_2025.csv"
)

test_results.to_csv(
    output_file,
    index=False
)

print("\n" + "=" * 70)
print("EVALUATION COMPLETE")
print("=" * 70)

print(f"\nSaved test predictions to:")
print(output_file)