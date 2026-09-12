from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def test_retro_model_cutoff():
 p=ROOT/"data/processed/ai1_retrospective_forecast_2021.csv"; assert p.exists(); d=pd.read_csv(p); assert (pd.to_datetime(d.training_end)<pd.to_datetime(d.timestamp)).all()
def test_no_future_feature_names():
 s=(ROOT/"src/rainfall_model/walk_forward_forecast.py").read_text(); block=s.split("FEATURES=",1)[1].split("]",1)[0]; assert "future_6h_rain" not in block
