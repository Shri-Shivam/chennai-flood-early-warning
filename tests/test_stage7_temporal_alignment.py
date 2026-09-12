from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_retro_csv_exists(): assert (ROOT/"data/processed/ai1_retrospective_forecast_2021.csv").exists()
def test_stage7_comparison_exists(): assert (ROOT/"data/processed/stage7_model_comparison.csv").exists()
def test_stage7_source_has_no_future_rain_feature(): assert "future_6h_rain" not in (ROOT/"src/models/train_inundation_risk_stage7.py").read_text()
