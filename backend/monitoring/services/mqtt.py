"""MQTT event normalizer. Existing ingestion API remains authoritative for durable writes."""
from datetime import datetime,timezone
from django.core.cache import cache
from .measurements import city_for

def normalize(payload):
 ids=payload.get('end_device_ids') or {}
 dp=((payload.get('uplink_message') or {}).get('decoded_payload') or payload.get('decoded_payload') or payload)
 raw=payload.get('raw_sensor_json') or payload.get('raw_sensors') or {}
 node=(payload.get('node_name') or ids.get('dev_eui') or payload.get('node') or '').strip()
 city=city_for(payload.get('city') or dp.get('city') or payload.get('city_name'))
 if not city:city=city_for(dp.get('place'))
 if not node or len(node)>128 or not city:return None
 def num(*keys):
  for k in keys:
   v=dp.get(k)
   if v is not None and not isinstance(v,bool):
    try:return float(v)
    except (TypeError,ValueError):pass
  return None
 stamp=payload.get('event_time') or payload.get('received_at') or datetime.now(timezone.utc).isoformat()
 return {'node':node,'city':city,'location':dp.get('place'),'lat':num('latitude'),'lon':num('longitude'),'timestamp':stamp,'pm25':num('pm25_ugm3','pm25_ug_m3'),'pm10':num('pm10_ugm3','pm10_ug_m3'),'temperature':num('temperature_c'),'humidity':num('humidity_pct'),'pressure':num('pressure_hpa'),'uv':num('uv_index_estimate'),'noise':num('noise_db')}
def store_live(payload):
 item=normalize(payload)
 if item is None:return False
 current=cache.get('smartcity:latest_live',{}) or {}
 current[item['node']]=item
 cache.set('smartcity:latest_live',current,3600)
 return True
