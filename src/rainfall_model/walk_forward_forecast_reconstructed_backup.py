"""SIH26071 Stage 6: leakage-safe walk-forward AI #1."""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import average_precision_score,precision_score,recall_score,f1_score,brier_score_loss
from xgboost import XGBClassifier,XGBRegressor
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/processed/rainfall_ml_dataset.csv"; RETRO=ROOT/"data/processed/ai1_retrospective_forecast_2021.csv"; MET=ROOT/"data/processed/ai1_walk_forward_metrics.csv"; REPORT=ROOT/"data/processed/ai1_stage6_report.txt"; MODEL=ROOT/"models/stage6_retrospective_2021"
FEATURES=["temperature_2m","relative_humidity_2m","surface_pressure","wind_speed_10m","precipitation","rain_lag_1h","rain_lag_3h","rain_lag_6h","rain_1h","rain_3h","rain_6h","rain_12h","rain_24h","pressure_change_3h","pressure_change_6h","humidity_change_3h","humidity_change_6h","hour","month","day_of_year"]
def load():
    d=pd.read_csv(DATA); d["timestamp"]=pd.to_datetime(d["time"] if "time" in d else d["timestamp"],format="mixed"); d=d.sort_values("timestamp").reset_index(drop=True)
    miss=[x for x in FEATURES+["target","future_6h_rain"] if x not in d]; assert not miss,f"Missing: {miss}"; return d
def clf():
    return XGBClassifier(n_estimators=400,max_depth=5,learning_rate=.05,subsample=.8,colsample_bytree=.8,objective="binary:logistic",eval_metric="aucpr",scale_pos_weight=243.40,random_state=42,n_jobs=-1,tree_method="hist")
def reg():
    return XGBRegressor(n_estimators=400,max_depth=5,learning_rate=.05,subsample=.8,colsample_bytree=.8,objective="reg:squarederror",random_state=42,n_jobs=-1,tree_method="hist")
def main():
    d=load(); tr=d[d.timestamp<="2021-10-31 23:00:00"].copy(); te=d[(d.timestamp>="2021-11-01")&(d.timestamp<"2021-12-01")].copy()
    m=clf().fit(tr[FEATURES],tr.target.astype(int)); r=reg().fit(tr[FEATURES],tr.future_6h_rain.astype(float))
    p=m.predict_proba(te[FEATURES])[:,1]; a=np.clip(r.predict(te[FEATURES]),0,None); y=te.target.astype(int).to_numpy(); yp=(p>=.90).astype(int)
    MODEL.mkdir(parents=True,exist_ok=True); m.save_model(MODEL/"xgboost_pre_nov2021.json"); r.save_model(MODEL/"xgboost_pre_nov2021_regressor.json")
    pd.DataFrame({"timestamp":te.timestamp.dt.strftime("%Y-%m-%d %H:%M:%S"),"training_end":"2021-10-31 23:00:00","predicted_probability":p,"predicted_class":yp,"actual_future_6h_rain":te.future_6h_rain,"actual_target":y,"predicted_amount_mm":a}).to_csv(RETRO,index=False,float_format="%.10g")
    rows=[]
    for year in range(2021,2026):
        a0=d[d.timestamp.dt.year<year]; b=d[d.timestamp.dt.year==year]
        mm=clf().fit(a0[FEATURES],a0.target.astype(int)); pb=mm.predict_proba(b[FEATURES])[:,1]; pv=mm.predict_proba(a0.tail(8760)[FEATURES])[:,1]; yy=a0.tail(8760).target.astype(int).to_numpy()
        best=max(((t, ((yy==1)&(pv>=t)).sum()/max(1,((yy==1)&(pv>=t)).sum()+((yy==0)&(pv>=t)).sum()+((yy==1)&(pv<t)).sum())) for t in np.linspace(.5,.95,46)),key=lambda z:z[1]); th=best[0]; q=(pb>=th).astype(int); yt=b.target.astype(int).to_numpy()
        rows.append({"year":year,"threshold":th,"precision":precision_score(yt,q,zero_division=0),"recall":recall_score(yt,q,zero_division=0),"F1":f1_score(yt,q,zero_division=0),"PR_AUC":average_precision_score(yt,pb),"n_test":len(b),"n_positive":int(yt.sum())})
    pd.DataFrame(rows).to_csv(MET,index=False)
    REPORT.write_text(f"Stage 6 reconstructed implementation.\nNovember 2021 precision={precision_score(y,yp,zero_division=0):.4f}; recall={recall_score(y,yp,zero_division=0):.4f}; F1={f1_score(y,yp,zero_division=0):.4f}; PR-AUC={average_precision_score(y,p):.4f}; Brier={brier_score_loss(y,p):.4f}\nFuture T+1..T+6 rainfall is target-only information.\n",encoding="utf8")
if __name__=="__main__": main()
