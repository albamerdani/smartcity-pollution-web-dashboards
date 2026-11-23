# SmartCity Environmental Web Dashboard

A **Python 3.12 / Django 6.1.3 / Django REST Framework** read-only public dashboard backend, **Vue 3** frontend (refactored from your uploaded project), **OpenStreetMap + Leaflet**, **PostgreSQL 16 + TimescaleDB**, **MQTT**, Redis and the uploaded `ml_forecast` project. **Albanian and English**. Django follows models / services / views / serializers / URLs separation (MVC-like Django MTV).

## Architecture

```text
Raspberry Pi (existing read_sensors.py)
  | POST existing ingestion API --> PostgreSQL 16 / TimescaleDB
  | optional MQTT publish --------> Mosquitto -> listener -> Redis live cache
                                                       |
PostgreSQL -------------------> Django DRF API <-------+
    |                                  |                 
    +--> scheduled ML worker ----------+--> Redis forecasts
                                       |
Vue frontend <-- nginx /api proxy -----+ --> OpenStreetMap tiles
```

**Important:** this web service does **not** replace or duplicate your Django ingestion service. It reads its PostgreSQL schema directly. The MQTT listener accepts JSON events into Redis for near-live display and refresh triggers; the historical database remains the authoritative measurement store. MQTT events **do not automatically write to TimescaleDB**, which requires the existing ingestion API. Real-time polling occurs every 30 seconds for the 'Now' view; model inference runs at a configurable cadence (default 300s), not on every event.

## Setup

1. Ensure the original ingestion service database and `smart_city_schema` exist. Verify `cities`, `locations`, `nodes`, `environmental_measurements` and that nodes have valid location/city foreign keys and coordinates.
2. Copy `config/.env.example` to `.env`; set a strong `DJANGO_SECRET_KEY`, PostgreSQL host/credentials, `DJANGO_ALLOWED_HOSTS`, and domain-specific CORS origins.
3. Run `docker compose up -d --build`.
4. Run `docker compose exec api python manage.py migrate` to create **Django auth/admin/session tables in public only** (legacy TimescaleDB measurements remain unmanaged).
5. Create staff user: `docker compose exec api python manage.py createsuperuser` and sign in using the public site's **Administrator login** button.
6. Visit `http://localhost:8080` (public); `http://localhost:8080/api/docs/` (OpenAPI Swagger), `/django-admin/` through API port only if exposed directly.

Use local override if desired: `docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`. The production Compose **does not publish the database or Redis**, but the web port is public by default.

### Existing PostgreSQL privileges

Provision a dedicated PostgreSQL role. It requires `CONNECT` to the existing DB; `USAGE` on `smart_city_schema`; `SELECT` on `smart_city_schema.cities`, `locations`, `nodes`, and `environmental_measurements`; and privileges to create/manage Django's standard auth/admin tables in **public**. For stricter separation, use separate database credentials/roles and a Django auth database. The shipped project uses a single database role, so do not grant it writes to existing measurement tables.

```sql
GRANT USAGE ON SCHEMA smart_city_schema TO smartcity_dashboard;
GRANT SELECT ON smart_city_schema.cities, smart_city_schema.locations,
 smart_city_schema.nodes, smart_city_schema.environmental_measurements TO smartcity_dashboard;
```

**Do not run migrations that create legacy schema tables**: their Django models are `managed=False`. User's original schema has an invalid `environmental_measurements(gateway_id)` index if that column is missing; repair the original schema separately before ingestion.

## Public API

- `GET /api/health/`: DB readiness.
- `GET /api/overview/`: recent reporting nodes.
- `GET /api/map/?window=now&param=pm25`: most recent valid reading per node within the selected period.
- `GET /api/trends/?window=week&param=pm25&city=Elbasan`: hourly averaged measured values.
- `POST /api/login/` `{ "username": "admin", "password": "..." }`: staff-only JWT token pair.
- `POST /api/login/refresh/`: JWT refresh.
- `GET /api/forecasts/` or `POST /api/forecasts/` `{ "city":"Tirana", "horizon_hours":24 }`: staff-only model computation (bounded 1–72 hours).
- `GET /api/schema/`, `/api/docs/`: OpenAPI schema/Swagger.

