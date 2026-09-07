# Chennai Flood Early Warning System

## Objective

Build an AI-assisted heavy rainfall early-warning and
flood-risk decision-support system for the Chennai region.

The system should estimate heavy rainfall risk, identify
areas that are more susceptible to runoff concentration,
validate predictions against a real historical flood event,
estimate population and infrastructure exposure, and provide
role-specific early-action recommendations.

---

## Core Pipeline

Weather Data
→ AI Rainfall Prediction
→ Terrain Susceptibility
→ Combined Flood Risk
→ Historical Backtest
→ Exposure Analysis
→ Early Action
→ Dashboard

---

## Study Area

Chennai Metropolitan Region, Tamil Nadu, India.

---

## Historical Event

November 2021 Chennai flood.

The historical event and available observed flood-extent
data must be verified before implementation.

---

## AI Component

XGBoost classifier.

---

## Prediction Target

Probability of heavy rainfall occurring within the next
6 hours.

The system should output:

- Heavy rainfall probability
- Rainfall risk category
- Model confidence/evidence indicators where appropriate

---

## Weather Features

Historical weather data may include:

- Rainfall
- Temperature
- Humidity
- Atmospheric pressure
- Wind speed
- Rainfall accumulation
- Pressure trend
- Humidity trend

Derived temporal features:

- Previous 1-hour rainfall
- Previous 3-hour rainfall
- Previous 6-hour rainfall
- Previous 12-hour rainfall
- Previous 24-hour rainfall
- Rolling rainfall accumulation

---

## Rainfall Classification

Use appropriate official rainfall classification or
thresholds, preferably from the India Meteorological
Department (IMD).

The classification and threshold values must be documented
in DATA_SOURCES.md.

---

## Terrain Analysis

Use SRTM Digital Elevation Model (DEM).

Derive:

- Elevation
- Slope
- Flow direction
- Flow accumulation

Terrain susceptibility should identify areas where
surface runoff is more likely to concentrate.

Flow accumulation should NOT be interpreted as directly
representing flood depth or water level.

---

## Additional Spatial Data

Where feasible, incorporate:

- River/drainage network
- Water bodies
- Land cover
- Built-up surface
- Roads
- Hospitals
- Schools
- Critical infrastructure

Possible sources include OpenStreetMap, satellite-derived
datasets, and authoritative government datasets.

---

## Combined Flood Risk

Combine:

- Rainfall risk
- Terrain susceptibility
- Water-body/drainage context
- Land-cover/built-up context where feasible

Generate an explainable risk score.

Risk levels:

- LOW
- MODERATE
- HIGH

The risk score must be explainable through its major
contributing factors.

---

## Historical Backtest Validation

Select a real historical flood event.

Recreate the event using historical weather conditions
and the same prediction pipeline.

Generate the predicted high-risk zones.

Compare predicted high-risk zones against observed flood
extent.

Possible spatial evaluation metrics:

- Intersection over Union (IoU)
- Spatial precision
- Spatial recall
- F1 score

A single historical event is a backtest and must not be
presented as proof of universal accuracy.

---

## Exposure Analysis

Use population-density data such as WorldPop where feasible.

Estimate:

"Approximate population located within the flagged
risk zone."

Do NOT claim:

"These people will definitely be flooded."

Where data permits, identify:

- Roads
- Hospitals
- Schools
- Critical facilities
- Electrical infrastructure

---

## Early Action

Generate role-specific recommendations for:

### Municipality

- Inspect critical drainage areas
- Prepare pumps and response equipment
- Monitor high-risk locations

### Rescue / Emergency Services

- Prepare response teams
- Position emergency equipment
- Monitor high-risk areas

### Electricity Department

- Inspect vulnerable electrical infrastructure
- Consider authorized precautionary isolation where required

### Hospitals

- Prepare emergency capacity
- Review accessibility and emergency routes

### Disaster Management

- Prepare shelters and emergency resources
- Coordinate response readiness

### Public

- Provide localized safety warnings
- Avoid unnecessary travel through high-risk areas
- Follow official emergency instructions

The system provides decision support and recommendations.

It does NOT autonomously:

- Command government departments
- Shut down electrical infrastructure
- Order evacuations

---

## Dashboard

The dashboard should display:

1. Rainfall prediction
2. Rainfall probability
3. Terrain susceptibility
4. Combined flood-risk map
5. Risk factors
6. Historical backtest
7. Predicted vs observed flood extent
8. Population exposure
9. Infrastructure exposure
10. Role-specific early actions
11. Confidence/evidence information

---

## Technology Stack

### Programming

- Python

### Machine Learning

- XGBoost
- Scikit-learn
- Pandas
- NumPy

### Geospatial

- Rasterio
- GeoPandas
- Shapely
- PyProj
- Appropriate DEM hydrology tools

### Data

- Open-Meteo
- SRTM DEM
- OpenStreetMap
- WorldPop
- Sentinel-1 / authoritative flood extent data
- IMD or other authoritative rainfall information where available

### Visualization

- Folium / Plotly
- Streamlit

---

## Validation Philosophy

The project must prioritize:

- Scientific defensibility
- Explainability
- Reproducibility
- Historical validation
- Honest uncertainty

The system must never present unsupported precision.

---

## Explicitly Out of MVP Scope

The following are NOT required for the MVP:

- Exact flood depth prediction
- Exact flood arrival time
- Dam-break simulation
- Full hydraulic flood modelling
- IoT sensor network
- CCTV drain blockage detection
- Autonomous electricity shutdown
- Autonomous evacuation orders
- Nationwide deployment