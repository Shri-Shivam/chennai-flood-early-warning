import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

# Import utilities
from frontend.utils import (
    load_geojson,
    get_risk_color,
    enhanced_api_call
)

# Configuration
API_BASE_URL = "http://localhost:8000"
SPATIAL_FEATURES_PATH = "data/processed/chennai_spatial_features_final.geojson"
FLOOD_LABELS_DIR = "data/processed/flood_labels"

def main():
    st.set_page_config(
        page_title="Chennai Flood Early Warning System",
        page_icon="🌧️",
        layout="wide"
    )

    # --- SIDEBAR & GLOBAL STATUS ---
    st.sidebar.header("System Status")
    health = enhanced_api_call("/health")
    if health:
        st.sidebar.success("Backend API is running")
    else:
        st.sidebar.error("Backend API is not reachable")
        st.sidebar.info("Please start the backend with: `uvicorn src.api.app:app --reload`")

    # Model info
    st.sidebar.header("Model Information")
    model_info = enhanced_api_call("/model-info")
    if model_info:
        with st.sidebar.expander("View Model Details"):
            st.json(model_info)

    # Scientific Limitations (Guardrail)
    st.sidebar.divider()
    st.sidebar.header("⚠️ Scientific Limitations")
    st.sidebar.markdown(
        """
        **AI#1 (Rainfall):** Predicts probability of $\\ge 20\\text{mm}$ rainfall in the next 6 hours.

        **AI#2 (Inundation):** Predicts **Inundation Risk**, not exact flood depth or arrival time.

        **Validation:** System is a retrospective proof-of-concept validated on two historical episodes.

        **Exposure:** Population data is currently unavailable.
        """
    )

    st.title("🌧️ Chennai Flood Early Warning System")
    st.caption("AI/ML-based Integrated Heavy Rainfall Early Warning and Inundation Prediction System")

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Rainfall Prediction",
        "Inundation Prediction",
        "Risk Assessment Map",
        "End-to-End",
        "Historical Demo"
    ])

    # --- TAB 1: RAINFALL PREDICTION ---
    with tab1:
        st.header("AI#1: 6-Hour Heavy Rainfall Probability")
        st.info("Predicts P(6-hour rainfall $\\ge 20\\text{mm}$)")

        with st.form("rainfall_form"):
            st.subheader("Input Features (AI#1)")
            col1, col2 = st.columns(2)
            with col1:
                temperature_2m = st.number_input("Temperature 2m (°C)", value=28.0)
                relative_humidity_2m = st.number_input("Relative Humidity 2m (%)", value=75.0, min_value=0.0, max_value=100.0)
                surface_pressure = st.number_input("Surface Pressure (hPa)", value=1010.0)
                wind_speed_10m = st.number_input("Wind Speed 10m (m/s)", value=5.0, min_value=0.0)
                precipitation = st.number_input("Precipitation (mm/hr)", value=0.0, min_value=0.0)
                rain_lag_1h = st.number_input("Rain Lag 1h (mm)", value=0.0, min_value=0.0)
                rain_lag_3h = st.number_input("Rain Lag 3h (mm)", value=0.0, min_value=0.0)
                rain_lag_6h = st.number_input("Rain Lag 6h (mm)", value=0.0, min_value=0.0)
                rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0)
                rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0)
            with col2:
                rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0)
                rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0)
                rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0)
                pressure_change_3h = st.number_input("Pressure Change 3h (hPa)", value=0.0)
                pressure_change_6h = st.number_input("Pressure Change 6h (hPa)", value=0.0)
                humidity_change_3h = st.number_input("Humidity Change 3h (%)", value=0.0)
                humidity_change_6h = st.number_input("Humidity Change 6h (%)", value=0.0)
                hour = st.number_input("Hour of Day (0-23)", value=12, min_value=0, max_value=23, step=1)
                month = st.number_input("Month (1-12)", value=6, min_value=1, max_value=12, step=1)
                day_of_year = st.number_input("Day of Year (1-366)", value=180, min_value=1, max_value=366, step=1)

            submitted = st.form_submit_button("Predict Rainfall Probability")
            if submitted:
                features = {
                    "temperature_2m": temperature_2m, "relative_humidity_2m": relative_humidity_2m,
                    "surface_pressure": surface_pressure, "wind_speed_10m": wind_speed_10m,
                    "precipitation": precipitation, "rain_lag_1h": rain_lag_1h,
                    "rain_lag_3h": rain_lag_3h, "rain_lag_6h": rain_lag_6h,
                    "rain_1h": rain_1h, "rain_3h": rain_3h, "rain_6h": rain_6h,
                    "rain_12h": rain_12h, "rain_24h": rain_24h, "pressure_change_3h": pressure_change_3h,
                    "pressure_change_6h": pressure_change_6h, "humidity_change_3h": humidity_change_3h,
                    "humidity_change_6h": humidity_change_6h, "hour": hour, "month": month, "day_of_year": day_of_year
                }
                result = enhanced_api_call("/predict/rainfall", "POST", features)
                if result:
                    st.success("Prediction successful!")
                    prob = result.get("significant_rainfall_probability")
                    if prob is not None:
                        st.metric("Significant Rainfall Probability", f"{prob:.1%}")
                        st.caption(result.get("threshold_note", ""))

    # --- TAB 2: INUNDATION PREDICTION ---
    with tab2:
        st.header("AI#2: Inundation Risk Prediction")
        st.info("Predicts inundation risk over a 250m spatial grid")

        with st.form("inundation_form"):
            st.subheader("Spatial Features for a Single Cell")
            col1, col2 = st.columns(2)
            with col1:
                cell_id = st.text_input("Cell ID", value="cell_001")
                rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0)
                rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0)
                rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0)
                elevation = st.number_input("Elevation (m)", value=10.0)
            with col2:
                rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0)
                rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0)
                slope_degrees = st.number_input("Slope (degrees)", value=5.0, min_value=0.0)
                distance_to_drainage = st.number_input("Distance to Drainage (m)", value=100.0, min_value=0.0)

            submitted = st.form_submit_button("Predict Inundation Risk")
            if submitted:
                request_data = {
                    "cells": [
                        {
                            "cell_id": cell_id, "rain_1h": rain_1h, "rain_3h": rain_3h, "rain_6h": rain_6h,
                            "rain_12h": rain_12h, "rain_24h": rain_24h, "elevation": elevation,
                            "slope_degrees": slope_degrees, "distance_to_drainage": distance_to_drainage
                        }
                    ]
                }
                result = enhanced_api_call("/predict/inundation", "POST", request_data)
                if result:
                    st.success("Prediction successful!")
                    if "results" in result and len(result["results"]) > 0:
                        for res in result["results"]:
                            st.metric(
                                label=f"Inundation Risk Probability for {res['cell_id']}",
                                value=f"{res['inundation_risk_probability']:.1%}"
                            )
                    st.caption(result.get("limitation_note", ""))

    # --- TAB 3: RISK ASSESSMENT MAP ---
    with tab3:
        st.header("Interactive Spatial Risk Map")
        st.info("Select a cell on the map to assess its inundation risk based on current rainfall.")
        st.caption("Visualizing Predicted Inundation Risk. This is a probability score, not a depth map.")

        # Load Spatial Features
        spatial_data = load_geojson(SPATIAL_FEATURES_PATH)
        if not spatial_data:
            st.error("Could not load spatial features. Please check the data path.")
        else:
            # Rainfall input for the map assessment
            current_rain = st.number_input("Enter Current Rainfall (last 6h, mm)", value=0.0, min_value=0.0, key="map_rain")

            # Initialize Folium Map
            m = folium.Map(location=[13.0827, 80.2707], zoom_start=11, tiles="CartoDB positron")

            # Handle map interactions
            # In Streamlit, we can use st_folium to get the last clicked location
            # However, since we are dealing with a GRID, we'll simplify:
            # We'll render the grid. If a user selects a cell ID from a dropdown, we highlight it and predict.

            st.write("### Cell Selection")
            cell_ids = [f["properties"]["cell_id"] for f in spatial_data["features"]]
            selected_cell_id = st.selectbox("Select Cell ID to Analyze", options=cell_ids)

            if selected_cell_id is not None:
                # Find cell properties
                cell_feat = next((f for f in spatial_data["features"] if f["properties"]["cell_id"] == selected_cell_id), None)
                if cell_feat:
                    props = cell_feat["properties"]

                    # Call /risk-map for this specific cell
                    # Note: /risk-map expects a list of cells. We'll send the one selected.
                    request_data = {
                        "cells": [
                            {
                                "cell_id": str(selected_cell_id),
                                "rain_1h": current_rain * 0.2, # simplified lag for demo
                                "rain_3h": current_rain * 0.5,
                                "rain_6h": current_rain,
                                "rain_12h": current_rain * 1.2,
                                "rain_24h": current_rain * 1.5,
                                "elevation": props["elevation"],
                                "slope_degrees": props["slope_degrees"],
                                "distance_to_drainage": props["distance_to_drainage"]
                            }
                        ]
                    }
                    risk_result = enhanced_api_call("/risk-map", "POST", request_data)

                    if risk_result:
                        res_cell = risk_result["cells"][0]
                        risk_class = res_cell["risk_class"]
                        prob = res_cell["inundation_risk_probability"]

                        st.metric("Risk Class", risk_class)
                        st.metric("Risk Probability", f"{prob:.1%}")

                        # Visual highlight on map
                        color = get_risk_color(risk_class)
                        folium.GeoJson(
                            cell_feat["geometry"],
                            style_function=lambda x: {"fillColor": color, "color": color, "fillOpacity": 0.7},
                            tooltip=f"Cell {selected_cell_id}: {risk_class}"
                        ).add_to(m)

            # Add the rest of the study area for context
            folium.GeoJson(
                spatial_data,
                style_function=lambda x: {"fillColor": "gray", "color": "gray", "weight": 1, "fillOpacity": 0.1},
                tooltip="Study Area Cell"
            ).add_to(m)

            st_folium(m, width=1000, height=600)

    # --- TAB 4: END-TO-END ---
    with tab4:
        st.header("End-to-End Prediction")
        st.info("Combines rainfall prediction, inundation prediction, risk assessment, and exposure assessment")

        with st.form("endtoend_form"):
            st.write("#### Rainfall Features (Optional)")
            use_rainfall_e2e = st.checkbox("Include AI#1 rainfall prediction", value=True, key="e2e_use_rain")
            rainfall_features_e2e = None
            if use_rainfall_e2e:
                with st.expander("Rainfall Features", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        e2e_temp = st.number_input("Temperature 2m (°C)", value=28.0, key="e2e_temp")
                        e2e_hum = st.number_input("Relative Humidity 2m (%)", value=75.0, min_value=0.0, max_value=100.0, key="e2e_hum")
                        e2e_pres = st.number_input("Surface Pressure (hPa)", value=1010.0, key="e2e_pres")
                        e2e_wind = st.number_input("Wind Speed 10m (m/s)", value=5.0, min_value=0.0, key="e2e_wind")
                        e2e_precip = st.number_input("Precipitation (mm/hr)", value=0.0, min_value=0.0, key="e2e_precip")
                        e2e_lag1 = st.number_input("Rain Lag 1h (mm)", value=0.0, min_value=0.0, key="e2e_lag1")
                        e2e_lag3 = st.number_input("Rain Lag 3h (mm)", value=0.0, min_value=0.0, key="e2e_lag3")
                        e2e_lag6 = st.number_input("Rain Lag 6h (mm)", value=0.0, min_value=0.0, key="e2e_lag6")
                        e2e_r1 = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, key="e2e_r1")
                        e2e_r3 = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, key="e2e_r3")
                        e2e_r6 = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, key="e2e_r6")
                    with col2:
                        e2e_r12 = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, key="e2e_r12")
                        e2e_r24 = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, key="e2e_r24")
                        e2e_pc3 = st.number_input("Pressure Change 3h (hPa)", value=0.0, key="e2e_pc3")
                        e2e_pc6 = st.number_input("Pressure Change 6h (hPa)", value=0.0, key="e2e_pc6")
                        e2e_hc3 = st.number_input("Humidity Change 3h (%)", value=0.0, key="e2e_hc3")
                        e2e_hc6 = st.number_input("Humidity Change 6h (%)", value=0.0, key="e2e_hc6")
                        e2e_hour = st.number_input("Hour of Day (0-23)", value=12, min_value=0, max_value=23, step=1, key="e2e_hour")
                        e2e_month = st.number_input("Month (1-12)", value=6, min_value=1, max_value=12, step=1, key="e2e_month")
                        e2e_doy = st.number_input("Day of Year (1-366)", value=180, min_value=1, max_value=366, step=1, key="e2e_doy")
                        rainfall_features_e2e = {
                            "temperature_2m": e2e_temp, "relative_humidity_2m": e2e_hum, "surface_pressure": e2e_pres,
                            "wind_speed_10m": e2e_wind, "precipitation": e2e_precip, "rain_lag_1h": e2e_lag1,
                            "rain_lag_3h": e2e_lag3, "rain_lag_6h": e2e_lag6, "rain_1h": e2e_r1, "rain_3h": e2e_r3,
                            "rain_6h": e2e_r6, "rain_12h": e2e_r12, "rain_24h": e2e_r24, "pressure_change_3h": e2e_pc3,
                            "pressure_change_6h": e2e_pc6, "humidity_change_3h": e2e_hc3, "humidity_change_6h": e2e_hc6,
                            "hour": e2e_hour, "month": e2e_month, "day_of_year": e2e_doy
                        }

            st.write("#### Inundation Cell Features")
            col1, col2 = st.columns(2)
            with col1:
                e2e_cell_id = st.text_input("Cell ID", value="cell_001", key="e2e_cell_id")
                e2e_rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, key="e2e_r1")
                e2e_rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, key="e2e_r3")
                e2e_rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, key="e2e_r6")
                e2e_elevation = st.number_input("Elevation (m)", value=10.0, key="e2e_elev")
            with col2:
                e2e_rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, key="e2e_r12")
                e2e_rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, key="e2e_r24")
                e2e_slope_degrees = st.number_input("Slope (degrees)", value=5.0, min_value=0.0, key="e2e_slope")
                e2e_distance_to_drainage = st.number_input("Distance to Drainage (m)", value=0.0, min_value=0.0, key="e2e_dist")

            submitted_e2e = st.form_submit_button("Run End-to-End Prediction")
            if submitted_e2e:
                request_data = {
                    "cells": [
                        {
                            "cell_id": e2e_cell_id, "rain_1h": e2e_rain_1h, "rain_3h": e2e_rain_3h, "rain_6h": e2e_rain_6h,
                            "rain_12h": e2e_rain_12h, "rain_24h": e2e_rain_24h, "elevation": e2e_elevation,
                            "slope_degrees": e2e_slope_degrees, "distance_to_drainage": e2e_distance_to_drainage
                        }
                    ]
                }
                if rainfall_features_e2e is not None:
                    request_data["rainfall_features"] = rainfall_features_e2e

                result = enhanced_api_call("/predict/end-to-end", "POST", request_data)
                if result:
                    st.success("End-to-end prediction successful!")

                    # Rainfall results
                    if "rainfall_significant_probability" in result and result["rainfall_significant_probability"] is not None:
                        st.metric("Significant Rainfall Probability", f"{result['rainfall_significant_probability']:.1%}")

                    # Inundation / Risk results
                    if "cells" in result and len(result["cells"]) > 0:
                        for cell in result["cells"]:
                            st.metric(
                                label=f"Risk Class for {cell['cell_id']}",
                                value=cell["risk_class"]
                            )
                            st.caption(f"Inundation risk probability: {cell['inundation_risk_probability']:.1%}")

                    # Exposure - Honest handling (Guardrail)
                    if "exposure" in result and len(result["exposure"]) > 0:
                        for exp in result["exposure"]:
                            if exp["data_available"]:
                                st.metric("Estimated Population Exposed", exp["estimated_population_population_exposed"] or "N/A")
                            else:
                                st.warning(f"Exposure data unavailable: {exp['reason_if_unavailable']}")

                    # Alerts
                    if "alerts" in result and len(result["alerts"]) > 0:
                        st.write("**Role-specific Alerts:**")
                        for alert in result["alerts"]:
                            st.write(f"- {alert['cell_id']} (Risk Class: {alert['risk_class']}): {alert['recommended_actions']}")

    # --- TAB 5: HISTORICAL DEMO ---
    with tab5:
        st.header("Retrospective Demonstration")
        st.info("Visualize verified observed flood extent from the 2021 Chennai event.")
        st.warning("HISTORICAL DEMONSTRATION: OBSERVED DATA. This is not a prediction.")

        # List flood label files
        if not os.path.exists(FLOOD_LABELS_DIR):
            st.error(f"Flood labels directory not found: {FLOOD_LABELS_DIR}")
        else:
            label_files = [f for f in os.listdir(FLOOD_LABELS_DIR) if f.endswith(".geojson")]
            if not label_files:
                st.error("No observed flood label GeoJSON files found.")
            else:
                selected_label_file = st.selectbox(
                    "Select Event Timestamp",
                    options=label_files,
                    format_func=lambda x: x.replace("flood_labels_", "").replace(".geojson", "")
                )

                if selected_label_file:
                    label_path = os.path.join(FLOOD_LABELS_DIR, selected_label_file)
                    observed_data = load_geojson(label_path)

                    if observed_data:
                        # Render in blue
                        m_hist = folium.Map(location=[13.0827, 80.2707], zoom_start=11, tiles="CartoDB positron")
                        folium.GeoJson(
                            observed_data,
                            style_function=lambda x: {"fillColor": "blue", "color": "blue", "fillOpacity": 0.6, "weight": 1},
                            tooltip="Observed Flood Extent"
                        ).add_to(m_hist)

                        st.write("### Observed Inundation Extent")
                        st_folium(m_hist, width=1000, height=600)
                    else:
                        st.error("Failed to load selected observed data.")

if __name__ == "__main__":
    main()
