import unittest
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE7_COMP_CSV = REPO_ROOT / "data/processed/stage7_model_comparison.csv"
RETRO_CSV = REPO_ROOT / "data/processed/ai1_retrospective_forecast_2021.csv"

class TestStage7TemporalAlignment(unittest.TestCase):
    def test_retro_csv_exists(self):
        self.assertTrue(RETRO_CSV.exists())

    def test_stage7_comparison_exists(self):
        self.assertTrue(STAGE7_COMP_CSV.exists())
