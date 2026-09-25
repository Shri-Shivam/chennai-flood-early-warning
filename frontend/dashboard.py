import streamlit as st
import requests
from typing import Dict, Any, List, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"

def api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an API request to the backend."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return {}

def main():
    st.set_page_config(
        page_title="Chennai Flood Early Warning System",
        page_icon="🌧️",
        layout="wide"
    )

    st.title("🌧️ Chennai Flood Early Warning System")
    st.caption("AI/ML-based Integrated Heavy Rainfall Early Warning and Inundation Prediction System")

    # Sidebar
    st.sidebar.header("System Status")
    health = api_request("/health")
    if health:
        st.sidebar.success("Backend API is running")
        st.sidebar.json(health)
    else:
        st.sidebar.error("Backend API is not reachable")
        st.sidebar.info("Please start the backend with: `uvicorn src.api.app:app --reload`")

    # Model info
    st.sidebar.header("Model Information")
    model_info = api_request("/model-info")
    if model_info:
        st.sidebar.json(model_info)

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["Rainfall Prediction", "Inundation Prediction", "Risk Assessment", "End-to-End"])

    with tab1:
        st.header("AI#1: 6-Hour Heavy Rainfall Probability")
        st.info("Predicts P(6-hour rainfall ≥ 20mm)")

        with st.form("rainfall_form"):
            st.subheader("Input Features (AI#1)")
            # We'll create input fields for each feature in RainfallFeatures
            # Using reasonable defaults (mid-range values)
            col1, col2 = st.columns(2)
            with col1:
                temperature_2m = st.number_input("Temperature 2m (°C)", value=28.0, help="Air temperature at 2 meters above ground")
                relative_humidity_2m = st.number_input("Relative Humidity 2m (%)", value=75.0, min_value=0.0, max_value=100.0, help="Relative humidity at 2 meters above ground")
                surface_pressure = st.number_input("Surface Pressure (hPa)", value=1010.0, help="Surface atmospheric pressure")
                wind_speed_10m = st.number_input("Wind Speed 10m (m/s)", value=5.0, min_value=0.0, help="Wind speed at 10 meters above ground")
                precipitation = st.number_input("Precipitation (mm/hr)", value=0.0, min_value=0.0, help="Liquid water equivalent precipitation rate")
                rain_lag_1h = st.number_input("Rain Lag 1h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the last 1 hour")
                rain_lag_3h = st.number_input("Rain Lag 3h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the last 3 hours")
                rain_lag_6h = st.number_input("Rain Lag 6h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the last 6 hours")
                rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 1 hour")
                rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 3 hours")
            with col2:
                rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 6 hours")
                rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 12 hours")
                rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 24 hours")
                pressure_change_3h = st.number_input("Pressure Change 3h (hPa)", value=0.0, help="Change in surface pressure over last 3 hours")
                pressure_change_6h = st.number_input("Pressure Change 6h (hPa)", value=0.0, help="Change in surface pressure over last 6 hours")
                humidity_change_3h = st.number_input("Humidity Change 3h (%)", value=0.0, help="Change in relative humidity over last 3 hours")
                humidity_change_6h = st.number_input("Humidity Change 6h (%)", value=0.0, help="Change in relative humidity over last 6 hours")
                hour = st.number_input("Hour of Day (0-23)", value=12, min_value=0, max_value=23, step=1, help="Hour of day in local time")
                month = st.number_input("Month (1-12)", value=6, min_value=1, max_value=12, step=1, help="Month of year")
                day_of_year = st.number_input("Day of Year (1-366)", value=180, min_value=1, max_value=366, step=1, help="Day of year")

            submitted = st.form_submit_button("Predict Rainfall Probability")
            if submitted:
                # Build the feature dictionary
                features = {
                    "temperature_2m": temperature_2m,
                    "relative_humidity_2m": relative_humidity_2m,
                    "surface_pressure": surface_pressure,
                    "wind_speed_10m": wind_speed_10m,
                    "precipitation": precipitation,
                    "rain_lag_1h": rain_lag_1h,
                    "rain_lag_3h": rain_lag_3h,
                    "rain_lag_6h": rain_lag_6h,
                    "rain_1h": rain_1h,
                    "rain_3h": rain_3h,
                    "rain_6h": rain_6h,
                    "rain_12h": rain_12h,
                    "rain_24h": rain_24h,
                    "pressure_change_3h": pressure_change_3h,
                    "pressure_change_6h": pressure_change_6h,
                    "humidity_change_3h": humidity_change_3h,
                    "humidity_change_6h": humidity_change_6h,
                    "hour": hour,
                    "month": month,
                    "day_of_year": day_of_year
                }
                result = api_request("/predict/rainfall", "POST", features)
                if result:
                    st.success("Prediction successful!")
                    st.subheader("Result")
                    st.json(result)
                    # Also display the probability in a more readable way
                    prob = result.get("significant_rainfall_probability")
                    if prob is not None:
                        st.metric("Significant Rainfall Probability", f"{prob:.1%}")
                        st.caption(result.get("threshold_note", ""))

    with tab2:
        st.header("AI#2: Inundation Risk Prediction")
        st.info("Predicts inundation risk over a 250m spatial grid")

        with st.form("inundation_form"):
            st.subheader("Spatial Features for a Single Cell")
            col1, col2 = st.columns(2)
            with col1:
                cell_id = st.text_input("Cell ID", value="cell_001", help="Identifier for the spatial grid cell")
                rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 1 hour")
                rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 3 hours")
                rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 6 hours")
                elevation = st.number_input("Elevation (m)", value=10.0, help="Height above sea level")
            with col2:
                rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 12 hours")
                rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, help="Rainfall volume in the previous 24 hours")
                slope_degrees = st.number_input("Slope (degrees)", value=5.0, min_value=0.0, help="Slope of the terrain")
                distance_to_drainage = st.number_input("Distance to Drainage (m)", value=100.0, min_value=0.0, help="Distance to nearest drainage channel")

            submitted = st.form_submit_button("Predict Inundation Risk")
            if submitted:
                # Build the request for a single cell
                request_data = {
                    "cells": [
                        {
                            "cell_id": cell_id,
                            "rain_1h": rain_1h,
                            "rain_3h": rain_3h,
                            "rain_6h": rain_6h,
                            "rain_12h": rain_12h,
                            "rain_24h": rain_24h,
                            "elevation": elevation,
                            "slope_degrees": slope_degrees,
                            "distance_to_drainage": distance_to_drainage
                        }
                    ]
                }
                result = api_request("/predict/inundation", "POST", request_data)
                if result:
                    st.success("Prediction successful!")
                    st.subheader("Result")
                    st.json(result)
                    # Display results in a table
                    if "results" in result and len(result["results"]) > 0:
                        for res in result["results"]:
                            st.metric(
                                label=f"Inundation Risk Probability for {res['cell_id']}",
                                value=f"{res['inundation_risk_probability']:.1%}"
                            )
                    st.caption(result.get("limitation_note", ""))

    with tab3:
        st.header("Risk Assessment & Alerts")
        st.info("Combines AI#1 and AI#2 predictions, derives risk class, and generates role-specific alerts")

        st.subheader("Risk Engine (AI#1 + AI#2)")
        st.write("Chains AI#1 and AI#2 outputs to produce risk_class (LOW/MODERATE/HIGH) based on AI#2 probability.")
        st.write("AI#1 (rainfall) and AI#2 (inundation) are reported separately, never blended into one number.")

        with st.form("risk_form"):
            st.write("#### Rainfall Features (Optional)")
            st.caption("If omitted, only AI#2 is used for risk assessment.")
            use_rainfall = st.checkbox("Include AI#1 rainfall prediction", value=True)
            rainfall_features = None
            if use_rainfall:
                # We'll reuse the same inputs as the rainfall tab but in a collapsed section
                with st.expander("Rainfall Features", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        r_temperature_2m = st.number_input("Temperature 2m (°C)", value=28.0, key="r_temp")
                        r_relative_humidity_2m = st.number_input("Relative Humidity 2m (%)", value=75.0, min_value=0.0, max_value=100.0, key="r_hum")
                        r_surface_pressure = st.number_input("Surface Pressure (hPa)", value=1010.0, key="r_pressure")
                        r_wind_speed_10m = st.number_input("Wind Speed 10m (m/s)", value=5.0, min_value=0.0, key="r_wind")
                        r_precipitation = st.number_input("Precipitation (mm/hr)", value=0.0, min_value=0.0, key="r_precip")
                        r_rain_lag_1h = st.number_input("Rain Lag 1h (mm)", value=0.0, min_value=0.0, key="r_lag1")
                        r_rain_lag_3h = st.number_input("Rain Lag 3h (mm)", value=0.0, min_value=0.0, key="r_lag3")
                        r_rain_lag_6h = st.number_input("Rain Lag 6h (mm)", value=0.0, min_value=0.0, key="r_lag6")
                        r_rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, key="r_r1")
                        r_rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, key="r_r3")
                        r_rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, key="r_r6")
                    with col2:
                        r_rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, key="r_r12")
                        r_rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, key="r_r24")
                        r_pressure_change_3h = st.number_input("Pressure Change 3h (hPa)", value=0.0, key="r_pc3")
                        r_pressure_change_6h = st.number_input("Pressure Change 6h (hPa)", value=0.0, key="r_pc6")
                        r_humidity_change_3h = st.number_input("Humidity Change 3h (%)", value=0.0, key="r_hc3")
                        r_humidity_change_6h = st.number_input("Humidity Change 6h (%)", value=0.0, key="r_hc6")
                        r_hour = st.number_input("Hour of Day (0-23)", value=12, min_value=0, max_value=23, step=1, key="r_hour")
                        r_month = st.number_input("Month (1-12)", value=6, min_value=1, max_value=12, step=1, key="r_month")
                        r_day_of_year = st.number_input("Day of Year (1-366)", value=180, min_value=1, max_value=366, step=1, key="r_doy")
                        rainfall_features = {
                            "temperature_2m": r_temperature_2m,
                            "relative_humidity_2m": r_relative_humidity_2m,
                            "surface_pressure": r_surface_pressure,
                            "wind_speed_10m": r_wind_speed_10m,
                            "precipitation": r_precipitation,
                            "rain_lag_1h": r_rain_lag_1h,
                            "rain_lag_3h": r_rain_lag_3h,
                            "rain_lag_6h": r_rain_lag_6h,
                            "rain_1h": r_rain_1h,
                            "rain_3h": r_rain_3h,
                            "rain_6h": r_rain_6h,
                            "rain_12h": r_rain_12h,
                            "rain_24h": r_rain_24h,
                            "pressure_change_3h": r_pressure_change_3h,
                            "pressure_change_6h": r_pressure_change_6h,
                            "humidity_change_3h": r_humidity_change_3h,
                            "humidity_change_6h": r_humidity_change_6h,
                            "hour": r_hour,
                            "month": r_month,
                            "day_of_year": r_day_of_year
                        }

            st.write("#### Inundation Cell Features")
            col1, col2 = st.columns(2)
            with col1:
                ri_cell_id = st.text_input("Cell ID", value="cell_001", key="ri_cell_id")
                ri_rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, key="ri_r1")
                ri_rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, key="ri_r3")
                ri_rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, key="ri_r6")
                ri_elevation = st.number_input("Elevation (m)", value=10.0, key="ri_elev")
            with col2:
                ri_rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, key="ri_r12")
                ri_rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, key="ri_r24")
                ri_slope_degrees = st.number_input("Slope (degrees)", value=5.0, min_value=0.0, key="ri_slope")
                ri_distance_to_drainage = st.number_input("Distance to Drainage (m)", value=100.0, min_value=0.0, key="ri_dist")

            submitted = st.form_submit_button("Assess Risk")
            if submitted:
                # Build request data
                request_data = {
                    "cells": [
                        {
                            "cell_id": ri_cell_id,
                            "rain_1h": ri_rain_1h,
                            "rain_3h": ri_rain_3h,
                            "rain_6h": ri_rain_6h,
                            "rain_12h": ri_rain_12h,
                            "rain_24h": ri_rain_24h,
                            "elevation": ri_elevation,
                            "slope_degrees": ri_slope_degrees,
                            "distance_to_drainage": ri_distance_to_drainage
                        }
                    ]
                }
                if rainfall_features is not None:
                    request_data["rainfall_features"] = rainfall_features

                result = api_request("/predict/risk", "POST", request_data)
                if result:
                    st.success("Risk assessment successful!")
                    st.subheader("Result")
                    st.json(result)
                    if "cells" in result and len(result["cells"]) > 0:
                        for cell in result["cells"]:
                            st.metric(
                                label=f"Risk Class for {cell['cell_id']}",
                                value=cell["risk_class"]
                            )
                            st.caption(f"Inundation risk probability: {cell['inundation_risk_probability']:.1%}")
                    st.caption(result.get("limitation_note", ""))

        st.divider()
        st.subheader("Alert Engine")
        st.write("Generates role-specific recommended actions based on risk class.")
        with st.form("alert_form"):
            st.write("#### Input from Risk Assessment")
            st.caption("You can use the output from the Risk Assessment above, or enter manually.")
            alert_cell_id = st.text_input("Cell ID", value="cell_001", key="alert_cell_id")
            alert_risk_class = st.selectbox(
                "Risk Class",
                options=["LOW", "MODERATE", "HIGH"],
                index=1,
                key="alert_risk_class"
            )
            submitted_alert = st.form_submit_button("Generate Alert")
            if submitted_alert:
                # We need to call /alerts endpoint with a CellRiskResult
                request_data = {
                    "cells": [
                        {
                            "cell_id": alert_cell_id,
                            "inundation_risk_probability": 0.5,  # placeholder, not used by alert engine? Actually alert engine uses risk_class only
                            "risk_class": alert_risk_class
                        }
                    ]
                }
                result = api_request("/alerts", "POST", request_data)
                if result:
                    st.success("Alert generated!")
                    st.subheader("Result")
                    st.json(result)
                    if "alerts" in result and len(result["alerts"]) > 0:
                        for alert in result["alerts"]:
                            st.write(f"**Recommended actions for {alert['cell_id']} (Risk Class: {alert['risk_class']}):**")
                            actions = alert.get("recommended_actions", {})
                            for role, action in actions.items():
                                st.write(f"- **{role}**: {action}")
                    st.caption(result.get("limitation_note", ""))

    with tab4:
        st.header("End-to-End Prediction")
        st.info("Combines rainfall prediction, inundation prediction, risk assessment, and exposure assessment")
        st.write("Note: Exposure data is not available in this repository, so the system returns honest 'not available' results.")

        with st.form("endtoend_form"):
            st.write("#### Rainfall Features (Optional)")
            use_rainfall_e2e = st.checkbox("Include AI#1 rainfall prediction", value=True, key="e2e_use_rain")
            rainfall_features_e2e = None
            if use_rainfall_e2e:
                with st.expander("Rainfall Features", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        e2e_temperature_2m = st.number_input("Temperature 2m (°C)", value=28.0, key="e2e_temp")
                        e2e_relative_humidity_2m = st.number_input("Relative Humidity 2m (%)", value=75.0, min_value=0.0, max_value=100.0, key="e2e_hum")
                        e2e_surface_pressure = st.number_input("Surface Pressure (hPa)", value=1010.0, key="e2e_pressure")
                        e2e_wind_speed_10m = st.number_input("Wind Speed 10m (m/s)", value=5.0, min_value=0.0, key="e2e_wind")
                        e2e_precipitation = st.number_input("Precipitation (mm/hr)", value=0.0, min_value=0.0, key="e2e_precip")
                        e2e_rain_lag_1h = st.number_input("Rain Lag 1h (mm)", value=0.0, min_value=0.0, key="e2e_lag1")
                        e2e_rain_lag_3h = st.number_input("Rain Lag 3h (mm)", value=0.0, min_value=0.0, key="e2e_lag3")
                        e2e_rain_lag_6h = st.number_input("Rain Lag 6h (mm)", value=0.0, min_value=0.0, key="e2e_lag6")
                        e2e_rain_1h = st.number_input("Rain 1h (mm)", value=0.0, min_value=0.0, key="e2e_r1")
                        e2e_rain_3h = st.number_input("Rain 3h (mm)", value=0.0, min_value=0.0, key="e2e_r3")
                        e2e_rain_6h = st.number_input("Rain 6h (mm)", value=0.0, min_value=0.0, key="e2e_r6")
                    with col2:
                        e2e_rain_12h = st.number_input("Rain 12h (mm)", value=0.0, min_value=0.0, key="e2e_r12")
                        e2e_rain_24h = st.number_input("Rain 24h (mm)", value=0.0, min_value=0.0, key="e2e_r24")
                        e2e_pressure_change_3h = st.number_input("Pressure Change 3h (hPa)", value=0.0, key="e2e_pc3")
                        e2e_pressure_change_6h = st.number_input("Pressure Change 6h (hPa)", value=0.0, key="e2e_pc6")
                        e2e_humidity_change_3h = st.number_input("Humidity Change 3h (%)", value=0.0, key="e2e_hc3")
                        e2e_humidity_change_6h = st.number_input("Humidity Change 6h (%)", value=0.0, key="e2e_hc6")
                        e2e_hour = st.number_input("Hour of Day (0-23)", value=12, min_value=0, max_value=23, step=1, key="e2e_hour")
                        e2e_month = st.number_input("Month (1-12)", value=6, min_value=1, max_value=12, step=1, key="e2e_month")
                        e2e_day_of_year = st.number_input("Day of Year (1-366)", value=180, min_value=1, max_value=366, step=1, key="e2e_doy")
                        rainfall_features_e2e = {
                            "temperature_2m": e2e_temperature_2m,
                            "relative_humidity_2m": e2e_relative_humidity_2m,
                            "surface_pressure": e2e_surface_pressure,
                            "wind_speed_10m": e2e_wind_speed_10m,
                            "precipitation": e2e_precipitation,
                            "rain_lag_1h": e2e_rain_lag_1h,
                            "rain_lag_3h": e2e_rain_lag_3h,
                            "rain_lag_6h": e2e_rain_lag_6h,
                            "rain_1h": e2e_rain_1h,
                            "rain_3h": e2e_rain_3h,
                            "rain_6h": e2e_rain_6h,
                            "rain_12h": e2e_rain_12h,
                            "rain_24h": e2e_rain_24h,
                            "pressure_change_3h": e2e_pressure_change_3h,
                            "pressure_change_6h": e2e_pressure_change_6h,
                            "humidity_change_3h": e2e_humidity_change_3h,
                            "humidity_change_6h": e2e_humidity_change_6h,
                            "hour": e2e_hour,
                            "month": e2e_month,
                            "day_of_year": e2e_day_of_year
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
                e2e_distance_to_drainage = st.number_input("Distance to Drainage (m)", value=100.0, min_value=0.0, key="e2e_dist")

            submitted_e2e = st.form_submit_button("Run End-to-End Prediction")
            if submitted_e2e:
                # Build request data
                request_data = {
                    "cells": [
                        {
                            "cell_id": e2e_cell_id,
                            "rain_1h": e2e_rain_1h,
                            "rain_3h": e2e_rain_3h,
                            "rain_6h": e2e_rain_6h,
                            "rain_12h": e2e_rain_12h,
                            "rain_24h": e2e_rain_24h,
                            "elevation": e2e_elevation,
                            "slope_degrees": e2e_slope_degrees,
                            "distance_to_drainage": e2e_distance_to_drainage
                        }
                    ]
                }
                if rainfall_features_e2e is not None:
                    request_data["rainfall_features"] = rainfall_features_e2e

                result = api_request("/predict/end-to-end", "POST", request_data)
                if result:
                    st.success("End-to-end prediction successful!")
                    st.subheader("Result")
                    st.json(result)
                    if "rainfall_significant_probability" in result and result["rainfall_significant_probability"] is not None:
                        st.metric("Significant Rainfall Probability", f"{result['rainfall_significant_probability']:.1%}")
                    if "cells" in result and len(result["cells"]) > 0:
                        for cell in result["cells"]:
                            st.metric(
                                label=f"Risk Class for {cell['cell_id']}",
                                value=cell["risk_class"]
                            )
                            st.caption(f"Inundation risk probability: {cell['inundation_risk_probability']:.1%}")
                    if "exposure" in result and len(result["exposure"]) > 0:
                        for exp in result["exposure"]:
                            st.write(f"**Exposure for {exp['cell_id']}:**")
                            if exp["data_available"]:
                                st.metric("Estimated Population Exposed", exp["estimated_population_exposed"] or "N/A")
                                if exp["affected_facilities"]:
                                    st.write("Affected Facilities: ", ", ".join(exp["affected_facilities"]))
                            else:
                                st.warning(f"Data not available: {exp['reason_if_unavailable']}")
                    if "alerts" in result and len(result["alerts"]) > 0:
                        st.write("**Role-specific Alerts:**")
                        for alert in result["alerts"]:
                            st.write(f"- {alert['cell_id']} (Risk Class: {alert['risk_class']}): {alert['recommended_actions']}")
                    st.caption(result.get("limitation_note", ""))

if __name__ == "__main__":
    main()