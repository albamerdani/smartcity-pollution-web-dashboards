import hashlib
import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, override_settings

@override_settings(ALLOWED_HOSTS=['testserver'])
class EndpointTests(SimpleTestCase):
    def test_health(self):
        self.assertEqual(self.client.get('/health/').status_code,200)
    def test_missing_key(self):
        self.assertEqual(self.client.post('/api/v1/ingest/',data='{}',content_type='application/json').status_code,401)
    def test_docs(self):
        self.assertEqual(self.client.get('/api/openapi.json').status_code,200)
        self.assertEqual(self.client.get('/api/docs/').status_code,200)
