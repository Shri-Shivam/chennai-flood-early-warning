# Project Decisions

## Decision 001 — Study Area

Use Chennai Metropolitan Region as the initial study area.

Reason:

Chennai has documented heavy-rainfall and flood events and
suitable satellite/observational data for historical
validation.

---

## Decision 002 — Primary Forecast Horizon

Use a 6-hour heavy rainfall prediction as the primary MVP
forecast horizon.

Reason:

A 6-hour horizon provides useful early warning while
remaining more practical to train and validate than an
unsupported long-range prediction.

---

## Decision 003 — Rainfall Prediction Target

Predict the probability of heavy rainfall occurring within
the next 6 hours.

Output:

- Probability
- Rainfall category
- Supporting model features

---

## Decision 004 — Rainfall Model

Use XGBoost as the primary machine-learning model.

Reason:

XGBoost performs well on structured/tabular weather data,
is relatively fast to train, and provides useful feature
importance/explainability.

---

## Decision 005 — Time-Based Validation

Use chronological train/validation/test splitting.

Reason:

Random splitting of time-series data can cause future
information to leak into training data.

---

## Decision 006 — Flood Depth

Do NOT predict exact flood depth.

Reason:

Reliable flood-depth prediction requires calibrated
hydraulic modelling and sufficient ground-truth data.

---

## Decision 007 — Flood Arrival Time

Do NOT provide an exact flood arrival time.

Reason:

Exact flood-routing predictions require stronger physical
and observational modelling than is available for the MVP.

---

## Decision 008 — Terrain Model

Use DEM-derived terrain susceptibility rather than a full
hydraulic flood simulation.

Derive:

- Elevation
- Slope
- Flow direction
- Flow accumulation

Reason:

This provides a computationally practical indication of
where runoff is more likely to concentrate without claiming
unsupported water depths.

---

## Decision 009 — Flow Accumulation Interpretation

Flow accumulation represents areas where surface runoff
naturally concentrates.

It must NOT be interpreted directly as:

- Flood depth
- Water level
- Flood arrival time

---

## Decision 010 — Combined Risk

Combine rainfall risk with terrain susceptibility and
available spatial context.

Risk levels:

- LOW
- MODERATE
- HIGH

The risk score should remain explainable.

---

## Decision 011 — Historical Validation

Use at least one real historical flood event for a
demonstration backtest.

Compare:

Predicted high-risk zones
vs.
Observed flood extent

Possible metrics:

- IoU
- Precision
- Recall
- F1

Reason:

Historical validation provides evidence that can be shown
during the SIH demonstration.

---

## Decision 012 — Validation Claim

A single historical event is a backtest.

It must NOT be presented as proof that the system works
universally across all rainfall and flood conditions.

---

## Decision 013 — Population Exposure

Use population-density data to estimate the approximate
population located within flagged risk zones.

Do NOT claim that all people within the zone will definitely
be flooded.

---

## Decision 014 — Early Action

Generate recommendations rather than autonomous government
commands.

The system may recommend:

- Drain inspection
- Pump preparation
- Rescue readiness
- Hospital preparedness
- Electrical infrastructure inspection
- Shelter/resource preparation
- Public safety warnings

---

## Decision 015 — Autonomous Infrastructure Control

The system must NOT autonomously:

- Shut down electricity
- Control pumps
- Order evacuations
- Command emergency services

Reason:

These actions require authorized human decision-makers and
operational systems.

---

## Decision 016 — Dashboard

Use Streamlit for the MVP dashboard.

Reason:

Streamlit allows rapid development of an interactive
Python-based demonstration.

---

## Decision 017 — Reproducibility

All major data-processing and modelling steps must be
implemented in reproducible Python scripts or notebooks.

The project should avoid manual processing that cannot be
repeated.

---

## Decision 018 — Source of Truth

GitHub is the project's source of truth.

The following documents control the project:

1. PROJECT_SPEC.md
2. ROADMAP.md
3. ARCHITECTURE.md
4. DECISIONS.md
5. DATA_SOURCES.md
6. MODEL_CARD.md

AI assistants must read these documents before making
major architectural changes.

---

## Decision 019 — AI Tool Usage

AI tools may assist with:

- Coding
- Debugging
- Documentation
- Research
- Testing
- Architecture review

AI-generated suggestions must be verified against official
documentation, data sources, experiments, and project
requirements.

---

## Decision 020 — MVP Priority

Prioritize a working end-to-end pipeline over adding a
large number of advanced features.

The minimum successful demonstration should show:

Weather
→ Rainfall Prediction
→ Terrain Susceptibility
→ Combined Risk
→ Historical Validation
→ Exposure
→ Early Action
→ Dashboard
---

## Decision 007 — Scientific Principles for Stages 6–9

1. **Project-Defined Rainfall Threshold**: The 20 mm / 6-hour rainfall threshold is a project-defined significant rainfall target; it must NEVER be cited as an IMD Heavy Rainfall classification.
2. **Rainfall Forecasting Horizon**: AI #1 predicts a rainfall-risk signal over a 6-hour rainfall forecasting horizon; it does NOT predict exact flood arrival time.
3. **Regional Trigger vs Spatial Field**: AI #1 probability serves as a regional weather trigger and must NOT be converted or broadcast as a simulated 250 m spatial rainfall field.
4. **Hydrologic Representation**: Flow accumulation represents runoff concentration and topographical drainage convergence; it must not be casually described as merely "low-lying."
5. **Spatial Resolution Bound**: The 250 m grid is a practical spatial analysis grid; unsupported claims of 100 m precision are prohibited.
6. **Exposure Definition**: Exposure denotes population, roads, or facilities located within a predicted risk zone; it does NOT imply that these entities will definitely experience inundation or structural damage.
7. **Infrastructure Status**: OpenStreetMap roads and facilities represent spatial exposure only and must NOT be treated as real-time operational status (e.g., closures or impassability).
8. **Sample Size & Proof-of-Concept**: Only two independently verified flood episodes (Nov 8–12 and Nov 28, 2021) are currently available in the ground-truth satellite label set; all validation results are proof-of-concept evidence rather than broad generalizations.
9. **Anti-Leakage Mandate**: Future observed rainfall ($T+1 \dots T+6$) must NEVER be used as a predictor or feature when evaluating forecast-driven risk.
