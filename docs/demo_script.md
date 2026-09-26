# SIH26071 Chennai Flood Early Warning System - Demo Script

**Total Duration**: 6-7 Minutes
**Goal**: Demonstrate the integrated pipeline from rainfall forecasting to spatial risk assessment and role-specific alerts, while maintaining scientific honesty.

---

## 0:00–0:45 | The Problem & Objective
- **Action**: Show the Dashboard landing page.
- **Narrative**: 
    - "Chennai faces recurring urban flooding. Our goal is not just to predict rain, but to assess the *risk* of inundation across the city's unique terrain."
    - "We've built an integrated system that chains a 6-hour rainfall forecast with a spatial inundation risk model."

## 0:45–1:30 | System Architecture
- **Action**: Briefly show the `ARCHITECTURE.md` or a diagram if available.
- **Narrative**: 
    - "The pipeline is: **Rain $\rightarrow$ Terrain $\rightarrow$ Risk $\rightarrow$ Impact $\rightarrow$ Act**."
    - "We use AI#1 for rainfall probability and AI#2 for spatial inundation risk, served via a FastAPI backend to a Streamlit frontend."

## 1:30–2:30 | AI#1: Rainfall Forecasting
- **Action**: Navigate to **Rainfall Prediction** tab. Enter realistic weather features.
- **Narrative**: 
    - "AI#1 predicts the probability that rainfall will exceed 20mm in the next 6 hours."
    - "Note that this is a project-defined threshold for significance, not an official IMD category."
    - "This provides the initial trigger for the warning system."

## 2:30–3:30 | AI#2: Terrain & Inundation Risk
- **Action**: Navigate to **Inundation Prediction** or **Risk Assessment Map**.
- **Narrative**: 
    - "Rain alone doesn't cause flooding; terrain does. AI#2 considers elevation, slope, and distance to drainage."
    - "By selecting a cell on the map, we can see how the same rainfall event creates different risk levels depending on the local geography."

## 3:30–4:30 | Risk Classification & Alerts
- **Action**: Run the **End-to-End** prediction. Show the result for a "HIGH" risk cell.
- **Narrative**: 
    - "The system derives a Risk Class (Low/Moderate/High) and generates role-specific advisory alerts."
    - "For example, the Municipal Authority is advised to inspect drainage hotspots, while citizens are told to avoid low-lying areas."
    - "These are recommendations for human decision-makers, not autonomous orders."

## 4:30–5:30 | Historical Retrospective (The 'Proof')
- **Action**: Navigate to **Historical Demo** tab. Select a 2021 event.
- **Narrative**: 
    - "To verify the system, we perform a retrospective replay of the November 2021 floods."
    - "Here we visualize the **OBSERVED** inundation extent. This allows us to compare our model's risk signals against what actually happened on the ground."
    - "This is a retrospective validation, distinguishing it from a live prospective prediction."

## 5:30–6:30 | Dashboard & API Integration
- **Action**: Show the **Model Information** and **System Status** in the sidebar.
- **Narrative**: 
    - "The entire frontend is decoupled from the backend via a REST API, ensuring that the ML models can be updated independently of the UI."
    - "The system remains honest about its data—for instance, exposure data is explicitly marked as unavailable rather than fabricated."

## 6:30–7:00 | Limitations & Future Work
- **Action**: Open the **Scientific Limitations** expander.
- **Narrative**: 
    - "This is a proof-of-concept validated on two historical episodes. It is not an operational government system."
    - "Future work includes integrating real-time population exposure data and expanding the validation set."

---

## Demo Fallback Procedure (If API/Network Fails)
1. **Static Capture**: Have screenshots of the Dashboard and API responses ready.
2. **Local Cache**: The dashboard can be shown with "demo mode" inputs that trigger pre-saved API responses.
3. **Documentation**: Refer to the `AUDIT_REPORT.md` and `stage8_report.txt` to show the quantitative validation results.
