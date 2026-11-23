from django.db import models

# Existing PostgreSQL tables: unmanaged to avoid ORM DDL on Timescale hypertables.

class ApiUsers(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.TextField(null=True, blank=True, unique=True)
    full_name = models.TextField(null=True, blank=True)
    email = models.TextField(null=True, blank=True, unique=True)
    token_hash = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."api_users"'

class Cities(models.Model):
    id = models.BigAutoField(primary_key=True)
    city_name = models.TextField(null=True, blank=True, unique=True)
    country_name = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."cities"'

class Locations(models.Model):
    id = models.BigAutoField(primary_key=True)
    city_id = models.BigIntegerField(null=True, blank=True)
    location_name = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    elevation_m = models.FloatField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."locations"'

class Gateways(models.Model):
    id = models.BigAutoField(primary_key=True)
    gateway_name = models.TextField(null=True, blank=True, unique=True)
    gateway_eui = models.TextField(null=True, blank=True)
    location_id = models.BigIntegerField(null=True, blank=True)
    gateway_type = models.TextField(null=True, blank=True)
    network_server = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."gateways"'

class Nodes(models.Model):
    id = models.BigAutoField(primary_key=True)
    node_name = models.TextField(null=True, blank=True, unique=True)
    node_external_id = models.TextField(null=True, blank=True)
    node_type = models.TextField(null=True, blank=True)
    communication_type = models.TextField(null=True, blank=True)
    location_id = models.BigIntegerField(null=True, blank=True)
    gateway_id = models.BigIntegerField(null=True, blank=True)
    microcontroller_model = models.TextField(null=True, blank=True)
    firmware_version = models.TextField(null=True, blank=True)
    script_version = models.TextField(null=True, blank=True)
    network_server = models.TextField(null=True, blank=True)
    identical_sensor_suite = models.BooleanField(null=True, blank=True)
    active = models.BooleanField(null=True, blank=True)
    installed_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."nodes"'

class IngestEvents(models.Model):
    id = models.UUIDField(primary_key=True)
    ingested_at = models.DateTimeField(null=True, blank=True)
    node_id = models.BigIntegerField(null=True, blank=True)
    node_name = models.TextField(null=True, blank=True)
    node_external_id = models.TextField(null=True, blank=True)
    source_type = models.TextField(null=True, blank=True)
    event_time = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_at_text = models.TextField(null=True, blank=True)
    gateway_id = models.BigIntegerField(null=True, blank=True)
    rssi = models.FloatField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    fcnt = models.BigIntegerField(null=True, blank=True)
    raw_payload_json = models.JSONField(null=True, blank=True)
    raw_sensor_json = models.JSONField(null=True, blank=True)
    decoded_payload_json = models.JSONField(null=True, blank=True)
    api_user_id = models.BigIntegerField(null=True, blank=True)
    api_endpoint = models.TextField(null=True, blank=True)
    http_status_code = models.IntegerField(null=True, blank=True)
    parse_status = models.TextField(null=True, blank=True)
    parse_error = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."ingest_events"'

class EnvironmentalMeasurements(models.Model):
    measured_at = models.DateTimeField(null=True, blank=True)
    id = models.BigAutoField(primary_key=True)
    ingest_id = models.UUIDField(null=True, blank=True)
    node_id = models.BigIntegerField(null=True, blank=True)
    source_type = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    temperature_c = models.FloatField(null=True, blank=True)
    humidity_pct = models.FloatField(null=True, blank=True)
    bmp_temperature_c = models.FloatField(null=True, blank=True)
    pressure_hpa = models.FloatField(null=True, blank=True)
    uv_digital_raw = models.SmallIntegerField(null=True, blank=True)
    uv_digital_state = models.TextField(null=True, blank=True)
    uv_raw = models.IntegerField(null=True, blank=True)
    uv_voltage = models.FloatField(null=True, blank=True)
    uv_index_estimate = models.FloatField(null=True, blank=True)
    rain_digital_raw = models.SmallIntegerField(null=True, blank=True)
    rain_digital_state = models.TextField(null=True, blank=True)
    rain_raw = models.IntegerField(null=True, blank=True)
    rain_voltage = models.FloatField(null=True, blank=True)
    rainfall_mm = models.FloatField(null=True, blank=True)
    sound_raw = models.IntegerField(null=True, blank=True)
    sound_voltage = models.FloatField(null=True, blank=True)
    sound_index = models.IntegerField(null=True, blank=True)
    noise_db = models.FloatField(null=True, blank=True)
    pm25_ug_m3 = models.FloatField(null=True, blank=True)
    pm10_ug_m3 = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    altitude_m = models.FloatField(null=True, blank=True)
    water_temperature_c = models.FloatField(null=True, blank=True)
    ph = models.FloatField(null=True, blank=True)
    turbidity = models.FloatField(null=True, blank=True)
    conductivity = models.FloatField(null=True, blank=True)
    impurity = models.FloatField(null=True, blank=True)
    dissolved_solids = models.FloatField(null=True, blank=True)
    rssi = models.FloatField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    fcnt = models.BigIntegerField(null=True, blank=True)
    decoded_payload_json = models.JSONField(null=True, blank=True)
    gateway_id = models.BigIntegerField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."environmental_measurements"'

class AlertRules(models.Model):
    id = models.BigAutoField(primary_key=True)
    rule_name = models.TextField(null=True, blank=True, unique=True)
    parameter_name = models.TextField(null=True, blank=True)
    operator = models.TextField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    severity = models.TextField(null=True, blank=True)
    enabled = models.BooleanField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."alert_rules"'

class Alerts(models.Model):
    id = models.BigAutoField(primary_key=True)
    node_id = models.BigIntegerField(null=True, blank=True)
    rule_id = models.BigIntegerField(null=True, blank=True)
    measurement_id = models.BigIntegerField(null=True, blank=True)
    measured_at = models.DateTimeField(null=True, blank=True)
    parameter_name = models.TextField(null=True, blank=True)
    measured_value = models.FloatField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    severity = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."alerts"'

class AnomalyEvents(models.Model):
    id = models.BigAutoField(primary_key=True)
    node_id = models.BigIntegerField(null=True, blank=True)
    measurement_id = models.BigIntegerField(null=True, blank=True)
    measured_at = models.DateTimeField(null=True, blank=True)
    model_version = models.TextField(null=True, blank=True)
    anomaly_score = models.FloatField(null=True, blank=True)
    features_snapshot = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = '"smart_city_schema"."anomaly_events"'
