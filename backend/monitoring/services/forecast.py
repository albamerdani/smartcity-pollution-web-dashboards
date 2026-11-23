"""Database -> archived ML model adapter with explicit fallback provenance.
No retraining or untrusted model loading from HTTP requests.
"""
import os,tempfile,sys,logging
from datetime import datetime,timezone,timedelta
from pathlib import Path
from django.conf import settings
from django.core.cache import cache
from .measurements import model_history,city_for,CITIES
logger=logging.getLogger(__name__)
MODEL_ROOT=Path(os.getenv('MODEL_ROOT',str(Path(__file__).resolve().parents[3]/'ml_forecast')))
TARGETS={'pm25':'pm25_ugm3','pm10':'pm10_ugm3','temperature':'temperature_c','humidity':'humidity_pct','pressure':'pressure_hpa'}
def fallback(city,horizon,reason):
 """Last-observation baseline, never falsely labelled ML."""
 rows=model_history(days=2,city=city)
 latest={}
 for row in rows:
  if row[6] is not None:latest[(row[1],'humidity')]=row[6]
  if row[7] is not None:latest[(row[1],'pm10')]=row[7]
  if row[8] is not None:latest[(row[1],'pm25')]=row[8]
  if row[9] is not None:latest[(row[1],'pressure')]=row[9]
  if row[12] is not None:latest[(row[1],'temperature')]=row[12]
 now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
 values=[]
 for (node,p),v in latest.items():
  for hour in range(1,horizon+1):
   values.append({'node':node,'city':city_for(next((r[2] for r in reversed(rows) if r[1]==node),'')),'param':p,'timestamp':(now+timedelta(hours=hour)).isoformat(),'value':float(v),'method':'persistence_baseline'})
 return {'status':'baseline','reason':reason,'generated_at':datetime.now(timezone.utc).isoformat(),'forecasts':values}
def adaptive_ml(city,horizon,reason):
 """Train a small data-driven model on recent measured hourly observations.
 This model is not the shipped archived model. It never pretends to be one.
 """
 import pandas as pd
 import numpy as np
 from sklearn.ensemble import HistGradientBoostingRegressor
 rows=model_history(days=45,city=city)
 if not rows:return fallback(city,horizon,reason)
 columns={'humidity':6,'pm10':7,'pm25':8,'pressure':9,'temperature':12}
 series={}
 for name,column in columns.items():
  per_node={}
  for entry in rows:
   node=entry[1];value=entry[column]
   if value is None:continue
   per_node.setdefault(node,[]).append((entry[5],float(value),city_for(entry[2])))
  for node,history in per_node.items():
   hist=pd.DataFrame(history,columns=['timestamp','value','city']).set_index('timestamp').sort_index()
   hourly=hist['value'].resample('1h').median().interpolate(limit=2)
   if len(hourly)<120 or hourly.notna().sum()<100:continue
   # Hourly seasonal features, lags, rolling mean. Train only on timestamps with known target.
   f=pd.DataFrame({'value':hourly})
   f['h']=f.index.hour;f['dow']=f.index.dayofweek
   for lag in (1,2,3,24):f[f'lag{lag}']=f.value.shift(lag)
   f['avg24']=f.value.shift(1).rolling(24,min_periods=5).mean()
   train=f.dropna()
   if len(train)<75:continue
   names=['h','dow','lag1','lag2','lag3','lag24','avg24']
   model=HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=15,min_samples_leaf=10,random_state=42)
   model.fit(train[names],train['value'])
   values=hourly.copy().astype(float)
   if pd.isna(values.iloc[-1]):continue
   origin=values.index.max()
   forecasts=[]
   for step in range(1,horizon+1):
    ts=origin+pd.Timedelta(hours=step)
    def lag_at(hours):
     v=values.get(ts-pd.Timedelta(hours=hours),np.nan)
     return float(v) if pd.notna(v) else float(values.dropna().iloc[-1])
    prior=values.loc[ts-pd.Timedelta(hours=24):ts-pd.Timedelta(hours=1)].dropna()
    avg=float(prior.mean()) if len(prior) else lag_at(1)
    predictors=pd.DataFrame([[ts.hour,ts.dayofweek,lag_at(1),lag_at(2),lag_at(3),lag_at(24),avg]],columns=names)
    prediction=float(model.predict(predictors)[0])
    if name in ('pm25','pm10'):prediction=max(0,prediction)
    if name=='humidity':prediction=max(0,min(100,prediction))
    values.loc[ts]=prediction
    forecasts.append({'node':node,'city':history[-1][2],'param':name,'timestamp':ts.isoformat(),'value':prediction,'method':'adaptive_hgb_model'})
   series[(node,name)]=forecasts
 if not series:return fallback(city,horizon,reason+'; insufficient ML training history')
 return {'status':'ml_adaptive','reason':reason,'model_version':'adaptive-hgb-v1','generated_at':datetime.now(timezone.utc).isoformat(),'forecasts':[item for records in series.values() for item in records]}

