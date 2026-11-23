"""Bounded, parameterized SQL against user-provided smart_city_schema.
All public queries are read-only. Unknown locations are NOT assigned invented coordinates.
"""
from datetime import timedelta
from django.db import connection
from django.utils import timezone
from django.core.cache import cache
PARAMS={'pm25':'pm25_ug_m3','pm10':'pm10_ug_m3','temperature':'temperature_c','humidity':'humidity_pct','pressure':'pressure_hpa','uv':'uv_index_estimate','noise':'noise_db'}
WINDOWS={'month':timedelta(days=30),'2weeks':timedelta(days=14),'week':timedelta(days=7),'3days':timedelta(days=3),'2days':timedelta(days=2),'day':timedelta(days=1),'3hours':timedelta(hours=3),'now':timedelta(minutes=20)}
CITY_CANON={'tirana':'Tirana','tiranë':'Tirana','elbasan':'Elbasan','korca':'Korca','korçë':'Korca','korce':'Korca'}
CITIES=['Tirana','Elbasan','Korca']
# Reference city centers are used only for city context; site positions come from database locations.
CITY_CENTERS={'Tirana':[41.3275,19.8187],'Elbasan':[41.1125,20.0822],'Korca':[40.6186,20.7808]}
def city_for(name):
 return CITY_CANON.get(str(name or '').strip().lower())
def parse_window(window):
 return WINDOWS.get(window,WINDOWS['now'])
def query_latest(window='now',param='pm25',limit=400):
 col=PARAMS[param]
 cutoff=timezone.now()-parse_window(window)
 # Find newest VALID observation per node within selected timeframe (avoid 0 representing a missing sensor).
 sql=f"""SELECT DISTINCT ON (n.id) n.id,n.node_name,c.city_name,l.location_name,l.latitude,l.longitude,m.measured_at,m.{col},m.temperature_c,m.pm25_ug_m3,m.pm10_ug_m3,m.humidity_pct,m.pressure_hpa
 FROM smart_city_schema.environmental_measurements m
 JOIN smart_city_schema.nodes n ON n.id=m.node_id AND n.active=true
 LEFT JOIN smart_city_schema.locations l ON n.location_id=l.id
 LEFT JOIN smart_city_schema.cities c ON l.city_id=c.id
 WHERE m.measured_at >= %s AND m.measured_at <= %s AND m.{col} IS NOT NULL
 ORDER BY n.id,m.measured_at DESC LIMIT %s"""
 with connection.cursor() as cur:
  cur.execute(sql,[cutoff,timezone.now()+timedelta(minutes=5),limit]);rows=cur.fetchall()
 result=[]
 for row in rows:
  node_id,node,city,site,lat,lon,ts,value,temp,pm25,pm10,hum,pressure=row
  normalized=city_for(city)
  if normalized not in CITIES:continue
  result.append({'node_id':node_id,'node':node,'city':normalized,'location':site,'lat':lat,'lon':lon,'timestamp':ts.isoformat(),'value':value,'temperature':temp,'pm25':pm25,'pm10':pm10,'humidity':hum,'pressure':pressure,'source':'database','stale':timezone.now()-ts>timedelta(minutes=20)})
 if window=='now':
  live=cache.get('smartcity:latest_live',{}) or {}
  known={v['node'] for v in result}
  for name,event in live.items():
   if name not in known and event.get('city') in CITIES and event.get(param) is not None:
    result.append({'node_id':None,'node':name,'city':event['city'],'location':event.get('location'),'lat':event.get('lat'),'lon':event.get('lon'),'timestamp':event['timestamp'],'value':event[param],'temperature':event.get('temperature'),'pm25':event.get('pm25'),'pm10':event.get('pm10'),'source':'mqtt','stale':False})
 return result

def timeseries(window='week',param='pm25',city=None,limit=2000):
 col=PARAMS[param]
 # Select bounded hourly buckets to avoid transferring huge sensor logs to the browser.
 sql=f"""SELECT date_trunc('hour',m.measured_at) AS bucket, c.city_name, AVG(m.{col}) AS value, COUNT(*) AS samples
 FROM smart_city_schema.environmental_measurements m JOIN smart_city_schema.nodes n ON m.node_id=n.id
 JOIN smart_city_schema.locations l ON n.location_id=l.id JOIN smart_city_schema.cities c ON l.city_id=c.id
 WHERE m.measured_at >= %s AND m.measured_at<=%s AND m.{col} IS NOT NULL
 GROUP BY bucket,c.city_name ORDER BY bucket DESC LIMIT %s"""
 with connection.cursor() as cur:
  cur.execute(sql,[timezone.now()-parse_window(window),timezone.now()+timedelta(minutes=5),limit]);rows=cur.fetchall()
 out=[{'timestamp':t.isoformat(),'city':city_for(c),'value':float(v),'samples':count} for t,c,v,count in rows if city_for(c) in CITIES]
 if city:out=[x for x in out if x['city']==city]
 return list(reversed(out))

def model_history(days=45,city=None):
 sql="""SELECT m.id,n.node_name,c.city_name,l.location_name,l.elevation_m,m.measured_at,m.humidity_pct,m.pm10_ug_m3,m.pm25_ug_m3,m.pressure_hpa,m.rain_raw,m.sound_raw,m.temperature_c,m.uv_raw
 FROM smart_city_schema.environmental_measurements m JOIN smart_city_schema.nodes n ON m.node_id=n.id
 LEFT JOIN smart_city_schema.locations l ON n.location_id=l.id LEFT JOIN smart_city_schema.cities c ON l.city_id=c.id
 WHERE m.measured_at >= %s AND m.measured_at <= %s ORDER BY m.measured_at ASC LIMIT %s"""
 with connection.cursor() as cur:
  cur.execute(sql,[timezone.now()-timedelta(days=days),timezone.now()+timedelta(minutes=5),250000]);rows=cur.fetchall()
 return [r for r in rows if city_for(r[2]) in CITIES and (not city or city_for(r[2])==city)]
