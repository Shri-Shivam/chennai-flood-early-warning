import pandas as pd
import numpy as np

from xgboost import XGBClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score
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
# FEATURES
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
# CHRONOLOGICAL SPLIT
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


# =========================================================
# CLASS WEIGHT
# =========================================================

negative_count = (y_train == 0).sum()
positive_count = (y_train == 1).sum()

scale_pos_weight = negative_count / positive_count


# =========================================================
# TRAIN MODEL
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

print("Training model...")

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

print("Training complete.")


# =========================================================
# VALIDATION PROBABILITIES
# =========================================================

val_probability = model.predict_proba(X_val)[:, 1]


# =========================================================
# THRESHOLD ANALYSIS
# =========================================================

thresholds = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90
]


print("\n" + "=" * 80)
print("VALIDATION THRESHOLD ANALYSIS")
print("=" * 80)

print(
    f"\n{'Threshold':>10}"
    f"{'Precision':>12}"
    f"{'Recall':>12}"
    f"{'F1':>12}"
    f"{'Alerts':>10}"
)

print("-" * 80)


for threshold in thresholds:

    prediction = (
        val_probability >= threshold
    ).astype(int)

    precision = precision_score(
        y_val,
        prediction,
        zero_division=0
    )

    recall = recall_score(
        y_val,
        prediction,
        zero_division=0
    )

    f1 = f1_score(
        y_val,
        prediction,
        zero_division=0
    )

    alerts = prediction.sum()

    print(
        f"{threshold:>10.2f}"
        f"{precision:>12.3f}"
        f"{recall:>12.3f}"
        f"{f1:>12.3f}"
        f"{alerts:>10}"
    )


print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)