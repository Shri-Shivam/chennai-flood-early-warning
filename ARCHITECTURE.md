# System Architecture

## 1. High-Level Architecture

The system follows this pipeline:

Weather Data
→ Data Cleaning
→ Feature Engineering
→ Rainfall Prediction Model
→ Rainfall Risk
→ Terrain Analysis
→ Terrain Susceptibility
→ Combined Risk
→ Historical Backtest
→ Exposure Analysis
→ Early Action
→ Streamlit Dashboard


## 2. Data Sources

### Weather

Historical hourly weather data:

- Rainfall
- Temperature
- Humidity
- Atmospheric pressure
- Wind

Primary candidate:

Open-Meteo historical weather API.


### Digital Elevation Model

Source:

SRTM DEM.

Used to derive:

- Elevation
- Slope
- Flow direction
- Flow accumulation


### Drainage and Water Bodies

Possible source:

OpenStreetMap.

Used for spatial context around:

- Rivers
- Canals
- Drains
- Lakes
- Water bodies


### Population

Possible source:

WorldPop.

Used to estimate population exposure
inside flagged risk zones.


### Historical Flood Extent

Possible sources:

- Sentinel-1 SAR
- NRSC/NDEM
- Government flood maps
- Other authoritative flood-extent datasets

Used for historical backtesting.


## 3. Weather Processing Pipeline

Raw Weather Data
→ Missing Value Handling
→ Timestamp Normalization
→ Quality Checks
→ Rainfall Accumulation
→ Lag Features
→ Trend Features
→ ML-Ready Dataset


## 4. Rainfall Prediction Model

### Input Features

- Recent rainfall
- 1-hour rainfall
- 3-hour rainfall
- 6-hour rainfall
- 12-hour rainfall
- 24-hour rainfall
- Temperature
- Humidity
- Pressure
- Wind
- Pressure change
- Humidity change
- Time-based features

### Model

XGBoost Classifier.

### Output

Probability of heavy rainfall
within the next 6 hours.

Example:

Heavy rainfall probability = 0.82

Rainfall risk = HIGH


## 5. Terrain Processing

SRTM DEM
→ Elevation
→ Slope
→ Flow Direction
→ Flow Accumulation
→ Terrain Susceptibility


### Interpretation

Terrain susceptibility represents the relative tendency
of surface runoff to concentrate in an area.

It is NOT a hydraulic simulation.

It does NOT directly provide:

- Flood depth
- Water level
- Flood arrival time


## 6. Combined Risk Engine

The combined risk engine integrates:

- Rainfall risk
- Terrain susceptibility
- Drainage and water-body context
- Land-cover and built-up context where feasible

Output:

Combined Risk Score
→ LOW
→ MODERATE
→ HIGH


### Explainability

The dashboard should show the major contributing factors.

Example:

HIGH RISK

Reasons:

- High rainfall probability
- High runoff concentration
- Close to drainage or water bodies
- Dense built-up area


## 7. Historical Backtesting

Historical Rainfall Conditions
→ Rainfall Prediction
→ Terrain Susceptibility
→ Combined Risk Map
→ Predicted High-Risk Zones

Compared against:

Observed Historical Flood Extent

Evaluation metrics:

- Intersection over Union (IoU)
- Spatial Precision
- Spatial Recall
- F1 Score


### Important

Historical backtesting evaluates performance on
a specific event.

It does not prove universal accuracy.


## 8. Exposure Analysis

Combined Risk Map
+
Population Data
→ Population Exposure

Output:

Approximate population within
flagged risk zones.


Combined Risk Map
+
Infrastructure Data
→ Infrastructure Exposure

Possible infrastructure:

- Roads
- Hospitals
- Schools
- Critical facilities
- Electrical infrastructure


## 9. Early Action Engine

Risk Level
→ Identify Relevant Role
→ Generate Recommended Action


### Municipality

- Inspect critical drainage areas
- Prepare pumps
- Monitor high-risk locations


### Rescue and Emergency Services

- Prepare response teams
- Prepare emergency equipment
- Monitor high-risk areas


### Electricity Department

- Inspect vulnerable electrical infrastructure
- Consider authorized precautionary isolation where required


### Hospitals

- Prepare emergency capacity
- Monitor accessibility


### Disaster Management

- Prepare shelters
- Prepare emergency resources


### Public

- Provide localized safety warnings
- Avoid unnecessary travel through high-risk areas
- Follow official emergency instructions


## 10. Dashboard Architecture

The system will use a Streamlit dashboard.

### Main Sections

#### Overview

- Current weather
- Heavy rainfall probability
- Overall risk

#### Maps

- Rainfall risk
- Terrain susceptibility
- Combined risk

#### Historical Validation

- Predicted risk map
- Observed flood extent
- Overlay comparison
- IoU
- Precision
- Recall
- F1 Score

#### Exposure

- Population exposure
- Roads
- Hospitals
- Schools
- Critical infrastructure

#### Early Action

Role-specific recommendations.

#### Evidence

Show:

- Data sources
- Model information
- Historical validation
- Confidence and evidence indicators


## 11. Project Architecture

```text
                    ┌─────────────────────┐
                    │    WEATHER DATA     │
                    │ Open-Meteo / etc.   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ DATA PROCESSING     │
                    │ Cleaning + Features  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ RAINFALL ML MODEL   │
                    │      XGBoost        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    RAINFALL RISK    │
                    └──────────┬──────────┘
                               │
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐             ┌──────────────────┐
    │     SRTM DEM     │             │ SPATIAL CONTEXT  │
    │                  │             │                  │
    │ Elevation        │             │ Drainage         │
    │ Slope            │             │ Water Bodies     │
    │ Flow Direction   │             │ Land Cover       │
    │ Flow Accumulation│             │ Built-up Area    │
    └────────┬─────────┘             └────────┬─────────┘
             │                                │
             ▼                                │
    ┌──────────────────┐                      │
    │ TERRAIN          │◄─────────────────────┘
    │ SUSCEPTIBILITY   │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────┐
    │ COMBINED RISK ENGINE │
    └──────────┬───────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌───────────────┐  ┌──────────────────┐
│ HISTORICAL    │  │ EXPOSURE         │
│ BACKTEST      │  │ POPULATION +     │
│ Sentinel-1    │  │ INFRASTRUCTURE   │
└───────┬───────┘  └────────┬─────────┘
        │                    │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ EARLY ACTION ENGINE│
        └─────────┬──────────┘
                  │
                  ▼
        ┌────────────────────┐
        │ STREAMLIT DASHBOARD│
        └────────────────────┘

##12. Technology Stack

Programming Language

Python

Machine Learning
XGBoost
Scikit-learn
Pandas
NumPy
Geospatial
GeoPandas
Rasterio
Shapely
PyProj
DEM hydrology tools
Visualization
Folium
Plotly
Streamlit
Version Control

Git + GitHub