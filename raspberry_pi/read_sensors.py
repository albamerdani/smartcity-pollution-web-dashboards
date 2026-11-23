import os
import time
import json
import socket
import uuid
import platform
import subprocess
import sqlite3
import logging
import smtplib
import serial
from datetime import datetime
from zoneinfo import ZoneInfo
from logging.handlers import RotatingFileHandler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import smbus2
import RPi.GPIO as GPIO
import board
import busio
import adafruit_dht
import adafruit_bmp280
from pysds011 import driver

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ============================================================
# REQUIRED ENVIRONMENT VARIABLES
# ============================================================

REQUIRED_ENV_VARS = [
    "HOME_DIR",
    "NODE_NAME",
    "PLACE",
    "DESCRIPTION",
    "API_URL",
    "API_KEY",
    "EMAIL_FROM",
    "EMAIL_PASSWORD",
    "EMAIL_TO",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "CONN_CHECK_HOST",
    "CONN_CHECK_PORT",
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_vars:
    raise RuntimeError(
        "Missing required environment variables: " + ", ".join(missing_vars)
    )

# ============================================================
# ENV CONFIG
# ============================================================

HOME_DIR = os.environ["HOME_DIR"]

NODE_NAME = os.environ["NODE_NAME"]
PLACE = os.environ["PLACE"]
DESCRIPTION = os.environ["DESCRIPTION"]

API_URL = os.environ["API_URL"]
API_KEY = os.environ["API_KEY"]

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_SMTP_HOST = os.environ["EMAIL_SMTP_HOST"]
EMAIL_SMTP_PORT = int(os.environ["EMAIL_SMTP_PORT"])

CONN_CHECK_HOST = os.environ["CONN_CHECK_HOST"]
CONN_CHECK_PORT = int(os.environ["CONN_CHECK_PORT"])

# ============================================================
# FIXED PATHS BASED ON HOME_DIR
# ============================================================

APP_DIR = os.path.join(HOME_DIR, "env-monitor")
LOG_DIR = os.path.join(HOME_DIR, "env-monitor-logs")
DATA_DIR = os.path.join(HOME_DIR, "env-monitor-data")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# HARDCODED CONFIG
# ============================================================

API_HEADERS = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY
}

LOOP_SECONDS = 300
SCRIPT_VERSION = os.getenv("SCRIPT_VERSION", "2.1.0")
CITY = os.getenv("CITY", "")
COUNTRY = os.getenv("COUNTRY", "Albania")
LOCATION_NAME = os.getenv("LOCATION_NAME", PLACE)
optional_float = lambda key: float(os.environ[key]) if os.getenv(key) else None
LONGITUDE = optional_float("LONGITUDE")
LATITUDE = optional_float("LATITUDE")
ALTITUDE_M = optional_float("ALTITUDE_M")
GATEWAY_NAME = os.getenv("GATEWAY_NAME")
GATEWAY_EUI = os.getenv("GATEWAY_EUI")
NODE_EXTERNAL_ID = os.getenv("NODE_EXTERNAL_ID", NODE_NAME)
NODE_MODEL = os.getenv("NODE_MODEL", "Raspberry Pi")
FIRMWARE_VERSION = os.getenv("FIRMWARE_VERSION", "")
HOSTNAME = socket.gethostname()
LOCAL_TIMEZONE = ZoneInfo("Europe/Tirane")

BME280_ADDR = 0x76

UV_DO_PIN = 17
RAIN_DO_PIN = 27

DHT_PIN = board.D4

PCF8591_ADDR = 0x48
PCF8591_BUS = 1

ADC_RAIN_AO = 0
ADC_UV_AO = 1
ADC_SOUND_AO = 2

PM_PORT = "/dev/ttyUSB0"

VREF = 3.3

LOCAL_DB_PATH = os.path.join(DATA_DIR, "offline_buffer.db")
CSV_FILE = os.path.join(DATA_DIR, "sensor_data_v2.csv")

CONN_CHECK_TIMEOUT = 5

LOG_FILE = os.path.join(LOG_DIR, "sensor.log")
LOG_MAX_BYTES = 500_000
LOG_BACKUP_COUNT = 3

EMAIL_ENABLED = True
EMAIL_FAIL_THRESHOLD = 10
EMAIL_RESEND_MINUTES = 20


# ============================================================
# LOGGING
# ============================================================

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("sensor_monitor")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(message)s", "%H:%M:%S"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


log = setup_logger()


# ============================================================
# HARDWARE SETUP
# ============================================================

