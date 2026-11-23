from unittest.mock import patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory,force_authenticate
from django.contrib.auth.models import AnonymousUser
from monitoring.services.mqtt import normalize
from monitoring.services.measurements import city_for,parse_window
class NormalizerTests(SimpleTestCase):
 def test_city_alias(self):self.assertEqual(city_for('Korçë'),'Korca')
 def test_period(self):self.assertEqual(parse_window('week').days,7)
 def test_null_sensor_not_zero(self):
  sample={'end_device_ids':{'dev_eui':'pi-a'},'city':'Elbasan','uplink_message':{'decoded_payload':{'pm25_ugm3':None,'temperature_c':0}}}
  data=normalize(sample)
  self.assertIsNone(data['pm25']);self.assertEqual(data['temperature'],0)
 def test_reject_unknown_city(self):self.assertIsNone(normalize({'node':'x','city':'Unknown'}))
