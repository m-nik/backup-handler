import os
import tarfile
import datetime
import logging
import sys
import configparser
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client.exposition import basic_auth_handler
import boto3

# === Load config.ini ===
config = configparser.ConfigParser()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
config.read(CONFIG_FILE)

# === Configuration ===
SOURCE_DIR = config["backup"]["source_dir"]
BACKUP_DIR = config["backup"].get("backup_dir", "/tmp/backups")
BACKUP_NAME = config["backup"].get("backup_name", "backup")

# Retention
RETENTION_ENABLED = config.getboolean("retention", "enable", fallback=True)
RETAIN_FILE_COUNT = config.getint("retention", "retain_file_count", fallback=5)

# Logging
LOG_FILE = config["logging"]["log_file"]

# S3
ENABLE_S3_UPLOAD = config.getboolean("s3", "enabled", fallback=False)
S3_REGION = config["s3"].get("region")
S3_BUCKET = config["s3"].get("bucket")
S3_PREFIX = config["s3"].get("prefix", "")
S3_ACCESS_KEY = config["s3"].get("access_key")
S3_SECRET_KEY = config["s3"].get("secret_key")
S3_ENDPOINT = config["s3"].get("endpoint")

# Prometheus
ENABLE_METRICS = config.getboolean("metrics", "enabled", fallback=False)
PUSHGATEWAY_URL = config["metrics"].get("pushgateway_url")
PROM_JOB_NAME = config["metrics"].get("job_name", "backup_job")
PROM_INSTANCE = config["metrics"].get("instance", "localhost")
PROM_USERNAME = config["metrics"].get("username")
PROM_PASSWORD = config["metrics"].get("password")

# ==== Logging ====
logger = logging.getLogger("generic-backup")
logger.setLevel(logging.INFO)
log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

try:
    log_dir = os.path.dirname(LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
except Exception as e:
    print(f"[FATAL] Failed to create log directory '{log_dir}': {e}")
    sys.exit(1)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(log_format)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


status_dict = {}

def update_backup_status(status: str, message: str = "", value: int = 0):
    truncated_message = message[:100]
    key = (status, truncated_message)
    status_dict[key] = value


def push_all_statuses_to_prometheus():
    if not ENABLE_METRICS or not status_dict:
        return
    try:
        registry = CollectorRegistry()
        g = Gauge('backup_status', 'Status of backup job', ['status', 'message'], registry=registry)

        for (status, message), value in status_dict.items():
            g.labels(status=status, message=message).set(value)

        if PROM_USERNAME and PROM_PASSWORD:
            def handler(url, method, timeout, headers, data):
                return basic_auth_handler(url, method, timeout, headers, data, PROM_USERNAME, PROM_PASSWORD)
        else:
            handler = None

        push_to_gateway(
            PUSHGATEWAY_URL,
            job=PROM_JOB_NAME,
            grouping_key={'instance': PROM_INSTANCE},
            registry=registry,
            handler=handler
        )
        logger.info(f"📊 Prometheus Push: pushed {len(status_dict)} statuses")

        status_dict.clear()

    except Exception as e:
        logger.warning(f"⚠️ Failed to push to Prometheus: {e}")


def clean_old_backups():
    try:

        if not RETENTION_ENABLED:
            logger.info("Backup retention is disabled; no old files will be deleted.")
            update_backup_status("retention", "retention disabled")
            return

        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")],
            key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f))
        )
        logger.info(f"Found {len(backups)} backup files in {BACKUP_DIR}")

        if len(backups) <= RETAIN_FILE_COUNT:
            logger.info("No retention needed, within backup retention limit.")
            update_backup_status("retention", "no cleanup needed")
            return

        to_delete = backups[:len(backups) - RETAIN_FILE_COUNT]
        deleted_count = 0
        for f in to_delete:
            path = os.path.join(BACKUP_DIR, f)
            try:
                os.remove(path)
                logger.info(f"Deleted old backup: {f}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {f}: {e}")

        update_backup_status("retention", "old backups cleaned", value=deleted_count)

    except Exception as e:
        logger.warning(f"Could not clean old backups: {e}")


def main():
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create backup directory '{BACKUP_DIR}': {e}")
            sys.exit(1)

        backup_filename = f"{BACKUP_NAME}_{timestamp}.tar.gz"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        logger.info(f"========================")
        logger.info(f"Creating backup from: {SOURCE_DIR}")

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(SOURCE_DIR, arcname=os.path.basename(SOURCE_DIR))
        logger.info(f"Backup file created: {backup_path}")
        update_backup_status("backup", "backup succeeded", 1)

        if ENABLE_S3_UPLOAD:
            try:
                s3 = boto3.client(
                    "s3",
                    region_name=S3_REGION,
                    aws_access_key_id=S3_ACCESS_KEY,
                    aws_secret_access_key=S3_SECRET_KEY,
                    endpoint_url=S3_ENDPOINT
                )

                s3_key = f"{S3_PREFIX}{backup_filename}"
                s3.upload_file(backup_path, S3_BUCKET, s3_key)
                logger.info(f"☁️  Successfully uploaded to S3: s3://{S3_BUCKET}/{s3_key}")
                update_backup_status("upload", "upload succeeded", 1)
            except Exception as e:
                logger.exception(f"❌ S3 upload failed: {e}")
                update_backup_status("upload", str(e))
        else:
            logger.info("☁️  S3 upload is disabled (s3.enabled is false)")
            update_backup_status("upload", "S3 upload is disabled")

        clean_old_backups()
        push_all_statuses_to_prometheus()

    except Exception as e:
        logger.exception(f"Error during backup: {e}")
        push_all_statuses_to_prometheus()
        sys.exit(1)


if __name__ == "__main__":
    main()