Period codes: `month`, `2weeks`, `week`, `3days`, `2days`, `day`, `3hours`, `now` (20-minute freshness lookback). Parameters: `pm25`, `pm10`, `temperature`, `humidity`, `pressure`, `uv`, `noise`. Readings without selected parameter are not converted to zero. `now` can display MQTT-only measurements if that node has no DB measurement in the selected 20-minute window. The other periods are DB-only. For historical periods the map shows **the latest measurement inside that period**, not a time-machine snapshot at an exact past date.

## Map zones and safety of interpretation

The map uses OpenStreetMap tiles and Leaflet station circles of ~1.4 km. Green/yellow/orange/red encode **configurable illustrative** bands, not regulatory compliance zones, ground-truth spatial interpolation, AQI, or official WHO thresholds. Temperature breakpoints are `<10`, `10–25`, `25–32`, `>=32°C`; PM2.5 breakpoints are `<10`, `10–25`, `25–50`, `>=50 µg/m³`; PM10 breakpoints are `<20`, `20–50`, `50–100`, `>=100 µg/m³`. Actual station GPS locations come only from database coordinates or an MQTT payload; missing coordinates are not assigned fabricated station positions. Map includes reference city context centers for Tirana, Elbasan and Korça.

## MQTT

Topic default: `smartcity/nodes/+/measurements`. Publish the same JSON object produced by the extended Raspberry Pi payload, **including** `node_name` or `end_device_ids.dev_eui`, and `city` / `city_name` / city-recognizable `decoded_payload.place`. Example:

```bash
mosquitto_pub -h 127.0.0.1 -t smartcity/nodes/elb_1/measurements -m '{"node_name":"elb_1","city":"Elbasan","received_at":"2026-11-23T13:00:00Z","uplink_message":{"decoded_payload":{"pm25_ugm3":18.2,"temperature_c":16.4}}}'
```

Default broker permits anonymous MQTT but is **bound to loopback on the VM**, so remote Pis cannot connect. For distributed devices configure a private VPN endpoint, password ACLs and TLS on your own broker; update `MQTT_HOST`, ports, credentials and topic. Never expose anonymous MQTT to the Internet. If the device publishes only GPS and no canonical city field, configure its city field before use.

## ML predictions

Uploaded `ml_forecast/src`, `config`, `artifacts` and `scripts` are retained. `forecast_worker` loads history from TimescaleDB, adapts it to the model's **original 16-column** training schema, checks the model/manifest checksum and code fingerprint, and attempts verified inference. The original model expects known device IDs, enough data history, valid timestamps, and its original model dependencies; its supplied manifest code fingerprint did not validate against its supplied source tree in this environment. When the archived model cannot execute, a **separate adaptive HistGradientBoosting model** can train on recent valid hourly history, labelled `ml_adaptive`. Only when this also lacks sufficient history does the API return an explicitly labelled persistence baseline. The uploaded archived model currently fails its original source-code fingerprint check, so expect the adaptive model until an aligned artifact is retrained. Worker outputs are shared with the admin endpoint and optionally overlaid on the public map with the Observed/Predicted selector. The forecast option is only available when the scheduled worker has produced cached forecasts; it is never the same as historical observations. `ml_forecast` trained artifact dates from August 2026 and training data ends June 2026; assess distribution shift and retrain before relying on it operationally. Joblib artifacts are executable deserialization; use only trusted files and verify independent supply-chain signatures for production.

## Directory layout

- `backend/config/` settings, REST urls, WSGI
- `backend/monitoring/models.py` unmanaged legacy models
- `backend/monitoring/services/` SQL, forecast bridge, MQTT normalization
- `backend/monitoring/views.py` + `serializers.py` DRF controllers and validation
- `backend/monitoring/management/commands/` live MQTT and prediction worker
- `frontend/` uploaded Vue/Leaflet design refactored to real data, bilingual pages
- `ml_forecast/` uploaded model, config, source, scripts and signed-by-manifest hash (hash is **not** a signature)
- `raspberry_pi/` earlier regenerated acquisition script and opt-in MQTT publish helper
- `integrations/existing_ingestion_service/` preserved earlier Django ingestion service source (not started automatically)
- `config/` MQTT + environment examples
- `.github/workflows/deploy.yml` CI build and SSH/rsync Compose deployment

