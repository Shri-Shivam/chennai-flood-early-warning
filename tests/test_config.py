"""SIH26071 - tests for centralized configuration."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_default_settings_load():
    from src.config import Settings
    s = Settings()
    assert s.ai1_rainfall_model_path == "models/xgboost_rainfall_model.json"
    assert 0.0 < s.ai2_default_threshold < 1.0


def test_resolve_returns_absolute_path_under_repo_root():
    from src.config import Settings, ROOT
    s = Settings()
    resolved = s.resolve(s.ai1_rainfall_model_path)
    assert resolved.is_absolute()
    assert resolved == ROOT / s.ai1_rainfall_model_path


def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("SIH26071_AI2_DEFAULT_THRESHOLD", "0.5")
    from src.config import Settings
    s = Settings()
    assert s.ai2_default_threshold == 0.5


def test_no_credential_fields_exist():
    """Config must never hold secrets -- verified by field-name inspection,
    not just a docstring claim."""
    from src.config import Settings
    field_names = set(Settings.model_fields.keys())
    forbidden_substrings = ("key", "token", "secret", "password", "credential")
    bad = [f for f in field_names if any(sub in f.lower() for sub in forbidden_substrings)]
    assert not bad, f"Config has suspicious credential-like field(s): {bad}"


def test_alert_thresholds_are_monotonically_increasing():
    from src.config import Settings
    s = Settings()
    assert s.alert_watch_threshold < s.alert_warning_threshold < s.alert_high_risk_threshold
