"""Transactional, idempotent ingest into pre-existing PostgreSQL 16 / TimescaleDB schema."""
import json
import math
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from django.db import connection, transaction
from django.utils import timezone

MEASUREMENT_FIELDS = (
    'temperature_c','humidity_pct','bmp_temperature_c','pressure_hpa',
    'uv_digital_raw','uv_digital_state','uv_raw','uv_voltage','uv_index_estimate',
    'rain_digital_raw','rain_digital_state','rain_raw','rain_voltage','rainfall_mm',
    'sound_raw','sound_voltage','sound_index','noise_db','pm25_ug_m3','pm10_ug_m3',
    'latitude','longitude','altitude_m','water_temperature_c','ph','turbidity',
    'conductivity','impurity','dissolved_solids','rssi','snr','fcnt',
)
INT_FIELDS = {'uv_digital_raw','uv_raw','rain_digital_raw','rain_raw','sound_raw','sound_index','fcnt'}
TEXT_FIELDS = {'uv_digital_state','rain_digital_state'}

class IngestError(ValueError):
    pass

def parse_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise IngestError('event_time/received_at must contain a timestamp')
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z','+00:00'))
    except ValueError as exc:
        raise IngestError('Invalid ISO timestamp') from exc
    # Old Raspberry Pi script uses naive Europe/Tirane timestamps.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('Europe/Tirane'))
    return dt

def validate_measurements(values):
    if not isinstance(values, dict):
        raise IngestError('measurements must be an object')
    unknown = set(values) - set(MEASUREMENT_FIELDS)
    if unknown:
        raise IngestError('Unrecognized measurements: ' + ', '.join(sorted(unknown)))
    clean = {}
    for k in MEASUREMENT_FIELDS:
        v = values.get(k)
        if v is not None:
            if k in TEXT_FIELDS:
                if not isinstance(v,str) or len(v)>100:
                    raise IngestError(f'Invalid {k}')
            elif isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
                raise IngestError(f'Invalid numeric value for {k}')
            elif k in INT_FIELDS and (not isinstance(v,int) or (k.endswith('digital_raw') and v not in (0,1))):
                raise IngestError(f'Invalid integer value for {k}')
        clean[k]=v
    for key,lower,upper in (('latitude',-90,90),('longitude',-180,180),('humidity_pct',0,100)):
        if clean[key] is not None and not lower <= clean[key] <= upper:
            raise IngestError(f'{key} out of range')
    return clean

def decode_legacy(payload):
    p=(payload.get('uplink_message') or {}).get('decoded_payload') or {}
    return {'temperature_c':p.get('temperature_c'),'humidity_pct':p.get('humidity_pct'),
            'pressure_hpa':p.get('pressure_hpa'),'rain_raw':p.get('rain_raw'),
            'sound_raw':p.get('sound_raw'),'uv_raw':p.get('uv_raw'),
            'pm25_ug_m3':p.get('pm25_ugm3'),'pm10_ug_m3':p.get('pm10_ugm3'),
            'altitude_m':p.get('altitude_m')}

