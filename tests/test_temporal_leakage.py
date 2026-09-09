import unittest
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAINFALL_CSV = REPO_ROOT / "data/processed/rainfall_ml_dataset.csv"
RETRO_CSV = REPO_ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"

class TestTemporalLeakage(unittest.TestCase):
    def test_retro_model_cutoff(self):
        if not RETRO_CSV.exists():
            raise unittest.SkipTest(f"Missing {RETRO_CSV}")
        retro_df = pd.read_csv(RETRO_CSV)
        for cutoff in retro_df["training_end"]:
            self.assertTrue(cutoff <= "2021-10-31 23:00:00")
