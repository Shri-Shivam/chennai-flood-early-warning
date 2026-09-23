"""SIH26071 - risk engine.

Chains AI#1 (rainfall) and AI#2 (inundation) into a structured per-cell
risk result. Deliberately does NOT blend the two into a single number:
Stage 7/8 found no consistent benefit from folding AI#1's probability
into AI#2's prediction, so this engine reports both, separately, and
classifies risk_class from AI#2's inundation probability alone -- AI#1's
rainfall probability remains an independent, upstream signal, exactly as
Stage 7/8's own scientific conclusion recommends.

No FastAPI dependency. No live data fetching (that's
src/ingestion/open_meteo.py's job, called by whoever assembles the
`rainfall_features` dict passed in here).
"""
from dataclasses import dataclass
from typing import List, Optional

from src.config import settings
from src.services.rainfall_service import predict_rainfall, RainfallResult
from src.services.inundation_service import predict_inundation


RISK_CLASSES = ("NORMAL", "WATCH", "WARNING", "HIGH_RISK")


def classify_risk(inundation_probability: float) -> str:
    """Engineering/demo thresholds, not officially validated -- see
    docs/backend.md and models/production/ai2_baseline_metadata.json for
    why no independently-validated production threshold exists for this
    exact classification. Configurable via src/config.py."""
    if inundation_probability >= settings.alert_high_risk_threshold:
        return "HIGH_RISK"
    if inundation_probability >= settings.alert_warning_threshold:
        return "WARNING"
    if inundation_probability >= settings.alert_watch_threshold:
        return "WATCH"
    return "NORMAL"


@dataclass(frozen=True)
class CellRiskResult:
    cell_id: str
    inundation_risk_probability: float
    risk_class: str


@dataclass(frozen=True)
class RiskEngineResult:
    rainfall: Optional[RainfallResult]
    cells: List[CellRiskResult]
    limitation_note: str = (
        "Retrospective, proof-of-concept models validated on only two "
        "independently verified historical flood episodes. risk_class "
        "boundaries are engineering/demo thresholds, not independently "
        "validated. This is a modeled risk score, not an observed or "
        "guaranteed inundation outcome."
    )


def assess_risk(
    rainfall_features: Optional[dict],
    cells: List[dict],
) -> RiskEngineResult:
    """rainfall_features: AI#1's 20 features, or None to skip the rainfall
    signal entirely (e.g. if only a spatial risk snapshot is wanted).
    cells: list of dicts, each with 'cell_id' + AI#2's 8 baseline features.
    """
    rainfall_result = predict_rainfall(rainfall_features) if rainfall_features is not None else None

    inundation_results = predict_inundation(cells)
    cell_results = [
        CellRiskResult(
            cell_id=r.cell_id,
            inundation_risk_probability=r.inundation_risk_probability,
            risk_class=classify_risk(r.inundation_risk_probability),
        )
        for r in inundation_results
    ]

    return RiskEngineResult(rainfall=rainfall_result, cells=cell_results)
