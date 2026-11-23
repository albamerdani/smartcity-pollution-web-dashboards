-- =========================================================
-- FINAL DATABASE SCHEMA
-- PostgreSQL 16 + TimescaleDB
-- Project: SmartCityPollution Monitoring System
-- =========================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS smart_city_schema;

-- =========================================================
-- USERS / API AUTHENTICATION
-- For Django/API endpoint authentication
-- Store only hashed tokens, not raw tokens.
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.api_users (
    id                  BIGSERIAL PRIMARY KEY,
    username            TEXT NOT NULL UNIQUE,
    full_name           TEXT,
    email               TEXT UNIQUE,
    token_hash          TEXT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at        TIMESTAMPTZ,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_users_active
    ON smart_city_schema.api_users (is_active);

-- =========================================================
-- DIMENSION TABLES
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.cities (
    id                  BIGSERIAL PRIMARY KEY,
    city_name           TEXT NOT NULL UNIQUE,
    country_name        TEXT NOT NULL DEFAULT 'Albania',
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS smart_city_schema.locations (
    id                  BIGSERIAL PRIMARY KEY,
    city_id             BIGINT REFERENCES smart_city_schema.cities(id) ON DELETE SET NULL,
    location_name       TEXT NOT NULL,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    elevation_m         DOUBLE PRECISION,
    description         TEXT,
    UNIQUE (city_id, location_name)
);

CREATE TABLE IF NOT EXISTS smart_city_schema.gateways (
    id                  BIGSERIAL PRIMARY KEY,
    gateway_name        TEXT NOT NULL UNIQUE,
    gateway_eui         TEXT,
    location_id         BIGINT REFERENCES smart_city_schema.locations(id) ON DELETE SET NULL,
    gateway_type        TEXT,
    network_server      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS smart_city_schema.nodes (
    id                          BIGSERIAL PRIMARY KEY,
    node_name                   TEXT NOT NULL UNIQUE,
    node_external_id            TEXT,
    node_type                   TEXT NOT NULL CHECK (
        node_type IN ('raspberry_pi', 'arduino', 'drone', 'mobile', 'other')
    ),
    communication_type          TEXT NOT NULL CHECK (
        communication_type IN ('http_api', 'lorawan', 'mqtt', 'other')
    ),

    location_id                 BIGINT REFERENCES smart_city_schema.locations(id) ON DELETE SET NULL,
    gateway_id                  BIGINT REFERENCES smart_city_schema.gateways(id) ON DELETE SET NULL,

    microcontroller_model       TEXT,
    firmware_version            TEXT,
    script_version              TEXT,
    network_server              TEXT,

    identical_sensor_suite      BOOLEAN NOT NULL DEFAULT TRUE,
    active                      BOOLEAN NOT NULL DEFAULT TRUE,

    installed_at                TIMESTAMPTZ,
    removed_at                  TIMESTAMPTZ,
    meta                        JSONB,
    notes                       TEXT
);

CREATE INDEX IF NOT EXISTS idx_nodes_location_id
    ON smart_city_schema.nodes (location_id);

CREATE INDEX IF NOT EXISTS idx_nodes_gateway_id
    ON smart_city_schema.nodes (gateway_id);

-- =========================================================
-- RAW INGEST EVENTS
-- Stores full received JSON payloads
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.ingest_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingested_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    node_id                     BIGINT REFERENCES smart_city_schema.nodes(id) ON DELETE SET NULL,
    node_name                   TEXT,
    node_external_id            TEXT,

    source_type                 TEXT NOT NULL CHECK (
        source_type IN ('raspberry_pi_api', 'arduino_lorawan', 'mqtt', 'other')
    ),

    event_time                  TIMESTAMPTZ,
    received_at                 TIMESTAMPTZ,
    received_at_text            TEXT,

    gateway_id                  BIGINT REFERENCES smart_city_schema.gateways(id) ON DELETE SET NULL,
    rssi                        DOUBLE PRECISION,
    snr                         DOUBLE PRECISION,
    fcnt                        BIGINT,

    raw_payload_json            JSONB NOT NULL,
    raw_sensor_json             JSONB,
    decoded_payload_json        JSONB,

    api_user_id                 BIGINT REFERENCES smart_city_schema.api_users(id) ON DELETE SET NULL,
    api_endpoint                TEXT,
    http_status_code            INTEGER,

    parse_status                TEXT NOT NULL DEFAULT 'parsed',
    parse_error                 TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingest_events_ingested_at
    ON smart_city_schema.ingest_events (ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingest_events_event_time
    ON smart_city_schema.ingest_events (event_time DESC);

CREATE INDEX IF NOT EXISTS idx_ingest_events_node_id
    ON smart_city_schema.ingest_events (node_id);

CREATE INDEX IF NOT EXISTS idx_ingest_events_api_user_id
    ON smart_city_schema.ingest_events (api_user_id);

CREATE INDEX IF NOT EXISTS idx_ingest_events_raw_payload_gin
    ON smart_city_schema.ingest_events USING GIN (raw_payload_json);

CREATE INDEX IF NOT EXISTS idx_ingest_events_decoded_payload_gin
    ON smart_city_schema.ingest_events USING GIN (decoded_payload_json);

-- =========================================================
-- MAIN TIMESCALE MEASUREMENTS TABLE
-- Typed columns for analytics + JSON snapshot
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.environmental_measurements (
    measured_at                 TIMESTAMPTZ NOT NULL,
    id                          BIGSERIAL,

    ingest_id                   UUID REFERENCES smart_city_schema.ingest_events(id) ON DELETE SET NULL,
    node_id                     BIGINT NOT NULL REFERENCES smart_city_schema.nodes(id) ON DELETE RESTRICT,

    source_type                 TEXT NOT NULL CHECK (
        source_type IN ('raspberry_pi_api', 'arduino_lorawan', 'mqtt', 'other')
    ),

    received_at                 TIMESTAMPTZ,
    gateway_id                  BIGINT REFERENCES smart_city_schema.gateways(id) ON DELETE SET NULL,

    temperature_c               DOUBLE PRECISION,
    humidity_pct                DOUBLE PRECISION,

    bmp_temperature_c           DOUBLE PRECISION,
    pressure_hpa                DOUBLE PRECISION,

    uv_digital_raw              SMALLINT,
    uv_digital_state            TEXT,
    uv_raw                      INTEGER,
    uv_voltage                  DOUBLE PRECISION,
    uv_index_estimate           DOUBLE PRECISION,

    rain_digital_raw            SMALLINT,
    rain_digital_state          TEXT,
    rain_raw                    INTEGER,
    rain_voltage                DOUBLE PRECISION,
    rainfall_mm                 DOUBLE PRECISION,

    sound_raw                   INTEGER,
    sound_voltage               DOUBLE PRECISION,
    sound_index                 INTEGER,
    noise_db                    DOUBLE PRECISION,

    pm25_ug_m3                  DOUBLE PRECISION,
    pm10_ug_m3                  DOUBLE PRECISION,

    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    altitude_m                  DOUBLE PRECISION,

    water_temperature_c         DOUBLE PRECISION,
    ph                          DOUBLE PRECISION,
    turbidity                   DOUBLE PRECISION,
    conductivity                DOUBLE PRECISION,
    impurity                    DOUBLE PRECISION,
    dissolved_solids            DOUBLE PRECISION,

    rssi                        DOUBLE PRECISION,
    snr                         DOUBLE PRECISION,
    fcnt                        BIGINT,

    decoded_payload_json        JSONB,

    PRIMARY KEY (measured_at, id)
);

SELECT create_hypertable(
    'smart_city_schema.environmental_measurements',
    'measured_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_measurements_node_time
    ON smart_city_schema.environmental_measurements (node_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_measurements_gateway_time
    ON smart_city_schema.environmental_measurements (gateway_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_measurements_source_time
    ON smart_city_schema.environmental_measurements (source_type, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_measurements_received_at
    ON smart_city_schema.environmental_measurements (received_at DESC);

CREATE INDEX IF NOT EXISTS idx_measurements_pm25
    ON smart_city_schema.environmental_measurements (pm25_ug_m3);

CREATE INDEX IF NOT EXISTS idx_measurements_pm10
    ON smart_city_schema.environmental_measurements (pm10_ug_m3);

CREATE INDEX IF NOT EXISTS idx_measurements_temp
    ON smart_city_schema.environmental_measurements (temperature_c);

CREATE INDEX IF NOT EXISTS idx_measurements_payload_gin
    ON smart_city_schema.environmental_measurements USING GIN (decoded_payload_json);

CREATE UNIQUE INDEX IF NOT EXISTS uq_measurements_node_measured_at
    ON smart_city_schema.environmental_measurements (node_id, measured_at);

-- =========================================================
-- ALERTING TABLES
-- Nullable foreign keys because alert logic may be added later
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.alert_rules (
    id                          BIGSERIAL PRIMARY KEY,
    rule_name                   TEXT NOT NULL UNIQUE,
    parameter_name              TEXT NOT NULL,
    operator                    TEXT NOT NULL CHECK (
        operator IN ('>', '>=', '<', '<=', '=', '!=')
    ),
    threshold_value             DOUBLE PRECISION NOT NULL,
    severity                    TEXT NOT NULL DEFAULT 'medium',
    enabled                     BOOLEAN NOT NULL DEFAULT TRUE,
    notes                       TEXT
);

CREATE TABLE IF NOT EXISTS smart_city_schema.alerts (
    id                          BIGSERIAL PRIMARY KEY,

    node_id                     BIGINT REFERENCES smart_city_schema.nodes(id) ON DELETE SET NULL,
    rule_id                     BIGINT REFERENCES smart_city_schema.alert_rules(id) ON DELETE SET NULL,
    measurement_id              BIGINT,
    measured_at                 TIMESTAMPTZ,

    parameter_name              TEXT,
    measured_value              DOUBLE PRECISION,
    threshold_value             DOUBLE PRECISION,
    severity                    TEXT,

    status                      TEXT NOT NULL DEFAULT 'open' CHECK (
        status IN ('open', 'closed', 'acknowledged')
    ),
    message                     TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at                   TIMESTAMPTZ,
    meta                        JSONB
);

CREATE INDEX IF NOT EXISTS idx_alerts_node_time
    ON smart_city_schema.alerts (node_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_rule_id
    ON smart_city_schema.alerts (rule_id);

CREATE INDEX IF NOT EXISTS idx_alerts_status
    ON smart_city_schema.alerts (status);

-- =========================================================
-- ANOMALY / ML EVENTS
-- Nullable relations because ML/anomaly module may be added later
-- =========================================================

CREATE TABLE IF NOT EXISTS smart_city_schema.anomaly_events (
    id                          BIGSERIAL PRIMARY KEY,

    node_id                     BIGINT REFERENCES smart_city_schema.nodes(id) ON DELETE SET NULL,
    measurement_id              BIGINT,
    measured_at                 TIMESTAMPTZ,

    model_version               TEXT,
    anomaly_score               DOUBLE PRECISION,
    features_snapshot           JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes                       TEXT
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_node_time
    ON smart_city_schema.anomaly_events (node_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_features_gin
    ON smart_city_schema.anomaly_events USING GIN (features_snapshot);

-- =========================================================
-- TIMESCALE COMPRESSION
-- =========================================================

-- ALTER TABLE smart_city_schema.environmental_measurements
-- SET (
    -- timescaledb.compress,
    -- timescaledb.compress_segmentby = 'node_id'
-- );

-- SELECT add_compression_policy(
    -- 'smart_city_schema.environmental_measurements',
    -- INTERVAL '30 days',
    -- if_not_exists => TRUE
-- );

-- =========================================================
-- OPTIONAL RETENTION POLICY
-- Uncomment only if you want automatic deletion.
-- =========================================================

-- SELECT add_retention_policy(
--     'smart_city_schema.environmental_measurements',
--     INTERVAL '2 years',
--     if_not_exists => TRUE
-- );

-- =========================================================
-- OPTIONAL CONTINUOUS AGGREGATE
-- Uncomment later if needed for dashboards.
-- =========================================================

-- CREATE MATERIALIZED VIEW smart_city_schema.measurements_hourly
-- WITH (timescaledb.continuous) AS
-- SELECT
--     time_bucket('1 hour', measured_at) AS bucket,
--     node_id,
--     avg(temperature_c) AS avg_temperature_c,
--     avg(humidity_pct) AS avg_humidity_pct,
--     avg(pressure_hpa) AS avg_pressure_hpa,
--     avg(pm25_ug_m3) AS avg_pm25_ug_m3,
--     avg(pm10_ug_m3) AS avg_pm10_ug_m3,
--     avg(sound_index) AS avg_sound_index,
--     max(pm25_ug_m3) AS max_pm25_ug_m3,
--     max(pm10_ug_m3) AS max_pm10_ug_m3
-- FROM smart_city_schema.environmental_measurements
-- GROUP BY bucket, node_id;

-- =========================================================
-- EXAMPLE SEED DATA
-- Adapt as needed.
-- =========================================================

-- INSERT INTO smart_city_schema.cities (city_name)
-- VALUES ('Elbasan'), ('Tirana'), ('Durres')
-- ON CONFLICT DO NOTHING;
