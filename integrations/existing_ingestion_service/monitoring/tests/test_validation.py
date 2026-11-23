from django.test import SimpleTestCase
from monitoring.services import validate_measurements, parse_timestamp, IngestError, decode_legacy

class ValidationTests(SimpleTestCase):
    def test_null_is_not_zero(self):
        result=validate_measurements({'temperature_c':None,'pm25_ug_m3':0})
        self.assertIsNone(result['temperature_c'])
        self.assertEqual(result['pm25_ug_m3'],0)
    def test_unknown_column_rejected(self):
        with self.assertRaises(IngestError):validate_measurements({'sql_injection':'abc'})
    def test_nan_rejected(self):
        with self.assertRaises(IngestError):validate_measurements({'temperature_c':float('nan')})
    def test_legacy_local_time(self):
        self.assertIsNotNone(parse_timestamp('2026-11-23 12:44:00').utcoffset())
    def test_legacy_mapping(self):
        self.assertEqual(decode_legacy({'uplink_message':{'decoded_payload':{'pm25_ugm3':12.5}}})['pm25_ug_m3'],12.5)
