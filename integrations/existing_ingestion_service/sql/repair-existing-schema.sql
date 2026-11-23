-- Apply once to pre-existing PostgreSQL 16/TimescaleDB before starting the API.
-- The supplied original SQL creates idx_measurements_gateway_time against
-- a nonexistent gateway_id column; this adds it and the FK without dropping data.
ALTER TABLE smart_city_schema.environmental_measurements
    ADD COLUMN IF NOT EXISTS gateway_id BIGINT;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='environmental_measurements_gateway_id_fkey'
 AND conrelid='smart_city_schema.environmental_measurements'::regclass) THEN
  ALTER TABLE smart_city_schema.environmental_measurements
   ADD CONSTRAINT environmental_measurements_gateway_id_fkey
   FOREIGN KEY (gateway_id) REFERENCES smart_city_schema.gateways(id) ON DELETE SET NULL;
 END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_measurements_gateway_time
 ON smart_city_schema.environmental_measurements (gateway_id, measured_at DESC);
-- IMPORTANT: existing time-series data is NOT altered.
