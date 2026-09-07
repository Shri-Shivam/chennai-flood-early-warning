# Project Roadmap

## Phase 0 — Project Setup

- [x] Create GitHub repository
- [x] Create project structure
- [x] Create project documentation
- [x] Define MVP scope

---

## Phase 1 — Data Acquisition

### Weather

- [ ] Select historical weather source
- [ ] Download hourly weather data
- [ ] Inspect missing values
- [ ] Clean weather data
- [ ] Save processed dataset

### Spatial

- [ ] Obtain SRTM DEM
- [ ] Obtain drainage/water-body data
- [ ] Obtain land-cover data if feasible
- [ ] Obtain population data
- [ ] Obtain historical flood extent

### Historical Event

- [ ] Verify November 2021 Chennai flood event
- [ ] Verify rainfall data availability
- [ ] Verify observed flood extent availability

---

## Phase 2 — Rainfall ML

- [ ] Define heavy rainfall threshold
- [ ] Create rainfall labels
- [ ] Create lag features
- [ ] Create rolling rainfall features
- [ ] Create pressure/humidity trend features
- [ ] Create time-based train/validation/test split
- [ ] Train baseline model
- [ ] Train XGBoost model
- [ ] Evaluate Precision
- [ ] Evaluate Recall
- [ ] Evaluate F1
- [ ] Evaluate PR-AUC
- [ ] Save trained model

### Primary Prediction

Predict probability of heavy rainfall
within the next 6 hours.

---

## Phase 3 — Terrain Analysis

- [ ] Process SRTM DEM
- [ ] Calculate elevation
- [ ] Calculate slope
- [ ] Calculate flow direction
- [ ] Calculate flow accumulation
- [ ] Generate terrain susceptibility layer

### Important

Flow accumulation represents areas where
surface runoff naturally concentrates.

It does NOT directly represent:

- Flood depth
- Water level
- Flood arrival time

---

## Phase 4 — Combined Risk

- [ ] Normalize rainfall risk
- [ ] Normalize terrain susceptibility
- [ ] Add drainage/water-body context
- [ ] Add land-cover/built-up context if feasible
- [ ] Create explainable risk score
- [ ] Generate LOW risk
- [ ] Generate MODERATE risk
- [ ] Generate HIGH risk
- [ ] Generate risk map

---

## Phase 5 — Historical Backtest

- [ ] Load historical rainfall conditions
- [ ] Run rainfall model
- [ ] Generate terrain susceptibility
- [ ] Generate predicted risk map
- [ ] Load observed flood extent
- [ ] Align coordinate systems
- [ ] Compare predicted vs observed extent
- [ ] Calculate IoU
- [ ] Calculate spatial precision
- [ ] Calculate spatial recall
- [ ] Calculate F1
- [ ] Create predicted vs actual visualization

### Important

A single historical event is a backtest.

It must NOT be presented as proof of
universal system accuracy.

---

## Phase 6 — Exposure Analysis

- [ ] Add population-density data
- [ ] Overlay population with risk zones
- [ ] Estimate population within flagged risk zones
- [ ] Add roads
- [ ] Add hospitals
- [ ] Add schools
- [ ] Add critical infrastructure
- [ ] Add electrical infrastructure where feasible

### Important

Report:

"Approximate population within flagged risk zone."

Do NOT report:

"People who will definitely be flooded."

---

## Phase 7 — Early Action

### Municipality

- [ ] Drain inspection recommendation
- [ ] Pump preparation recommendation
- [ ] High-risk area monitoring

### Rescue

- [ ] Prepare response teams
- [ ] Prepare emergency equipment
- [ ] Monitor high-risk areas

### Electricity

- [ ] Identify vulnerable infrastructure
- [ ] Recommend inspection
- [ ] Recommend authorized precautionary isolation where required

### Hospitals

- [ ] Emergency capacity preparation
- [ ] Accessibility monitoring

### Disaster Management

- [ ] Shelter preparation
- [ ] Emergency resource preparation

### Public

- [ ] Localized warning
- [ ] Safety recommendations
- [ ] Follow official emergency instructions

---

## Phase 8 — Dashboard

Build a Streamlit dashboard containing:

- [ ] Current rainfall information
- [ ] 6-hour heavy rainfall probability
- [ ] Rainfall risk
- [ ] Terrain susceptibility map
- [ ] Combined risk map
- [ ] Risk factors
- [ ] Historical backtest
- [ ] Predicted vs observed flood extent
- [ ] Population exposure
- [ ] Infrastructure exposure
- [ ] Role-specific early actions
- [ ] Confidence/evidence information

---

## Phase 9 — Testing & Demo

- [ ] Test complete pipeline
- [ ] Test missing-data handling
- [ ] Test model inference
- [ ] Test map generation
- [ ] Test dashboard
- [ ] Prepare historical event demo
- [ ] Prepare architecture diagram
- [ ] Prepare results
- [ ] Prepare limitations
- [ ] Prepare SIH presentation