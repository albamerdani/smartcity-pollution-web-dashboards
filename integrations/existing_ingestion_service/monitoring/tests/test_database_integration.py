"""Integration test, opt-in via python manage.py test monitoring.tests.test_database_integration --keepdb.
Requires provisioned PostgreSQL+TimescaleDB schema and a DB login that can write tables.
"""
import os
import uuid
from datetime import datetime, timezone
from django.test import TransactionTestCase
from django.db import connection
from monitoring.services import ingest_payload

class IngestDatabaseTests(TransactionTestCase):
    databases={'default'}
    def setUp(self):
        if os.getenv('RUN_DB_INTEGRATION')!='1': self.skipTest('Set RUN_DB_INTEGRATION=1 and provision existing schema')
        self.node='test_pi_'+uuid.uuid4().hex[:10]
        with connection.cursor() as cur:
            cur.execute('INSERT INTO smart_city_schema.api_users (username,token_hash) VALUES (%s,%s) RETURNING id',[self.node,'integration-only'])
            self.user_id=cur.fetchone()[0]
    def tearDown(self):
        if not hasattr(self,'user_id'):return
        with connection.cursor() as cur:
            cur.execute('DELETE FROM smart_city_schema.environmental_measurements WHERE node_id IN (SELECT id FROM smart_city_schema.nodes WHERE node_name=%s)',[self.node])
            cur.execute('DELETE FROM smart_city_schema.ingest_events WHERE api_user_id=%s',[self.user_id])
            cur.execute('DELETE FROM smart_city_schema.nodes WHERE node_name=%s',[self.node])
            cur.execute('DELETE FROM smart_city_schema.api_users WHERE id=%s',[self.user_id])
    def test_ingest_replay_is_idempotent(self):
        time=datetime.now(timezone.utc).isoformat()
        payload={'event_id':str(uuid.uuid4()),'node':{'node_name':self.node},'event_time':time,'received_at':time,
                 'measurements':{'temperature_c':22.5,'pm25_ug_m3':None},'location':{'city_name':None,'location_name':None}}
        first=ingest_payload(payload,self.user_id)
        second=ingest_payload(payload,self.user_id)
        self.assertEqual(first['status'],'created')
        self.assertEqual(second['status'],'duplicate')
        with connection.cursor() as cur:
            cur.execute('SELECT count(*) FROM smart_city_schema.environmental_measurements WHERE node_id=(SELECT id FROM smart_city_schema.nodes WHERE node_name=%s)',[self.node])
            self.assertEqual(cur.fetchone()[0],1)
