# Optional existing ingestion service and Raspberry Pi integration

This folder is a **reference copy** of the ingestion project from the preceding delivery, not a second instance launched by the dashboard Docker Compose file. Deploy the existing ingestion service separately on its own API port; it owns writes to `smart_city_schema`.

The `raspberry_pi/` directory contains the previously regenerated acquisition script and unchanged method names, its original baseline, deployment workflow and optional MQTT helper. The helper is opt-in: call `publish_measurement(payload)` after `build_payload(data)` if you want the same payload delivered over MQTT as well as your ingestion API. A remote Pi needs a secured, reachable broker and configured city information.

Do **not** start both this project's web API and the ingestion reference using the same Django module path or host port without adjusting deployment configurations.
