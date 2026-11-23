import json,logging,time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from monitoring.services.mqtt import store_live
log=logging.getLogger(__name__)
class Command(BaseCommand):
 help='Subscribe to Raspberry Pi measurement events and refresh live dashboard cache'
 def handle(self,*args,**options):
  import paho.mqtt.client as mqtt
  client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='smartcity-dashboard',clean_session=True)
  if settings.MQTT_USERNAME:client.username_pw_set(settings.MQTT_USERNAME,settings.MQTT_PASSWORD)
  def connected(client,userdata,flags,reason_code,properties):
   if reason_code==0:client.subscribe(settings.MQTT_TOPIC,qos=1);log.info('Subscribed %s',settings.MQTT_TOPIC)
   else:log.warning('MQTT connect failed: %s',reason_code)
  def message(client,userdata,msg):
   try:
    if len(msg.payload)>128000:raise ValueError('Payload too large')
    payload=json.loads(msg.payload)
    if not isinstance(payload,dict):raise ValueError('Expected JSON object')
    if store_live(payload):cache.delete('smartcity:forecast:all:24')
   except (ValueError,TypeError,KeyError) as exc:log.warning('Invalid MQTT message: %s',exc)
  client.on_connect=connected;client.on_message=message
  client.connect(settings.MQTT_HOST,settings.MQTT_PORT,keepalive=60)
  client.loop_forever(retry_first_connection=True)