## Testing / operations

```bash
python -m compileall -q backend ml_forecast
cd frontend && npm ci && npm run build
# With installed backend requirements and a reachable DB:
cd ../backend && python manage.py check && python manage.py test monitoring.tests
# Container smoke checks:
cd .. && docker compose logs -f api mqtt-listener forecast-worker
curl -f http://localhost:8080/api/health/
```

CI verifies frontend build, Python syntax and image build. GitHub secrets: `VM_HOST`, `VM_USER`, `VM_SSH_KEY`; production VM needs its own `/opt/smartcity-web/.env`, Docker Compose, SSH/rsync permissions and a Postgres route. Deployment updates source and runs `migrate`/`check`. Use a reverse proxy and HTTPS, firewall, secure MQTT broker, audited PostgreSQL role, backup and monitoring before public deployment.

## Limits

No real VM/TimescaleDB, Raspberry Pi MQTT feed or full Docker runtime was provided in this conversation, so they cannot be certified end-to-end here. The original frontend synthetic replay sources are retained as unused reference modules; the active boot path does not import them or fall back to fabricated observations. Live forecast accuracy requires representative ongoing data, data quality checks, and measured validation.

one MQTT broker on the VM, one shared PostgreSQL/TimescaleDB instance, three GitHub repositories, and separate Docker Compose deployments for ingestion and dashboard services. This keeps ownership clear, avoids duplicate database writes, and lets you evolve real-time analytics independently of sensor collection.

6. Final implementation checklist
Implementation progress

0 / 25 completed



Raspberry Pi repo
0/6
[ ] Move mqtt_publish_helper.py into the existing Pi repository
[ ] Add MQTT settings to each node's .env
[ ] Implement authenticated TLS publishing and reconnect behavior
[ ] Publish the same event ID and payload through MQTT and HTTP
[ ] Preserve existing SQLite buffering and HTTP ingestion
[ ] Update Raspberry Pi GitHub Actions deployment


Ingestion service repo
0/5
[ ] Keep the ingestion API separate from the dashboard
[ ] Verify city, location and node database relationships
[ ] Persist actual GPS coordinates and timestamps
[ ] Add event idempotency and missing-value handling
[ ] Grant the dashboard read-only measurement permissions


Web dashboard repo
0/9
[ ] Remove raspberry_pi/ and integrations/existing_ingestion_service/
[ ] Select one central MQTT broker and secure it
[ ] Configure the dashboard MQTT listener to subscribe to that broker
[ ] Prefer fresh MQTT readings over stale DB values in the Now view
[ ] Integrate live MQTT data into ML forecasting inputs
[ ] Implement event-triggered or debounced ML forecast refresh
[ ] Separate historical snapshots from lookback-window queries
[ ] Verify admin login, public dashboards and bilingual pages
[ ] Update Docker Compose, .env and GitHub Actions


End-to-end validation
0/5
[ ] Verify sensor → ingestion API → TimescaleDB
[ ] Verify sensor → MQTT → Redis → live dashboard
[ ] Verify database + recent MQTT → ML forecast → frontend
[ ] Check offline recovery, duplicates, stale events and reconnects
[ ] Test all four deployed nodes and all three city views

 Copy checklist
7. Recommended deployment order
Deploy and test the applications in this sequence:
1. PostgreSQL and ingestion service — verify that environmental measurements are correctly persisted.
2. MQTT broker — configure authentication, TLS and network access.
3. Raspberry Pi nodes — enable MQTT publishing while retaining HTTP.
4. Web dashboard — connect Django to PostgreSQL and its MQTT listener to the broker.
5. ML forecasting service — integrate live inputs, retrain or validate models, and verify predictions.
6. GitHub Actions — automate independent deployments after tests pass.