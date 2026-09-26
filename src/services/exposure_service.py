"""SIH26071 - exposure service.

HONEST STATUS: no population, building, road, or critical-infrastructure
dataset currently exists anywhere in this repository (verified by
inspection before writing this file -- see docs/backend.md). ROADMAP.md
lists population/infrastructure exposure as unchecked future work.

Per this project's own explicit rule ("if required datasets are not
present, implement the clean interface and document the missing data
rather than fabricating values"), this module implements the interface
a real exposure engine would have, and returns an explicit
"not available" result with a clear reason -- never an invented number,
never a silent zero that could be misread as "zero people exposed."
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ExposureResult:
    cell_id: str
    estimated_population_exposed: Optional[int]
    affected_facilities: Optional[List[str]]
    data_available: bool
    reason_if_unavailable: Optional[str]


NO_DATA_REASON = (
    "No population, building, or critical-infrastructure dataset is currently "
    "integrated into this project (see ROADMAP.md Phase 6 and docs/backend.md). "
    "This is not a computed zero -- it means exposure has not been estimated."
)


def estimate_exposure(cell_ids: List[str]) -> List[ExposureResult]:
    """Returns an explicit not-available result for every cell. This
    function exists so callers (the API, a future dashboard) can depend
    on a stable interface now, and it will start returning real numbers
    the moment real data is wired in -- without any caller code changing.
    Never fabricates a population or facility count."""
    return [
        ExposureResult(
            cell_id=cid,
            estimated_population_exposed=None,
            affected_facilities=None,
            data_available=False,
            reason_if_unavailable=NO_DATA_REASON,
        )
        for cid in cell_ids
    ]
