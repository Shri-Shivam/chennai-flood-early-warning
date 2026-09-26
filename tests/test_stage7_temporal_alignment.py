from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "models"))


def test_retro_csv_exists(): assert (ROOT/"data/processed/ai1_retrospective_forecast_2021.csv").exists()
def test_stage7_comparison_exists(): assert (ROOT/"data/processed/stage7_model_comparison.csv").exists()


def test_stage7_source_has_no_future_rain_feature():
    """Checks the actual predictor-set definitions, not a raw substring
    search over the whole file -- a substring search would false-positive
    on legitimate comments/docstrings/forbidden-column assertions that
    *mention* future_6h_rain specifically in order to exclude it, which is
    the opposite of a leakage bug."""
    import train_inundation_risk_stage7 as s7
    forbidden = {"future_6h_rain", "target", "label"}
    for exp_name, feats in s7.LEARNED_EXPERIMENTS.items():
        bad = forbidden & set(feats)
        assert not bad, f"{exp_name} predictor set contains forbidden column(s): {bad}"
