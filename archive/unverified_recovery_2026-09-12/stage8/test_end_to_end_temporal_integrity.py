import unittest
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = REPO_ROOT / "data/processed/stage8_end_to_end_metrics.csv"
CONF_CSV = REPO_ROOT / "data/processed/stage8_confusion_matrices.csv"
EVENTS_CSV = REPO_ROOT / "data/processed/stage8_event_summary.csv"

class TestEndToEndTemporalIntegrity(unittest.TestCase):
    def test_metrics_file_exists(self):
        self.assertTrue(METRICS_CSV.exists())