def ingest_payload(payload, api_user_id, endpoint='/api/v1/ingest/'):
    if not isinstance(payload,dict):
        raise IngestError('JSON object required')
    node_obj = payload.get('node') or {}
    ids = payload.get('end_device_ids') or {}
    node_name = node_obj.get('node_name') or ids.get('dev_eui')
    if not isinstance(node_name,str) or not 1 <= len(node_name) <= 150:
        raise IngestError('node.node_name or end_device_ids.dev_eui is required')
    if payload.get('source_type','raspberry_pi_api') != 'raspberry_pi_api':
        raise IngestError('This endpoint only accepts raspberry_pi_api')
    received_text = payload.get('received_at')
    measured_at = parse_timestamp(payload.get('event_time') or received_text)
    received_at = parse_timestamp(received_text) if received_text else measured_at
    event_id_str = payload.get('event_id')
    try:
        event_id = uuid.UUID(event_id_str) if event_id_str else uuid.uuid4()
    except (ValueError,TypeError,AttributeError):
        raise IngestError('event_id must be UUID')
    measurement = validate_measurements(payload.get('measurements', decode_legacy(payload)))
    location = payload.get('location') or {}
    gateway = payload.get('gateway') or {}
    decoded=(payload.get('uplink_message') or {}).get('decoded_payload') or {}
    if not isinstance(decoded,dict) or not isinstance(location,dict) or not isinstance(gateway,dict) or not isinstance(node_obj,dict):
        raise IngestError('Invalid nested objects')
    loc_name = location.get('location_name') or decoded.get('place')
    city_name = location.get('city_name')
    if city_name is not None and (not isinstance(city_name,str) or len(city_name)>200):
        raise IngestError('Invalid city_name')
    if loc_name is not None and (not isinstance(loc_name,str) or len(loc_name)>200):
        raise IngestError('Invalid location_name')
    for k in ('latitude','longitude','elevation_m'):
        v=location.get(k)
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)):
            raise IngestError(f'Invalid location.{k}')
    if location.get('latitude') is not None and not -90 <= location['latitude'] <= 90:
        raise IngestError('location.latitude out of range')
    if location.get('longitude') is not None and not -180 <= location['longitude'] <= 180:
        raise IngestError('location.longitude out of range')
    # Never trust caller-provided api_user_id, node IDs, or system timestamps.
    with transaction.atomic():
        with connection.cursor() as cur:
            # A credential is scoped to its own node; avoids one node impersonating another.
            cur.execute('SELECT username FROM smart_city_schema.api_users WHERE id=%s AND is_active=true', [api_user_id])
            row=cur.fetchone()
            if not row or row[0] != node_name:
                raise IngestError('API credential is not authorized for node')
            cur.execute('SELECT raw_payload_json FROM smart_city_schema.ingest_events WHERE id=%s', [event_id])
            previous=cur.fetchone()
            if previous:
                prev=previous[0]
                if isinstance(prev,str): prev=json.loads(prev)
                if prev != payload:
                    raise IngestError('event_id already exists with different payload')
                return {'event_id':str(event_id),'status':'duplicate','node_name':node_name}
            city_id=None
            if city_name:
                cur.execute('INSERT INTO smart_city_schema.cities (city_name,country_name) VALUES (%s,%s) ON CONFLICT (city_name) DO UPDATE SET country_name=EXCLUDED.country_name RETURNING id',
                            [city_name,location.get('country_name') or 'Albania'])
                city_id=cur.fetchone()[0]
            location_id=None
            if loc_name:
                # NULL city_id does not participate in SQL UNIQUE; reuse an existing NULL-city location.
                cur.execute('SELECT id FROM smart_city_schema.locations WHERE city_id IS NOT DISTINCT FROM %s AND location_name=%s ORDER BY id LIMIT 1', [city_id,loc_name])
                existing=cur.fetchone()
                if existing:
                    location_id=existing[0]
                    cur.execute('UPDATE smart_city_schema.locations SET latitude=COALESCE(%s,latitude),longitude=COALESCE(%s,longitude),elevation_m=COALESCE(%s,elevation_m),description=COALESCE(%s,description) WHERE id=%s',
                                [location.get('latitude'),location.get('longitude'),location.get('elevation_m'),location.get('description') or decoded.get('description'),location_id])
                else:
                    cur.execute('INSERT INTO smart_city_schema.locations (city_id,location_name,latitude,longitude,elevation_m,description) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                                [city_id,loc_name,location.get('latitude'),location.get('longitude'),location.get('elevation_m'),location.get('description') or decoded.get('description')])
                    location_id=cur.fetchone()[0]
            gateway_id=None
            if gateway.get('gateway_name'):
                cur.execute('INSERT INTO smart_city_schema.gateways (gateway_name,gateway_eui,location_id,gateway_type,network_server) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (gateway_name) DO UPDATE SET location_id=COALESCE(EXCLUDED.location_id,smart_city_schema.gateways.location_id) RETURNING id',
                            [gateway['gateway_name'],gateway.get('gateway_eui'),location_id,gateway.get('gateway_type'),gateway.get('network_server')])
                gateway_id=cur.fetchone()[0]
            cur.execute('''INSERT INTO smart_city_schema.nodes
                (node_name,node_external_id,node_type,communication_type,location_id,gateway_id,microcontroller_model,firmware_version,script_version,network_server,identical_sensor_suite,meta)
                VALUES (%s,%s,'raspberry_pi','http_api',%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (node_name) DO UPDATE SET
                location_id=COALESCE(EXCLUDED.location_id,smart_city_schema.nodes.location_id),
                gateway_id=COALESCE(EXCLUDED.gateway_id,smart_city_schema.nodes.gateway_id),
                script_version=COALESCE(EXCLUDED.script_version,smart_city_schema.nodes.script_version),
                firmware_version=COALESCE(EXCLUDED.firmware_version,smart_city_schema.nodes.firmware_version),
                meta=COALESCE(EXCLUDED.meta,smart_city_schema.nodes.meta)
                RETURNING id''', [node_name,node_obj.get('node_external_id') or node_name,location_id,gateway_id,
                node_obj.get('microcontroller_model'),node_obj.get('firmware_version'),node_obj.get('script_version'),
                node_obj.get('network_server'),node_obj.get('identical_sensor_suite',True),json.dumps({'hostname':node_obj.get('hostname'),'os_release':node_obj.get('os_release')})])
            node_id=cur.fetchone()[0]
            cur.execute('''INSERT INTO smart_city_schema.ingest_events
                (id,node_id,node_name,node_external_id,source_type,event_time,received_at,received_at_text,gateway_id,rssi,snr,fcnt,raw_payload_json,raw_sensor_json,decoded_payload_json,api_user_id,api_endpoint,http_status_code,parse_status)
                VALUES (%s,%s,%s,%s,'raspberry_pi_api',%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,200,'parsed')''',
                [event_id,node_id,node_name,node_obj.get('node_external_id') or node_name,measured_at,received_at,received_text,
                 gateway_id,measurement['rssi'],measurement['snr'],measurement['fcnt'],json.dumps(payload),
                 json.dumps(payload.get('raw_sensor_data')) if payload.get('raw_sensor_data') is not None else None,
                 json.dumps(decoded),api_user_id,endpoint])
            names=['measured_at','ingest_id','node_id','source_type','received_at','gateway_id']+list(MEASUREMENT_FIELDS)+['decoded_payload_json']
            # Parameters are static allowlisted columns only.
            vals=[measured_at,event_id,node_id,'raspberry_pi_api',received_at,gateway_id]+[measurement[k] for k in MEASUREMENT_FIELDS]+[json.dumps(decoded)]
            columns=','.join(names)
            placeholders=','.join(['%s']*(len(names)-1)+['%s::jsonb'])
            cur.execute(f'''INSERT INTO smart_city_schema.environmental_measurements ({columns}) VALUES ({placeholders})
                ON CONFLICT (node_id,measured_at) DO NOTHING RETURNING id''', vals)
            measurement_row=cur.fetchone()
            return {'event_id':str(event_id),'status':'created' if measurement_row else 'measurement_already_exists',
                    'node_name':node_name,'measurement_id':measurement_row[0] if measurement_row else None}
