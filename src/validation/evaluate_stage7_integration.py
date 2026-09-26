from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def validate():
 p=ROOT/"data/processed/stage7_ai1_ai2_predictions.csv"; r=ROOT/"data/processed/stage7_model_comparison.csv"; assert p.exists() and r.exists(); d=pd.read_csv(p); assert d.risk_probability.between(0,1).all(); assert d.duplicated(["cell_id","timestamp","experiment"]).sum()==0; return True
if __name__=="__main__": print("Stage 7 validation:",validate())
