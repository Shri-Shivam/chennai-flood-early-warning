"""SIH26071 - Stage 6
Leakage-safe retrospective and walk-forward forecasting for AI #1.

Design:
- 20 causal predictor features only.
- future_6h_rain is used only to define/evaluate the target.
- Retrospective November 2021 model is trained only on observations <= 2021-10-31 23:00.
- Walk-forward yearly evaluation trains each year's model only on earlier years.
- Threshold selection uses a chronological validation slice immediately before the
  test year; the test year is never used for threshold selection.
- Regression is retained as a secondary exploratory output.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix,
)
from xgboost import XGBClassifier, XGBRegressor

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/processed/rainfall_ml_dataset.csv"
RETRO = ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"
MET = ROOT / "data/processed/ai1_walk_forward_metrics.csv"
REPORT = ROOT / "data/processed/ai1_stage6_report.txt"
MODEL_DIR = ROOT / "models/stage6_retrospective_2021"

FEATURES=[
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "wind_speed_10m", "precipitation",
    "rain_lag_1h", "rain_lag_3h", "rain_lag_6h",
    "rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h",
    "pressure_change_3h", "pressure_change_6h",
    "humidity_change_3h", "humidity_change_6h",
    "hour", "month", "day_of_year",
]
TARGET = "target"
FUTURE = "future_6h_rain"

XGB_PARAMS = dict(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="aucpr",
        random_state=42,
    n_jobs=-1,
    tree_method="hist",
)

REG_PARAMS = dict(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
    tree_method="hist",
)

THRESHOLDS = np.round(np.arange(0.50, 0.951, 0.01), 2)


def load_dataset():
    d = pd.read_csv(DATA)
    if "time" not in d.columns:
        raise ValueError("Expected 'time' column.")
    d["timestamp"] = pd.to_datetime(d["time"], errors="raise")
    d = d.sort_values("timestamp").reset_index(drop=True)

    required = FEATURES + [TARGET, FUTURE]
    missing = [c for c in required if c not in d.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    forbidden = {"future_6h_rain", "target"}
    bad = [c for c in FEATURES if c in forbidden]
    if bad:
        raise AssertionError(f"Future/target leakage in FEATURES: {bad}")

    if not d["timestamp"].is_monotonic_increasing:
        raise AssertionError("Dataset is not chronological.")

    if d[required].isna().any().any():
        raise ValueError("Required Stage 6 fields contain missing values.")

    return d


def classifier(train_data):
    y = train_data[TARGET].astype(int)
    positives = int(y.sum())
    negatives = int(len(y) - positives)

    if positives == 0:
        raise ValueError("Training data contains no positive target samples.")

    params = dict(XGB_PARAMS)
    params["scale_pos_weight"] = negatives / positives
    return XGBClassifier(**params)


def regressor():
    return XGBRegressor(**REG_PARAMS)


def csi(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return tp / max(1, tp + fp + fn)


def select_threshold(y_val, p_val):
    """Select threshold from validation data only.

    Primary objective is CSI, with F1 as a deterministic tie-breaker.
    """
    best = None
    for t in THRESHOLDS:
        pred = (p_val >= t).astype(int)
        score = csi(y_val, pred)
        f1 = f1_score(y_val, pred, zero_division=0)
        candidate = (score, f1, t)
        if best is None or candidate > best:
            best = candidate
    return float(best[2])


def classification_metrics(y, p, threshold):
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "F1": float(f1_score(y, pred, zero_division=0)),
        "PR_AUC": float(average_precision_score(y, p)),
        "Brier": float(brier_score_loss(y, p)),
        "CSI": float(csi(y, pred)),
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
    }


def chronological_validation_split(train):
    """Use the last 25% of the final pre-test year as validation.

    The split is chronological and does not use the test-year observations.
    If the training history is short, use the last 20% instead.
    """
    train = train.sort_values("timestamp").reset_index(drop=True)
    last_year = int(train["timestamp"].dt.year.max())
    candidate = train[train["timestamp"].dt.year == last_year]
    if len(candidate) >= 1000 and candidate[TARGET].sum() > 0:
        # Hold out the last 25% of the final pre-test year as validation.
        cut = int(len(candidate) * 0.75)
        fit_part = candidate.iloc[:cut]
        val_part = candidate.iloc[cut:]
        older = train[train["timestamp"].dt.year < last_year]
        fit = pd.concat([older, fit_part], ignore_index=True)
        if val_part[TARGET].sum() > 0:
            return fit, val_part

    cut = max(1, int(len(train) * 0.80))
    return train.iloc[:cut].copy(), train.iloc[cut:].copy()


def fit_and_predict(train_fit, validation, test):
    model = classifier(train_fit)
    model.fit(train_fit[FEATURES], train_fit[TARGET].astype(int))
    p_val = model.predict_proba(validation[FEATURES])[:, 1]
    threshold = select_threshold(
        validation[TARGET].astype(int).to_numpy(), p_val
    )
    p_test = model.predict_proba(test[FEATURES])[:, 1]
    return model, threshold, p_test


def retrospective_2021(d):
    cutoff = pd.Timestamp("2021-10-31 23:00:00")
    test_start = pd.Timestamp("2021-11-01 00:00:00")
    test_end = pd.Timestamp("2021-12-01 00:00:00")

    train = d[d["timestamp"] <= cutoff].copy()
    test = d[(d["timestamp"] >= test_start) & (d["timestamp"] < test_end)].copy()

    fit, validation = chronological_validation_split(train)
    model = classifier(train_fit)
    model.fit(fit[FEATURES], fit[TARGET].astype(int))

    p_val = model.predict_proba(validation[FEATURES])[:, 1]
    threshold = select_threshold(
        validation[TARGET].astype(int).to_numpy(), p_val
    )

    p = model.predict_proba(test[FEATURES])[:, 1]

    # Secondary regression; future_6h_rain is NEVER a predictor.
    reg = regressor()
    reg.fit(fit[FEATURES], fit[FUTURE].astype(float))
    amount = np.clip(reg.predict(test[FEATURES]), 0, None)

    y = test[TARGET].astype(int).to_numpy()
    metrics = classification_metrics(y, p, threshold)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_DIR / "xgboost_pre_nov2021.json")
    reg.save_model(MODEL_DIR / "xgboost_pre_nov2021_regressor.json")

    pred = pd.DataFrame({
        "timestamp": test["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "training_end": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "threshold_selected_pre_event": threshold,
        "predicted_probability": p,
        "predicted_class": (p >= threshold).astype(int),
        "actual_future_6h_rain": test[FUTURE].to_numpy(),
        "actual_target": y,
        "predicted_amount_mm": amount,
    })
    pred.to_csv(RETRO, index=False, float_format="%.10g")

    # Regression metrics on the retrospective month.
    actual_amount = test[FUTURE].astype(float).to_numpy()
    reg_metrics = {
        "MAE": float(mean_absolute_error(actual_amount, amount)),
        "RMSE": float(mean_squared_error(actual_amount, amount) ** 0.5),
        "R2": float(r2_score(actual_amount, amount)),
    }

    return metrics, reg_metrics, threshold


def walk_forward(d):
    rows = []
    for year in range(2021, 2026):
        train = d[d["timestamp"].dt.year < year].copy()
        test = d[d["timestamp"].dt.year == year].copy()
        if train.empty or test.empty:
            continue

        fit, validation = chronological_validation_split(train)
        model, threshold, p_test = fit_and_predict(fit, validation, test)
        y_test = test[TARGET].astype(int).to_numpy()
        m = classification_metrics(y_test, p_test, threshold)
        m.update({
            "year": year,
            "n_test": len(test),
            "n_positive": int(y_test.sum()),
            "training_end": train["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S"),
        })
        rows.append(m)

    out = pd.DataFrame(rows)
    cols = [
        "year", "threshold", "precision", "recall", "F1", "PR_AUC",
        "Brier", "CSI", "TN", "FP", "FN", "TP", "n_test",
        "n_positive", "training_end",
    ]
    out = out[cols]
    out.to_csv(MET, index=False)
    return out


def write_report(retro, reg, retro_threshold, walk):
    lines = [
        "SIH26071 - Stage 6: AI #1 Rainfall Forecasting",
        "",
        "Leakage controls:",
        "- Predictor set contains only 20 causal features.",
        "- future_6h_rain is never used as a predictor.",
        "- November 2021 retrospective training cutoff: 2021-10-31 23:00.",
        "- Walk-forward models train only on years before each test year.",
        "- Test-year labels are not used for threshold selection.",
        "",
        "November 2021 retrospective results:",
        f"- Selected threshold: {retro_threshold:.2f}",
        f"- Precision: {retro['precision']:.4f}",
        f"- Recall: {retro['recall']:.4f}",
        f"- F1: {retro['F1']:.4f}",
        f"- PR-AUC: {retro['PR_AUC']:.4f}",
        f"- Brier: {retro['Brier']:.4f}",
        f"- CSI: {retro['CSI']:.4f}",
        f"- Confusion matrix: TN={retro['TN']}, FP={retro['FP']}, FN={retro['FN']}, TP={retro['TP']}",
        "",
        "Secondary rainfall-amount regression:",
        f"- MAE: {reg['MAE']:.4f} mm",
        f"- RMSE: {reg['RMSE']:.4f} mm",
        f"- R2: {reg['R2']:.4f}",
        "",
        "Walk-forward results:",
    ]
    for _, r in walk.iterrows():
        lines.append(
            f"- {int(r['year'])}: threshold={r['threshold']:.2f}, "
            f"precision={r['precision']:.4f}, recall={r['recall']:.4f}, "
            f"F1={r['F1']:.4f}, PR-AUC={r['PR_AUC']:.4f}, "
            f"CSI={r['CSI']:.4f}"
        )

    lines += [
        "",
        "Interpretation:",
        "- Classification is the primary operational warning output.",
        "- Regression amount is exploratory and should not be interpreted as an exact rainfall forecast.",
        "- This Stage 6 output represents a 6-hour rainfall forecasting horizon, not an exact flood arrival-time prediction.",
        "- Historical reference metrics should be compared separately; they must not be hard-coded into this implementation.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    d = load_dataset()
    retro, reg, threshold = retrospective_2021(d)
    walk = walk_forward(d)
    write_report(retro, reg, threshold, walk)

    print("Stage 6 completed.")
    print(
        f"November 2021: threshold={threshold:.2f}, "
        f"precision={retro['precision']:.4f}, "
        f"recall={retro['recall']:.4f}, "
        f"F1={retro['F1']:.4f}, "
        f"PR-AUC={retro['PR_AUC']:.4f}"
    )
    print(f"Walk-forward metrics: {MET}")
    print(f"Retrospective predictions: {RETRO}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()


