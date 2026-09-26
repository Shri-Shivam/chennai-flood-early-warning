"""SIH26071 - Model loading layer.

Separates model I/O and schema validation from both training code and
API code. Models are loaded once per process (cached) and never retrain
during inference.

Schema validation is real, not decorative: every model file used here is
an XGBoost JSON export that embeds its own `feature_names` (captured
automatically when the model was originally trained on a pandas
DataFrame). This module reads that embedded list directly from the model
file rather than hard-coding a second copy of it, so there is exactly
one source of truth for "what features does this model expect."
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from xgboost import XGBClassifier, XGBRegressor

from src.config import settings

ROOT = Path(__file__).resolve().parents[2]


class SchemaValidationError(ValueError):
    """Raised when input data does not satisfy a loaded model's required feature schema."""


@dataclass(frozen=True)
class LoadedModel:
    name: str
    path: Path
    feature_names: tuple
    model: object  # XGBClassifier or XGBRegressor

    def validate(self, df: pd.DataFrame) -> None:
        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            raise SchemaValidationError(
                f"Model '{self.name}' requires feature(s) not present in input: {missing}. "
                f"Required schema: {list(self.feature_names)}."
            )

    def predict_proba(self, df: pd.DataFrame):
        """Predict positive-class probability. Validates schema first, then
        selects exactly the model's required columns in the model's own
        recorded order before predicting -- never trusts caller ordering."""
        self.validate(df)
        ordered = df[list(self.feature_names)]
        return self.model.predict_proba(ordered)[:, 1]

    def predict_value(self, df: pd.DataFrame):
        """For regressors (e.g. the Stage 6 rainfall-amount regressor)."""
        self.validate(df)
        ordered = df[list(self.feature_names)]
        return self.model.predict(ordered)


_CACHE: dict = {}


def _load_xgb_json(path: Path, kind: str):
    if kind == "classifier":
        m = XGBClassifier()
    elif kind == "regressor":
        m = XGBRegressor()
    else:
        raise ValueError(f"Unknown model kind: {kind!r}")
    m.load_model(str(path))
    return m


def load_model(name: str, relative_path: str, kind: str = "classifier") -> LoadedModel:
    """Load (or return a cached) model by a logical name.

    relative_path is relative to the repository root. Raises FileNotFoundError
    if the model file does not exist -- this function never fabricates a
    model or falls back to a default.
    """
    if name in _CACHE:
        return _CACHE[name]

    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Model file not found for '{name}': {path}")

    model = _load_xgb_json(path, kind)
    booster = model.get_booster()
    feature_names = tuple(booster.feature_names or ())
    if not feature_names:
        raise SchemaValidationError(
            f"Model '{name}' at {path} has no embedded feature_names metadata -- "
            "cannot safely validate inputs against it."
        )

    loaded = LoadedModel(name=name, path=path, feature_names=feature_names, model=model)
    _CACHE[name] = loaded
    return loaded


def clear_cache() -> None:
    """Testing/debug helper -- not used by the API in normal operation."""
    _CACHE.clear()


# Known, documented model registry. Adding a model here is the only
# change needed to make it loadable/servable -- no other code should
# hard-code a model path.
REGISTRY = {
    "ai1_rainfall": {
        "path": settings.ai1_rainfall_model_path,
        "kind": "classifier",
        "description": "AI#1: current production rainfall classifier "
                        "(chronological split train 2016-2022 / val 2023-2024 / test 2025). "
                        "Predicts P(future_6h_rain >= 20mm).",
    },
    "ai2_baseline_production": {
        "path": settings.ai2_production_model_path,
        "kind": "classifier",
        "description": "AI#2: production inundation-risk baseline (Exp_A_Baseline "
                        "architecture, refit on all available class-0/1 ground truth). "
                        "See models/production/ai2_baseline_metadata.json for details -- "
                        "its operating threshold was selected via spatial-block OOF CV, "
                        "not validated against an independent flood episode.",
    },
}


def load_registered(name: str) -> LoadedModel:
    if name not in REGISTRY:
        raise KeyError(f"'{name}' is not a registered model. Known models: {list(REGISTRY)}")
    entry = REGISTRY[name]
    return load_model(name, entry["path"], entry["kind"])
