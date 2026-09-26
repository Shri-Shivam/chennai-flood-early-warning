"""SIH26071 - AI#1 rainfall service.

Thin, testable wrapper around the model-loader for AI#1. Contains no
FastAPI dependency -- usable from the API, from a batch script, or from
tests directly.
"""
from dataclasses import dataclass

import pandas as pd

from src.inference.model_loader import load_registered


@dataclass(frozen=True)
class RainfallResult:
    significant_rainfall_probability: float
    model_version: str


def predict_rainfall(features: dict) -> RainfallResult:
    """features must contain exactly AI#1's 20 documented predictors
    (see src/data/create_rainfall_features.py). Raises SchemaValidationError
    (via the model loader) if any required feature is missing."""
    model = load_registered("ai1_rainfall")
    df = pd.DataFrame([features])
    proba = model.predict_proba(df)
    return RainfallResult(
        significant_rainfall_probability=float(proba[0]),
        model_version=model.path.name,
    )