GPIO.setmode(GPIO.BCM)
GPIO.setup(UV_DO_PIN, GPIO.IN)
GPIO.setup(RAIN_DO_PIN, GPIO.IN)

dht = adafruit_dht.DHT11(DHT_PIN, use_pulseio=False)

i2c_bus = smbus2.SMBus(PCF8591_BUS)
i2c = busio.I2C(board.SCL, board.SDA)

try:
    bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=BME280_ADDR)
    log.info(f"BMP280  | initialized at address 0x{BME280_ADDR:02X}")
except Exception as e:
    bmp280 = None
    log.warning(f"BMP280  | not found, continuing without it: {e}")

pm_sensor = None
pm_serial = None
pm_log = logging.getLogger("pysds011")


# ============================================================
# TIME
# ============================================================

def get_local_timestamp() -> str:
    return datetime.now(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# CONNECTIVITY
# ============================================================

def is_connected() -> bool:
    try:
        socket.setdefaulttimeout(CONN_CHECK_TIMEOUT)
        with socket.create_connection((CONN_CHECK_HOST, CONN_CHECK_PORT)):
            return True
    except OSError:
        return False


# ============================================================
# EMAIL ALERTS
# ============================================================

def send_email_alert(consecutive_failures: int, last_status_code: int | None, pending_count: int):
    if not EMAIL_ENABLED:
        return

    now = get_local_timestamp()
    subject = f"[ALERT] {NODE_NAME} API failing ({consecutive_failures} consecutive errors)"

    body = (
        f"Smart Pollution Monitor — API Alert\n"
        f"{'-' * 50}\n\n"
        f"Node        : {NODE_NAME}\n"
        f"Place       : {PLACE}\n"
        f"Description : {DESCRIPTION}\n"
        f"Time        : {now}\n\n"
        f"The API has failed for {consecutive_failures} consecutive attempts.\n\n"
        f"Last HTTP status: {last_status_code if last_status_code else 'Connection failed'}\n"
        f"Buffered readings: {pending_count}\n\n"
        f"Data is stored locally in:\n"
        f"{LOCAL_DB_PATH}\n\n"
        f"API URL: {API_URL}\n"
    )

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        log.info(f"EMAIL   | alert sent to {EMAIL_TO}")

    except Exception as e:
        log.warning(f"EMAIL   | failed to send alert: {e}")


# ============================================================
# LOCAL SQLITE OFFLINE BUFFER
# ============================================================

def init_db():
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    log.info(f"DB      | local buffer ready -> {LOCAL_DB_PATH}")


def save_locally(payload: dict) -> int:
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.execute(
        "INSERT INTO pending_readings (timestamp, payload_json) VALUES (?, ?)",
        (payload["received_at"], json.dumps(payload))
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM pending_readings").fetchone()[0]
    conn.close()

    log.info(f"OFFLINE | reading buffered locally | total pending: {count}")
    return count


def flush_pending_data() -> int:
    conn = sqlite3.connect(LOCAL_DB_PATH)
    rows = conn.execute(
        "SELECT id, payload_json FROM pending_readings ORDER BY id ASC"
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    log.info(f"FLUSH   | replaying {len(rows)} buffered reading(s)")
    flushed = 0

    for row_id, payload_json in rows:
        payload = json.loads(payload_json)

        try:
            response = requests.post(API_URL, headers=API_HEADERS, json=payload, timeout=30)

            if response.status_code == 200:
                conn = sqlite3.connect(LOCAL_DB_PATH)
                conn.execute("DELETE FROM pending_readings WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()

                flushed += 1
                log.info(f"FLUSH   | row {row_id} sent and deleted ({flushed}/{len(rows)})")
            else:
                log.warning(f"FLUSH   | API returned {response.status_code}; stopping flush")
                break

        except requests.exceptions.RequestException as e:
            log.warning(f"FLUSH   | network error: {e}; stopping flush")
            break

    return flushed


# ============================================================
# SENSOR READERS
# ============================================================

def read_bmp280():
    if bmp280 is None:
        return None, None

    try:
        temperature = round(bmp280.temperature, 2)
        pressure = round(bmp280.pressure, 2)
        return temperature, pressure
    except Exception:
        return None, None


def read_pcf8591(channel: int) -> int | None:
    try:
        if channel not in (0, 1, 2, 3):
            raise ValueError("PCF8591 channel must be 0..3")

        control_byte = 0x40 | channel
        i2c_bus.write_byte(PCF8591_ADDR, control_byte)
        time.sleep(0.01)

        i2c_bus.read_byte(PCF8591_ADDR)
        return i2c_bus.read_byte(PCF8591_ADDR)

    except Exception as e:
        log.warning(f"ADC     | failed reading channel {channel}: {e}")
        return None


def adc_to_voltage(raw: int | None) -> float | None:
    if raw is None:
        return None
    return raw * (VREF / 255.0)


def read_dht11():
    try:
        temp_c = dht.temperature
        humidity = dht.humidity
        return temp_c, humidity
    except RuntimeError:
        return None, None
    except Exception:
        return None, None


def read_pm_values():
    global pm_sensor

    if pm_sensor is None:
        return None, None

    try:
        data = pm_sensor.cmd_query_data()
        if not data:
            return None, None

        return data.get("pm25"), data.get("pm10")

    except Exception:
        return None, None


# ============================================================
# SENSOR INTERPRETATION
# ============================================================

def approximate_uv_index(voltage: float | None) -> float | None:
    if voltage is None:
        return None
    if voltage < 0.4:
        return 0.0
    return round((voltage - 0.4) * 5.0, 2)


def approximate_sound_index(raw: int | None) -> int | None:
    if raw is None:
        return None
    return max(0, min(100, int((raw / 255.0) * 100)))


def rain_state_from_do(value: int) -> str:
    if value == 0:
        return "RAIN DETECTED"
    if value == 1:
        return "DRY"
    return "UNKNOWN"


def uv_state_from_do(value: int) -> str:
    if value == 0:
        return "UV ABOVE THRESHOLD"
    if value == 1:
        return "UV BELOW THRESHOLD"
    return "UNKNOWN"


# ============================================================
# READ ALL SENSORS
# ============================================================

def read_all_sensors() -> dict:
    uv_do = GPIO.input(UV_DO_PIN)
    rain_do = GPIO.input(RAIN_DO_PIN)

    rain_raw = read_pcf8591(ADC_RAIN_AO)
    uv_raw = read_pcf8591(ADC_UV_AO)
    sound_raw = read_pcf8591(ADC_SOUND_AO)

    rain_voltage = adc_to_voltage(rain_raw)
    uv_voltage = adc_to_voltage(uv_raw)
    sound_voltage = adc_to_voltage(sound_raw)

    temp_c, humidity = read_dht11()
    bmp_temp, bmp_pressure = read_bmp280()
    pm25, pm10 = read_pm_values()

    uv_index_est = approximate_uv_index(uv_voltage)
    sound_index = approximate_sound_index(sound_raw)

    return {
        "timestamp": get_local_timestamp(),
        "measured_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="microseconds"),
        "dht11": {
            "temperature_c": temp_c,
            "humidity_percent": humidity,
        },
        "uv": {
            "digital_raw": uv_do,
            "digital_state": uv_state_from_do(uv_do),
            "analog_raw": uv_raw,
            "analog_voltage": round(uv_voltage, 3) if uv_voltage is not None else None,
            "uv_index_estimate": uv_index_est,
        },
        "bmp280": {
            "temperature_c": bmp_temp,
            "pressure_hpa": bmp_pressure,
        },
        "rain": {
            "digital_raw": rain_do,
            "digital_state": rain_state_from_do(rain_do),
            "analog_raw": rain_raw,
            "analog_voltage": round(rain_voltage, 3) if rain_voltage is not None else None,
        },
        "sound": {
            "analog_raw": sound_raw,
            "analog_voltage": round(sound_voltage, 3) if sound_voltage is not None else None,
            "relative_sound_index_0_100": sound_index,
        },
        "pm": {
            "pm25_ug_m3": pm25,
            "pm10_ug_m3": pm10,
        },
    }


# ============================================================
# CSV BACKUP
# ============================================================

def save_to_csv(data: dict):
    file_exists = os.path.isfile(CSV_FILE)

    row = {
        "timestamp": data["timestamp"],
        "temperature_c": data["dht11"]["temperature_c"],
        "humidity_percent": data["dht11"]["humidity_percent"],
        "uv_digital_raw": data["uv"]["digital_raw"],
        "uv_digital_state": data["uv"]["digital_state"],
        "uv_analog_raw": data["uv"]["analog_raw"],
        "uv_analog_voltage": data["uv"]["analog_voltage"],
        "uv_index_estimate": data["uv"]["uv_index_estimate"],
        "rain_digital_raw": data["rain"]["digital_raw"],
        "rain_digital_state": data["rain"]["digital_state"],
        "rain_analog_raw": data["rain"]["analog_raw"],
        "rain_analog_voltage": data["rain"]["analog_voltage"],
        "sound_analog_raw": data["sound"]["analog_raw"],
        "sound_analog_voltage": data["sound"]["analog_voltage"],
        "sound_index": data["sound"]["relative_sound_index_0_100"],
        "pm25_ug_m3": data["pm"]["pm25_ug_m3"],
        "pm10_ug_m3": data["pm"]["pm10_ug_m3"],
        "pressure_hpa": data["bmp280"]["pressure_hpa"],
    }

    with open(CSV_FILE, "a", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ============================================================
# PAYLOAD
# ============================================================

def zero_if_none(value):
    return 0 if value is None else value


def build_payload(data: dict) -> dict:
    # The legacy envelope and keys are retained for existing downstream consumers.
    # Stable event ID is generated once here, then stored verbatim in the offline queue.
    measured_at = data.get("measured_at") or datetime.now(LOCAL_TIMEZONE).isoformat()
    readings = {
        "temperature_c": data["dht11"]["temperature_c"],
        "humidity_pct": data["dht11"]["humidity_percent"],
        "bmp_temperature_c": data["bmp280"]["temperature_c"],
        "pressure_hpa": data["bmp280"]["pressure_hpa"],
        "uv_digital_raw": data["uv"]["digital_raw"],
        "uv_digital_state": data["uv"]["digital_state"],
        "uv_raw": data["uv"]["analog_raw"],
        "uv_voltage": data["uv"]["analog_voltage"],
        "uv_index_estimate": data["uv"]["uv_index_estimate"],
        "rain_digital_raw": data["rain"]["digital_raw"],
        "rain_digital_state": data["rain"]["digital_state"],
        "rain_raw": data["rain"]["analog_raw"],
        "rain_voltage": data["rain"]["analog_voltage"],
        "rainfall_mm": None,  # sensor does not measure calibrated rainfall depth
        "sound_raw": data["sound"]["analog_raw"],
        "sound_voltage": data["sound"]["analog_voltage"],
        "sound_index": data["sound"]["relative_sound_index_0_100"],
        "noise_db": None,  # no calibrated decibel microphone
        "pm25_ug_m3": data["pm"]["pm25_ug_m3"],
        "pm10_ug_m3": data["pm"]["pm10_ug_m3"],
        "latitude": LATITUDE, "longitude": LONGITUDE, "altitude_m": ALTITUDE_M,
        "water_temperature_c": None, "ph": None, "turbidity": None,
        "conductivity": None, "impurity": None, "dissolved_solids": None,
        "rssi": None, "snr": None, "fcnt": None,  # HTTP is not LoRaWAN
    }
    decoded = {
        "place": PLACE, "description": DESCRIPTION,
        "altitude_m": ALTITUDE_M,
        "humidity_pct": readings["humidity_pct"],
        "pm10_ugm3": readings["pm10_ug_m3"],
        "pm25_ugm3": readings["pm25_ug_m3"],
        "pressure_hpa": readings["pressure_hpa"],
        "rain_raw": readings["rain_raw"],
        "sound_raw": readings["sound_raw"],
        "temperature_c": readings["temperature_c"],
        "uv_raw": readings["uv_raw"],
    }
    return {
        "event_id": str(uuid.uuid4()),
        "schema_version": "2.1",
        "source_type": "raspberry_pi_api",
        "end_device_ids": {"dev_eui": NODE_NAME, "join_eui": NODE_NAME, "dev_addr": NODE_NAME},
        "received_at": measured_at,  # compatible name, timezone-aware timestamp
        "event_time": measured_at,
        "sensor_timestamp_local": data["timestamp"],
        "sent_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="microseconds"),
        "node": {
            "node_name": NODE_NAME, "node_external_id": NODE_EXTERNAL_ID,
            "node_type": "raspberry_pi", "communication_type": "http_api",
            "microcontroller_model": NODE_MODEL, "script_version": SCRIPT_VERSION,
            "firmware_version": FIRMWARE_VERSION or None,
            "hostname": HOSTNAME, "os_release": platform.release(),
            "identical_sensor_suite": True,
        },
        "location": {
            "city_name": CITY or None, "country_name": COUNTRY,
            "location_name": LOCATION_NAME, "latitude": LATITUDE,
            "longitude": LONGITUDE, "elevation_m": ALTITUDE_M,
            "description": DESCRIPTION,
        },
        "gateway": ({"gateway_name": GATEWAY_NAME, "gateway_eui": GATEWAY_EUI,
                     "gateway_type": "http", "network_server": None}
                    if GATEWAY_NAME else None),
        "measurements": readings,
        "raw_sensor_data": data,
        "logs": {"capture_status": "completed", "logger_name": "sensor_monitor",
                 "captured_at": measured_at,
                 "unavailable_sensors": [name for name, values in (
                     ("dht11", (readings["temperature_c"], readings["humidity_pct"])),
                     ("bmp280", (readings["bmp_temperature_c"], readings["pressure_hpa"])),
                     ("sds011", (readings["pm25_ug_m3"], readings["pm10_ug_m3"])))
                     if all(value is None for value in values)]},
        "uplink_message": {"decoded_payload": decoded},
    }


# ============================================================
# API
# ============================================================

def send_to_api(payload: dict):
    try:
        response = requests.post(API_URL, headers=API_HEADERS, json=payload, timeout=30)

        if response.status_code == 200:
            dp = payload["uplink_message"]["decoded_payload"]
            log.info(
                f"SENT    | status=200 "
                f"| temp={dp['temperature_c']} "
                f"| hum={dp['humidity_pct']} "
                f"| pm25={dp['pm25_ugm3']} "
                f"| pm10={dp['pm10_ugm3']} "
                f"| place={dp['place']}"
            )
            return True, 200

        log.warning(f"SENT    | API error {response.status_code}: {response.text[:120]}")
        return False, response.status_code

    except requests.exceptions.RequestException as e:
        log.warning(f"SENT    | request failed: {e}")
        return False, None


# ============================================================
# PM INITIALIZATION
# ============================================================

def initialize_pm_sensor():
    global pm_sensor, pm_serial

    try:
        pm_serial = serial.Serial(PM_PORT, 9600, timeout=2)
        if not pm_serial.is_open:
            pm_serial.open()

        pm_sensor = driver.SDS011(pm_serial, pm_log)

        log.info("PM      | sensor initialized")
        log.info("PM      | waking up")
        pm_sensor.cmd_set_sleep(0)

        log.info("PM      | setting query mode")
        pm_sensor.cmd_set_mode(1)

        log.info("PM      | warming up for 30 seconds")
        time.sleep(30)

    except Exception as e:
        pm_sensor = None
        log.warning(f"PM      | sensor initialization failed, continuing without PM: {e}")


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    log.info("=" * 60)
    log.info("Smart Pollution Monitor starting")
    log.info(f"Node        : {NODE_NAME}")
    log.info(f"Place       : {PLACE}")
    log.info(f"Description : {DESCRIPTION}")
    log.info(f"Timezone    : {LOCAL_TIMEZONE}")
    log.info(f"Loop        : every {LOOP_SECONDS} seconds")
    log.info(f"API         : {API_URL}")
    log.info(f"App dir     : {APP_DIR}")
    log.info(f"Log dir     : {LOG_DIR}")
    log.info(f"Data dir    : {DATA_DIR}")
    log.info("=" * 60)

    init_db()
    initialize_pm_sensor()

    consecutive_failures = 0
    last_alert_time = None
    last_status_code = None
    was_online = None

    try:
        while True:
            online = is_connected()

            if online and was_online is False:
                log.info("NET     | connection restored")
                flush_pending_data()
                consecutive_failures = 0
                last_status_code = None

            data = read_all_sensors()
            log.info(
                "SENSORS | %s",
                json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            )
            save_to_csv(data)

            payload = build_payload(data)

            if online:
                success, status_code = send_to_api(payload)

                if success:
                    consecutive_failures = 0
                    last_status_code = None
                else:
                    consecutive_failures += 1
                    last_status_code = status_code
                    buffered = save_locally(payload)
                    online = False

                    log.warning(
                        f"ALERT   | consecutive API failures: "
                        f"{consecutive_failures}/{EMAIL_FAIL_THRESHOLD}"
                    )

                    if consecutive_failures >= EMAIL_FAIL_THRESHOLD:
                        now = datetime.now(LOCAL_TIMEZONE)
                        should_send = (
                            last_alert_time is None
                            or (now - last_alert_time).total_seconds()
                            >= EMAIL_RESEND_MINUTES * 60
                        )

                        if should_send:
                            send_email_alert(consecutive_failures, last_status_code, buffered)
                            last_alert_time = now

            else:
                log.info("NET     | offline, storing reading locally")
                save_locally(payload)

            was_online = online
            time.sleep(LOOP_SECONDS)

    except KeyboardInterrupt:
        log.info("Monitor stopped by user")

    finally:
        GPIO.cleanup()
        i2c_bus.close()

        try:
            dht.exit()
        except Exception:
            pass

        try:
            if pm_serial and pm_serial.is_open:
                pm_serial.close()
        except Exception:
            pass

        log.info("Cleanup done. Goodbye.")


if __name__ == "__main__":
    main()
