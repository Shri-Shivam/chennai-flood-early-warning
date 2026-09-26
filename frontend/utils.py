import requests
import streamlit as st
import json
from typing import Dict, Any, Optional
from pathlib import Path

def load_geojson(path: str) -> Dict[str, Any]:
    """Load and cache a GeoJSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading GeoJSON {path}: {e}")
        return {}

def get_risk_color(risk_class: str) -> str:
    """Map risk class to a color for visualization."""
    mapping = {
        "LOW": "green",
        "MODERATE": "orange",
        "HIGH": "red"
    }
    return mapping.get(risk_class.upper(), "gray")

def enhanced_api_call(endpoint: str, method: str = "GET", data: Optional[Dict] = None, base_url: str = "http://localhost:8000") -> Optional[Dict[str, Any]]:
    """
    Enhanced API request wrapper with timeout and explicit error handling.
    """
    url = f"{base_url}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code == 503:
            st.error("Backend Service Unavailable (503). Please ensure the FastAPI server is running.")
            return None
        elif response.status_code == 422:
            st.error(f"Validation Error (422): {response.json().get('detail', 'Invalid input data')}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("API request timed out. The server may be overloaded.")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the Backend API. Is it running at http://localhost:8000?")
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")

    return None
