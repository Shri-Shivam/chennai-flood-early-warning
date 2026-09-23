"""SIH26071 - AI#2 inundation-risk service.

Thin, testable wrapper around the model-loader for the production AI#2
baseline. No FastAPI dependency.
"""
from dataclasses import dataclass
from typing import List

import pandas as pd

from src.inference.model_loader import load_registered


@dataclass(frozen=True)
class InundationCellResult:
    cell_id: str
    inundation_risk_probability: float


def predict_inundation(cells: List[dict]) -> List[InundationCellResult]:
    """Each dict in `cells` must contain 'cell_id' plus AI#2's 8 documented
    baseline predictors (rain_1h..rain_24h, elevation, slope_degrees,
    distance_to_drainage). Raises SchemaValidationError if any required
    feature is missing from any cell."""
    model = load_registered("ai2_baseline_production")
    df = pd.DataFrame(cells)
    proba = model.predict_proba(df)
    return [
        InundationCellResult(cell_id=cid, inundation_risk_probability=float(p))
        for cid, p in zip(df["cell_id"], proba)
    ]
