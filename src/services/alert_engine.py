"""SIH26071 - alert / action engine.

Maps a risk_class (from src/services/risk_engine.py's classify_risk,
itself driven by configurable, NOT officially validated thresholds -- see
docs/backend.md) to role-specific recommended actions. All actions are
recommendations for a human decision-maker. Nothing in this module
triggers, controls, or automates any physical system -- electricity
output is explicitly a recommendation to "consider," never a command.
"""
from dataclasses import dataclass
from typing import Dict, List

from src.services.risk_engine import RISK_CLASSES

ROLES = ("citizen", "municipal_authority", "disaster_management", "hospitals", "electricity_operator")

_ACTIONS: Dict[str, Dict[str, List[str]]] = {
    "NORMAL": {
        "citizen": ["No specific action needed. Stay aware of official weather updates."],
        "municipal_authority": ["Routine monitoring."],
        "disaster_management": ["No action required."],
        "hospitals": ["No action required."],
        "electricity_operator": ["No action required."],
    },
    "WATCH": {
        "citizen": ["Monitor official rainfall and flood updates.", "Avoid unnecessary travel through known low-lying areas."],
        "municipal_authority": ["Increase monitoring of drainage hotspots in flagged cells."],
        "disaster_management": ["Review readiness of response teams for the flagged area."],
        "hospitals": ["No specific action required yet."],
        "electricity_operator": ["No specific action required yet."],
    },
    "WARNING": {
        "citizen": ["Avoid low-lying roads in the flagged area.", "Move valuables/essential items to higher ground if in a flagged zone."],
        "municipal_authority": ["Inspect drainage hotspots in flagged cells.", "Prepare pumps for the flagged area."],
        "disaster_management": ["Stage resources near flagged high-risk clusters."],
        "hospitals": ["Review contingency plans for flagged-area facilities."],
        "electricity_operator": ["Consider inspection of infrastructure in flagged high-risk areas."],
    },
    "HIGH_RISK": {
        "citizen": ["Avoid the flagged area if possible.", "Follow official evacuation guidance if issued by authorities."],
        "municipal_authority": ["Prepare pumps and drainage response for the flagged area.", "Coordinate with disaster management."],
        "disaster_management": ["Prepare response teams for the flagged high-risk clusters."],
        "hospitals": ["Activate contingency plans for flagged-area facilities if applicable."],
        "electricity_operator": ["Consider isolating electricity supply in flagged high-risk areas, per standard safety protocol. This is a recommendation for a human operator, not an automated action."],
    },
}


@dataclass(frozen=True)
class Alert:
    cell_id: str
    risk_class: str
    recommended_actions: Dict[str, List[str]]


def generate_alert(cell_id: str, risk_class: str) -> Alert:
    if risk_class not in RISK_CLASSES:
        raise ValueError(f"Unknown risk_class {risk_class!r}. Must be one of {RISK_CLASSES}.")
    return Alert(cell_id=cell_id, risk_class=risk_class, recommended_actions=_ACTIONS[risk_class])
