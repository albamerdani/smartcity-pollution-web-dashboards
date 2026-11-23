"""Optional publish helper; import from existing read_sensors.py after build_payload(data).
Not enabled automatically: preserves original acquisition / API buffering behavior.
Requires paho-mqtt>=2.1 and environment MQTT_* options.
"""
import os,json,logging
import paho.mqtt.publish as publish

def publish_measurement(payload):
    host=os.getenv('MQTT_HOST')
    if not host:return False
    node=os.getenv('NODE_NAME','raspberry_pi')
    message=dict(payload)
    message['node_name']=node
    message['city']=os.getenv('CITY_NAME','')
    auth=None
    if os.getenv('MQTT_USERNAME'):
        auth={'username':os.environ['MQTT_USERNAME'],'password':os.getenv('MQTT_PASSWORD','')}
    publish.single(
        os.getenv('MQTT_TOPIC',f'smartcity/nodes/{node}/measurements'),
        payload=json.dumps(message),hostname=host,port=int(os.getenv('MQTT_PORT','1883')),
        auth=auth,qos=1,retain=False,
    )
    return True