def generate(city=None,horizon=24):
 rows=model_history(days=45,city=city)
 if not rows:return {'status':'insufficient_data','reason':'No recent database history','forecasts':[]}
 if not settings.MODEL_ENABLED:return fallback(city,horizon,'Model disabled')
 try:
  import pandas as pd
  sys.path.insert(0,str(MODEL_ROOT.parent))
  from ml_forecast.src.modeling import load_verified_bundle,predict_from_loaded_bundle
  from ml_forecast.src.preprocessing import prepare_data
  names=['id','indoor_lora_dev_eui','indoor_lora_join_eui','indoor_lora_dev_adr','place','description','altitude_m','humidity_pct','pm10_ugm3','pm25_ugm3','pressure_hpa','rain_raw','sound_raw','temperature_c','uv_raw','created_at']
  records=[]
  for item in rows:
   i,node,city_name,site,elev,ts,hum,pm10,pm25,pr,rain,sound,temp,uv=item
   records.append([i,node,node,node,site or city_name,city_name,elev,hum,pm10,pm25,pr,rain,sound,temp,uv,ts.astimezone(timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')])
  bundle=load_verified_bundle(MODEL_ROOT/'artifacts/environmental_forecasting_model.joblib')
  with tempfile.TemporaryDirectory() as d:
   inp=Path(d)/'history.csv';out=Path(d)/'forecast.csv';eli=Path(d)/'eligibility.csv'
   pd.DataFrame(records,columns=names).to_csv(inp,index=False)
   prepared=prepare_data(inp,bundle['config'])
   frame=predict_from_loaded_bundle(bundle,prepared,out,eli)
  if frame.empty:return adaptive_ml(city,horizon,'Archived model returned no eligible series')
  reverse={v:k for k,v in TARGETS.items()}
  cities={node:city_for(c) for _,node,c,*_ in rows}
  result=[]
  for entry in frame.to_dict('records'):
   node=str(entry.get('sensor_id',''));param=reverse.get(entry.get('target'))
   step=int(entry.get('horizon_hour',0))
   if not param or not (1<=step<=horizon):continue
   stamp=entry.get('timestamp')
   val=entry.get('prediction')
   if pd.isna(val):continue
   result.append({'node':node,'city':cities.get(node),'param':param,'timestamp':str(stamp),'value':float(val),'method':str(entry.get('model_name','trained_model'))})
  if not result:return adaptive_ml(city,horizon,'No matched archived model targets')
  return {'status':'ml','model_version':bundle.get('bundle_version'),'generated_at':datetime.now(timezone.utc).isoformat(),'forecasts':result}
 except Exception as exc:
  logger.exception('ML prediction failed')
  
  try:return adaptive_ml(city,horizon,'Archived model unavailable: '+type(exc).__name__)
  except Exception:
   logger.exception('Adaptive ML failed');return fallback(city,horizon,'All models unavailable')
def run_cached(city=None,horizon=24):
 key=f'smartcity:forecast:{city or "all"}:{horizon}'
 val=cache.get(key)
 if val:return val
 val=generate(city,horizon)
 cache.set(key,val,300)
 return val
